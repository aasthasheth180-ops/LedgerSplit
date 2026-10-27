import jwt

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.database import get_db
from app.models.user import User


bearer_scheme = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:

    authentication_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired authentication token",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not settings.JWT_SECRET_KEY:
        raise RuntimeError("JWT_SECRET_KEY is not configured")

    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            options={"require": ["sub", "exp", "iat"]},
        )

        user_id = int(payload["sub"])

    except (jwt.InvalidTokenError, ValueError, TypeError):
        raise authentication_error

    if user_id <= 0:
        raise authentication_error

    user = db.get(User, user_id)

    if user is None or not user.is_active:
        raise authentication_error

    return user