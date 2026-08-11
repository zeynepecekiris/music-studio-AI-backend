import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Boolean, DateTime, Integer, Text,
    ForeignKey, Enum as SAEnum
)
from sqlalchemy.orm import relationship
import enum

from db.base import Base


def _uuid():
    return str(uuid.uuid4())


class VerificationCode(Base):
    __tablename__ = "verification_codes"

    id = Column(String, primary_key=True, default=_uuid)
    email = Column(String, nullable=False, index=True)
    code = Column(String, nullable=False)
    type = Column(String, nullable=False, default="email_verification")
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class FriendshipStatus(str, enum.Enum):
    pending = "pending"
    accepted = "accepted"
    blocked = "blocked"


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=_uuid)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    bio = Column(Text, nullable=True)
    avatar_url = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    songs = relationship("Song", back_populates="user", foreign_keys="Song.user_id")
    sent_requests = relationship("Friendship", foreign_keys="Friendship.requester_id", back_populates="requester")
    received_requests = relationship("Friendship", foreign_keys="Friendship.addressee_id", back_populates="addressee")


class Song(Base):
    __tablename__ = "songs"

    id = Column(String, primary_key=True, default=_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String, nullable=False, default="Untitled")
    audio_url = Column(String, nullable=False)
    cover_art_url = Column(String, nullable=True)
    lyrics = Column(Text, nullable=True)
    genre = Column(String, nullable=True)
    mood = Column(String, nullable=True)
    duration = Column(Integer, nullable=True)
    is_public = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="songs", foreign_keys=[user_id])
    messages = relationship("Message", back_populates="song")


class Friendship(Base):
    __tablename__ = "friendships"

    id = Column(String, primary_key=True, default=_uuid)
    requester_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    addressee_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    status = Column(SAEnum(FriendshipStatus), default=FriendshipStatus.pending, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    requester = relationship("User", foreign_keys=[requester_id], back_populates="sent_requests")
    addressee = relationship("User", foreign_keys=[addressee_id], back_populates="received_requests")


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(String, primary_key=True, default=_uuid)
    user_a_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    user_b_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    messages = relationship("Message", back_populates="conversation", order_by="Message.created_at")
    user_a = relationship("User", foreign_keys=[user_a_id])
    user_b = relationship("User", foreign_keys=[user_b_id])


class Message(Base):
    __tablename__ = "messages"

    id = Column(String, primary_key=True, default=_uuid)
    conversation_id = Column(String, ForeignKey("conversations.id"), nullable=False, index=True)
    sender_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    content = Column(Text, nullable=True)
    song_id = Column(String, ForeignKey("songs.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    conversation = relationship("Conversation", back_populates="messages")
    sender = relationship("User", foreign_keys=[sender_id])
    song = relationship("Song", back_populates="messages")
