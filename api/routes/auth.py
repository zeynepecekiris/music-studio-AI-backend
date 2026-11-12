import re
import uuid
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional

from db.session import get_db
from db.models import User
from services.email_service import send_new_user_notification
from services.auth_service import (
    hash_password, verify_password,
    create_access_token, create_refresh_token,
    get_current_user, _decode_token,
)
from services.verification_service import create_and_send_code, verify_code
from services.storage_service import upload_file
from config.settings import settings

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    email: str = Field(..., description="Email address")
    username: str = Field(..., min_length=3, max_length=30)
    password: str = Field(..., min_length=6)
    bio: Optional[str] = Field(None, max_length=300)


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: dict


class RefreshRequest(BaseModel):
    refresh_token: str


class ForgotPasswordRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    email: str
    code: str = Field(..., min_length=6, max_length=6)
    new_password: str = Field(..., min_length=6)


from services.world import world_fields, city_key
from services.activity import log_activity, log_profile_changes


def _user_dict(user: User) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "username": user.username,
        "display_name": user.display_name,
        "bio": user.bio,
        "avatar_url": user.avatar_url,
        "favorite_genres": list(user.favorite_genres or []),
        **world_fields(user),
        "created_at": user.created_at.isoformat(),
    }


# Stable ids; the app shows localized names. Keep in sync with the app's GENRES.
GENRES = {
    "pop", "rock", "rap", "rnb", "electronic", "jazz", "arabesk", "turkpop",
    "lofi", "classical", "metal", "indie", "folk", "reggae", "kpop", "acoustic",
}

MAX_AVATAR_BYTES = 5 * 1024 * 1024


class UpdateProfileRequest(BaseModel):
    display_name: Optional[str] = Field(None, max_length=50)
    bio: Optional[str] = Field(None, max_length=300)
    favorite_genres: Optional[List[str]] = Field(None, max_length=10)
    country_code: Optional[str] = Field(None, max_length=2)
    city: Optional[str] = Field(None, max_length=60)
    visited_countries: Optional[List[str]] = Field(None, max_length=250)
    languages: Optional[List[str]] = Field(None, max_length=12)

    @field_validator("country_code")
    @classmethod
    def _country(cls, v):
        if v in (None, ""):
            return None
        v = v.strip().upper()
        if not re.fullmatch(r"[A-Z]{2}", v):
            raise ValueError("country_code must be a 2-letter ISO code")
        return v

    @field_validator("visited_countries")
    @classmethod
    def _countries(cls, v):
        if v is None:
            return v
        out = [c.strip().upper() for c in v]
        if any(not re.fullmatch(r"[A-Z]{2}", c) for c in out):
            raise ValueError("visited_countries must be 2-letter ISO codes")
        return list(dict.fromkeys(out))

    @field_validator("languages")
    @classmethod
    def _languages(cls, v):
        if v is None:
            return v
        out = [c.strip().lower() for c in v]
        if any(not re.fullmatch(r"[a-z]{2,3}", c) for c in out):
            raise ValueError("languages must be ISO 639 codes")
        return list(dict.fromkeys(out))

    @field_validator("display_name", "bio", "city")
    @classmethod
    def _strip(cls, v):
        return v.strip() if isinstance(v, str) else v

    @field_validator("favorite_genres")
    @classmethod
    def _known_genres(cls, v):
        if v is None:
            return v
        unknown = [g for g in v if g not in GENRES]
        if unknown:
            raise ValueError(f"Unknown genres: {', '.join(unknown)}")
        return list(dict.fromkeys(v))  # dedupe, keep order


def _image_type(data: bytes) -> Optional[str]:
    """Detect by content, not by the client-supplied header."""
    if data[:3] == b"\xff\xd8\xff":
        return "jpg"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    return None


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(req: RegisterRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == req.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    if db.query(User).filter(User.username == req.username).first():
        raise HTTPException(status_code=400, detail="Username already taken")

    user = User(
        email=req.email,
        username=req.username,
        hashed_password=hash_password(req.password),
        bio=req.bio,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    background_tasks.add_task(send_new_user_notification, user.username, user.email)

    return TokenResponse(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
        user=_user_dict(user),
    )


@router.post("/login", response_model=TokenResponse)
def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == req.email).first()
    if not user or not verify_password(req.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    return TokenResponse(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
        user=_user_dict(user),
    )


@router.post("/forgot-password", status_code=200)
def forgot_password(req: ForgotPasswordRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == req.email).first()
    if not user:
        return {"message": "If this email is registered, a reset code has been sent"}
    create_and_send_code(req.email, db, code_type="password_reset")
    return {"message": "If this email is registered, a reset code has been sent"}


@router.post("/reset-password", status_code=200)
def reset_password(req: ResetPasswordRequest, db: Session = Depends(get_db)):
    if not verify_code(req.email, req.code, db, code_type="password_reset"):
        raise HTTPException(status_code=400, detail="Invalid or expired reset code")
    user = db.query(User).filter(User.email == req.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.hashed_password = hash_password(req.new_password)
    db.commit()
    return {"message": "Password reset successful"}


@router.post("/refresh", response_model=TokenResponse)
def refresh(req: RefreshRequest, db: Session = Depends(get_db)):
    user_id = _decode_token(req.refresh_token)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return TokenResponse(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
        user=_user_dict(user),
    )


@router.get("/me")
def me(current_user: User = Depends(get_current_user)):
    return _user_dict(current_user)


@router.patch("/me")
def update_me(
    req: UpdateProfileRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Users can only edit their own profile (the token decides whose)."""
    fields = req.model_dump(exclude_unset=True)
    before = {
        "country_code": current_user.country_code, "city": current_user.city, "bio": current_user.bio,
        "visited_countries": list(current_user.visited_countries or []),
        "favorite_genres": list(current_user.favorite_genres or []),
    }
    if "display_name" in fields:
        current_user.display_name = fields["display_name"] or None
    if "bio" in fields:
        current_user.bio = fields["bio"] or None
    if "favorite_genres" in fields:
        current_user.favorite_genres = fields["favorite_genres"] or []
    if "country_code" in fields:
        current_user.country_code = fields["country_code"]
    if "city" in fields:
        current_user.city = fields["city"] or None
        current_user.city_key = city_key(current_user.city)
    if "visited_countries" in fields:
        current_user.visited_countries = fields["visited_countries"] or []
    if "languages" in fields:
        current_user.languages = fields["languages"] or []
    current_user.updated_at = datetime.utcnow()
    log_profile_changes(db, current_user, before)   # shows up on Keşfet
    db.commit()
    db.refresh(current_user)
    return _user_dict(current_user)


@router.post("/me/avatar")
async def upload_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not (settings.S3_BUCKET_NAME and settings.S3_ACCESS_KEY) and not settings.DEBUG:
        # Heroku's disk is wiped daily; a photo saved there would vanish
        raise HTTPException(status_code=503, detail="Photo storage is not configured yet")

    data = await file.read(MAX_AVATAR_BYTES + 1)
    if len(data) > MAX_AVATAR_BYTES:
        raise HTTPException(status_code=413, detail="Image too large (max 5 MB)")
    ext = _image_type(data)
    if not ext:
        raise HTTPException(status_code=400, detail="Only JPEG, PNG or WebP images")

    content_type = {"jpg": "image/jpeg", "png": "image/png", "webp": "image/webp"}[ext]
    # New name per upload so caches never show the old photo
    url = await upload_file(data, f"avatars/{current_user.id}", f"{uuid.uuid4().hex}.{ext}", content_type)

    current_user.avatar_url = url
    current_user.updated_at = datetime.utcnow()
    log_activity(db, current_user.id, "avatar", {"avatar_url": url})
    db.commit()
    db.refresh(current_user)
    return _user_dict(current_user)


@router.get("/check-username")
def check_username(username: str, db: Session = Depends(get_db)):
    exists = db.query(User).filter(User.username == username).first()
    return {"available": not exists}


@router.delete("/me")
def delete_account(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from db.models import Song, Friendship, Conversation, Message
    conv_ids = [cid for (cid,) in db.query(Conversation.id).filter(
        (Conversation.user_a_id == current_user.id) |
        (Conversation.user_b_id == current_user.id)
    )]
    # Both sides' messages must go before the conversations (FK)
    db.query(Message).filter(
        (Message.sender_id == current_user.id) | Message.conversation_id.in_(conv_ids)
    ).delete(synchronize_session=False)
    db.query(Conversation).filter(Conversation.id.in_(conv_ids)).delete(synchronize_session=False)
    db.query(Friendship).filter(
        (Friendship.requester_id == current_user.id) |
        (Friendship.addressee_id == current_user.id)
    ).delete()
    db.query(Song).filter(Song.user_id == current_user.id).delete()
    db.delete(current_user)
    db.commit()
    return {"message": "Account deleted"}
