import uuid
from datetime import datetime, timedelta
from sqlalchemy import (
    Column, String, Boolean, DateTime, Integer, Text, JSON,
    ForeignKey, Enum as SAEnum
)
from sqlalchemy.dialects.postgresql import ARRAY
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
    display_name = Column(String(50), nullable=True)
    bio = Column(Text, nullable=True)
    avatar_url = Column(String, nullable=True)
    # TEXT[] on Postgres, JSON list on local SQLite
    favorite_genres = Column(ARRAY(String).with_variant(JSON, "sqlite"), nullable=False, default=list)
    # International profile: ISO 3166-1 alpha-2 codes, ISO 639-1 language codes
    country_code = Column(String(2), nullable=True, index=True)
    city = Column(String(60), nullable=True)
    city_key = Column(String(60), nullable=True)  # services.world.city_key(city)
    visited_countries = Column(ARRAY(String).with_variant(JSON, "sqlite"), nullable=False, default=list)
    languages = Column(ARRAY(String).with_variant(JSON, "sqlite"), nullable=False, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=True, onupdate=datetime.utcnow)

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
    status = Column(SAEnum(FriendshipStatus, name="friendshipstatus", create_type=False), default=FriendshipStatus.pending, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    requester = relationship("User", foreign_keys=[requester_id], back_populates="sent_requests")
    addressee = relationship("User", foreign_keys=[addressee_id], back_populates="received_requests")


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(String, primary_key=True, default=_uuid)
    user_a_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    user_b_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=True)
    last_message_at = Column(DateTime, nullable=True, default=datetime.utcnow)

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
    read_at = Column(DateTime, nullable=True)

    conversation = relationship("Conversation", back_populates="messages")
    sender = relationship("User", foreign_keys=[sender_id])
    song = relationship("Song", back_populates="messages")


# Tables below are created by db/migrations/*.sql; models mirror them.

class WallPost(Base):
    __tablename__ = "wall_posts"

    id = Column(String, primary_key=True, default=_uuid)
    wall_owner_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    author_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    content = Column(Text, nullable=True)
    song_id = Column(String, ForeignKey("songs.id", ondelete="SET NULL"), nullable=True)
    quote_post_id = Column(String, ForeignKey("wall_posts.id", ondelete="SET NULL"), nullable=True)
    quote_song_id = Column(String, ForeignKey("songs.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    deleted_at = Column(DateTime, nullable=True)

    wall_owner = relationship("User", foreign_keys=[wall_owner_id])
    author = relationship("User", foreign_keys=[author_id])
    song = relationship("Song", foreign_keys=[song_id])
    quote_post = relationship("WallPost", remote_side=[id], foreign_keys=[quote_post_id])
    quote_song = relationship("Song", foreign_keys=[quote_song_id])
    mentions = relationship("PostMention", back_populates="post", cascade="all, delete-orphan")


class PostMention(Base):
    __tablename__ = "post_mentions"

    id = Column(String, primary_key=True, default=_uuid)
    post_id = Column(String, ForeignKey("wall_posts.id", ondelete="CASCADE"), nullable=False)
    mentioned_user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    post = relationship("WallPost", back_populates="mentions")
    mentioned_user = relationship("User")


class AdReward(Base):
    __tablename__ = "ad_rewards"

    id = Column(String, primary_key=True, default=_uuid)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    reward_type = Column(String(32), nullable=False)  # 'lyrics' | 'add_friend'
    transaction_id = Column(String, unique=True, nullable=True)
    verified = Column(Boolean, default=False, nullable=False)
    consumed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class LyricsDraft(Base):
    __tablename__ = "lyrics_drafts"

    id = Column(String, primary_key=True, default=_uuid)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(120), nullable=True)
    story = Column(Text, nullable=True)
    theme = Column(String(40), nullable=True)
    lyrics = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)


def _story_expiry():
    return datetime.utcnow() + timedelta(hours=24)


class MusicStory(Base):
    __tablename__ = "music_stories"

    id = Column(String, primary_key=True, default=_uuid)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    song_id = Column(String, ForeignKey("songs.id", ondelete="CASCADE"), nullable=False)
    caption = Column(String(150), nullable=True)
    style = Column(String(32), nullable=False, default="neon")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, default=_story_expiry, nullable=False, index=True)

    user = relationship("User")
    song = relationship("Song")


class StoryView(Base):
    __tablename__ = "story_views"

    story_id = Column(String, ForeignKey("music_stories.id", ondelete="CASCADE"), primary_key=True)
    viewer_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True, index=True)
    viewed_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class SongLike(Base):
    __tablename__ = "song_likes"

    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    song_id = Column(String, ForeignKey("songs.id", ondelete="CASCADE"), primary_key=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class Activity(Base):
    """Things people do that others can discover on Keşfet (likes, profile changes)."""
    __tablename__ = "activities"

    id = Column(String, primary_key=True, default=_uuid)
    actor_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    kind = Column(String(32), nullable=False)
    song_id = Column(String, ForeignKey("songs.id", ondelete="CASCADE"), nullable=True)
    data = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    actor = relationship("User")
    song = relationship("Song")



class PushToken(Base):
    __tablename__ = "push_tokens"

    token = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    platform = Column(String(16), nullable=True)
    language = Column(String(8), nullable=True)  # app language, for the notification text
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)
