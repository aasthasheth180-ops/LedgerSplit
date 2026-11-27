from datetime import datetime, timedelta, timezone
from http.cookies import SimpleCookie
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.core.config import settings
from app.core.security import hash_refresh_token
from app.models.auth_session import AuthSession
from app.models.refresh_token import RefreshToken


@pytest.fixture
def login_user(client):

    def login(remember_me=False):

        email = f"rotation_api_{uuid4().hex}@example.com"
        password = "SecurePassword123!"

        registration = client.post(
            "/auth/register",
            json={
                "full_name": "Rotation API User",
                "email": email,
                "password": password,
            },
        )

        assert registration.status_code == 201

        response = client.post(
            "/auth/login",
            json={
                "email": email,
                "password": password,
                "remember_me": remember_me,
            },
        )

        assert response.status_code == 200

        return registration.json()

    return login


def test_refresh_replaces_cookie(client, login_user):

    login_user()

    old_token = client.cookies.get(
        settings.REFRESH_COOKIE_NAME
    )

    response = client.post("/auth/refresh")

    assert response.status_code == 200

    new_token = client.cookies.get(
        settings.REFRESH_COOKIE_NAME
    )

    assert old_token is not None
    assert new_token is not None
    assert new_token != old_token
    assert "set-cookie" in response.headers


def test_refresh_invalidates_old_cookie(
    client,
    login_user,
):

    login_user()

    old_token = client.cookies.get(
        settings.REFRESH_COOKIE_NAME
    )

    response = client.post("/auth/refresh")

    assert response.status_code == 200

    client.cookies.clear()

    client.cookies.set(
        settings.REFRESH_COOKIE_NAME,
        old_token,
        path="/auth",
    )

    response = client.post("/auth/refresh")

    assert response.status_code == 401


def test_refresh_persists_rotated_token(
    client,
    db_session,
    login_user,
):

    user = login_user()

    old_token = client.cookies.get(
        settings.REFRESH_COOKIE_NAME
    )

    response = client.post("/auth/refresh")

    assert response.status_code == 200

    new_token = client.cookies.get(
        settings.REFRESH_COOKIE_NAME
    )

    auth_session = db_session.scalar(
        select(AuthSession).where(
            AuthSession.user_id == user["id"]
        )
    )

    assert auth_session is not None

    tokens = db_session.scalars(
        select(RefreshToken).where(
            RefreshToken.session_id == auth_session.id
        )
    ).all()

    assert len(tokens) == 2

    token_map = {
        token.token_hash: token
        for token in tokens
    }

    assert token_map[
        hash_refresh_token(old_token)
    ].used_at is not None

    assert token_map[
        hash_refresh_token(new_token)
    ].used_at is None


def test_refresh_preserves_session_cookie(
    client,
    login_user,
):

    login_user(remember_me=False)

    response = client.post("/auth/refresh")

    assert response.status_code == 200

    cookies = SimpleCookie()
    cookies.load(response.headers["set-cookie"])

    cookie = cookies[settings.REFRESH_COOKIE_NAME]

    assert cookie["httponly"]
    assert cookie["samesite"].lower() == "lax"
    assert cookie["path"] == "/auth"
    assert cookie["max-age"] == ""
    assert cookie["expires"] == ""


def test_refresh_preserves_remaining_cookie_lifetime(
    client,
    db_session,
    login_user,
):

    user = login_user(remember_me=True)

    auth_session = db_session.scalar(
        select(AuthSession).where(
            AuthSession.user_id == user["id"]
        )
    )

    assert auth_session is not None

    auth_session.expires_at = (
        datetime.now(timezone.utc)
        + timedelta(hours=2)
    )

    db_session.commit()

    original_expiration = auth_session.expires_at

    response = client.post("/auth/refresh")

    assert response.status_code == 200

    cookies = SimpleCookie()
    cookies.load(response.headers["set-cookie"])

    cookie = cookies[settings.REFRESH_COOKIE_NAME]

    max_age = int(cookie["max-age"])

    assert 0 < max_age <= 7200

    db_session.refresh(auth_session)

    assert auth_session.expires_at == original_expiration


def test_multiple_successful_api_refreshes(
    client,
    login_user,
):

    login_user()

    tokens = {
        client.cookies.get(settings.REFRESH_COOKIE_NAME)
    }

    for _ in range(3):

        response = client.post("/auth/refresh")

        assert response.status_code == 200

        new_token = client.cookies.get(
            settings.REFRESH_COOKIE_NAME
        )

        assert new_token is not None
        assert new_token not in tokens
        assert new_token not in response.text

        tokens.add(new_token)

    assert len(tokens) == 4