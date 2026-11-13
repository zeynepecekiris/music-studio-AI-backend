from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from db.session import get_db
from db.models import User, PushToken
from services.auth_service import get_current_user

router = APIRouter(prefix="/notifications", tags=["notifications"])


class TokenRequest(BaseModel):
    token: str = Field(..., min_length=10, max_length=255)
    platform: Optional[str] = Field(None, max_length=16)
    language: Optional[str] = Field(None, max_length=8)


@router.post("/token")
def register_token(
    req: TokenRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Save this device's push token. A device that changes accounts moves with it."""
    row = db.query(PushToken).filter(PushToken.token == req.token).first()
    if row is None:
        row = PushToken(token=req.token)
        db.add(row)
    row.user_id = current_user.id
    row.platform = req.platform
    row.language = req.language
    row.updated_at = datetime.utcnow()
    db.commit()
    return {"ok": True}


@router.delete("/token")
def unregister_token(
    token: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Called on logout so the device stops getting this account's notifications."""
    db.query(PushToken).filter(
        PushToken.token == token, PushToken.user_id == current_user.id
    ).delete(synchronize_session=False)
    db.commit()
    return {"ok": True}
