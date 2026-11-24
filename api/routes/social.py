"""
Likes and comments on any feed item.

A feed item is identified by (target_type, target_id):
    post      a wall post
    song      a published song (likes stay in song_likes, see likes.py)
    story     a music clip / story
    activity  a profile change (new photo, moved, visited, bio, genres)

POST   /feed-likes/{type}/{id}        like (post | story | activity)
DELETE /feed-likes/{type}/{id}        unlike
GET    /comments/{type}/{id}          comments, oldest first, paged with `before`
POST   /comments/{type}/{id}          add a comment
DELETE /comments/{comment_id}         delete (its author or the item's owner)

Blocks work both ways: you can't like or comment on the items of someone you
blocked or who blocked you, and you don't see each other's comments.
"""
from datetime import datetime
from typing import Dict, Iterable, Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from db.models import Activity, Comment, FeedLike, MusicStory, Song, User, WallPost
from db.session import get_db
from services.auth_service import get_current_user
from services.moderation import hidden_user_ids, is_blocked_between
from services.push import notify, _display

router = APIRouter(tags=["social"])

TARGETS = {"post", "song", "story", "activity"}
LIKE_TARGETS = {"post", "story", "activity"}
MAX_COMMENT_CHARS = 500

Key = Tuple[str, str]


def target_owner(db: Session, target_type: str, target_id: str, me: Optional[User]) -> str:
    """Owner id of a visible feed item, or 404."""
    owner = None
    if target_type == "post":
        row = db.query(WallPost.author_id).filter(WallPost.id == target_id, WallPost.deleted_at.is_(None)).first()
        owner = row[0] if row else None
    elif target_type == "song":
        row = db.query(Song.user_id, Song.is_public).filter(Song.id == target_id).first()
        if row and (row[1] or (me and row[0] == me.id)):
            owner = row[0]
    elif target_type == "story":
        row = db.query(MusicStory.user_id).filter(MusicStory.id == target_id).first()
        owner = row[0] if row else None
    elif target_type == "activity":
        row = db.query(Activity.actor_id).filter(Activity.id == target_id).first()
        owner = row[0] if row else None
    if owner is None or (me and is_blocked_between(db, me.id, owner)):
        raise HTTPException(status_code=404, detail="Not found")
    return owner


def social_info(db: Session, keys: Iterable[Key], me: Optional[User]) -> Dict[Key, dict]:
    """{(type, id): {like_count, liked, comment_count}} for many items in a few queries.
    like_count/liked are only filled for LIKE_TARGETS (songs have their own)."""
    keys = list({k for k in keys if k and k[1]})
    if not keys:
        return {}
    out = {k: {"comment_count": 0} for k in keys}
    hidden = hidden_user_ids(db, me.id if me else None)

    by_type: Dict[str, list] = {}
    for t, i in keys:
        by_type.setdefault(t, []).append(i)

    for t, ids in by_type.items():
        cq = db.query(Comment.target_id, func.count()).filter(
            Comment.target_type == t, Comment.target_id.in_(ids), Comment.deleted_at.is_(None))
        if hidden:
            cq = cq.filter(Comment.author_id.notin_(hidden))
        for tid, n in cq.group_by(Comment.target_id):
            out[(t, tid)]["comment_count"] = n

        if t in LIKE_TARGETS:
            counts = dict(db.query(FeedLike.target_id, func.count()).filter(
                FeedLike.target_type == t, FeedLike.target_id.in_(ids)).group_by(FeedLike.target_id))
            mine = set()
            if me:
                mine = {tid for (tid,) in db.query(FeedLike.target_id).filter(
                    FeedLike.user_id == me.id, FeedLike.target_type == t, FeedLike.target_id.in_(ids))}
            for tid in ids:
                out[(t, tid)]["like_count"] = counts.get(tid, 0)
                out[(t, tid)]["liked"] = tid in mine
    return out


def _check_type(target_type: str, allowed=TARGETS):
    if target_type not in allowed:
        raise HTTPException(status_code=400, detail="Unknown target")


def _like_count(db: Session, target_type: str, target_id: str) -> int:
    return db.query(func.count()).select_from(FeedLike).filter(
        FeedLike.target_type == target_type, FeedLike.target_id == target_id).scalar() or 0


@router.post("/feed-likes/{target_type}/{target_id}")
def like_item(target_type: str, target_id: str, me: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _check_type(target_type, LIKE_TARGETS)
    owner = target_owner(db, target_type, target_id, me)
    exists = db.query(FeedLike).filter(
        FeedLike.user_id == me.id, FeedLike.target_type == target_type, FeedLike.target_id == target_id).first()
    if not exists:
        db.add(FeedLike(user_id=me.id, target_type=target_type, target_id=target_id))
        db.commit()
        if owner != me.id:
            notify(db, owner, "feed_like",
                   {"type": "feed_like", "target_type": target_type, "target_id": target_id, "user_id": me.id},
                   name=_display(me))
    return {"liked": True, "like_count": _like_count(db, target_type, target_id)}


@router.delete("/feed-likes/{target_type}/{target_id}")
def unlike_item(target_type: str, target_id: str, me: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _check_type(target_type, LIKE_TARGETS)
    db.query(FeedLike).filter(
        FeedLike.user_id == me.id, FeedLike.target_type == target_type, FeedLike.target_id == target_id,
    ).delete(synchronize_session=False)
    db.commit()
    return {"liked": False, "like_count": _like_count(db, target_type, target_id)}


def _comment_dict(c: Comment, me: User, owner_id: str) -> dict:
    u = c.author
    return {
        "id": c.id,
        "content": c.content,
        "created_at": c.created_at.isoformat(),
        "author": {"id": u.id, "username": u.username, "display_name": u.display_name,
                   "avatar_url": u.avatar_url, "country_code": u.country_code},
        "can_delete": me.id in (c.author_id, owner_id),
        "is_mine": me.id == c.author_id,
    }


@router.get("/comments/{target_type}/{target_id}")
def list_comments(
    target_type: str,
    target_id: str,
    before: Optional[datetime] = Query(None, description="Cursor: created_at of the oldest comment seen"),
    limit: int = Query(30, ge=1, le=100),
    me: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _check_type(target_type)
    owner = target_owner(db, target_type, target_id, me)
    q = db.query(Comment).options(joinedload(Comment.author)).filter(
        Comment.target_type == target_type, Comment.target_id == target_id, Comment.deleted_at.is_(None))
    hidden = hidden_user_ids(db, me.id)
    if hidden:
        q = q.filter(Comment.author_id.notin_(hidden))
    if before is not None:
        q = q.filter(Comment.created_at < before)
    rows = q.order_by(Comment.created_at.desc()).limit(limit + 1).all()
    has_more = len(rows) > limit
    rows = rows[:limit]
    return {
        "items": [_comment_dict(c, me, owner) for c in reversed(rows)],  # oldest first
        "has_more": has_more,
        "next_before": rows[-1].created_at.isoformat() if has_more and rows else None,
        "owner_id": owner,
    }


class CommentRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=MAX_COMMENT_CHARS)


@router.post("/comments/{target_type}/{target_id}", status_code=201)
def add_comment(target_type: str, target_id: str, req: CommentRequest,
                me: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _check_type(target_type)
    text = req.content.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Empty comment")
    owner = target_owner(db, target_type, target_id, me)
    c = Comment(target_type=target_type, target_id=target_id, target_owner_id=owner, author_id=me.id, content=text)
    db.add(c)
    db.commit()
    db.refresh(c)
    if owner != me.id:
        preview = text if len(text) <= 120 else text[:117] + "..."
        notify(db, owner, "comment",
               {"type": "comment", "target_type": target_type, "target_id": target_id, "user_id": me.id},
               name=_display(me), text=preview)
    return _comment_dict(c, me, owner)


@router.delete("/comments/{comment_id}")
def delete_comment(comment_id: str, me: User = Depends(get_current_user), db: Session = Depends(get_db)):
    c = db.query(Comment).filter(Comment.id == comment_id, Comment.deleted_at.is_(None)).first()
    if not c:
        raise HTTPException(status_code=404, detail="Not found")
    if me.id not in (c.author_id, c.target_owner_id):
        raise HTTPException(status_code=403, detail="Not allowed")
    c.deleted_at = datetime.utcnow()
    db.commit()
    return {"deleted": True}
