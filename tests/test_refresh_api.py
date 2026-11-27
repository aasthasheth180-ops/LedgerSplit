from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.core.config import settings
from app.models.auth_session import AuthSession
from app.models.refresh_token import RefreshToken
from app.models.user import User


@pytest.fixture
def logged_in_user(client):

    email = f"refresh_api_{uuid4().hex}@example.com"
    password = "SecurePassword123!"

    registration = client.post(
        "/auth/register",
        json={
            "full_name": "Refresh API Test User",
            "email": email,
            "password": password,
        },
    )

    assert registration.status_code == 201

    login = client.post(
        "/auth/login",
        json={
            "email": email,
            "password": password,
        },
    )

    assert login.status_code == 200

    return registration.json()


def test_refresh_success(client, logged_in_user):

    response = client.post("/auth/refresh")

    assert response.status_code == 200

    data = response.json()

    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert "refresh_token" not in data
    assert response.headers["cache-control"] == "no-store"

    profile = client.get(
        "/users/me",
        headers={
            "Authorization": f"Bearer {data['access_token']}"
        },
    )

    assert profile.status_code == 200
    assert profile.json()["id"] == logged_in_user["id"]


def test_refresh_missing_cookie(client):

    client.cookies.clear()

    response = client.post("/auth/refresh")

    assert response.status_code == 401
    assert response.json()["detail"] == (
        "Invalid or expired refresh token"
    )


def test_refresh_invalid_cookie(client):

    client.cookies.clear()

    client.cookies.set(
        settings.REFRESH_COOKIE_NAME,
        "invalid_refresh_token",
        path="/auth",
    )

    response = client.post("/auth/refresh")

    assert response.status_code == 401


@pytest.mark.parametrize(
    "origin",
    [
        "https://untrusted.example.com",
        "null",
        None,
    ],
)
def test_refresh_rejects_untrusted_origin(
    client,
    logged_in_user,
    origin,
):

    request = client.build_request(
        "POST",
        "/auth/refresh",
    )

    if origin is None:
        request.headers.pop("origin", None)
    else:
        request.headers["Origin"] = origin

    response = client.send(request)

    assert response.status_code == 403
    assert response.json()["detail"] == (
        "Untrusted request origin"
    )


def test_refresh_expired_session(
    client,
    db_session,
    logged_in_user,
):

    auth_session = db_session.scalar(
        select(AuthSession).where(
            AuthSession.user_id == logged_in_user["id"]
        )
    )

    assert auth_session is not None

    auth_session.expires_at = (
        datetime.now(timezone.utc) - timedelta(seconds=1)
    )

    db_session.commit()

    response = client.post("/auth/refresh")

    assert response.status_code == 401


def test_refresh_revoked_session(
    client,
    db_session,
    logged_in_user,
):

    auth_session = db_session.scalar(
        select(AuthSession).where(
            AuthSession.user_id == logged_in_user["id"]
        )
    )

    assert auth_session is not None

    auth_session.revoked_at = datetime.now(timezone.utc)

    db_session.commit()

    response = client.post("/auth/refresh")

    assert response.status_code == 401


def test_refresh_used_token(
    client,
    db_session,
    logged_in_user,
):

    auth_session = db_session.scalar(
        select(AuthSession).where(
            AuthSession.user_id == logged_in_user["id"]
        )
    )

    assert auth_session is not None

    refresh_token = db_session.scalar(
        select(RefreshToken).where(
            RefreshToken.session_id == auth_session.id
        )
    )

    assert refresh_token is not None

    refresh_token.used_at = datetime.now(timezone.utc)

    db_session.commit()

    response = client.post("/auth/refresh")

    assert response.status_code == 401


def test_refresh_inactive_user(
    client,
    db_session,
    logged_in_user,
):

    user = db_session.get(
        User,
        logged_in_user["id"],
    )

    assert user is not None

    user.is_active = False

    db_session.commit()

    response = client.post("/auth/refresh")

    assert response.status_code == 401