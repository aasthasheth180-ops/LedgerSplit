from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.core.security import hash_password, hash_refresh_token
from app.models.user import User
from app.models.refresh_token import RefreshToken
from app.services.session_service import (
    create_auth_session,
    validate_refresh_token,
    InvalidRefreshTokenError,
)


@pytest.fixture
def refresh_session(db_session):

    user = User(
        full_name="Refresh Validation User",
        email=f"refresh_{uuid4().hex}@example.com",
        hashed_password=hash_password("SecurePassword123!"),
        is_active=True,
    )

    db_session.add(user)
    db_session.commit()

    auth_session, raw_token = create_auth_session(
        db=db_session,
        user_id=user.id,
    )

    return user, auth_session, raw_token


def test_valid_refresh_token(db_session, refresh_session):

    user, auth_session, raw_token = refresh_session

    saved_session, saved_token, saved_user = validate_refresh_token(
        db=db_session,
        raw_refresh_token=raw_token,
    )

    assert saved_session.id == auth_session.id
    assert saved_user.id == user.id
    assert saved_token.session_id == auth_session.id
    assert saved_token.token_hash == hash_refresh_token(raw_token)
    assert saved_token.used_at is None


@pytest.mark.parametrize(
    "raw_token",
    ["", "invalid_refresh_token"],
)
def test_invalid_refresh_token(db_session, raw_token):

    with pytest.raises(InvalidRefreshTokenError):
        validate_refresh_token(
            db=db_session,
            raw_refresh_token=raw_token,
        )


def test_expired_session(db_session, refresh_session):

    _, auth_session, raw_token = refresh_session

    auth_session.expires_at = (
        datetime.now(timezone.utc) - timedelta(seconds=1)
    )

    db_session.commit()

    with pytest.raises(InvalidRefreshTokenError):
        validate_refresh_token(
            db=db_session,
            raw_refresh_token=raw_token,
        )


def test_revoked_session(db_session, refresh_session):

    _, auth_session, raw_token = refresh_session

    auth_session.revoked_at = datetime.now(timezone.utc)

    db_session.commit()

    with pytest.raises(InvalidRefreshTokenError):
        validate_refresh_token(
            db=db_session,
            raw_refresh_token=raw_token,
        )


def test_used_refresh_token(db_session, refresh_session):

    _, auth_session, raw_token = refresh_session

    saved_token = db_session.scalar(
        select(RefreshToken).where(
            RefreshToken.session_id == auth_session.id
        )
    )

    assert saved_token is not None

    saved_token.used_at = datetime.now(timezone.utc)

    db_session.commit()

    with pytest.raises(InvalidRefreshTokenError):
        validate_refresh_token(
            db=db_session,
            raw_refresh_token=raw_token,
        )


def test_inactive_user(db_session, refresh_session):

    user, _, raw_token = refresh_session

    user.is_active = False

    db_session.commit()

    with pytest.raises(InvalidRefreshTokenError):
        validate_refresh_token(
            db=db_session,
            raw_refresh_token=raw_token,
        )