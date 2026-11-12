"""
Activity log for Keşfet: likes and profile changes become feed items.

Repeated changes of the same kind within COALESCE_MINUTES update the latest
entry instead of adding new ones, so one busy edit session is one feed item.
"""
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from db.models import Activity

COALESCE_MINUTES = 30


def log_activity(db: Session, actor_id: str, kind: str, data: Optional[dict] = None, song_id: Optional[str] = None):
    """Add (or refresh) an activity. Caller commits."""
    data = dict(data or {})
    now = datetime.utcnow()

    if kind == "like_song":
        exists = db.query(Activity).filter(
            Activity.actor_id == actor_id, Activity.kind == kind, Activity.song_id == song_id).first()
        if not exists:
            db.add(Activity(actor_id=actor_id, kind=kind, song_id=song_id, data=data, created_at=now))
        return

    recent = db.query(Activity).filter(
        Activity.actor_id == actor_id, Activity.kind == kind,
        Activity.created_at > now - timedelta(minutes=COALESCE_MINUTES),
    ).order_by(Activity.created_at.desc()).first()

    if recent:
        merged = dict(recent.data or {})
        if "added" in data:  # lists of new countries / genres accumulate
            merged["added"] = list(dict.fromkeys(list(merged.get("added", [])) + list(data["added"])))
            data = {k: v for k, v in data.items() if k != "added"}
        merged.update(data)
        recent.data = merged
        recent.created_at = now
    else:
        db.add(Activity(actor_id=actor_id, kind=kind, song_id=song_id, data=data, created_at=now))


def remove_like_activity(db: Session, actor_id: str, song_id: str):
    db.query(Activity).filter(
        Activity.actor_id == actor_id, Activity.kind == "like_song", Activity.song_id == song_id
    ).delete(synchronize_session=False)


def log_profile_changes(db: Session, user, before: dict):
    """Compare a user's profile with `before` and log what changed."""
    if user.country_code and (user.country_code != before.get("country_code") or (user.city or "") != (before.get("city") or "")):
        log_activity(db, user.id, "moved", {"country_code": user.country_code, "city": user.city})
    new_visited = [c for c in (user.visited_countries or []) if c not in (before.get("visited_countries") or [])]
    if new_visited:
        log_activity(db, user.id, "visited", {"added": new_visited})
    if user.bio and user.bio != before.get("bio"):
        log_activity(db, user.id, "bio", {"bio": user.bio})
    new_genres = [g for g in (user.favorite_genres or []) if g not in (before.get("favorite_genres") or [])]
    if new_genres:
        log_activity(db, user.id, "genres", {"added": new_genres})
