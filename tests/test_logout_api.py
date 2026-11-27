from uuid import uuid4
from http.cookies import SimpleCookie

import pytest

from sqlalchemy import select

from app.core.config import settings
from app.models.auth_session import AuthSession
from app.models.refresh_token import RefreshToken
from app.core.security import hash_refresh_token


@pytest.fixture
def logged_in_user(client, db_session):

    email = f"logout_{uuid4().hex}@example.com"
    password = "SecurePassword123!"

    response = client.post(
        "/auth/register",
        json={
            "full_name": "Logout Test User",
            "email": email,
            "password": password,
        },
    )

    assert response.status_code == 201

    user_id = response.json()["id"]

    response = client.post(
        "/auth/login",
        json={
            "email": email,
            "password": password,
        },
    )

    assert response.status_code == 200

    raw_token = client.cookies.get(
        settings.REFRESH_COOKIE_NAME
    )

    assert raw_token is not None

    refresh_token = db_session.scalar(
        select(RefreshToken).where(
            RefreshToken.token_hash
            == hash_refresh_token(raw_token)
        )
    )

    assert refresh_token is not None

    return {
        "user_id": user_id,
        "email": email,
        "password": password,
        "raw_token": raw_token,
        "session_id": refresh_token.session_id,
    }


def test_logout_returns_204(client, logged_in_user):

    response = client.post("/auth/logout")

    assert response.status_code == 204
    assert response.content == b""


def test_logout_revokes_database_session(
    client,
    db_session,
    logged_in_user,
):

    response = client.post("/auth/logout")

    assert response.status_code == 204

    db_session.expire_all()

    auth_session = db_session.get(
        AuthSession,
        logged_in_user["session_id"],
    )

    assert auth_session is not None
    assert auth_session.revoked_at is not None


def test_logout_clears_refresh_cookie(
    client,
    logged_in_user,
):

    response = client.post("/auth/logout")

    assert response.status_code == 204

    cookie = SimpleCookie()
    cookie.load(response.headers["set-cookie"])

    refresh_cookie = cookie[
        settings.REFRESH_COOKIE_NAME
    ]

    assert refresh_cookie.value == ""
    assert refresh_cookie["max-age"] == "0"
    assert refresh_cookie["path"] == settings.REFRESH_COOKIE_PATH
    assert refresh_cookie["httponly"]
    assert refresh_cookie["samesite"].lower() == (
        settings.REFRESH_COOKIE_SAMESITE.lower()
    )
    assert bool(refresh_cookie["secure"]) == (
        settings.REFRESH_COOKIE_SECURE
    )

    assert client.cookies.get(
        settings.REFRESH_COOKIE_NAME
    ) is None


def test_logout_prevents_refresh(
    client,
    logged_in_user,
):

    response = client.post("/auth/logout")

    assert response.status_code == 204

    response = client.post("/auth/refresh")

    assert response.status_code == 401


def test_logged_out_token_cannot_be_reused(
    client,
    logged_in_user,
):

    response = client.post("/auth/logout")

    assert response.status_code == 204

    client.cookies.clear()

    client.cookies.set(
        settings.REFRESH_COOKIE_NAME,
        logged_in_user["raw_token"],
        domain="testserver.local",
        path="/auth",
    )

    response = client.post("/auth/refresh")

    assert response.status_code == 401


def test_repeated_logout_is_safe(
    client,
    db_session,
    logged_in_user,
):

    response = client.post("/auth/logout")

    assert response.status_code == 204

    auth_session = db_session.get(
        AuthSession,
        logged_in_user["session_id"],
    )

    db_session.refresh(auth_session)

    original_revocation = auth_session.revoked_at

    assert original_revocation is not None

    client.cookies.set(
        settings.REFRESH_COOKIE_NAME,
        logged_in_user["raw_token"],
        domain="testserver.local",
        path="/auth",
    )

    response = client.post("/auth/logout")

    assert response.status_code == 204

    db_session.refresh(auth_session)

    assert auth_session.revoked_at == original_revocation


def test_logout_without_cookie(client):

    client.cookies.clear()

    response = client.post("/auth/logout")

    assert response.status_code == 204
    assert "max-age=0" in response.headers[
        "set-cookie"
    ].lower()


def test_logout_with_invalid_cookie(client):

    client.cookies.clear()

    client.cookies.set(
        settings.REFRESH_COOKIE_NAME,
        "invalid_refresh_token",
        domain="testserver.local",
        path="/auth",
    )

    response = client.post("/auth/logout")

    assert response.status_code == 204

    assert client.cookies.get(
        settings.REFRESH_COOKIE_NAME
    ) is None


@pytest.mark.parametrize(
    "origin",
    [
        "https://untrusted.example.com",
        "null",
        None,
    ],
)
def test_logout_rejects_untrusted_origin(
    client,
    db_session,
    logged_in_user,
    origin,
):

    request = client.build_request(
        "POST",
        "/auth/logout",
    )

    if origin is None:
        request.headers.pop("origin", None)
    else:
        request.headers["Origin"] = origin

    response = client.send(request)

    assert response.status_code == 403

    db_session.expire_all()

    auth_session = db_session.get(
        AuthSession,
        logged_in_user["session_id"],
    )

    assert auth_session.revoked_at is None

    assert "set-cookie" not in response.headers


def test_logout_response_is_not_cached(
    client,
    logged_in_user,
):

    response = client.post("/auth/logout")

    assert response.status_code == 204
    assert response.headers["cache-control"] == "no-store"


def test_logout_does_not_revoke_other_sessions(
    client,
    db_session,
    logged_in_user,
):

    first_session_id = logged_in_user["session_id"]
    first_token = logged_in_user["raw_token"]

    response = client.post(
        "/auth/login",
        json={
            "email": logged_in_user["email"],
            "password": logged_in_user["password"],
        },
    )

    assert response.status_code == 200

    second_token = client.cookies.get(
        settings.REFRESH_COOKIE_NAME
    )

    assert second_token is not None
    assert second_token != first_token

    second_refresh_token = db_session.scalar(
        select(RefreshToken).where(
            RefreshToken.token_hash
            == hash_refresh_token(second_token)
        )
    )

    second_session_id = second_refresh_token.session_id

    assert second_session_id != first_session_id

    response = client.post("/auth/logout")

    assert response.status_code == 204

    db_session.expire_all()

    first_session = db_session.get(
        AuthSession,
        first_session_id,
    )

    second_session = db_session.get(
        AuthSession,
        second_session_id,
    )

    assert first_session.revoked_at is None
    assert second_session.revoked_at is not None

    client.cookies.clear()

    client.cookies.set(
        settings.REFRESH_COOKIE_NAME,
        first_token,
        domain="testserver.local",
        path="/auth",
    )

    response = client.post("/auth/refresh")

    assert response.status_code == 200