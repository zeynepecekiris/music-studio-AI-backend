"""Song likes. Liking shows up on Keşfet ("Ayşe bu şarkıyı beğendi")."""
from typing import Dict, Iterable, Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from db.models import Song, SongLike, User
from db.session import get_db
from services.activity import log_activity, remove_like_activity
from services.auth_service import get_current_user

router = APIRouter(tags=["likes"])


def like_info(db: Session, song_ids: Iterable[str], me: Optional[User]) -> Dict[str, Tuple[int, bool]]:
    """{song_id: (like_count, liked_by_me)} for many songs in two queries."""
    ids = list({s for s in song_ids if s})
    if not ids:
        return {}
    counts = dict(db.query(SongLike.song_id, func.count()).filter(SongLike.song_id.in_(ids)).group_by(SongLike.song_id))
    mine = set()
    if me:
        mine = {sid for (sid,) in db.query(SongLike.song_id).filter(SongLike.user_id == me.id, SongLike.song_id.in_(ids))}
    return {sid: (counts.get(sid, 0), sid in mine) for sid in ids}


def _visible_song(db: Session, song_id: str, me: User) -> Song:
    song = db.query(Song).filter(Song.id == song_id).first()
    if not song or (not song.is_public and song.user_id != me.id):
        raise HTTPException(status_code=404, detail="Şarkı bulunamadı")
    return song


@router.post("/songs/{song_id}/like")
def like_song(song_id: str, me: User = Depends(get_current_user), db: Session = Depends(get_db)):
    song = _visible_song(db, song_id, me)
    if not db.query(SongLike).filter(SongLike.user_id == me.id, SongLike.song_id == song_id).first():
        db.add(SongLike(user_id=me.id, song_id=song_id))
        if song.user_id != me.id:  # liking your own song isn't news
            log_activity(db, me.id, "like_song", song_id=song_id)
        db.commit()
    count, _ = like_info(db, [song_id], me)[song_id]
    return {"liked": True, "like_count": count}


@router.delete("/songs/{song_id}/like")
def unlike_song(song_id: str, me: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _visible_song(db, song_id, me)
    db.query(SongLike).filter(SongLike.user_id == me.id, SongLike.song_id == song_id).delete(synchronize_session=False)
    remove_like_activity(db, me.id, song_id)
    db.commit()
    count, _ = like_info(db, [song_id], me)[song_id]
    return {"liked": False, "like_count": count}
