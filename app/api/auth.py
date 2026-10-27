from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.user import UserCreate, UserResponse
from app.services.user_service import (
    EmailAlreadyRegisteredError,
    create_user,
)

from app.core.security import create_access_token
from app.schemas.user import UserLogin
from app.services.authentication_services import authenticate_user

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_user(
    user_data: UserCreate,
    db: Session = Depends(get_db),
):
    try:
        return create_user(db, user_data)
    except (EmailAlreadyRegisteredError, IntegrityError):
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

@router.post("/login")
def login_user(
    credentials: UserLogin,
    db: Session = Depends(get_db),
):
    user = authenticate_user(
        db=db,
        email=str(credentials.email),
        password=credentials.password,
    )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(user_id=user.id)

    return {
        "access_token": access_token,
        "token_type": "bearer",
    }