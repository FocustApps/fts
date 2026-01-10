"""
Tests for user authentication service (registration, login, token refresh, logout).
"""

import pytest
from datetime import datetime, timezone
from fastapi import HTTPException

from app.services.user_auth_service import get_user_auth_service
from app.models.auth_models import RegisterRequest, LoginRequest
from common.service_connections.db_service.models.account_models.auth_user_model import (
    query_auth_user_by_email,
)
from common.service_connections.db_service.database.engine import (
    get_database_session as session,
)


@pytest.fixture
def test_email():
    """Generate unique test email."""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
    return f"test_{timestamp}@example.com"


class TestUserAuthService:
    """Test user authentication service."""

    def test_register_user(self, engine, test_email):
        """Test user registration."""
        auth_service = get_user_auth_service(engine)

        request = RegisterRequest(
            email=test_email, password="StrongPass123!", username="testuser"
        )

        user = auth_service.register_user(request)

        assert user.email == test_email
        assert user.username == "testuser"
        assert user.is_active is True
        assert user.is_admin is False
        assert user.password_hash is not None

    def test_register_user_duplicate_email(self, engine, test_email):
        """Test registration fails with duplicate email."""
        auth_service = get_user_auth_service(engine)

        # Register first user
        request = RegisterRequest(
            email=test_email, password="StrongPass123!", username="testuser1"
        )
        auth_service.register_user(request)

        # Try to register with same email
        with pytest.raises(HTTPException) as exc_info:
            request2 = RegisterRequest(
                email=test_email, password="AnotherPass456!", username="testuser2"
            )
            auth_service.register_user(request2)

        assert exc_info.value.status_code == 400
        assert "already registered" in exc_info.value.detail.lower()

    def test_register_user_weak_password(self, engine, test_email):
        """Test registration fails with weak password."""
        auth_service = get_user_auth_service(engine)

        request = RegisterRequest(email=test_email, password="weak", username="testuser")

        with pytest.raises(HTTPException) as exc_info:
            auth_service.register_user(request)

        assert exc_info.value.status_code == 400

    def test_authenticate_success(self, engine, test_email):
        """Test successful authentication."""
        auth_service = get_user_auth_service(engine)

        # Register user
        password = "StrongPass123!"
        request = RegisterRequest(
            email=test_email, password=password, username="testuser"
        )
        auth_service.register_user(request)

        # Authenticate
        login_request = LoginRequest(
            email=test_email, password=password, remember_me=False
        )

        token_response = auth_service.authenticate(
            login_request, device_info="Test Device", ip_address="127.0.0.1"
        )

        assert token_response.access_token is not None
        assert token_response.refresh_token is not None
        assert token_response.token_type == "bearer"
        assert token_response.expires_in > 0

    def test_authenticate_wrong_password(self, engine, test_email):
        """Test authentication fails with wrong password."""
        auth_service = get_user_auth_service(engine)

        # Register user
        request = RegisterRequest(
            email=test_email, password="StrongPass123!", username="testuser"
        )
        auth_service.register_user(request)

        # Try wrong password
        with pytest.raises(HTTPException) as exc_info:
            login_request = LoginRequest(
                email=test_email, password="WrongPassword", remember_me=False
            )
            auth_service.authenticate(login_request)

        assert exc_info.value.status_code == 401

    def test_authenticate_nonexistent_user(self, engine):
        """Test authentication fails for nonexistent user."""
        auth_service = get_user_auth_service(engine)

        with pytest.raises(HTTPException) as exc_info:
            login_request = LoginRequest(
                email="nonexistent@example.com",
                password="AnyPassword123!",
                remember_me=False,
            )
            auth_service.authenticate(login_request)

        assert exc_info.value.status_code == 401

    def test_refresh_tokens(self, engine, test_email):
        """Test token refresh."""
        auth_service = get_user_auth_service(engine)

        # Register and login
        password = "StrongPass123!"
        request = RegisterRequest(
            email=test_email, password=password, username="testuser"
        )
        user = auth_service.register_user(request)

        login_request = LoginRequest(
            email=test_email, password=password, remember_me=False
        )
        token_response = auth_service.authenticate(login_request)

        # Refresh tokens
        refresh_response = auth_service.refresh_tokens(
            token_response.refresh_token,
            device_info="Test Device",
            ip_address="127.0.0.1",
        )

        assert refresh_response.access_token != token_response.access_token
        assert refresh_response.refresh_token != token_response.refresh_token
        assert refresh_response.previous_refresh_token == token_response.refresh_token

    def test_refresh_token_reuse_detection(self, engine, test_email):
        """Test token reuse detection revokes entire family."""
        auth_service = get_user_auth_service(engine)

        # Register and login
        password = "StrongPass123!"
        request = RegisterRequest(
            email=test_email, password=password, username="testuser"
        )
        user = auth_service.register_user(request)

        login_request = LoginRequest(
            email=test_email, password=password, remember_me=False
        )
        token_response = auth_service.authenticate(login_request)

        # Refresh once
        refresh_response = auth_service.refresh_tokens(token_response.refresh_token)

        # Try to reuse old refresh token (reuse attack)
        with pytest.raises(HTTPException) as exc_info:
            auth_service.refresh_tokens(token_response.refresh_token)

        assert exc_info.value.status_code == 401
        assert "reuse" in exc_info.value.detail.lower()

    def test_logout(self, engine, test_email):
        """Test single device logout."""
        auth_service = get_user_auth_service(engine)

        # Register and login
        password = "StrongPass123!"
        request = RegisterRequest(
            email=test_email, password=password, username="testuser"
        )
        user = auth_service.register_user(request)

        login_request = LoginRequest(
            email=test_email, password=password, remember_me=False
        )
        token_response = auth_service.authenticate(login_request)

        # Logout
        result = auth_service.logout(token_response.refresh_token)
        assert result is True

        # Try to refresh with logged out token
        with pytest.raises(HTTPException):
            auth_service.refresh_tokens(token_response.refresh_token)

    def test_logout_all(self, engine, test_email):
        """Test logout from all devices."""
        auth_service = get_user_auth_service(engine)

        # Register and login twice (two devices)
        password = "StrongPass123!"
        request = RegisterRequest(
            email=test_email, password=password, username="testuser"
        )
        user = auth_service.register_user(request)

        login_request = LoginRequest(
            email=test_email, password=password, remember_me=False
        )

        token1 = auth_service.authenticate(login_request, device_info="Device 1")
        token2 = auth_service.authenticate(login_request, device_info="Device 2")

        # Logout all
        count = auth_service.logout_all(user.auth_user_id)
        assert count == 2

        # Both tokens should be invalid
        with pytest.raises(HTTPException):
            auth_service.refresh_tokens(token1.refresh_token)

        with pytest.raises(HTTPException):
            auth_service.refresh_tokens(token2.refresh_token)

    def test_get_user_sessions(self, engine, test_email):
        """Test getting user sessions."""
        auth_service = get_user_auth_service(engine)

        # Register and login multiple times
        password = "StrongPass123!"
        request = RegisterRequest(
            email=test_email, password=password, username="testuser"
        )
        user = auth_service.register_user(request)

        login_request = LoginRequest(
            email=test_email, password=password, remember_me=False
        )

        auth_service.authenticate(
            login_request, device_info="Device 1", ip_address="192.168.1.1"
        )
        auth_service.authenticate(
            login_request, device_info="Device 2", ip_address="192.168.1.2"
        )

        # Get sessions
        sessions = auth_service.get_user_sessions(user.auth_user_id)

        assert len(sessions) == 2
        assert any(s.device_info == "Device 1" for s in sessions)
        assert any(s.device_info == "Device 2" for s in sessions)

    def test_request_password_reset(self, engine, test_email):
        """Test password reset request."""
        auth_service = get_user_auth_service(engine)

        # Register user
        request = RegisterRequest(
            email=test_email, password="StrongPass123!", username="testuser"
        )
        auth_service.register_user(request)

        # Request reset
        reset_token = auth_service.request_password_reset(test_email)

        assert isinstance(reset_token, str)
        assert len(reset_token) == 64

        # Check user has reset token
        user = query_auth_user_by_email(test_email, session, engine)
        assert user.password_reset_token == reset_token
        assert user.password_reset_expires is not None

    def test_reset_password(self, engine, test_email):
        """Test password reset completion."""
        auth_service = get_user_auth_service(engine)

        # Register user
        old_password = "OldPass123!"
        request = RegisterRequest(
            email=test_email, password=old_password, username="testuser"
        )
        user = auth_service.register_user(request)

        # Request reset
        reset_token = auth_service.request_password_reset(test_email)

        # Reset password
        new_password = "NewPass456!"
        result = auth_service.reset_password(reset_token, new_password)
        assert result is True

        # Old password should not work
        with pytest.raises(HTTPException):
            login_request = LoginRequest(
                email=test_email, password=old_password, remember_me=False
            )
            auth_service.authenticate(login_request)

        # New password should work
        login_request = LoginRequest(
            email=test_email, password=new_password, remember_me=False
        )
        token_response = auth_service.authenticate(login_request)
        assert token_response.access_token is not None
