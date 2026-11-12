import uuid
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from db.session import get_db
from db.models import User, Song, Friendship, FriendshipStatus, WallPost
from services.auth_service import get_current_user, get_optional_user
from services.elevenlabs_service import elevenlabs_service, PromptSafetyError
from services.storage_service import upload_audio
from services.world import world_fields, city_key
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
            "display_name": song.user.display_name,
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
        "display_name": user.display_name,
        "bio": user.bio,
        "avatar_url": user.avatar_url,
        "favorite_genres": list(user.favorite_genres or []),
        **world_fields(user),
        "created_at": user.created_at.isoformat(),
        "song_count": song_count,
        "friendship_status": friendship_status,
        "friendship_id": friendship_id,
    }


async def save_generated_song(
    db: Session,
    user: User,
    request: MusicGenerationRequest,
    music_response,
    title: Optional[str] = None,
    is_public: bool = True,
) -> Song:
    """Upload a freshly generated track to cloud storage and record it as the user's song."""
    import os, aiofiles
    from config.settings import settings

    # ElevenLabs output lands on local disk as /music/<id>.mp3
    local_path = os.path.join(settings.UPLOAD_DIR, "music", f"{music_response.id}.mp3")
    async with aiofiles.open(local_path, "rb") as f:
        audio_bytes = await f.read()
    audio_url = await upload_audio(audio_bytes, f"{music_response.id}.mp3")

    song = Song(
        id=music_response.id,
        user_id=user.id,
        title=(title or request.title or "").strip() or f"{request.genre.value.title()} – {request.theme.value.title()}",
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
    return song


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
        song = await save_generated_song(db, current_user, request, music_response, title, is_public)

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


def can_view_profile(viewer: Optional[User], owner: User) -> bool:
    """Every profile is public for now. Private profiles plug in here later."""
    return True


def _friend_count(db: Session, user_id: str) -> int:
    return db.query(func.count(Friendship.id)).filter(
        Friendship.status == FriendshipStatus.accepted,
        (Friendship.requester_id == user_id) | (Friendship.addressee_id == user_id),
    ).scalar() or 0


def _build_profile(db: Session, user: User, current_user: Optional[User]) -> dict:
    if not can_view_profile(current_user, user):
        raise HTTPException(status_code=403, detail="This profile is private")

    songs_query = db.query(Song).filter(Song.user_id == user.id)
    if not current_user or current_user.id != user.id:
        songs_query = songs_query.filter(Song.is_public == True)
    songs = songs_query.order_by(Song.created_at.desc()).all()

    friendship_status = None
    friendship_id = None
    if current_user and current_user.id != user.id:
        friendship = db.query(Friendship).filter(
            ((Friendship.requester_id == current_user.id) & (Friendship.addressee_id == user.id)) |
            ((Friendship.requester_id == user.id) & (Friendship.addressee_id == current_user.id))
        ).first()
        if friendship:
            friendship_id = friendship.id
            friendship_status = friendship.status.value
            if friendship.status == FriendshipStatus.pending and friendship.requester_id == user.id:
                friendship_status = "received_request"

    profile = _user_profile_dict(user, len(songs), friendship_status, friendship_id)
    profile["friend_count"] = _friend_count(db, user.id)
    profile["post_count"] = db.query(func.count(WallPost.id)).filter(
        WallPost.wall_owner_id == user.id, WallPost.deleted_at.is_(None)
    ).scalar() or 0
    profile["is_self"] = bool(current_user and current_user.id == user.id)
    profile["songs"] = [_song_dict(s, include_user=False) for s in songs]
    return profile


@router.get("/users/{user_id}/profile")
def get_user_profile(
    user_id: str,
    current_user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return _build_profile(db, user, current_user)


@router.get("/users/by-username/{username}/profile")
def get_user_profile_by_username(
    username: str,
    current_user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    """Backs /profile/:username links."""
    user = db.query(User).filter(func.lower(User.username) == username.lower()).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return _build_profile(db, user, current_user)


@router.get("/users/{user_id}/friends")
def get_user_friends(
    user_id: str,
    current_user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    """A user's friend list, shown on their profile."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not can_view_profile(current_user, user):
        raise HTTPException(status_code=403, detail="This profile is private")

    friendships = db.query(Friendship).options(
        joinedload(Friendship.requester), joinedload(Friendship.addressee)
    ).filter(
        Friendship.status == FriendshipStatus.accepted,
        (Friendship.requester_id == user_id) | (Friendship.addressee_id == user_id),
    ).order_by(Friendship.created_at.desc()).all()

    friends = [f.addressee if f.requester_id == user_id else f.requester for f in friendships]
    return [
        {
            "id": u.id,
            "username": u.username,
            "display_name": u.display_name,
            "avatar_url": u.avatar_url,
            "bio": u.bio,
        }
        for u in friends
    ]


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
    term = f"%{username.strip().lstrip('@')}%"
    users = db.query(User).filter(
        User.username.ilike(term) | User.display_name.ilike(term)
    ).limit(20).all()
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
            "display_name": u.display_name,
            "bio": u.bio,
            "avatar_url": u.avatar_url,
            "country_code": u.country_code,
            "city": u.city,
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
    scope: Optional[str] = Query(None, pattern="^(city|country|world)$"),
    current_user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    """All registered users with their latest song and friendship status.

    scope (needs a signed-in user with a country):
      city    – same country and city as me
      country – same country as me
      world   – people from other countries (shuffled)
    """
    offset = (page - 1) * per_page

    query = db.query(User)
    order = User.created_at.desc()
    if scope:
        if not current_user:
            return {"items": [], "total": 0, "page": page, "per_page": per_page, "has_next": False}
        query = query.filter(User.id != current_user.id)
        mine = current_user.country_code
        if scope == "world":
            query = query.filter(User.country_code.isnot(None))
            if mine:
                query = query.filter(User.country_code != mine)
            order = func.random()
        elif not mine or (scope == "city" and not current_user.city):
            return {"items": [], "total": 0, "page": page, "per_page": per_page, "has_next": False}
        else:
            query = query.filter(User.country_code == mine)
            if scope == "city":
                query = query.filter(User.city_key == city_key(current_user.city))

    total = query.count()
    users = query.order_by(order).offset(offset).limit(per_page).all()

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

    # Latest public song per user, in one query instead of one per user
    user_ids = [u.id for u in users]
    ranked = select(
        Song.id,
        func.row_number().over(
            partition_by=Song.user_id, order_by=Song.created_at.desc()
        ).label("rn"),
    ).where(Song.user_id.in_(user_ids), Song.is_public == True).subquery()
    latest_songs = {
        s.user_id: s
        for s in db.query(Song).join(ranked, ranked.c.id == Song.id).filter(ranked.c.rn == 1)
    } if user_ids else {}

    # Discover ranking signals, a few grouped queries for the whole page
    song_stats = {
        uid: (cnt, last) for uid, cnt, last in db.query(
            Song.user_id, func.count(Song.id), func.max(Song.created_at)
        ).filter(Song.user_id.in_(user_ids)).group_by(Song.user_id)
    } if user_ids else {}
    last_posts = {
        uid: last for uid, last in db.query(
            WallPost.author_id, func.max(WallPost.created_at)
        ).filter(WallPost.author_id.in_(user_ids)).group_by(WallPost.author_id)
    } if user_ids else {}

    def accepted_friends(ids):
        rows = db.query(Friendship.requester_id, Friendship.addressee_id).filter(
            Friendship.status == FriendshipStatus.accepted,
            (Friendship.requester_id.in_(ids)) | (Friendship.addressee_id.in_(ids)),
        ).all()
        out = {}
        for a, b in rows:
            out.setdefault(a, set()).add(b)
            out.setdefault(b, set()).add(a)
        return out

    page_friends = accepted_friends(user_ids) if user_ids else {}
    my_friends = accepted_friends([current_user.id]).get(current_user.id, set()) if current_user else set()
    my_genres = set(current_user.favorite_genres or []) if current_user else set()

    result = []
    for u in users:
        latest_song = latest_songs.get(u.id)
        song_count, last_song_at = song_stats.get(u.id, (0, None))
        activity = [d for d in (last_song_at, last_posts.get(u.id), u.updated_at) if d]
        genres = list(u.favorite_genres or [])

        result.append({
            "id": u.id,
            "username": u.username,
            "display_name": u.display_name,
            "bio": u.bio,
            "avatar_url": u.avatar_url,
            "created_at": u.created_at.isoformat(),
            "friendship_status": friendship_map.get(u.id, (None, None))[0],
            "friendship_id": friendship_map.get(u.id, (None, None))[1],
            "latest_song": _song_dict(latest_song, include_user=False) if latest_song else None,
            "favorite_genres": genres,
            "country_code": u.country_code,
            "city": u.city,
            "same_country": bool(current_user and current_user.country_code and u.country_code == current_user.country_code),
            "song_count": song_count,
            "last_active_at": max(activity).isoformat() if activity else u.created_at.isoformat(),
            "mutual_friend_count": len(my_friends & page_friends.get(u.id, set())) if current_user else 0,
            "common_genre_count": len(my_genres & set(genres)),
        })

    return {
        "items": result,
        "total": total,
        "page": page,
        "per_page": per_page,
        "has_next": (offset + per_page) < total,
    }
