"""The signed-in user's lyrics, autosaved from the notebook screen."""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from db.models import LyricsDraft, User
from db.session import get_db
from services.auth_service import get_current_user

router = APIRouter(prefix="/me/lyrics", tags=["lyrics drafts"])

MAX_LYRICS = 10000


class CreateDraft(BaseModel):
    lyrics: str = Field(..., min_length=1, max_length=MAX_LYRICS)
    title: Optional[str] = Field(None, max_length=120)
    story: Optional[str] = Field(None, max_length=5000)
    theme: Optional[str] = Field(None, max_length=40)


class UpdateDraft(BaseModel):
    lyrics: Optional[str] = Field(None, min_length=1, max_length=MAX_LYRICS)
    title: Optional[str] = Field(None, max_length=120)


def _dict(d: LyricsDraft) -> dict:
    return {
        "id": d.id, "title": d.title, "story": d.story, "theme": d.theme, "lyrics": d.lyrics,
        "created_at": d.created_at.isoformat(), "updated_at": d.updated_at.isoformat(),
    }


def _own(db: Session, draft_id: str, user: User) -> LyricsDraft:
    d = db.query(LyricsDraft).filter(LyricsDraft.id == draft_id).first()
    if not d or d.user_id != user.id:
        raise HTTPException(status_code=404, detail="Lyrics not found")
    return d


@router.get("")
def list_drafts(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.query(LyricsDraft).filter(LyricsDraft.user_id == current_user.id) \
        .order_by(LyricsDraft.updated_at.desc()).limit(200).all()
    return [_dict(d) for d in rows]


@router.post("", status_code=201)
def create_draft(req: CreateDraft, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    d = LyricsDraft(user_id=current_user.id, **req.model_dump())
    db.add(d)
    db.commit()
    return _dict(d)


@router.patch("/{draft_id}")
def update_draft(draft_id: str, req: UpdateDraft,
                 current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    d = _own(db, draft_id, current_user)
    for k, v in req.model_dump(exclude_unset=True).items():
        if v is not None:
            setattr(d, k, v)
    d.updated_at = datetime.utcnow()
    db.commit()
    return _dict(d)
