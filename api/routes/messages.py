from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload
from pydantic import BaseModel

from db.session import get_db
from db.models import User, Conversation, Message, Song, Friendship, FriendshipStatus
from services.auth_service import get_current_user
from services.push import notify_new_message

router = APIRouter(prefix="/conversations", tags=["messages"])


class SendMessageRequest(BaseModel):
    content: Optional[str] = None
    song_id: Optional[str] = None


def _message_dict(msg: Message) -> dict:
    d = {
        "id": msg.id,
        "conversation_id": msg.conversation_id,
        "sender_id": msg.sender_id,
        "content": msg.content,
        "created_at": msg.created_at.isoformat(),
        "read_at": msg.read_at.isoformat() if msg.read_at else None,
        "song": None,
    }
    if msg.song:
        d["song"] = {
            "id": msg.song.id,
            "title": msg.song.title,
            "audio_url": msg.song.audio_url,
            "cover_art_url": msg.song.cover_art_url,
        }
    return d


def _conversation_dict(
    conv: Conversation,
    current_user_id: str,
    last_msg: Optional[Message],
    unread_count: int,
) -> dict:
    other = conv.user_b if conv.user_a_id == current_user_id else conv.user_a
    last_at = conv.last_message_at or conv.created_at
    return {
        "id": conv.id,
        "created_at": conv.created_at.isoformat(),
        "last_message_at": last_at.isoformat() if last_at else None,
        "other_user": {
            "id": other.id,
            "username": other.username,
            "display_name": other.display_name,
            "avatar_url": other.avatar_url,
        },
        "last_message": _message_dict(last_msg) if last_msg else None,
        "unread_count": unread_count,
    }


def _member_or_403(db: Session, conversation_id: str, user_id: str) -> Conversation:
    conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if user_id not in (conv.user_a_id, conv.user_b_id):
        raise HTTPException(status_code=403, detail="Not authorized")
    return conv


def create_message(
    db: Session,
    conv: Conversation,
    sender_id: str,
    content: Optional[str],
    song_id: Optional[str],
) -> Message:
    """Persist a message and bump the conversation. Shared by REST and WebSocket."""
    msg = Message(
        conversation_id=conv.id,
        sender_id=sender_id,
        content=content,
        song_id=song_id,
    )
    db.add(msg)
    db.flush()
    conv.last_message_at = msg.created_at
    conv.updated_at = msg.created_at
    db.commit()
    db.refresh(msg)
    return msg


def _get_or_create_conversation(db: Session, user_a_id: str, user_b_id: str) -> Conversation:
    conv = db.query(Conversation).filter(
        ((Conversation.user_a_id == user_a_id) & (Conversation.user_b_id == user_b_id)) |
        ((Conversation.user_a_id == user_b_id) & (Conversation.user_b_id == user_a_id))
    ).first()
    if not conv:
        conv = Conversation(user_a_id=user_a_id, user_b_id=user_b_id)
        db.add(conv)
        db.commit()
        db.refresh(conv)
    return conv


@router.get("")
def list_conversations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    convs = db.query(Conversation).options(
        joinedload(Conversation.user_a),
        joinedload(Conversation.user_b),
    ).filter(
        (Conversation.user_a_id == current_user.id) |
        (Conversation.user_b_id == current_user.id)
    ).order_by(
        func.coalesce(Conversation.last_message_at, Conversation.created_at).desc()
    ).all()
    if not convs:
        return []
    ids = [c.id for c in convs]

    # Only the newest message of each conversation, in a single query
    ranked = select(
        Message.id,
        func.row_number().over(
            partition_by=Message.conversation_id,
            order_by=Message.created_at.desc(),
        ).label("rn"),
    ).where(Message.conversation_id.in_(ids)).subquery()
    last_msgs = {
        m.conversation_id: m
        for m in db.query(Message)
        .options(joinedload(Message.song))
        .join(ranked, ranked.c.id == Message.id)
        .filter(ranked.c.rn == 1)
    }

    unread = dict(
        db.query(Message.conversation_id, func.count(Message.id))
        .filter(
            Message.conversation_id.in_(ids),
            Message.sender_id != current_user.id,
            Message.read_at.is_(None),
        )
        .group_by(Message.conversation_id)
        .all()
    )

    return [
        _conversation_dict(c, current_user.id, last_msgs.get(c.id), unread.get(c.id, 0))
        for c in convs
    ]


@router.get("/unread-count")
def unread_count(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Total unread messages across all conversations (tab badge)."""
    count = (
        db.query(func.count(Message.id))
        .join(Conversation, Conversation.id == Message.conversation_id)
        .filter(
            (Conversation.user_a_id == current_user.id) |
            (Conversation.user_b_id == current_user.id),
            Message.sender_id != current_user.id,
            Message.read_at.is_(None),
        )
        .scalar()
    )
    return {"count": count or 0}


@router.post("/with/{other_user_id}")
def start_conversation(
    other_user_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    other = db.query(User).filter(User.id == other_user_id).first()
    if not other:
        raise HTTPException(status_code=404, detail="User not found")

    conv = _get_or_create_conversation(db, current_user.id, other_user_id)
    return {"conversation_id": conv.id}


@router.get("/{conversation_id}/messages")
def get_messages(
    conversation_id: str,
    page: int = Query(1, ge=1),
    per_page: int = Query(30, ge=1, le=100),
    before: Optional[datetime] = Query(None, description="Return messages older than this (cursor paging)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _member_or_403(db, conversation_id, current_user.id)

    query = db.query(Message).filter(Message.conversation_id == conversation_id)
    if before is not None:
        # Cursor paging: stable even while new messages arrive
        query = query.filter(Message.created_at < before)
        offset = 0
    else:
        offset = (page - 1) * per_page
    total = query.count()
    msgs = (
        query.options(joinedload(Message.song))
        .order_by(Message.created_at.desc())
        .offset(offset)
        .limit(per_page)
        .all()
    )
    return {
        "items": [_message_dict(m) for m in reversed(msgs)],
        "total": total,
        "page": page,
        "per_page": per_page,
        "has_more": (offset + per_page) < total,
    }


@router.post("/{conversation_id}/read")
def mark_read(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _member_or_403(db, conversation_id, current_user.id)
    updated = (
        db.query(Message)
        .filter(
            Message.conversation_id == conversation_id,
            Message.sender_id != current_user.id,
            Message.read_at.is_(None),
        )
        .update({Message.read_at: datetime.utcnow()}, synchronize_session=False)
    )
    db.commit()
    return {"marked": updated}


@router.post("/{conversation_id}/messages")
def send_message(
    conversation_id: str,
    req: SendMessageRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not req.content and not req.song_id:
        raise HTTPException(status_code=400, detail="Message must have content or a song")

    conv = _member_or_403(db, conversation_id, current_user.id)

    if req.song_id:
        song = db.query(Song).filter(Song.id == req.song_id, Song.user_id == current_user.id).first()
        if not song:
            raise HTTPException(status_code=404, detail="Song not found or not yours")

    msg = create_message(db, conv, current_user.id, req.content, req.song_id)
    notify_new_message(db, conv, msg, current_user)
    return _message_dict(msg)
