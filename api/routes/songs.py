import uuid
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from db.session import get_db
from db.models import User, Song, Friendship, FriendshipStatus
from services.auth_service import get_current_user, get_optional_user
from services.elevenlabs_service import elevenlabs_service, PromptSafetyError
from services.storage_service import upload_audio
from models.schemas import MusicGenerationRequest

router = APIRouter(tags=["songs"])


def _song_dict(song: Song, include_user: bool = True) -> dict:
    d = {
        "id": song.id,
        "title": song.title,
        "audio_url": song.audio_url,
        "cover_art_url": song.cover_art_url,
        "lyrics": song.lyrics,
        "genre": song.genre,
        "mood": song.mood,
        "duration": song.duration,
        "is_public": song.is_public,
        "created_at": song.created_at.isoformat(),
    }
    if include_user and song.user:
        d["user"] = {
            "id": song.user.id,
            "username": song.user.username,
            "avatar_url": song.user.avatar_url,
        }
    return d


def _user_profile_dict(
    user: User,
    song_count: int,
    friendship_status: Optional[str] = None,
    friendship_id: Optional[str] = None,
) -> dict:
    return {
        "id": user.id,
        "username": user.username,
        "bio": user.bio,
        "avatar_url": user.avatar_url,
        "created_at": user.created_at.isoformat(),
        "song_count": song_count,
        "friendship_status": friendship_status,
        "friendship_id": friendship_id,
    }


@router.post("/songs/generate")
async def generate_song(
    request: MusicGenerationRequest,
    title: Optional[str] = Query(None),
    is_public: bool = Query(True),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Generate a song via ElevenLabs, upload to storage, save to DB."""
    try:
        if request.lyrics and len(request.lyrics.strip()) < 10:
            raise HTTPException(status_code=400, detail="Lyrics must be at least 10 characters when provided")
        if request.duration < 15 or request.duration > 300:
            raise HTTPException(status_code=400, detail="Duration must be between 15 and 300 seconds")

        music_response = await elevenlabs_service.generate_music(request)

        # music_response.audio_url is like /music/<uuid>.mp3 (local path)
        # Re-read the bytes and upload to configured storage
        import os, aiofiles
        from config.settings import settings
        local_path = os.path.join(settings.UPLOAD_DIR, "music", f"{music_response.id}.mp3")

        async with aiofiles.open(local_path, "rb") as f:
            audio_bytes = await f.read()

        filename = f"{music_response.id}.mp3"
        audio_url = await upload_audio(audio_bytes, filename)

        song = Song(
            id=music_response.id,
            user_id=current_user.id,
            title=title or f"{request.genre.value.title()} – {request.theme.value.title()}",
            audio_url=audio_url,
            lyrics=request.lyrics,
            genre=request.genre.value,
            mood=request.mood.value,
            duration=request.duration,
            is_public=is_public,
        )
        db.add(song)
        db.commit()
        db.refresh(song)

        result = _song_dict(song, include_user=False)
        result["processing_time"] = music_response.processing_time
        return result

    except PromptSafetyError as e:
        raise HTTPException(status_code=400, detail={
            "code": "BAD_PROMPT",
            "message": str(e),
            "promptSuggestion": e.suggestion,
        })
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating song: {str(e)}")


@router.get("/feed")
def get_feed(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=50),
    current_user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    """Public + friends' songs feed, newest first."""
    offset = (page - 1) * per_page

    if current_user:
        # Friends' user IDs
        accepted = db.query(Friendship).filter(
            Friendship.status == FriendshipStatus.accepted,
        ).filter(
            (Friendship.requester_id == current_user.id) |
            (Friendship.addressee_id == current_user.id)
        ).all()

        friend_ids = set()
        for f in accepted:
            friend_ids.add(f.requester_id if f.addressee_id == current_user.id else f.addressee_id)
        friend_ids.add(current_user.id)

        query = db.query(Song).options(joinedload(Song.user)).filter(
            (Song.is_public == True) | (Song.user_id.in_(friend_ids))
        )
    else:
        query = db.query(Song).options(joinedload(Song.user)).filter(Song.is_public == True)

    total = query.count()
    songs = query.order_by(Song.created_at.desc()).offset(offset).limit(per_page).all()

    return {
        "items": [_song_dict(s) for s in songs],
        "total": total,
        "page": page,
        "per_page": per_page,
        "has_next": (offset + per_page) < total,
    }


@router.get("/users/{user_id}/profile")
def get_user_profile(
    user_id: str,
    current_user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    songs_query = db.query(Song).filter(Song.user_id == user_id)
    if not current_user or current_user.id != user_id:
        songs_query = songs_query.filter(Song.is_public == True)
    songs = songs_query.order_by(Song.created_at.desc()).all()

    friendship_status = None
    friendship_id = None
    if current_user and current_user.id != user_id:
        friendship = db.query(Friendship).filter(
            ((Friendship.requester_id == current_user.id) & (Friendship.addressee_id == user_id)) |
            ((Friendship.requester_id == user_id) & (Friendship.addressee_id == current_user.id))
        ).first()
        if friendship:
            friendship_id = friendship.id
            friendship_status = friendship.status.value
            if friendship.status == FriendshipStatus.pending and friendship.requester_id == user_id:
                friendship_status = "received_request"

    profile = _user_profile_dict(user, len(songs), friendship_status, friendship_id)
    profile["songs"] = [_song_dict(s, include_user=False) for s in songs]
    return profile


@router.get("/users/{user_id}/songs")
def get_user_songs(
    user_id: str,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=50),
    current_user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    offset = (page - 1) * per_page
    query = db.query(Song).filter(Song.user_id == user_id)
    if not current_user or current_user.id != user_id:
        query = query.filter(Song.is_public == True)

    total = query.count()
    songs = query.order_by(Song.created_at.desc()).offset(offset).limit(per_page).all()

    return {
        "items": [_song_dict(s, include_user=False) for s in songs],
        "total": total,
        "page": page,
        "per_page": per_page,
        "has_next": (offset + per_page) < total,
    }


@router.get("/users/search")
def search_users(
    username: str,
    current_user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    users = db.query(User).filter(User.username.ilike(f"%{username}%")).limit(20).all()
    friendship_map = {}
    if current_user:
        friendships = db.query(Friendship).filter(
            (Friendship.requester_id == current_user.id) |
            (Friendship.addressee_id == current_user.id)
        ).all()
        for f in friendships:
            other_id = f.addressee_id if f.requester_id == current_user.id else f.requester_id
            status = f.status.value
            if f.status == FriendshipStatus.pending and f.requester_id != current_user.id:
                status = "received_request"
            friendship_map[other_id] = (status, f.id)

    return [
        {
            "id": u.id,
            "username": u.username,
            "bio": u.bio,
            "avatar_url": u.avatar_url,
            "friendship_status": friendship_map.get(u.id, (None, None))[0],
            "friendship_id": friendship_map.get(u.id, (None, None))[1],
            "is_self": current_user.id == u.id if current_user else False,
        }
        for u in users
    ]


@router.get("/users")
def list_users(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=50),
    current_user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    """All registered users with their latest song and friendship status."""
    offset = (page - 1) * per_page

    query = db.query(User)

    total = query.count()
    users = query.order_by(User.created_at.desc()).offset(offset).limit(per_page).all()

    # Friendship statuses for current user
    friendship_map = {}
    if current_user:
        friendships = db.query(Friendship).filter(
            (Friendship.requester_id == current_user.id) |
            (Friendship.addressee_id == current_user.id)
        ).all()
        for f in friendships:
            other_id = f.addressee_id if f.requester_id == current_user.id else f.requester_id
            status = f.status.value
            if f.status == FriendshipStatus.pending and f.requester_id != current_user.id:
                status = "received_request"
            friendship_map[other_id] = (status, f.id)

    result = []
    for u in users:
        latest_song = db.query(Song).filter(
            Song.user_id == u.id, Song.is_public == True
        ).order_by(Song.created_at.desc()).first()

        result.append({
            "id": u.id,
            "username": u.username,
            "bio": u.bio,
            "avatar_url": u.avatar_url,
            "created_at": u.created_at.isoformat(),
            "friendship_status": friendship_map.get(u.id, (None, None))[0],
            "friendship_id": friendship_map.get(u.id, (None, None))[1],
            "latest_song": _song_dict(latest_song, include_user=False) if latest_song else None,
        })

    return {
        "items": result,
        "total": total,
        "page": page,
        "per_page": per_page,
        "has_next": (offset + per_page) < total,
    }
