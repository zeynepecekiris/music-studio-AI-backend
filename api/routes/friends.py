from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from db.session import get_db
from db.models import User, Friendship, FriendshipStatus
from services.auth_service import get_current_user

router = APIRouter(prefix="/friends", tags=["friends"])


def _friend_dict(user: User) -> dict:
    return {
        "id": user.id,
        "username": user.username,
        "display_name": user.display_name,
        "bio": user.bio,
        "avatar_url": user.avatar_url,
    }


def _friendship_dict(f: Friendship, perspective_user_id: str) -> dict:
    other = f.addressee if f.requester_id == perspective_user_id else f.requester
    return {
        "friendship_id": f.id,
        "status": f.status.value,
        "created_at": f.created_at.isoformat(),
        "user": _friend_dict(other),
        "is_sender": f.requester_id == perspective_user_id,
    }


@router.post("/request")
def send_friend_request(
    addressee_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if addressee_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot add yourself")

    target = db.query(User).filter(User.id == addressee_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    existing = db.query(Friendship).filter(
        ((Friendship.requester_id == current_user.id) & (Friendship.addressee_id == addressee_id)) |
        ((Friendship.requester_id == addressee_id) & (Friendship.addressee_id == current_user.id))
    ).first()

    if existing:
        raise HTTPException(status_code=400, detail=f"Friendship already exists with status: {existing.status.value}")

    friendship = Friendship(requester_id=current_user.id, addressee_id=addressee_id)
    db.add(friendship)
    db.commit()
    db.refresh(friendship)
    return {"message": "Friend request sent", "friendship_id": friendship.id}


@router.post("/{friendship_id}/accept")
def accept_friend_request(
    friendship_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    friendship = db.query(Friendship).filter(Friendship.id == friendship_id).first()
    if not friendship:
        raise HTTPException(status_code=404, detail="Request not found")
    if friendship.addressee_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    if friendship.status != FriendshipStatus.pending:
        raise HTTPException(status_code=400, detail="Request is not pending")

    friendship.status = FriendshipStatus.accepted
    db.commit()
    return {"message": "Friend request accepted"}


@router.post("/{friendship_id}/reject")
def reject_friend_request(
    friendship_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    friendship = db.query(Friendship).filter(Friendship.id == friendship_id).first()
    if not friendship:
        raise HTTPException(status_code=404, detail="Request not found")
    if friendship.addressee_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    db.delete(friendship)
    db.commit()
    return {"message": "Friend request rejected"}


@router.delete("/{friendship_id}/cancel")
def cancel_friend_request(
    friendship_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    friendship = db.query(Friendship).filter(Friendship.id == friendship_id).first()
    if not friendship:
        raise HTTPException(status_code=404, detail="Request not found")
    if friendship.requester_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    if friendship.status != FriendshipStatus.pending:
        raise HTTPException(status_code=400, detail="Request is not pending")

    db.delete(friendship)
    db.commit()
    return {"message": "Friend request cancelled"}


@router.get("")
def list_friends(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    friendships = db.query(Friendship).filter(
        Friendship.status == FriendshipStatus.accepted,
        (Friendship.requester_id == current_user.id) |
        (Friendship.addressee_id == current_user.id)
    ).all()
    return [_friendship_dict(f, current_user.id) for f in friendships]


@router.get("/requests")
def list_incoming_requests(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    friendships = db.query(Friendship).filter(
        Friendship.addressee_id == current_user.id,
        Friendship.status == FriendshipStatus.pending,
    ).all()
    return [_friendship_dict(f, current_user.id) for f in friendships]
