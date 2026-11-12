"""
Profile walls (Twitter-like posts on a user's profile).

Rules (the API enforces them; the app only hides buttons):
- Anyone can read any wall (profiles are public, see songs.can_view_profile).
- You can always post on your own wall; on someone else's only if you're friends.
- Text up to 280 characters, a song of your own, or both.
- Anyone can be mentioned (found by searching their name).
- The author or the wall owner can delete a post (soft delete).
"""
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session, joinedload

from api.routes.songs import can_view_profile
from db.models import Friendship, FriendshipStatus, PostMention, Song, User, WallPost
from db.session import get_db
from services.auth_service import get_current_user, get_optional_user

router = APIRouter(tags=["wall"])

MAX_POST_CHARS = 280
MAX_MENTIONS = 10


class CreatePostRequest(BaseModel):
    content: Optional[str] = Field(None, max_length=MAX_POST_CHARS)
    song_id: Optional[str] = None
    mention_ids: List[str] = Field(default_factory=list, max_length=MAX_MENTIONS)


def _friend_ids(db: Session, user_id: str) -> set:
    rows = db.query(Friendship.requester_id, Friendship.addressee_id).filter(
        Friendship.status == FriendshipStatus.accepted,
        (Friendship.requester_id == user_id) | (Friendship.addressee_id == user_id),
    ).all()
    return {a if b == user_id else b for a, b in rows}


def _mini_user(u: User) -> dict:
    return {
        "id": u.id,
        "username": u.username,
        "display_name": u.display_name,
        "avatar_url": u.avatar_url,
    }


def _post_dict(post: WallPost, viewer: Optional[User]) -> dict:
    song = None
    if post.song:
        song = {
            "id": post.song.id,
            "title": post.song.title,
            "audio_url": post.song.audio_url,
            "cover_art_url": post.song.cover_art_url,
            "genre": post.song.genre,
            "duration": post.song.duration,
        }
    viewer_id = viewer.id if viewer else None
    return {
        "id": post.id,
        "content": post.content,
        "created_at": post.created_at.isoformat(),
        "author": _mini_user(post.author),
        "wall_owner": _mini_user(post.wall_owner),
        "song": song,
        "mentions": [_mini_user(m.mentioned_user) for m in post.mentions],
        "can_delete": viewer_id in (post.author_id, post.wall_owner_id),
    }


def _load_posts_query(db: Session):
    return db.query(WallPost).options(
        joinedload(WallPost.author),
        joinedload(WallPost.wall_owner),
        joinedload(WallPost.song),
        joinedload(WallPost.mentions).joinedload(PostMention.mentioned_user),
    )


@router.get("/users/{user_id}/wall")
def get_wall(
    user_id: str,
    before: Optional[datetime] = Query(None, description="Cursor: created_at of the last post seen"),
    limit: int = Query(20, ge=1, le=50),
    current_user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    owner = db.query(User).filter(User.id == user_id).first()
    if not owner:
        raise HTTPException(status_code=404, detail="User not found")
    if not can_view_profile(current_user, owner):
        raise HTTPException(status_code=403, detail="This profile is private")

    q = _load_posts_query(db).filter(WallPost.wall_owner_id == user_id, WallPost.deleted_at.is_(None))
    if before is not None:
        q = q.filter(WallPost.created_at < before)
    posts = q.order_by(WallPost.created_at.desc()).limit(limit + 1).all()

    has_more = len(posts) > limit
    posts = posts[:limit]
    return {
        "items": [_post_dict(p, current_user) for p in posts],
        "has_more": has_more,
        "next_before": posts[-1].created_at.isoformat() if has_more and posts else None,
        "can_post": bool(current_user) and (
            current_user.id == user_id or current_user.id in _friend_ids(db, user_id)
        ),
    }


@router.post("/users/{user_id}/wall", status_code=201)
def create_post(
    user_id: str,
    req: CreatePostRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    owner = db.query(User).filter(User.id == user_id).first()
    if not owner:
        raise HTTPException(status_code=404, detail="User not found")

    my_friends = _friend_ids(db, current_user.id)
    if current_user.id != user_id and user_id not in my_friends:
        raise HTTPException(status_code=403, detail="Only friends can post on this wall")

    content = (req.content or "").strip() or None
    if not content and not req.song_id:
        raise HTTPException(status_code=400, detail="Write something or share a song")

    if req.song_id:
        song = db.query(Song).filter(Song.id == req.song_id, Song.user_id == current_user.id).first()
        if not song:
            raise HTTPException(status_code=404, detail="Song not found or not yours")

    mention_ids = list(dict.fromkeys(req.mention_ids))
    if mention_ids:
        found = {uid for (uid,) in db.query(User.id).filter(User.id.in_(mention_ids))}
        if len(found) != len(mention_ids):
            raise HTTPException(status_code=400, detail="Mentioned user not found")

    post = WallPost(
        wall_owner_id=user_id,
        author_id=current_user.id,
        content=content,
        song_id=req.song_id,
    )
    post.mentions = [PostMention(mentioned_user_id=m) for m in mention_ids]
    db.add(post)
    db.commit()

    post = _load_posts_query(db).filter(WallPost.id == post.id).first()
    return _post_dict(post, current_user)


@router.delete("/wall/{post_id}")
def delete_post(
    post_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    post = db.query(WallPost).filter(WallPost.id == post_id, WallPost.deleted_at.is_(None)).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    if current_user.id not in (post.author_id, post.wall_owner_id):
        raise HTTPException(status_code=403, detail="Only the author or the wall owner can delete this")

    post.deleted_at = datetime.utcnow()
    db.commit()
    return {"message": "Post deleted"}
