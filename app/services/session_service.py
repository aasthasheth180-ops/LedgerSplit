from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import (
    generate_refresh_token,
    hash_refresh_token,
)
from app.models.auth_session import AuthSession
from app.models.refresh_token import RefreshToken
from app.models.user import User


class InvalidRefreshTokenError(Exception):
    pass


class RefreshTokenReuseError(InvalidRefreshTokenError):
    pass


def create_auth_session(
    db: Session,
    user_id: int,
    remember_me: bool = False,
) -> tuple[AuthSession, str]:

    now = datetime.now(timezone.utc)

    session_days = (
        settings.REMEMBER_ME_EXPIRE_DAYS
        if remember_me
        else settings.SESSION_EXPIRE_DAYS
    )

    expires_at = now + timedelta(days=session_days)

    auth_session = AuthSession(
        user_id=user_id,
        remember_me=remember_me,
        expires_at=expires_at,
    )

    try:
        db.add(auth_session)
        db.flush()

        raw_refresh_token = generate_refresh_token()

        refresh_token = RefreshToken(
            session_id=auth_session.id,
            token_hash=hash_refresh_token(
                raw_refresh_token
            ),
        )

        db.add(refresh_token)

        db.commit()

    except Exception:
        db.rollback()
        raise

    return auth_session, raw_refresh_token


def validate_refresh_token(
    db: Session,
    raw_refresh_token: str,
) -> tuple[AuthSession, RefreshToken, User]:

    if not raw_refresh_token:
        raise InvalidRefreshTokenError()

    token_hash = hash_refresh_token(raw_refresh_token)

    refresh_token = db.scalar(
        select(RefreshToken).where(
            RefreshToken.token_hash == token_hash
        )
    )

    if refresh_token is None:
        raise InvalidRefreshTokenError()

    auth_session = db.get(
        AuthSession,
        refresh_token.session_id,
    )

    if auth_session is None:
        raise InvalidRefreshTokenError()

    if auth_session.revoked_at is not None:
        raise InvalidRefreshTokenError()

    if auth_session.expires_at <= datetime.now(timezone.utc):
        raise InvalidRefreshTokenError()

    if refresh_token.used_at is not None:
        raise InvalidRefreshTokenError()

    user = db.get(User, auth_session.user_id)

    if user is None or not user.is_active:
        raise InvalidRefreshTokenError()

    return auth_session, refresh_token, user


def rotate_refresh_token(
    db: Session,
    raw_refresh_token: str,
) -> tuple[AuthSession, str, User]:

    try:
        if not raw_refresh_token:
            raise InvalidRefreshTokenError()

        token_hash = hash_refresh_token(raw_refresh_token)

        session_id = db.scalar(
            select(RefreshToken.session_id).where(
                RefreshToken.token_hash == token_hash
            )
        )

        if session_id is None:
            raise InvalidRefreshTokenError()

        auth_session = db.scalar(
            select(AuthSession)
            .where(AuthSession.id == session_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )

        if auth_session is None:
            raise InvalidRefreshTokenError()

        refresh_token = db.scalar(
            select(RefreshToken)
            .where(
                RefreshToken.token_hash == token_hash,
                RefreshToken.session_id == auth_session.id,
            )
            .with_for_update()
            .execution_options(populate_existing=True)
        )

        if refresh_token is None:
            raise InvalidRefreshTokenError()

        now = datetime.now(timezone.utc)

        if auth_session.revoked_at is not None:
            raise InvalidRefreshTokenError()

        if auth_session.expires_at <= now:
            raise InvalidRefreshTokenError()

        if refresh_token.used_at is not None:
            auth_session.revoked_at = now

            db.commit()

            raise RefreshTokenReuseError()

        user = db.get(
            User,
            auth_session.user_id,
            populate_existing=True,
        )

        if user is None or not user.is_active:
            raise InvalidRefreshTokenError()

        new_raw_token = generate_refresh_token()

        new_refresh_token = RefreshToken(
            session_id=auth_session.id,
            token_hash=hash_refresh_token(new_raw_token),
        )

        refresh_token.used_at = now

        db.add(new_refresh_token)

        db.commit()

        return auth_session, new_raw_token, user

    except RefreshTokenReuseError:
        raise

    except Exception:
        db.rollback()
        raise

def revoke_auth_session(
    db: Session,
    raw_refresh_token: str,
) -> bool:

    if not raw_refresh_token:
        return False

    try:
        token_hash = hash_refresh_token(raw_refresh_token)

        session_id = db.scalar(
            select(RefreshToken.session_id).where(
                RefreshToken.token_hash == token_hash
            )
        )

        if session_id is None:
            db.rollback()
            return False

        auth_session = db.scalar(
            select(AuthSession)
            .where(AuthSession.id == session_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )

        if auth_session is None:
            db.rollback()
            return False

        if auth_session.revoked_at is None:
            auth_session.revoked_at = datetime.now(
                timezone.utc
            )

        db.commit()

        return True

    except Exception:
        db.rollback()
        raise