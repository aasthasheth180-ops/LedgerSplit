from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from threading import Barrier

import pytest

from sqlalchemy import select, delete, func

from app.core.config import settings
from app.core.security import (
    generate_refresh_token,
    hash_refresh_token,
)

from app.models.google_auth_challenge import GoogleAuthChallenge
from app.models.auth_session import AuthSession

from app.services.google_auth_service import GoogleIdentity
from app.services.google_challenge_service import (
    create_google_challenge,
    consume_google_challenge,
    InvalidGoogleChallengeError,
)

from tests.conftest import TestingSessionLocal


COOKIE_NAME = "ledgersplit_google_browser"


@pytest.fixture(autouse=True)
def configure_google(monkeypatch):
    monkeypatch.setattr(
        settings,
        "GOOGLE_CLIENT_ID",
        "test-client.apps.googleusercontent.com",
    )


@pytest.fixture
def mock_google(monkeypatch):
    def verify(credential):
        return GoogleIdentity(
            subject="google-challenge-test",
            email="challengeuser@example.com",
            full_name="Challenge Test User",
            nonce=credential or None,
        )

    monkeypatch.setattr(
        "app.api.auth.verify_google_credential",
        verify,
    )


def issue_challenge(client):
    response = client.post("/auth/google/challenge")

    assert response.status_code == 200, response.text

    return response.json()["nonce"]


def submit_google(client, nonce):
    return client.post(
        "/auth/google",
        json={
            "credential": nonce,
            "accepted_terms": True,
            "remember_me": False,
        },
    )


def test_valid_challenge(client, mock_google):
    nonce = issue_challenge(client)

    response = submit_google(client, nonce)

    assert response.status_code == 200
    assert "access_token" in response.json()


def test_missing_nonce(client, monkeypatch):
    issue_challenge(client)

    monkeypatch.setattr(
        "app.api.auth.verify_google_credential",
        lambda credential: GoogleIdentity(
            subject="missing-nonce-subject",
            email="missingnonce@example.com",
            full_name="Missing Nonce User",
            nonce=None,
        ),
    )

    response = submit_google(client, "mock-token")

    assert response.status_code == 401


def test_missing_browser_cookie(client, mock_google):
    nonce = issue_challenge(client)

    client.cookies.clear()

    response = submit_google(client, nonce)

    assert response.status_code == 401


def test_incorrect_nonce(client, mock_google):
    issue_challenge(client)

    response = submit_google(
        client,
        generate_refresh_token(),
    )

    assert response.status_code == 401


def test_expired_nonce(client, db_session, mock_google):
    nonce = issue_challenge(client)

    challenge = db_session.get(
        GoogleAuthChallenge,
        hash_refresh_token(nonce),
    )

    assert challenge is not None

    challenge.expires_at = (
        datetime.now(timezone.utc)
        - timedelta(seconds=1)
    )

    db_session.commit()

    response = submit_google(client, nonce)

    assert response.status_code == 401


def test_reused_nonce(client, db_session, mock_google):
    nonce = issue_challenge(client)

    first = submit_google(client, nonce)

    assert first.status_code == 200

    sessions_before = db_session.scalar(
        select(func.count(AuthSession.id))
    )

    second = submit_google(client, nonce)

    assert second.status_code == 401

    sessions_after = db_session.scalar(
        select(func.count(AuthSession.id))
    )

    assert sessions_after == sessions_before


def test_different_browser(client, mock_google):
    nonce = issue_challenge(client)

    original_cookie = client.cookies.get(COOKIE_NAME)

    client.cookies.clear()

    client.cookies.set(
        COOKIE_NAME,
        generate_refresh_token(),
        path="/auth/google",
    )

    response = submit_google(client, nonce)

    assert response.status_code == 401

    # The incorrect browser must not consume the challenge.
    client.cookies.clear()

    client.cookies.set(
        COOKIE_NAME,
        original_cookie,
        path="/auth/google",
    )

    original_response = submit_google(client, nonce)

    assert original_response.status_code == 200


def test_concurrent_nonce_consumption():
    browser_token = generate_refresh_token()

    with TestingSessionLocal() as db:
        nonce = create_google_challenge(
            db=db,
            browser_token=browser_token,
        )

    barrier = Barrier(2)

    def consume():
        with TestingSessionLocal() as db:
            barrier.wait(timeout=10)

            try:
                consume_google_challenge(
                    db=db,
                    nonce=nonce,
                    browser_token=browser_token,
                )

                return "success"

            except InvalidGoogleChallengeError:
                return "rejected"

    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            first = executor.submit(consume)
            second = executor.submit(consume)

            results = [
                first.result(timeout=30),
                second.result(timeout=30),
            ]

        assert sorted(results) == [
            "rejected",
            "success",
        ]

    finally:
        with TestingSessionLocal() as db:
            db.execute(
                delete(GoogleAuthChallenge).where(
                    GoogleAuthChallenge.nonce_hash
                    == hash_refresh_token(nonce)
                )
            )

            db.commit()


def test_untrusted_challenge_origin(client):
    response = client.post(
        "/auth/google/challenge",
        headers={
            "Origin": "https://untrusted.example.com",
        },
    )

    assert response.status_code == 403


def test_challenge_cookie_security(client, db_session):
    response = client.post("/auth/google/challenge")

    assert response.status_code == 200

    cookie = response.headers["set-cookie"].lower()

    assert COOKIE_NAME in cookie
    assert "httponly" in cookie
    assert "samesite=lax" in cookie
    assert "path=/auth/google" in cookie
    assert "max-age=300" in cookie

    if settings.REFRESH_COOKIE_SECURE:
        assert "secure" in cookie

    assert response.headers["cache-control"] == "no-store"
    assert response.json()["expires_in"] == 300

    nonce = response.json()["nonce"]

    challenge = db_session.get(
        GoogleAuthChallenge,
        hash_refresh_token(nonce),
    )

    assert challenge is not None
    assert challenge.nonce_hash != nonce

    browser_token = client.cookies.get(COOKIE_NAME)

    assert challenge.browser_token_hash == (
        hash_refresh_token(browser_token)
    )

    assert challenge.browser_token_hash != browser_token