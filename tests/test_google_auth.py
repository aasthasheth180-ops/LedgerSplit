import pytest
import jwt

from sqlalchemy import select, func
from dataclasses import replace
from app.core.config import settings
from app.models.user import User
from app.models.oauth_identity import OAuthIdentity

from app.services.google_auth_service import (
    GoogleIdentity,
    InvalidGoogleCredentialError,
    GoogleAuthUnavailableError,
)


@pytest.fixture
def google_identity(monkeypatch):
    identity = GoogleIdentity(
        subject="google-test-subject-001",
        email="googleuser@example.com",
        full_name="Google Test User",
    )

    monkeypatch.setattr(
        "app.api.auth.verify_google_credential",
        lambda credential: replace(
                    identity,
                    nonce=credential,
                ),
    )

    return identity


def google_login(
    client,
    accepted_terms=True,
    remember_me=False,
):
    challenge = client.post("/auth/google/challenge")

    assert challenge.status_code == 200, challenge.text

    nonce = challenge.json()["nonce"]

    return client.post(
        "/auth/google",
        json={
            "credential": nonce,
            "accepted_terms": accepted_terms,
            "remember_me": remember_me,
        },
    )

def test_google_registration(
    client, db_session, google_identity
):
    response = google_login(client)

    assert response.status_code == 200, response.text

    user = db_session.scalar(
        select(User).where(
            User.email == google_identity.email
        )
    )

    assert user is not None
    assert user.full_name == google_identity.full_name
    assert user.hashed_password is None
    assert user.is_active is True

    identity = db_session.scalar(
        select(OAuthIdentity).where(
            OAuthIdentity.user_id == user.id
        )
    )

    assert identity is not None
    assert identity.provider == "google"
    assert identity.provider_subject == google_identity.subject

    assert response.json()["token_type"] == "bearer"


def test_returning_google_user(
    client, db_session, google_identity
):
    first = google_login(client)
    assert first.status_code == 200

    second = google_login(
        client,
        accepted_terms=False,
    )

    assert second.status_code == 200

    user_count = db_session.scalar(
        select(func.count(User.id)).where(
            User.email == google_identity.email
        )
    )

    identity_count = db_session.scalar(
        select(func.count(OAuthIdentity.id)).where(
            OAuthIdentity.provider == "google",
            OAuthIdentity.provider_subject
            == google_identity.subject,
        )
    )

    assert user_count == 1
    assert identity_count == 1


def test_google_registration_requires_terms(
    client, db_session, google_identity
):
    response = google_login(
        client,
        accepted_terms=False,
    )

    assert response.status_code == 400

    user = db_session.scalar(
        select(User).where(
            User.email == google_identity.email
        )
    )

    assert user is None


def test_google_existing_password_account_collision(
    client, db_session, google_identity
):
    registration = client.post(
        "/auth/register",
        json={
            "full_name": "Existing User",
            "email": google_identity.email,
            "password": "SecurePassword123!",
        },
    )

    assert registration.status_code == 201

    response = google_login(client)

    assert response.status_code == 409

    user = db_session.get(
        User,
        registration.json()["id"],
    )

    assert user.hashed_password is not None

    identity = db_session.scalar(
        select(OAuthIdentity).where(
            OAuthIdentity.user_id == user.id
        )
    )

    assert identity is None


def test_inactive_google_user(
    client, db_session, google_identity
):
    assert google_login(client).status_code == 200

    user = db_session.scalar(
        select(User).where(
            User.email == google_identity.email
        )
    )

    user.is_active = False
    db_session.commit()

    response = google_login(client)

    assert response.status_code == 403


def test_google_invalid_credential(client, monkeypatch):
    def reject_credential(credential):
        raise InvalidGoogleCredentialError()

    monkeypatch.setattr(
        "app.api.auth.verify_google_credential",
        reject_credential,
    )

    response = google_login(client)

    assert response.status_code == 401
    assert response.json()["detail"] == (
        "Invalid Google credential"
    )


def test_google_provider_unavailable(client, monkeypatch):
    def unavailable(credential):
        raise GoogleAuthUnavailableError()

    monkeypatch.setattr(
        "app.api.auth.verify_google_credential",
        unavailable,
    )

    response = google_login(client)

    assert response.status_code == 503


def test_google_untrusted_origin(client, google_identity):
    response = client.post(
        "/auth/google",
        headers={
            "Origin": "https://untrusted.example.com",
        },
        json={
            "credential": "mock-google-credential",
            "accepted_terms": True,
        },
    )

    assert response.status_code == 403


def test_google_access_token_and_cookie(
    client, google_identity
):
    response = google_login(client)

    assert response.status_code == 200

    token = response.json()["access_token"]

    payload = jwt.decode(
        token,
        settings.JWT_SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM],
    )

    assert "sub" in payload
    assert "sid" in payload
    assert "exp" in payload

    cookie = response.headers["set-cookie"].lower()

    assert settings.REFRESH_COOKIE_NAME.lower() in cookie
    assert "httponly" in cookie
    assert "samesite=lax" in cookie
    assert "path=/auth" in cookie
    assert "max-age" not in cookie

    assert response.headers["cache-control"] == "no-store"

    profile = client.get(
        "/users/me",
        headers={
            "Authorization": f"Bearer {token}",
        },
    )

    assert profile.status_code == 200
    assert profile.json()["email"] == google_identity.email


def test_google_remember_me(client, google_identity):
    response = google_login(
        client,
        remember_me=True,
    )

    assert response.status_code == 200

    max_age = (
        settings.REMEMBER_ME_EXPIRE_DAYS
        * 24 * 60 * 60
    )

    cookie = response.headers["set-cookie"].lower()

    assert f"max-age={max_age}" in cookie


def test_google_session_refresh_and_logout(
    client, google_identity
):
    login = google_login(client)
    assert login.status_code == 200

    refresh = client.post("/auth/refresh")

    assert refresh.status_code == 200

    token = refresh.json()["access_token"]

    profile = client.get(
        "/users/me",
        headers={
            "Authorization": f"Bearer {token}",
        },
    )

    assert profile.status_code == 200

    logout = client.post("/auth/logout")

    assert logout.status_code == 204

    profile_after_logout = client.get(
        "/users/me",
        headers={
            "Authorization": f"Bearer {token}",
        },
    )

    assert profile_after_logout.status_code == 401

    refresh_after_logout = client.post("/auth/refresh")

    assert refresh_after_logout.status_code == 401


def test_google_only_user_cannot_use_password_login(
    client, google_identity
):
    assert google_login(client).status_code == 200

    response = client.post(
        "/auth/login",
        json={
            "email": google_identity.email,
            "password": "SecurePassword123!",
        },
    )

    assert response.status_code == 401