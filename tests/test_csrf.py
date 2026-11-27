import pytest

from fastapi import HTTPException
from starlette.requests import Request

from app.core.config import settings
from app.core.csrf import require_trusted_origin


def make_request(origin: str | None = None) -> Request:

    headers = []

    if origin is not None:
        headers.append(
            (b"origin", origin.encode())
        )

    return Request({
        "type": "http",
        "method": "POST",
        "headers": headers,
    })


def test_trusted_origin_is_allowed(monkeypatch):

    monkeypatch.setattr(
        settings,
        "TRUSTED_ORIGINS",
        ["http://localhost:5173"],
    )

    request = make_request("http://localhost:5173")

    assert require_trusted_origin(request) is None


@pytest.mark.parametrize(
    "origin",
    [
        "https://untrusted.example",
        "http://localhost:3000",
        "http://localhost:5173.untrusted.example",
        "null",
        None,
    ],
)
def test_untrusted_origin_is_rejected(origin, monkeypatch):

    monkeypatch.setattr(
        settings,
        "TRUSTED_ORIGINS",
        ["http://localhost:5173"],
    )

    request = make_request(origin)

    with pytest.raises(HTTPException) as exc_info:
        require_trusted_origin(request)

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Untrusted request origin"