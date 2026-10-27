from datetime import datetime, timedelta, timezone

import jwt

from app.core.config import settings






def test_register_user_success(client):
    response = client.post(
        "/auth/register",
        json={
            "full_name": "Automated Test User",
            "email": "automated@example.com",
            "password": "SecurePassword123!",
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["full_name"] == "Automated Test User"
    assert data["email"] == "automated@example.com"
    assert data["is_active"] is True
    assert isinstance(data["id"], int)
    assert "created_at" in data

    # Sensitive information must not appear in the response.
    assert "password" not in data
    assert "hashed_password" not in data


def test_register_duplicate_email(client):
    user_data = {
        "full_name": "First User",
        "email": "duplicate@example.com",
        "password": "SecurePassword123!",
    }

    first_response = client.post(
        "/auth/register",
        json=user_data,
    )

    assert first_response.status_code == 201

    second_response = client.post(
        "/auth/register",
        json={
            "full_name": "Second User",
            "email": "duplicate@example.com",
            "password": "AnotherPassword123!",
        },
    )

    assert second_response.status_code == 409
    assert second_response.json() == {
        "detail": "Email already registered"
    }


def test_login_success(client):
    client.post(
        "/auth/register",
        json={
            "full_name": "Login Test User",
            "email": "login@example.com",
            "password": "SecurePassword123!",
        },
    )

    response = client.post(
        "/auth/login",
        json={
            "email": "login@example.com",
            "password": "SecurePassword123!",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert "access_token" in data
    assert isinstance(data["access_token"], str)
    assert len(data["access_token"]) > 0
    assert data["token_type"] == "bearer"


def test_login_wrong_password(client):
    client.post(
        "/auth/register",
        json={
            "full_name": "Login Test User",
            "email": "wrongpassword@example.com",
            "password": "SecurePassword123!",
        },
    )

    response = client.post(
        "/auth/login",
        json={
            "email": "wrongpassword@example.com",
            "password": "IncorrectPassword123!",
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"



def test_get_profile_with_valid_token(client):
    register_response = client.post(
        "/auth/register",
        json={
            "full_name": "Profile Test User",
            "email": "profile@example.com",
            "password": "SecurePassword123!",
        },
    )

    assert register_response.status_code == 201

    login_response = client.post(
        "/auth/login",
        json={
            "email": "profile@example.com",
            "password": "SecurePassword123!",
        },
    )

    assert login_response.status_code == 200

    token = login_response.json()["access_token"]

    response = client.get(
        "/users/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200

    data = response.json()

    assert data["email"] == "profile@example.com"
    assert data["full_name"] == "Profile Test User"
    assert data["id"] == register_response.json()["id"]
    assert "hashed_password" not in data


def test_get_profile_without_token(client):
    response = client.get("/users/me")

    assert response.status_code == 401


def test_get_profile_with_invalid_token(client):
    response = client.get(
        "/users/me",
        headers={
            "Authorization": "Bearer invalid.jwt.token"
        },
    )

    assert response.status_code == 401



def test_get_profile_with_expired_token(client):
    expired_time = datetime.now(timezone.utc) - timedelta(
        minutes=10
    )

    expired_token = jwt.encode(
        {
            "sub": "1",
            "iat": expired_time - timedelta(minutes=30),
            "exp": expired_time,
        },
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )

    response = client.get(
        "/users/me",
        headers={
            "Authorization": f"Bearer {expired_token}"
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == (
        "Invalid or expired authentication token"
    )