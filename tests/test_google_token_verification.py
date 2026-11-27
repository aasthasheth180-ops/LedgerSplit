import pytest

from google.auth import exceptions

from app.core.config import settings
from app.services.google_auth_service import (
    verify_google_credential,
    InvalidGoogleCredentialError,
    GoogleAuthUnavailableError,
)


@pytest.fixture
def valid_claims(monkeypatch):
    monkeypatch.setattr(
        settings,
        "GOOGLE_CLIENT_ID",
        "test-client.apps.googleusercontent.com",
    )

    return {
        "sub": "google-subject-123",
        "email": "TestUser@example.com",
        "email_verified": True,
        "name": "Google Test User",
    }


def mock_google_verification(monkeypatch, claims):
    monkeypatch.setattr(
        "app.services.google_auth_service.id_token.verify_oauth2_token",
        lambda *args, **kwargs: claims,
    )


def test_valid_google_credential(monkeypatch, valid_claims):
    mock_google_verification(monkeypatch, valid_claims)

    identity = verify_google_credential("mock-token")

    assert identity.subject == "google-subject-123"
    assert identity.email == "testuser@example.com"
    assert identity.full_name == "Google Test User"


@pytest.mark.parametrize(
    "field,value",
    [
        ("sub", None),
        ("sub", ""),
        ("sub", "x" * 256),
        ("email", None),
        ("email", "invalid-email"),
        ("email_verified", False),
        ("email_verified", None),
        ("email_verified", "true"),
    ],
)
def test_invalid_google_claims(
    monkeypatch, valid_claims, field, value
):
    valid_claims[field] = value

    mock_google_verification(monkeypatch, valid_claims)

    with pytest.raises(InvalidGoogleCredentialError):
        verify_google_credential("mock-token")


@pytest.mark.parametrize(
    "message",
    [
        "Token expired",
        "Incorrect token audience",
        "Invalid token signature",
        "Invalid token issuer",
    ],
)
def test_google_verification_rejection(
    monkeypatch, valid_claims, message
):
    def reject_token(*args, **kwargs):
        raise ValueError(message)

    monkeypatch.setattr(
        "app.services.google_auth_service.id_token.verify_oauth2_token",
        reject_token,
    )

    with pytest.raises(InvalidGoogleCredentialError):
        verify_google_credential("mock-token")


def test_google_transport_failure(
    monkeypatch, valid_claims
):
    def transport_failure(*args, **kwargs):
        raise exceptions.TransportError("Network unavailable")

    monkeypatch.setattr(
        "app.services.google_auth_service.id_token.verify_oauth2_token",
        transport_failure,
    )

    with pytest.raises(GoogleAuthUnavailableError):
        verify_google_credential("mock-token")


def test_google_client_id_missing(monkeypatch):
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_ID", "")

    with pytest.raises(GoogleAuthUnavailableError):
        verify_google_credential("mock-token")


def test_google_missing_name(monkeypatch, valid_claims):
    valid_claims.pop("name")

    mock_google_verification(monkeypatch, valid_claims)

    identity = verify_google_credential("mock-token")

    assert identity.full_name == "testuser"


def test_google_long_name(monkeypatch, valid_claims):
    valid_claims["name"] = "A" * 150

    mock_google_verification(monkeypatch, valid_claims)

    identity = verify_google_credential("mock-token")

    assert len(identity.full_name) == 100


def test_google_correct_audience_passed(
    monkeypatch, valid_claims
):
    def verify_token(credential, request, audience):
        assert credential == "mock-token"
        assert audience == settings.GOOGLE_CLIENT_ID
        return valid_claims

    monkeypatch.setattr(
        "app.services.google_auth_service.id_token.verify_oauth2_token",
        verify_token,
    )

    identity = verify_google_credential("mock-token")

    assert identity.subject == valid_claims["sub"]