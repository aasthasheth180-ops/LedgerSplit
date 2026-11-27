from datetime import datetime, timedelta, timezone
from uuid import uuid4

import jwt
import pytest

from app.core.config import settings
from app.core.security import create_access_token
from app.models.auth_session import AuthSession


def decode_token(token):
    return jwt.decode(
        token,
        settings.JWT_SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM],
    )


def encode_token(payload):
    return jwt.encode(
        payload,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


def get_profile(client, token):
    return client.get(
        "/users/me",
        headers={"Authorization": f"Bearer {token}"},
    )


def register_and_login(client):

    email = f"session_jwt_{uuid4().hex}@example.com"
    password = "SecurePassword123!"

    response = client.post(
        "/auth/register",
        json={
            "full_name": "Session JWT Test User",
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

    token = response.json()["access_token"]
    payload = decode_token(token)

    return {
        "user_id": user_id,
        "session_id": int(payload["sid"]),
        "access_token": token,
        "email": email,
        "password": password,
    }


@pytest.fixture
def authenticated_session(client):

    data = register_and_login(client)

    response = get_profile(
        client,
        data["access_token"],
    )

    assert response.status_code == 200

    return data


def test_login_jwt_contains_correct_session(
    db_session,
    authenticated_session,
):

    payload = decode_token(
        authenticated_session["access_token"]
    )

    assert payload["sub"] == str(
        authenticated_session["user_id"]
    )

    auth_session = db_session.get(
        AuthSession,
        int(payload["sid"]),
    )

    assert auth_session is not None
    assert auth_session.user_id == (
        authenticated_session["user_id"]
    )
    assert auth_session.revoked_at is None


def test_valid_session_token_can_access_profile(
    client,
    authenticated_session,
):

    response = get_profile(
        client,
        authenticated_session["access_token"],
    )

    assert response.status_code == 200

    assert response.json()["id"] == (
        authenticated_session["user_id"]
    )


def test_missing_session_id_is_rejected(
    client,
    authenticated_session,
):

    payload = decode_token(
        authenticated_session["access_token"]
    )

    del payload["sid"]

    response = get_profile(
        client,
        encode_token(payload),
    )

    assert response.status_code == 401


@pytest.mark.parametrize(
    "invalid_sid",
    [
        "",
        "invalid",
        "0",
        "-1",
        "1.5",
        "2147483648",
        None,
        123,
        True,
        [],
        {},
    ],
)
def test_invalid_session_id_is_rejected(
    client,
    authenticated_session,
    invalid_sid,
):

    payload = decode_token(
        authenticated_session["access_token"]
    )

    payload["sid"] = invalid_sid

    response = get_profile(
        client,
        encode_token(payload),
    )

    assert response.status_code == 401


def test_nonexistent_session_is_rejected(
    client,
    db_session,
    authenticated_session,
):

    nonexistent_id = 2147483647

    assert db_session.get(
        AuthSession,
        nonexistent_id,
    ) is None

    token = create_access_token(
        user_id=authenticated_session["user_id"],
        session_id=nonexistent_id,
    )

    response = get_profile(client, token)

    assert response.status_code == 401


def test_revoked_session_is_rejected(
    client,
    db_session,
    authenticated_session,
):

    auth_session = db_session.get(
        AuthSession,
        authenticated_session["session_id"],
    )

    auth_session.revoked_at = datetime.now(
        timezone.utc
    )

    db_session.commit()

    response = get_profile(
        client,
        authenticated_session["access_token"],
    )

    assert response.status_code == 401


def test_expired_session_is_rejected(
    client,
    db_session,
    authenticated_session,
):

    auth_session = db_session.get(
        AuthSession,
        authenticated_session["session_id"],
    )

    auth_session.expires_at = (
        datetime.now(timezone.utc)
        - timedelta(seconds=1)
    )

    db_session.commit()

    response = get_profile(
        client,
        authenticated_session["access_token"],
    )

    assert response.status_code == 401


def test_session_ownership_mismatch_is_rejected(
    client,
    authenticated_session,
):

    second_user = register_and_login(client)

    token = create_access_token(
        user_id=authenticated_session["user_id"],
        session_id=second_user["session_id"],
    )

    response = get_profile(client, token)

    assert response.status_code == 401


def test_logout_immediately_invalidates_access_token(
    client,
    authenticated_session,
):

    token = authenticated_session["access_token"]

    assert get_profile(
        client,
        token,
    ).status_code == 200

    response = client.post("/auth/logout")

    assert response.status_code == 204

    # The JWT itself has not expired.
    decode_token(token)

    response = get_profile(client, token)

    assert response.status_code == 401


def test_refresh_preserves_session_id(
    client,
    authenticated_session,
):

    response = client.post("/auth/refresh")

    assert response.status_code == 200

    new_token = response.json()["access_token"]
    payload = decode_token(new_token)

    assert payload["sid"] == str(
        authenticated_session["session_id"]
    )

    assert payload["sub"] == str(
        authenticated_session["user_id"]
    )

    assert get_profile(
        client,
        new_token,
    ).status_code == 200


def test_token_reuse_invalidates_access_tokens(
    client,
    authenticated_session,
):

    from app.core.config import settings

    old_refresh_token = client.cookies.get(
        settings.REFRESH_COOKIE_NAME
    )

    assert old_refresh_token is not None

    original_access_token = (
        authenticated_session["access_token"]
    )

    response = client.post("/auth/refresh")

    assert response.status_code == 200

    new_access_token = response.json()["access_token"]

    assert get_profile(
        client,
        new_access_token,
    ).status_code == 200

    client.cookies.clear()

    client.cookies.set(
        settings.REFRESH_COOKIE_NAME,
        old_refresh_token,
        domain="testserver.local",
        path="/auth",
    )

    response = client.post("/auth/refresh")

    assert response.status_code == 401

    assert get_profile(
        client,
        original_access_token,
    ).status_code == 401

    assert get_profile(
        client,
        new_access_token,
    ).status_code == 401


def test_logout_preserves_other_session_access(
    client,
    authenticated_session,
):

    first_token = authenticated_session["access_token"]

    response = client.post(
        "/auth/login",
        json={
            "email": authenticated_session["email"],
            "password": authenticated_session["password"],
        },
    )

    assert response.status_code == 200

    second_token = response.json()["access_token"]

    assert decode_token(first_token)["sid"] != (
        decode_token(second_token)["sid"]
    )

    assert get_profile(
        client,
        second_token,
    ).status_code == 200

    response = client.post("/auth/logout")

    assert response.status_code == 204

    assert get_profile(
        client,
        second_token,
    ).status_code == 401

    assert get_profile(
        client,
        first_token,
    ).status_code == 200

@pytest.mark.parametrize("claim", ["sub", "sid"])
@pytest.mark.parametrize(
    "format_id",
    [
        "0{}",
        "+{}",
        " {}",
        "{} ",
        "{}\n",
    ],
)
def test_noncanonical_jwt_identifier_is_rejected(
    client,
    authenticated_session,
    claim,
    format_id,
):
    payload = decode_token(
        authenticated_session["access_token"]
    )

    payload[claim] = format_id.format(payload[claim])

    response = get_profile(
        client,
        encode_token(payload),
    )

    assert response.status_code == 401