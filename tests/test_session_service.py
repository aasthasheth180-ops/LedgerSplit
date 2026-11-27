from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.config import settings
from app.core.security import hash_password, hash_refresh_token
from app.models.user import User
from app.models.auth_session import AuthSession
from app.models.refresh_token import RefreshToken
from app.services.session_service import create_auth_session


@pytest.fixture
def session_user(db_session):

    user = User(
        full_name="Session Test User",
        email=f"session_{uuid4().hex}@example.com",
        hashed_password=hash_password("SecurePassword123!"),
        is_active=True,
    )

    db_session.add(user)
    db_session.commit()

    return user


def test_create_auth_session(db_session, session_user):

    auth_session, raw_token = create_auth_session(
        db=db_session,
        user_id=session_user.id,
    )

    db_session.expire_all()

    saved_session = db_session.get(
        AuthSession,
        auth_session.id,
    )

    assert saved_session is not None
    assert saved_session.user_id == session_user.id
    assert saved_session.remember_me is False
    assert saved_session.revoked_at is None
    assert len(raw_token) == 43


@pytest.mark.parametrize("remember_me", [False, True])
def test_session_expiration(
    db_session,
    session_user,
    remember_me,
):

    expected_days = (
        settings.REMEMBER_ME_EXPIRE_DAYS
        if remember_me
        else settings.SESSION_EXPIRE_DAYS
    )

    before = datetime.now(timezone.utc)

    auth_session, _ = create_auth_session(
        db=db_session,
        user_id=session_user.id,
        remember_me=remember_me,
    )

    after = datetime.now(timezone.utc)

    db_session.refresh(auth_session)

    assert auth_session.remember_me == remember_me

    assert (
        before + timedelta(days=expected_days)
        <= auth_session.expires_at
        <= after + timedelta(days=expected_days)
    )


def test_refresh_token_is_stored_as_hash(
    db_session,
    session_user,
):

    auth_session, raw_token = create_auth_session(
        db=db_session,
        user_id=session_user.id,
    )

    saved_token = db_session.scalar(
        select(RefreshToken).where(
            RefreshToken.session_id == auth_session.id
        )
    )

    assert saved_token is not None
    assert saved_token.token_hash == hash_refresh_token(raw_token)
    assert saved_token.token_hash != raw_token
    assert len(saved_token.token_hash) == 64
    assert saved_token.used_at is None


def test_multiple_sessions_have_unique_tokens(
    db_session,
    session_user,
):

    first_session, first_token = create_auth_session(
        db=db_session,
        user_id=session_user.id,
    )

    second_session, second_token = create_auth_session(
        db=db_session,
        user_id=session_user.id,
    )

    assert first_session.id != second_session.id
    assert first_token != second_token

    assert (
        hash_refresh_token(first_token)
        != hash_refresh_token(second_token)
    )


def test_session_creation_rolls_back_on_token_failure(
    db_session,
    session_user,
    monkeypatch,
):

    user_id = session_user.id

    fixed_token = "fixed_refresh_token_for_rollback_test"

    monkeypatch.setattr(
        "app.services.session_service.generate_refresh_token",
        lambda: fixed_token,
    )

    first_session, _ = create_auth_session(
        db=db_session,
        user_id=user_id,
    )

    first_session_id = first_session.id

    # Force a duplicate token hash.
    with pytest.raises(IntegrityError):
        create_auth_session(
            db=db_session,
            user_id=user_id,
        )

    sessions = db_session.scalars(
        select(AuthSession).where(
            AuthSession.user_id == user_id
        )
    ).all()

    assert len(sessions) == 1
    assert sessions[0].id == first_session_id

    tokens = db_session.scalars(
        select(RefreshToken).where(
            RefreshToken.session_id == first_session_id
        )
    ).all()

    assert len(tokens) == 1
    assert tokens[0].token_hash == hash_refresh_token(fixed_token)

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
            raise InvalidRefreshTokenError()

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

    except Exception:
        db.rollback()
        raise