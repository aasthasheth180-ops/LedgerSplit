from uuid import uuid4

import pytest

from app.core.security import hash_password
from app.models.user import User
from app.models.auth_session import AuthSession

from app.services.session_service import (
    create_auth_session,
    revoke_auth_session,
    validate_refresh_token,
    rotate_refresh_token,
    InvalidRefreshTokenError,
)


@pytest.fixture
def revocation_session(db_session):

    user = User(
        full_name="Session Revocation User",
        email=f"revocation_{uuid4().hex}@example.com",
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


def test_revoke_session(
    db_session,
    revocation_session,
):

    _, auth_session, raw_token = revocation_session

    result = revoke_auth_session(db_session, raw_token)

    assert result is True

    db_session.refresh(auth_session)

    assert auth_session.revoked_at is not None


def test_revocation_persists_after_rollback(
    db_session,
    revocation_session,
):

    _, auth_session, raw_token = revocation_session

    session_id = auth_session.id

    revoke_auth_session(db_session, raw_token)

    db_session.rollback()
    db_session.expire_all()

    saved_session = db_session.get(
        AuthSession,
        session_id,
    )

    assert saved_session is not None
    assert saved_session.revoked_at is not None


def test_revoked_token_cannot_be_validated(
    db_session,
    revocation_session,
):

    _, _, raw_token = revocation_session

    revoke_auth_session(db_session, raw_token)

    with pytest.raises(InvalidRefreshTokenError):
        validate_refresh_token(db_session, raw_token)


def test_revoked_token_cannot_be_rotated(
    db_session,
    revocation_session,
):

    _, _, raw_token = revocation_session

    revoke_auth_session(db_session, raw_token)

    with pytest.raises(InvalidRefreshTokenError):
        rotate_refresh_token(db_session, raw_token)


def test_repeated_revocation_is_safe(
    db_session,
    revocation_session,
):

    _, auth_session, raw_token = revocation_session

    assert revoke_auth_session(
        db_session,
        raw_token,
    ) is True

    db_session.refresh(auth_session)

    original_revocation = auth_session.revoked_at

    assert original_revocation is not None

    assert revoke_auth_session(
        db_session,
        raw_token,
    ) is True

    db_session.refresh(auth_session)

    assert auth_session.revoked_at == original_revocation


def test_missing_refresh_token(db_session):

    result = revoke_auth_session(db_session, "")

    assert result is False


def test_unknown_refresh_token(
    db_session,
    revocation_session,
):

    _, auth_session, raw_token = revocation_session

    result = revoke_auth_session(
        db_session,
        "unknown_refresh_token",
    )

    assert result is False

    db_session.refresh(auth_session)

    assert auth_session.revoked_at is None

    validate_refresh_token(db_session, raw_token)


def test_unrelated_session_remains_active(
    db_session,
    revocation_session,
):

    user, first_session, first_token = revocation_session

    second_session, second_token = create_auth_session(
        db=db_session,
        user_id=user.id,
    )

    revoke_auth_session(db_session, first_token)

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


def test_rotated_token_can_revoke_session(
    db_session,
    revocation_session,
):

    _, auth_session, old_token = revocation_session

    _, new_token, _ = rotate_refresh_token(
        db_session,
        old_token,
    )

    result = revoke_auth_session(
        db_session,
        old_token,
    )

    assert result is True

    db_session.refresh(auth_session)

    assert auth_session.revoked_at is not None

    with pytest.raises(InvalidRefreshTokenError):
        validate_refresh_token(db_session, new_token)