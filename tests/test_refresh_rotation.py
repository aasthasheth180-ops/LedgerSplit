from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.security import hash_password, hash_refresh_token
from app.models.user import User
from app.models.auth_session import AuthSession
from app.models.refresh_token import RefreshToken
from app.services.session_service import (
    create_auth_session,
    rotate_refresh_token,
    validate_refresh_token,
    InvalidRefreshTokenError,
)


@pytest.fixture
def rotation_session(db_session):

    user = User(
        full_name="Rotation Test User",
        email=f"rotation_{uuid4().hex}@example.com",
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


def test_rotation_generates_new_token(
    db_session,
    rotation_session,
):

    user, auth_session, old_token = rotation_session

    rotated_session, new_token, rotated_user = (
        rotate_refresh_token(
            db=db_session,
            raw_refresh_token=old_token,
        )
    )

    assert new_token != old_token
    assert rotated_session.id == auth_session.id
    assert rotated_user.id == user.id


def test_rotation_marks_old_token_as_used(
    db_session,
    rotation_session,
):

    _, _, old_token = rotation_session

    rotate_refresh_token(
        db=db_session,
        raw_refresh_token=old_token,
    )

    saved_token = db_session.scalar(
        select(RefreshToken).where(
            RefreshToken.token_hash == hash_refresh_token(old_token)
        )
    )

    assert saved_token is not None
    assert saved_token.used_at is not None


def test_rotation_persists_new_token_hash(
    db_session,
    rotation_session,
):

    _, auth_session, old_token = rotation_session

    _, new_token, _ = rotate_refresh_token(
        db=db_session,
        raw_refresh_token=old_token,
    )

    saved_token = db_session.scalar(
        select(RefreshToken).where(
            RefreshToken.token_hash == hash_refresh_token(new_token)
        )
    )

    assert saved_token is not None
    assert saved_token.session_id == auth_session.id
    assert saved_token.used_at is None
    assert saved_token.token_hash != new_token


def test_rotation_preserves_session_expiration(
    db_session,
    rotation_session,
):

    _, auth_session, old_token = rotation_session

    original_expiration = auth_session.expires_at

    rotated_session, _, _ = rotate_refresh_token(
        db=db_session,
        raw_refresh_token=old_token,
    )

    assert rotated_session.expires_at == original_expiration


def test_rotation_rejects_old_token(
    db_session,
    rotation_session,
):

    _, _, old_token = rotation_session

    rotate_refresh_token(
        db=db_session,
        raw_refresh_token=old_token,
    )

    with pytest.raises(InvalidRefreshTokenError):

        rotate_refresh_token(
            db=db_session,
            raw_refresh_token=old_token,
        )


def test_rotated_token_is_valid(
    db_session,
    rotation_session,
):

    user, auth_session, old_token = rotation_session

    _, new_token, _ = rotate_refresh_token(
        db=db_session,
        raw_refresh_token=old_token,
    )

    saved_session, saved_token, saved_user = (
        validate_refresh_token(
            db=db_session,
            raw_refresh_token=new_token,
        )
    )

    assert saved_session.id == auth_session.id
    assert saved_user.id == user.id
    assert saved_token.used_at is None


def test_multiple_rotations(
    db_session,
    rotation_session,
):

    _, auth_session, first_token = rotation_session

    _, second_token, _ = rotate_refresh_token(
        db=db_session,
        raw_refresh_token=first_token,
    )

    _, third_token, _ = rotate_refresh_token(
        db=db_session,
        raw_refresh_token=second_token,
    )

    assert len({first_token, second_token, third_token}) == 3

    tokens = db_session.scalars(
        select(RefreshToken).where(
            RefreshToken.session_id == auth_session.id
        )
    ).all()

    assert len(tokens) == 3

    active_tokens = [
        token for token in tokens
        if token.used_at is None
    ]

    assert len(active_tokens) == 1

    assert active_tokens[0].token_hash == (
        hash_refresh_token(third_token)
    )


def test_rotation_rolls_back_on_failure(
    db_session,
    rotation_session,
    monkeypatch,
):

    _, auth_session, old_token = rotation_session

    session_id = auth_session.id

    monkeypatch.setattr(
        "app.services.session_service.generate_refresh_token",
        lambda: old_token,
    )

    with pytest.raises(IntegrityError):

        rotate_refresh_token(
            db=db_session,
            raw_refresh_token=old_token,
        )

    db_session.expire_all()

    saved_session, saved_token, _ = (
        validate_refresh_token(
            db=db_session,
            raw_refresh_token=old_token,
        )
    )

    assert saved_session.id == session_id
    assert saved_token.used_at is None

    tokens = db_session.scalars(
        select(RefreshToken).where(
            RefreshToken.session_id == session_id
        )
    ).all()

    assert len(tokens) == 1