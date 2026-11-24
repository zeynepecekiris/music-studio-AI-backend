"""
Block users and report content (App Store guideline 1.2).

POST   /users/{id}/block   block someone (also ends a friendship/request)
DELETE /users/{id}/block   unblock
GET    /blocks             people I blocked
POST   /reports            report a post, user, message, story, song or comment
"""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from db.models import Comment, Friendship, Message, MusicStory, Report, Song, User, UserBlock, WallPost
from db.session import get_db
from services.auth_service import get_current_user
from services.moderation import AUTO_HIDE_REPORTS, notify_admin_of_report

router = APIRouter(tags=["moderation"])

TARGETS = {"post", "user", "message", "story", "song", "comment"}
REASONS = {"spam", "harassment", "hate", "sexual", "violence", "copyright", "other"}


def _mini(u: User) -> dict:
    return {"id": u.id, "username": u.username, "display_name": u.display_name, "avatar_url": u.avatar_url}


@router.post("/users/{user_id}/block")
def block_user(user_id: str, me: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user_id == me.id:
        raise HTTPException(status_code=400, detail="You can't block yourself")
    other = db.query(User).filter(User.id == user_id).first()
    if not other:
        raise HTTPException(status_code=404, detail="User not found")
    if not db.query(UserBlock).filter(UserBlock.blocker_id == me.id, UserBlock.blocked_id == user_id).first():
        db.add(UserBlock(blocker_id=me.id, blocked_id=user_id))
    # A block ends any friendship or pending request between the two
    db.query(Friendship).filter(or_(
        (Friendship.requester_id == me.id) & (Friendship.addressee_id == user_id),
        (Friendship.requester_id == user_id) & (Friendship.addressee_id == me.id),
    )).delete(synchronize_session=False)
    db.commit()
    return {"blocked": True}


@router.delete("/users/{user_id}/block")
def unblock_user(user_id: str, me: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db.query(UserBlock).filter(UserBlock.blocker_id == me.id, UserBlock.blocked_id == user_id).delete()
    db.commit()
    return {"blocked": False}


@router.get("/blocks")
def list_blocked(me: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = (db.query(User).join(UserBlock, UserBlock.blocked_id == User.id)
            .filter(UserBlock.blocker_id == me.id).order_by(UserBlock.created_at.desc()).all())
    return [_mini(u) for u in rows]


class ReportRequest(BaseModel):
    target_type: str
    target_id: str
    reason: str = "other"
    note: Optional[str] = Field(None, max_length=500)


def _owner_of(db: Session, target_type: str, target_id: str) -> Optional[str]:
    if target_type == "user":
        return target_id if db.query(User.id).filter(User.id == target_id).first() else None
    if target_type == "post":
        row = db.query(WallPost.author_id).filter(WallPost.id == target_id).first()
    elif target_type == "message":
        row = db.query(Message.sender_id).filter(Message.id == target_id).first()
    elif target_type == "comment":
        row = db.query(Comment.author_id).filter(Comment.id == target_id).first()
    elif target_type == "story":
        row = db.query(MusicStory.user_id).filter(MusicStory.id == target_id).first()
    else:
        row = db.query(Song.user_id).filter(Song.id == target_id).first()
    return row[0] if row else None


@router.post("/reports", status_code=201)
def report(req: ReportRequest, me: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if req.target_type not in TARGETS:
        raise HTTPException(status_code=400, detail="Unknown report target")
    reason = req.reason if req.reason in REASONS else "other"
    owner_id = _owner_of(db, req.target_type, req.target_id)
    if owner_id is None:
        raise HTTPException(status_code=404, detail="Not found")

    r = Report(reporter_id=me.id, target_type=req.target_type, target_id=req.target_id,
               target_user_id=owner_id, reason=reason, note=(req.note or None))
    db.add(r)
    db.flush()

    # Enough different people reporting the same post or story hides it right away
    hidden = False
    if req.target_type in ("post", "story", "comment"):
        n = db.query(func.count(func.distinct(Report.reporter_id))).filter(
            Report.target_type == req.target_type, Report.target_id == req.target_id,
        ).scalar() or 0
        if n >= AUTO_HIDE_REPORTS:
            if req.target_type == "comment":
                c = db.query(Comment).filter(Comment.id == req.target_id).first()
                if c and c.deleted_at is None:
                    c.deleted_at = datetime.utcnow()
                    hidden = True
            elif req.target_type == "post":
                post = db.query(WallPost).filter(WallPost.id == req.target_id).first()
                if post and post.deleted_at is None:
                    post.deleted_at = datetime.utcnow()
                    hidden = True
            else:
                story = db.query(MusicStory).filter(MusicStory.id == req.target_id).first()
                if story and story.expires_at > datetime.utcnow():
                    story.expires_at = datetime.utcnow()
                    hidden = True
    db.commit()

    target_user = db.query(User.username).filter(User.id == owner_id).first()
    notify_admin_of_report(r.id, me.username, req.target_type, req.target_id,
                           target_user[0] if target_user else None, reason, req.note)
    return {"reported": True, "hidden": hidden}
