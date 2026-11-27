from datetime import datetime, timezone

import jwt

from fastapi import Depends, HTTPException, status
from fastapi.security import (
    HTTPBearer,
    HTTPAuthorizationCredentials,
)
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.database import get_db
from app.models.user import User
from app.models.auth_session import AuthSession


bearer_scheme = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(
        bearer_scheme
    ),
    db: Session = Depends(get_db),
) -> User:

    authentication_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired authentication token",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not settings.JWT_SECRET_KEY:
        raise RuntimeError(
            "JWT_SECRET_KEY is not configured"
        )

    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            options={
                "require": [
                    "sub",
                    "sid",
                    "exp",
                    "iat",
                ]
            },
        )

        raw_user_id = payload["sub"]
        raw_session_id = payload["sid"]

        if not isinstance(raw_user_id, str):
            raise authentication_error

        if not isinstance(raw_session_id, str):
            raise authentication_error

        user_id = int(raw_user_id)
        session_id = int(raw_session_id)

        if raw_user_id != str(user_id):
            raise authentication_error

        if raw_session_id != str(session_id):
            raise authentication_error

    except (jwt.InvalidTokenError, ValueError, TypeError):
        raise authentication_error

    if not 0 < user_id <= 2147483647:
        raise authentication_error

    if not 0 < session_id <= 2147483647:
        raise authentication_error

    auth_session = db.get(
        AuthSession,
        session_id,
        populate_existing=True,
    )

    if auth_session is None:
        raise authentication_error

    if auth_session.user_id != user_id:
        raise authentication_error

    if auth_session.revoked_at is not None:
        raise authentication_error

    if auth_session.expires_at <= datetime.now(timezone.utc):
        raise authentication_error

    user = db.get(
        User,
        user_id,
        populate_existing=True,
    )

    if user is None or not user.is_active:
        raise authentication_error

    return user