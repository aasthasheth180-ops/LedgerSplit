from uuid import uuid4

import pytest

from app.core.config import settings
from app.core.security import hash_password
from app.models.user import User
from app.models.auth_session import AuthSession
from app.services.session_service import (
    create_auth_session,
    rotate_refresh_token,
    validate_refresh_token,
    InvalidRefreshTokenError,
    RefreshTokenReuseError,
)


@pytest.fixture
def reuse_session(db_session):

    user = User(
        full_name="Reuse Detection User",
        email=f"reuse_{uuid4().hex}@example.com",
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


def test_reused_token_raises_dedicated_error(
    db_session,
    reuse_session,
):

    _, _, old_token = reuse_session

    rotate_refresh_token(db_session, old_token)

    with pytest.raises(RefreshTokenReuseError):
        rotate_refresh_token(db_session, old_token)


def test_reuse_revokes_authentication_session(
    db_session,
    reuse_session,
):

    _, auth_session, old_token = reuse_session

    session_id = auth_session.id

    rotate_refresh_token(db_session, old_token)

    with pytest.raises(RefreshTokenReuseError):
        rotate_refresh_token(db_session, old_token)

    db_session.expire_all()

    saved_session = db_session.get(
        AuthSession,
        session_id,
    )

    assert saved_session is not None
    assert saved_session.revoked_at is not None


def test_revocation_survives_rollback(
    db_session,
    reuse_session,
):

    _, auth_session, old_token = reuse_session

    session_id = auth_session.id

    rotate_refresh_token(db_session, old_token)

    with pytest.raises(RefreshTokenReuseError):
        rotate_refresh_token(db_session, old_token)

    db_session.rollback()
    db_session.expire_all()

    saved_session = db_session.get(
        AuthSession,
        session_id,
    )

    assert saved_session is not None
    assert saved_session.revoked_at is not None


def test_replacement_token_becomes_invalid(
    db_session,
    reuse_session,
):

    _, _, old_token = reuse_session

    _, new_token, _ = rotate_refresh_token(
        db_session,
        old_token,
    )

    with pytest.raises(RefreshTokenReuseError):
        rotate_refresh_token(db_session, old_token)

    with pytest.raises(InvalidRefreshTokenError):
        validate_refresh_token(db_session, new_token)

    with pytest.raises(InvalidRefreshTokenError):
        rotate_refresh_token(db_session, new_token)


def test_unrelated_session_remains_valid(
    db_session,
    reuse_session,
):

    user, first_session, old_token = reuse_session

    second_session, second_token = create_auth_session(
        db=db_session,
        user_id=user.id,
    )

    rotate_refresh_token(db_session, old_token)

    with pytest.raises(RefreshTokenReuseError):
        rotate_refresh_token(db_session, old_token)

    db_session.refresh(first_session)
    db_session.refresh(second_session)

    assert first_session.revoked_at is not None
    assert second_session.revoked_at is None

    valid_session, _, valid_user = validate_refresh_token(
        db_session,
        second_token,
    )

    assert valid_session.id == second_session.id
    assert valid_user.id == user.id


def test_unknown_token_does_not_revoke_session(
    db_session,
    reuse_session,
):

    _, auth_session, raw_token = reuse_session

    with pytest.raises(InvalidRefreshTokenError):
        rotate_refresh_token(
            db_session,
            "unknown_refresh_token",
        )

    db_session.refresh(auth_session)

    assert auth_session.revoked_at is None

    validate_refresh_token(db_session, raw_token)


def test_repeated_reuse_preserves_revocation_timestamp(
    db_session,
    reuse_session,
):

    _, auth_session, old_token = reuse_session

    rotate_refresh_token(db_session, old_token)

    with pytest.raises(RefreshTokenReuseError):
        rotate_refresh_token(db_session, old_token)

    db_session.refresh(auth_session)

    original_revocation = auth_session.revoked_at

    assert original_revocation is not None

    with pytest.raises(InvalidRefreshTokenError):
        rotate_refresh_token(db_session, old_token)

    db_session.refresh(auth_session)

    assert auth_session.revoked_at == original_revocation


def test_api_reuse_revokes_session(
    client,
    db_session,
    reuse_session,
):

    _, auth_session, old_token = reuse_session

    client.cookies.clear()

    client.cookies.set(
        settings.REFRESH_COOKIE_NAME,
        old_token,
        domain="testserver.local",
        path="/auth",
    )

    response = client.post("/auth/refresh")

    assert response.status_code == 200

    new_token = client.cookies.get(
        settings.REFRESH_COOKIE_NAME,
        domain="testserver.local",
        path="/auth",
    )

    assert new_token is not None
    assert new_token != old_token

    client.cookies.clear()

    client.cookies.set(
        settings.REFRESH_COOKIE_NAME,
        old_token,
        domain="testserver.local",
        path="/auth",
    )

    response = client.post("/auth/refresh")

    assert response.status_code == 401
    assert response.json()["detail"] == (
        "Invalid or expired refresh token"
    )

    db_session.refresh(auth_session)

    assert auth_session.revoked_at is not None

    client.cookies.clear()

    client.cookies.set(
        settings.REFRESH_COOKIE_NAME,
        new_token,
        domain="testserver.local",
        path="/auth",
    )

    response = client.post("/auth/refresh")

    assert response.status_code == 401