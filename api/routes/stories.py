"""
Music stories: like Instagram stories, but every story is one of the
author's own songs shown as a clip (visual style + lyrics) for 24 hours.

- Anyone can watch stories (profiles are public).
- Only your own songs can become a story.
- The story row puts you first, then people with unseen stories,
  friends before others, newest first.
"""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session, joinedload

from db.models import Friendship, FriendshipStatus, MusicStory, Song, StoryView, User
from db.session import get_db
from services.auth_service import get_current_user, get_optional_user

router = APIRouter(tags=["stories"])

STYLES = {"neon", "sunset", "ocean", "galaxy", "candy", "mono"}
MAX_STORY_USERS = 60


class CreateStoryRequest(BaseModel):
    song_id: str
    caption: Optional[str] = Field(None, max_length=150)
    style: str = Field("neon", max_length=32)


def _mini_user(u: User) -> dict:
    return {"id": u.id, "username": u.username, "display_name": u.display_name, "avatar_url": u.avatar_url}


def _story_dict(s: MusicStory, seen: bool) -> dict:
    song = s.song
    return {
        "id": s.id,
        "caption": s.caption,
        "style": s.style,
        "created_at": s.created_at.isoformat(),
        "expires_at": s.expires_at.isoformat(),
        "seen": seen,
        "song": {
            "id": song.id,
            "title": song.title,
            "audio_url": song.audio_url,
            "cover_art_url": song.cover_art_url,
            "genre": song.genre,
            "mood": song.mood,
            "duration": song.duration,
            "lyrics": song.lyrics,
        },
    }


@router.post("/stories", status_code=201)
def create_story(body: CreateStoryRequest, me: User = Depends(get_current_user), db: Session = Depends(get_db)):
    song = db.query(Song).filter(Song.id == body.song_id).first()
    if not song or song.user_id != me.id:
        raise HTTPException(status_code=404, detail="Şarkı bulunamadı")
    style = body.style if body.style in STYLES else "neon"
    caption = (body.caption or "").strip() or None
    story = MusicStory(user_id=me.id, song_id=song.id, caption=caption, style=style)
    db.add(story)
    db.commit()
    db.refresh(story)
    return _story_dict(story, seen=True)


@router.get("/stories/feed")
def story_feed(me: Optional[User] = Depends(get_optional_user), db: Session = Depends(get_db)):
    now = datetime.utcnow()
    stories = (
        db.query(MusicStory)
        .options(joinedload(MusicStory.user), joinedload(MusicStory.song))
        .filter(MusicStory.expires_at > now)
        .order_by(MusicStory.created_at.asc())
        .all()
    )
    seen_ids, friend_ids = set(), set()
    if me:
        ids = [s.id for s in stories]
        if ids:
            seen_ids = {r[0] for r in db.query(StoryView.story_id).filter(
                StoryView.viewer_id == me.id, StoryView.story_id.in_(ids))}
        rows = db.query(Friendship.requester_id, Friendship.addressee_id).filter(
            Friendship.status == FriendshipStatus.accepted,
            (Friendship.requester_id == me.id) | (Friendship.addressee_id == me.id),
        ).all()
        friend_ids = {a if b == me.id else b for a, b in rows}

    groups = {}
    for s in stories:
        g = groups.setdefault(s.user_id, {"user": _mini_user(s.user), "stories": []})
        g["stories"].append(_story_dict(s, seen=(me is not None and (s.id in seen_ids or s.user_id == me.id))))

    out = []
    for uid, g in groups.items():
        g["all_seen"] = all(x["seen"] for x in g["stories"])
        g["latest_at"] = g["stories"][-1]["created_at"]
        g["is_me"] = bool(me and uid == me.id)
        g["is_friend"] = uid in friend_ids
        out.append(g)
    out.sort(key=lambda g: (not g["is_me"], g["all_seen"], not g["is_friend"], _neg(g["latest_at"])))
    return {"items": out[:MAX_STORY_USERS]}


def _neg(iso: str) -> float:
    return -datetime.fromisoformat(iso).timestamp()


@router.post("/stories/{story_id}/view", status_code=204)
def view_story(story_id: str, me: User = Depends(get_current_user), db: Session = Depends(get_db)):
    story = db.query(MusicStory).filter(MusicStory.id == story_id).first()
    if not story:
        raise HTTPException(status_code=404, detail="Hikaye bulunamadı")
    if story.user_id != me.id and not db.query(StoryView).filter(
        StoryView.story_id == story_id, StoryView.viewer_id == me.id
    ).first():
        db.add(StoryView(story_id=story_id, viewer_id=me.id))
        db.commit()


@router.get("/stories/{story_id}/viewers")
def story_viewers(story_id: str, me: User = Depends(get_current_user), db: Session = Depends(get_db)):
    story = db.query(MusicStory).filter(MusicStory.id == story_id).first()
    if not story or story.user_id != me.id:
        raise HTTPException(status_code=404, detail="Hikaye bulunamadı")
    rows = (db.query(StoryView, User).join(User, User.id == StoryView.viewer_id)
            .filter(StoryView.story_id == story_id).order_by(StoryView.viewed_at.desc()).all())
    return {"count": len(rows), "items": [{**_mini_user(u), "viewed_at": v.viewed_at.isoformat()} for v, u in rows]}


@router.delete("/stories/{story_id}", status_code=204)
def delete_story(story_id: str, me: User = Depends(get_current_user), db: Session = Depends(get_db)):
    story = db.query(MusicStory).filter(MusicStory.id == story_id).first()
    if not story or story.user_id != me.id:
        raise HTTPException(status_code=404, detail="Hikaye bulunamadı")
    db.delete(story)
    db.commit()
