"""
Integration tests for JWT authentication API routes.
"""

import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from app.fenrir_app import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def test_email():
    """Generate unique test email."""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
    return f"test_{timestamp}@example.com"


class TestRegisterEndpoint:
    """Test POST /api/auth/register."""

    def test_register_success(self, client, test_email):
        """Test successful registration."""
        response = client.post(
            "/api/auth/register",
            json={
                "email": test_email,
                "password": "StrongPass123!",
                "username": "testuser",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["email"] == test_email
        assert data["username"] == "testuser"
        assert "password_hash" not in data  # Should not be exposed

    def test_register_duplicate_email(self, client, test_email):
        """Test registration fails with duplicate email."""
        # Register first time
        client.post(
            "/api/auth/register",
            json={
                "email": test_email,
                "password": "StrongPass123!",
                "username": "testuser1",
            },
        )

        # Try again
        response = client.post(
            "/api/auth/register",
            json={
                "email": test_email,
                "password": "AnotherPass456!",
                "username": "testuser2",
            },
        )

        assert response.status_code == 400
        assert "already registered" in response.json()["detail"].lower()

    def test_register_weak_password(self, client, test_email):
        """Test registration fails with weak password."""
        response = client.post(
            "/api/auth/register",
            json={"email": test_email, "password": "weak", "username": "testuser"},
        )

        assert response.status_code == 400

    def test_register_invalid_email(self, client):
        """Test registration fails with invalid email."""
        response = client.post(
            "/api/auth/register",
            json={
                "email": "not_an_email",
                "password": "StrongPass123!",
                "username": "testuser",
            },
        )

        assert response.status_code == 422  # Validation error


class TestLoginEndpoint:
    """Test POST /api/auth/login."""

    def test_login_success(self, client, test_email):
        """Test successful login."""
        # Register user first
        password = "StrongPass123!"
        client.post(
            "/api/auth/register",
            json={"email": test_email, "password": password, "username": "testuser"},
        )

        # Login
        response = client.post(
            "/api/auth/login",
            json={"email": test_email, "password": password, "remember_me": False},
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert data["expires_in"] > 0

    def test_login_wrong_password(self, client, test_email):
        """Test login fails with wrong password."""
        # Register user first
        client.post(
            "/api/auth/register",
            json={
                "email": test_email,
                "password": "StrongPass123!",
                "username": "testuser",
            },
        )

        # Try wrong password
        response = client.post(
            "/api/auth/login",
            json={"email": test_email, "password": "WrongPassword", "remember_me": False},
        )

        assert response.status_code == 401

    def test_login_nonexistent_user(self, client):
        """Test login fails for nonexistent user."""
        response = client.post(
            "/api/auth/login",
            json={
                "email": "nonexistent@example.com",
                "password": "AnyPassword123!",
                "remember_me": False,
            },
        )

        assert response.status_code == 401


class TestRefreshEndpoint:
    """Test POST /api/auth/refresh."""

    def test_refresh_success(self, client, test_email):
        """Test successful token refresh."""
        # Register and login
        password = "StrongPass123!"
        client.post(
            "/api/auth/register",
            json={"email": test_email, "password": password, "username": "testuser"},
        )

        login_response = client.post(
            "/api/auth/login",
            json={"email": test_email, "password": password, "remember_me": False},
        )

        refresh_token = login_response.json()["refresh_token"]

        # Refresh
        response = client.post("/api/auth/refresh", json={"refresh_token": refresh_token})

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["refresh_token"] != refresh_token  # Should be new token
        assert "previous_refresh_token" in data

    def test_refresh_invalid_token(self, client):
        """Test refresh fails with invalid token."""
        response = client.post(
            "/api/auth/refresh", json={"refresh_token": "invalid_token"}
        )

        assert response.status_code == 401

    def test_refresh_reused_token(self, client, test_email):
        """Test refresh fails when token is reused."""
        # Register and login
        password = "StrongPass123!"
        client.post(
            "/api/auth/register",
            json={"email": test_email, "password": password, "username": "testuser"},
        )

        login_response = client.post(
            "/api/auth/login",
            json={"email": test_email, "password": password, "remember_me": False},
        )

        refresh_token = login_response.json()["refresh_token"]

        # Refresh once
        client.post("/api/auth/refresh", json={"refresh_token": refresh_token})

        # Try to reuse
        response = client.post("/api/auth/refresh", json={"refresh_token": refresh_token})

        assert response.status_code == 401


class TestLogoutEndpoints:
    """Test logout endpoints."""

    def test_logout_success(self, client, test_email):
        """Test successful logout."""
        # Register and login
        password = "StrongPass123!"
        client.post(
            "/api/auth/register",
            json={"email": test_email, "password": password, "username": "testuser"},
        )

        login_response = client.post(
            "/api/auth/login",
            json={"email": test_email, "password": password, "remember_me": False},
        )

        access_token = login_response.json()["access_token"]
        refresh_token = login_response.json()["refresh_token"]

        # Logout
        response = client.post(
            "/api/auth/logout",
            json={"refresh_token": refresh_token},
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == 200
        assert response.json()["message"] == "Logged out successfully"

    def test_logout_all_success(self, client, test_email):
        """Test logout from all devices."""
        # Register and login twice
        password = "StrongPass123!"
        client.post(
            "/api/auth/register",
            json={"email": test_email, "password": password, "username": "testuser"},
        )

        login1 = client.post(
            "/api/auth/login",
            json={"email": test_email, "password": password, "remember_me": False},
        )

        login2 = client.post(
            "/api/auth/login",
            json={"email": test_email, "password": password, "remember_me": False},
        )

        access_token = login1.json()["access_token"]

        # Logout all
        response = client.post(
            "/api/auth/logout-all", headers={"Authorization": f"Bearer {access_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["sessions_revoked"] == 2


class TestSessionsEndpoints:
    """Test sessions management endpoints."""

    def test_get_sessions(self, client, test_email):
        """Test getting user sessions."""
        # Register and login multiple times
        password = "StrongPass123!"
        client.post(
            "/api/auth/register",
            json={"email": test_email, "password": password, "username": "testuser"},
        )

        login1 = client.post(
            "/api/auth/login",
            json={"email": test_email, "password": password, "remember_me": False},
        )

        client.post(
            "/api/auth/login",
            json={"email": test_email, "password": password, "remember_me": False},
        )

        access_token = login1.json()["access_token"]

        # Get sessions
        response = client.get(
            "/api/auth/sessions", headers={"Authorization": f"Bearer {access_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "sessions" in data
        assert len(data["sessions"]) == 2

    def test_revoke_session(self, client, test_email):
        """Test revoking specific session."""
        # Register and login twice
        password = "StrongPass123!"
        client.post(
            "/api/auth/register",
            json={"email": test_email, "password": password, "username": "testuser"},
        )

        login1 = client.post(
            "/api/auth/login",
            json={"email": test_email, "password": password, "remember_me": False},
        )

        login2 = client.post(
            "/api/auth/login",
            json={"email": test_email, "password": password, "remember_me": False},
        )

        access_token1 = login1.json()["access_token"]

        # Get session ID from sessions list
        sessions_response = client.get(
            "/api/auth/sessions", headers={"Authorization": f"Bearer {access_token1}"}
        )

        session_id = sessions_response.json()["sessions"][1]["token_id"]

        # Revoke second session
        response = client.delete(
            f"/api/auth/sessions/{session_id}",
            headers={"Authorization": f"Bearer {access_token1}"},
        )

        assert response.status_code == 200


class TestPasswordResetEndpoints:
    """Test password reset endpoints."""

    def test_request_password_reset(self, client, test_email):
        """Test requesting password reset."""
        # Register user
        client.post(
            "/api/auth/register",
            json={
                "email": test_email,
                "password": "StrongPass123!",
                "username": "testuser",
            },
        )

        # Request reset
        response = client.post(
            "/api/auth/password-reset-request", json={"email": test_email}
        )

        assert response.status_code == 200
        assert "email sent" in response.json()["message"].lower()

    def test_reset_password(self, client, test_email):
        """Test password reset completion."""
        # This test would require accessing the reset token from the database
        # or mocking the email service to get the token
        # For now, just verify the endpoint exists and requires valid token
        response = client.post(
            "/api/auth/password-reset",
            json={"reset_token": "fake_token", "new_password": "NewPass456!"},
        )

        # Should fail with invalid token
        assert response.status_code in [400, 404]
