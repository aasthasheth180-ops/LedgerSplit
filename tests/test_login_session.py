from uuid import uuid4

import pytest
from sqlalchemy import select

from app.core.config import settings
from app.core.security import hash_refresh_token
from app.models.auth_session import AuthSession
from app.models.refresh_token import RefreshToken


@pytest.fixture
def registered_user(client):

    email = f"login_session_{uuid4().hex}@example.com"
    password = "SecurePassword123!"

    response = client.post(
        "/auth/register",
        json={
            "full_name": "Login Session Test User",
            "email": email,
            "password": password,
        },
    )

    assert response.status_code == 201

    return {
        "id": response.json()["id"],
        "email": email,
        "password": password,
    }


def test_login_creates_database_session(
    client,
    db_session,
    registered_user,
):

    response = client.post(
        "/auth/login",
        json={
            "email": registered_user["email"],
            "password": registered_user["password"],
        },
    )

    assert response.status_code == 200

    auth_session = db_session.scalar(
        select(AuthSession).where(
            AuthSession.user_id == registered_user["id"]
        )
    )

    assert auth_session is not None
    assert auth_session.remember_me is False
    assert auth_session.revoked_at is None

    raw_token = response.cookies.get(
        settings.REFRESH_COOKIE_NAME
    )

    assert raw_token is not None

    saved_token = db_session.scalar(
        select(RefreshToken).where(
            RefreshToken.session_id == auth_session.id
        )
    )

    assert saved_token is not None
    assert saved_token.token_hash == hash_refresh_token(raw_token)
    assert saved_token.used_at is None


@pytest.mark.parametrize("remember_me", [False, True])
def test_login_refresh_cookie(
    client,
    db_session,
    registered_user,
    remember_me,
):

    response = client.post(
        "/auth/login",
        json={
            "email": registered_user["email"],
            "password": registered_user["password"],
            "remember_me": remember_me,
        },
    )

    assert response.status_code == 200

    cookie = response.headers["set-cookie"].lower()

    assert settings.REFRESH_COOKIE_NAME.lower() in cookie
    assert "httponly" in cookie
    assert "samesite=lax" in cookie
    assert "path=/auth" in cookie
    assert "domain=" not in cookie

    if settings.REFRESH_COOKIE_SECURE:
        assert "secure" in cookie
    else:
        assert "secure" not in cookie

    if remember_me:
        expected_age = (
            settings.REMEMBER_ME_EXPIRE_DAYS * 86400
        )
        assert f"max-age={expected_age}" in cookie
    else:
        assert "max-age=" not in cookie
        assert "expires=" not in cookie

    auth_session = db_session.scalar(
        select(AuthSession).where(
            AuthSession.user_id == registered_user["id"]
        )
    )

    assert auth_session is not None
    assert auth_session.remember_me == remember_me


def test_login_does_not_expose_refresh_token(
    client,
    registered_user,
):

    response = client.post(
        "/auth/login",
        json={
            "email": registered_user["email"],
            "password": registered_user["password"],
        },
    )

    assert response.status_code == 200

    data = response.json()

    raw_token = response.cookies.get(
        settings.REFRESH_COOKIE_NAME
    )

    assert raw_token is not None
    assert "access_token" in data
    assert "refresh_token" not in data
    assert raw_token not in response.text
    assert response.headers["cache-control"] == "no-store"


@pytest.mark.parametrize(
    "origin",
    [
        "https://untrusted.example.com",
        "null",
        None,
    ],
)
def test_login_rejects_untrusted_origin(
    client,
    db_session,
    registered_user,
    origin,
):

    request = client.build_request(
        "POST",
        "/auth/login",
        json={
            "email": registered_user["email"],
            "password": registered_user["password"],
        },
    )

    if origin is None:
        request.headers.pop("origin", None)
    else:
        request.headers["Origin"] = origin

    response = client.send(request)

    assert response.status_code == 403
    assert response.json()["detail"] == "Untrusted request origin"
    assert "set-cookie" not in response.headers

    auth_session = db_session.scalar(
        select(AuthSession).where(
            AuthSession.user_id == registered_user["id"]
        )
    )

    assert auth_session is None


def test_failed_login_does_not_create_session(
    client,
    db_session,
    registered_user,
):

    response = client.post(
        "/auth/login",
        json={
            "email": registered_user["email"],
            "password": "IncorrectPassword123!",
        },
    )

    assert response.status_code == 401
    assert "set-cookie" not in response.headers

    auth_session = db_session.scalar(
        select(AuthSession).where(
            AuthSession.user_id == registered_user["id"]
        )
    )

    assert auth_session is None