from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from pydantic import BaseModel

from db.session import get_db
from db.models import User, Conversation, Message, Song, Friendship, FriendshipStatus
from services.auth_service import get_current_user

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


def _conversation_dict(conv: Conversation, current_user_id: str) -> dict:
    other = conv.user_b if conv.user_a_id == current_user_id else conv.user_a
    last_msg = conv.messages[-1] if conv.messages else None
    return {
        "id": conv.id,
        "created_at": conv.created_at.isoformat(),
        "other_user": {
            "id": other.id,
            "username": other.username,
            "avatar_url": other.avatar_url,
        },
        "last_message": _message_dict(last_msg) if last_msg else None,
    }


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
        joinedload(Conversation.messages).joinedload(Message.song),
        joinedload(Conversation.user_a),
        joinedload(Conversation.user_b),
    ).filter(
        (Conversation.user_a_id == current_user.id) |
        (Conversation.user_b_id == current_user.id)
    ).all()
    return [_conversation_dict(c, current_user.id) for c in convs]


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
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if current_user.id not in (conv.user_a_id, conv.user_b_id):
        raise HTTPException(status_code=403, detail="Not authorized")

    offset = (page - 1) * per_page
    total = db.query(Message).filter(Message.conversation_id == conversation_id).count()
    msgs = (
        db.query(Message)
        .options(joinedload(Message.song))
        .filter(Message.conversation_id == conversation_id)
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


@router.post("/{conversation_id}/messages")
def send_message(
    conversation_id: str,
    req: SendMessageRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not req.content and not req.song_id:
        raise HTTPException(status_code=400, detail="Message must have content or a song")

    conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if current_user.id not in (conv.user_a_id, conv.user_b_id):
        raise HTTPException(status_code=403, detail="Not authorized")

    if req.song_id:
        song = db.query(Song).filter(Song.id == req.song_id, Song.user_id == current_user.id).first()
        if not song:
            raise HTTPException(status_code=404, detail="Song not found or not yours")

    msg = Message(
        conversation_id=conversation_id,
        sender_id=current_user.id,
        content=req.content,
        song_id=req.song_id,
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)
    if msg.song_id:
        msg.song  # eager load
    return _message_dict(msg)
