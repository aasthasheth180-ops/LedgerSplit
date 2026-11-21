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