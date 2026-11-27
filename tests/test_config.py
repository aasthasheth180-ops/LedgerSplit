import pytest

from app.core.config import Settings


def test_rejects_zero_token_expiration(monkeypatch):
    monkeypatch.setenv("ACCESS_TOKEN_EXPIRE_MINUTES", "0")

    with pytest.raises(ValueError):
        Settings()

def test_rejects_negative_token_expiration(monkeypatch):
    monkeypatch.setenv("ACCESS_TOKEN_EXPIRE_MINUTES", "-10")

    with pytest.raises(ValueError):
        Settings()


def test_rejects_weak_jwt_secret(monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", "abc123")

    with pytest.raises(ValueError):
        Settings()


@pytest.mark.parametrize(
    "invalid_origin",
    [
        "*",
        "null",
        "",
        "example.com",
        "ftp://example.com",
        "https://example.com/path",
        "https://example.com?query=1",
        "https://example.com#fragment",
        "https://user:password@example.com",
        "https://example.com:invalid",
        "https://example.com:99999",
        "https://*.example.com",
        "https://example.com/",
        "https://exam ple.com",
    ],
)
def test_rejects_invalid_trusted_origin(
    monkeypatch,
    invalid_origin,
):
    monkeypatch.setenv(
        "TRUSTED_ORIGINS",
        invalid_origin,
    )

    with pytest.raises(ValueError):
        Settings()


def test_accepts_valid_trusted_origins(monkeypatch):
    monkeypatch.setenv(
        "TRUSTED_ORIGINS",
        "http://localhost:5173,https://example.com",
    )

    config = Settings()

    assert config.TRUSTED_ORIGINS == [
        "http://localhost:5173",
        "https://example.com",
    ]