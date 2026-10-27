from argon2 import PasswordHasher
from argon2.exceptions import (
    InvalidHashError,
    VerifyMismatchError,
)

from datetime import datetime, timedelta, timezone

import jwt

from app.core.config import settings

password_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(
    plain_password: str,
    hashed_password: str,
) -> bool:
    try:
        return password_hasher.verify(
            hashed_password,
            plain_password,
        )
    except (VerifyMismatchError, InvalidHashError):
        return False


def create_access_token(user_id: int) -> str:
    if not settings.JWT_SECRET_KEY:
        raise RuntimeError("JWT_SECRET_KEY is not configured")

    expiration = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )

    payload = {
        "sub": str(user_id),
        "exp": expiration,
        "iat": datetime.now(timezone.utc),
    }

    token = jwt.encode(
        payload,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )

    return token