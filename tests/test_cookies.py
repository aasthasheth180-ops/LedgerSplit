from http.cookies import SimpleCookie

from fastapi import Response

from app.core.config import settings
from app.core.cookies import (
    set_refresh_cookie,
    clear_refresh_cookie,
)


def get_refresh_cookie(response):
    cookies = SimpleCookie()
    cookies.load(response.headers["set-cookie"])

    return cookies[settings.REFRESH_COOKIE_NAME]


def test_session_cookie_security(monkeypatch):

    monkeypatch.setattr(
        settings, "REFRESH_COOKIE_SECURE", False
    )

    response = Response()

    set_refresh_cookie(response, "example_token")

    cookie = get_refresh_cookie(response)

    assert cookie.value == "example_token"
    assert cookie["httponly"]
    assert cookie["samesite"] == "lax"
    assert cookie["path"] == "/auth"
    assert not cookie["max-age"]
    assert not cookie["expires"]
    assert not cookie["secure"]
    assert not cookie["domain"]


def test_persistent_cookie():

    response = Response()

    set_refresh_cookie(
        response,
        "example_token",
        max_age=2592000,
    )

    cookie = get_refresh_cookie(response)

    assert cookie["max-age"] == "2592000"
    assert cookie["httponly"]


def test_secure_cookie(monkeypatch):

    monkeypatch.setattr(
        settings, "REFRESH_COOKIE_SECURE", True
    )

    response = Response()

    set_refresh_cookie(response, "example_token")

    cookie = get_refresh_cookie(response)

    assert cookie["secure"]
    assert cookie["httponly"]


def test_clear_refresh_cookie():

    response = Response()

    clear_refresh_cookie(response)

    cookie = get_refresh_cookie(response)

    assert cookie.value == ""
    assert cookie["max-age"] == "0"
    assert cookie["expires"]
    assert cookie["path"] == "/auth"
    assert cookie["httponly"]
    assert cookie["samesite"] == "lax"