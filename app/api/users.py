from fastapi import APIRouter, Depends, HTTPException, Response
from datetime import datetime, timezone
from sqlalchemy import select, update
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.auth_session import AuthSession
from app.core.security import hash_password, verify_password
from app.core.cookies import clear_refresh_cookie
from app.core.csrf import require_trusted_origin
from app.schemas.user import ProfileUpdate, Preferences, PasswordChange

from app.api.dependencies import get_current_user
from app.models.user import User
from app.schemas.user import UserResponse


router = APIRouter(
    prefix="/users",
    tags=["Users"],
)


@router.get("/me", response_model=UserResponse)
def get_my_profile(
    current_user: User = Depends(get_current_user),
):
    return current_user

@router.patch("/me", response_model=UserResponse)
def update_profile(payload: ProfileUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    user.full_name = payload.full_name
    db.commit()
    db.refresh(user)
    return user


@router.get("/me/preferences", response_model=Preferences)
def preferences(user: User = Depends(get_current_user)):
    return user


@router.patch("/me/preferences", response_model=Preferences)
def update_preferences(payload: Preferences, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    user.preferred_currency = payload.preferred_currency
    user.reminders_enabled = payload.reminders_enabled
    db.commit()
    db.refresh(user)
    return user


@router.post("/me/change-password", status_code=204, dependencies=[Depends(require_trusted_origin)])
def change_password(payload: PasswordChange, response: Response, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    locked = db.scalar(select(User).where(User.id == user.id).with_for_update().execution_options(populate_existing=True))
    if not locked or not locked.is_active:
        raise HTTPException(403, "Account unavailable")
    if locked.hashed_password is None:
        raise HTTPException(400, "This account uses Google sign-in")
    if not verify_password(payload.current_password, locked.hashed_password):
        raise HTTPException(400, "Current password is incorrect")
    if payload.current_password == payload.new_password:
        raise HTTPException(400, "Choose a different password")
    locked.hashed_password = hash_password(payload.new_password)
    db.execute(update(AuthSession).where(AuthSession.user_id == locked.id, AuthSession.revoked_at.is_(None)).values(revoked_at=datetime.now(timezone.utc)))
    db.commit()
    clear_refresh_cookie(response)
    response.headers["Cache-Control"] = "no-store"
    return response
