"""
Comprehensive test suite for multi-user authentication system.

This test suite includes:
- Database operations testing
- CRUD operations for auth users
- Email service mocking and verification
- Authentication flow testing
- API endpoint testing
- Error handling validation
"""

import asyncio
import random
from unittest.mock import patch
from datetime import datetime, timezone
from contextlib import contextmanager

import pytest

from app.services.multi_user_auth_service import (
    get_multi_user_auth_service,
    MultiUserAuthError,
)
from app.services.email_service import EmailServiceError
from common.service_connections.db_service.database import (
    get_database_session,
    AuthUserTable,
)
from common.service_connections.db_service.db_manager import DB_ENGINE
from common.app_logging import create_logging

logger = create_logging()


def generate_random_test_email(prefix="test"):
    """Generate a random test email with a 4-digit number for better isolation."""
    random_suffix = random.randint(0, 9999)
    return f"{prefix}{random_suffix:04d}@example.com"


class MockEmailService:
    """Mock email service for testing without sending real emails."""

    def __init__(self):
        self.sent_emails = []

    def send_notification(self, user_email, token, username=None, is_new_user=False):
        """Mock sending email notification."""
        self.sent_emails.append(
            {
                "to": user_email,
                "token": token,
                "username": username,
                "is_new_user": is_new_user,
                "timestamp": datetime.now(timezone.utc),
            }
        )
        return True

    def get_sent_emails(self):
        """Get list of sent emails."""
        return self.sent_emails

    def clear_sent_emails(self):
        """Clear sent emails list."""
        self.sent_emails.clear()


@contextmanager
def database_transaction():
    """Context manager for database transactions with proper cleanup."""
    try:
        yield
    finally:
        # Cleanup any test data
        pass


def completely_delete_user(email):
    """Completely delete a user from the database (not just deactivate)."""
    try:
        with get_database_session(DB_ENGINE) as session:
            user = session.query(AuthUserTable).filter_by(email=email).first()
            if user:
                session.delete(user)
                session.commit()
                logger.info(f"Completely deleted user: {email}")
                return True
    except Exception as e:
        logger.warning(f"Error deleting user {email}: {e}")
    return False


class TestMultiUserAuth:
    """Test cases for multi-user authentication system."""

    @pytest.fixture
    def mock_email_service(self):
        """Create a mock email service for testing."""
        return MockEmailService()

    @pytest.fixture
    def test_user_email(self):
        """Generate a unique test user email."""
        return generate_random_test_email("pytest")

    @pytest.fixture
    def auth_service(self):
        """Get the multi-user auth service."""
        return get_multi_user_auth_service()

    @pytest.fixture(autouse=True)
    def cleanup_test_users(self):
        """Cleanup test users after each test."""
        test_emails = []
        yield test_emails
        # Cleanup after test
        for email in test_emails:
            completely_delete_user(email)

    @pytest.mark.asyncio
    async def test_add_user_basic(
        self, auth_service, test_user_email, cleanup_test_users
    ):
        """Test basic user addition functionality."""
        cleanup_test_users.append(test_user_email)

        with patch(
            "app.services.email_service.send_multiuser_token_notification"
        ) as mock_email:
            mock_email.return_value = True

            user = await auth_service.add_user(
                email=test_user_email,
                username="Test User",
                is_admin=False,
                send_welcome_email=False,
            )

            assert user is not None
            assert user.email == test_user_email
            assert user.username == "Test User"
            assert user.is_admin is False
            assert user.is_active is True
            assert user.created_at is not None

    @pytest.mark.asyncio
    async def test_add_user_with_email_notification(
        self, auth_service, test_user_email, cleanup_test_users
    ):
        """Test user addition with email notification."""
        cleanup_test_users.append(test_user_email)

        with patch(
            "app.services.email_service.send_multiuser_token_notification"
        ) as mock_email:
            mock_email.return_value = True

            user = await auth_service.add_user(
                email=test_user_email,
                username="Test User",
                is_admin=False,
                send_welcome_email=True,
            )

            assert user is not None
            assert mock_email.called
            mock_email.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_duplicate_user(
        self, auth_service, test_user_email, cleanup_test_users
    ):
        """Test that adding duplicate user raises error."""
        cleanup_test_users.append(test_user_email)

        with patch(
            "app.services.email_service.send_multiuser_token_notification"
        ) as mock_email:
            mock_email.return_value = True

            # Add user first time
            await auth_service.add_user(
                email=test_user_email,
                username="Test User",
                is_admin=False,
                send_welcome_email=False,
            )

            # Try to add same user again
            with pytest.raises(MultiUserAuthError, match="already exists"):
                await auth_service.add_user(
                    email=test_user_email,
                    username="Another User",
                    is_admin=False,
                    send_welcome_email=False,
                )

    @pytest.mark.asyncio
    async def test_generate_user_token(
        self, auth_service, test_user_email, cleanup_test_users
    ):
        """Test token generation for a user."""
        cleanup_test_users.append(test_user_email)

        with patch(
            "app.services.email_service.send_multiuser_token_notification"
        ) as mock_email:
            mock_email.return_value = True

            # Add user first
            user = await auth_service.add_user(
                email=test_user_email,
                username="Test User",
                is_admin=False,
                send_welcome_email=False,
            )

            # Generate token
            token = await auth_service.generate_user_token(
                test_user_email, send_email=False
            )

            assert token is not None
            assert len(token) == 64  # Standard token length
            assert isinstance(token, str)

    @pytest.mark.asyncio
    async def test_validate_user_token(
        self, auth_service, test_user_email, cleanup_test_users
    ):
        """Test token validation for a user."""
        cleanup_test_users.append(test_user_email)

        with patch(
            "app.services.email_service.send_multiuser_token_notification"
        ) as mock_email:
            mock_email.return_value = True

            # Add user and generate token
            await auth_service.add_user(
                email=test_user_email,
                username="Test User",
                is_admin=False,
                send_welcome_email=False,
            )

            token = await auth_service.generate_user_token(
                test_user_email, send_email=False
            )

            # Validate token
            is_valid = auth_service.validate_user_token(test_user_email, token)
            assert is_valid is True

            # Test invalid token
            is_valid = auth_service.validate_user_token(test_user_email, "invalid_token")
            assert is_valid is False

            # Test wrong user email
            is_valid = auth_service.validate_user_token("wrong@email.com", token)
            assert is_valid is False

    def test_get_user_by_email(self, auth_service, test_user_email, cleanup_test_users):
        """Test getting user by email."""
        cleanup_test_users.append(test_user_email)

        with patch(
            "app.services.email_service.send_multiuser_token_notification"
        ) as mock_email:
            mock_email.return_value = True

            # Test non-existent user
            user = auth_service.get_user_by_email(test_user_email)
            assert user is None

            # Add user and test retrieval
            asyncio.run(
                auth_service.add_user(
                    email=test_user_email,
                    username="Test User",
                    is_admin=False,
                    send_welcome_email=False,
                )
            )

            user = auth_service.get_user_by_email(test_user_email)
            assert user is not None
            assert user.email == test_user_email

    def test_list_users(self, auth_service):
        """Test listing users."""
        # Get initial user count
        initial_users = auth_service.list_users()
        initial_count = len(initial_users)

        # Add test users
        test_emails = []
        with patch(
            "app.services.email_service.send_multiuser_token_notification"
        ) as mock_email:
            mock_email.return_value = True

            for i in range(3):
                email = generate_random_test_email(f"list_test_{i}")
                test_emails.append(email)
                asyncio.run(
                    auth_service.add_user(
                        email=email,
                        username=f"Test User {i}",
                        is_admin=False,
                        send_welcome_email=False,
                    )
                )

        try:
            # Test listing all users
            all_users = auth_service.list_users()
            assert len(all_users) == initial_count + 3

            # Test listing only active users
            active_users = auth_service.list_users(include_inactive=False)
            assert len(active_users) == initial_count + 3

            # Deactivate one user and test again
            auth_service.deactivate_user(test_emails[0])
            active_users = auth_service.list_users(include_inactive=False)
            assert len(active_users) == initial_count + 2

            all_users = auth_service.list_users(include_inactive=True)
            assert len(all_users) == initial_count + 3

        finally:
            # Cleanup
            for email in test_emails:
                completely_delete_user(email)

    def test_deactivate_user(self, auth_service, test_user_email, cleanup_test_users):
        """Test user deactivation."""
        cleanup_test_users.append(test_user_email)

        with patch(
            "app.services.email_service.send_multiuser_token_notification"
        ) as mock_email:
            mock_email.return_value = True

            # Add user
            asyncio.run(
                auth_service.add_user(
                    email=test_user_email,
                    username="Test User",
                    is_admin=False,
                    send_welcome_email=False,
                )
            )

            # Verify user is active
            user = auth_service.get_user_by_email(test_user_email)
            assert user.is_active is True

            # Deactivate user
            result = auth_service.deactivate_user(test_user_email)
            assert result is True

            # Verify user is deactivated
            user = auth_service.get_user_by_email(test_user_email)
            assert user.is_active is False
            assert user.current_token is None

            # Test deactivating non-existent user
            result = auth_service.deactivate_user("nonexistent@email.com")
            assert result is False

    @pytest.mark.asyncio
    async def test_rotate_user_token(
        self, auth_service, test_user_email, cleanup_test_users
    ):
        """Test token rotation for a user."""
        cleanup_test_users.append(test_user_email)

        with patch(
            "app.services.email_service.send_multiuser_token_notification"
        ) as mock_email:
            mock_email.return_value = True

            # Add user and generate initial token
            await auth_service.add_user(
                email=test_user_email,
                username="Test User",
                is_admin=False,
                send_welcome_email=False,
            )

            initial_token = await auth_service.generate_user_token(
                test_user_email, send_email=False
            )

            # Rotate token
            new_token = await auth_service.rotate_user_token(test_user_email)

            assert new_token is not None
            assert new_token != initial_token
            assert len(new_token) == 64

            # Verify old token is invalid
            is_valid = auth_service.validate_user_token(test_user_email, initial_token)
            assert is_valid is False

            # Verify new token is valid
            is_valid = auth_service.validate_user_token(test_user_email, new_token)
            assert is_valid is True

    def test_clean_expired_tokens(self, auth_service):
        """Test cleaning expired tokens."""
        # This test would require manipulating the database to set expired tokens
        # For now, we'll test that the method runs without error
        cleaned_count = auth_service.clean_expired_tokens()
        assert isinstance(cleaned_count, int)
        assert cleaned_count >= 0

    @pytest.mark.asyncio
    async def test_email_service_error_handling(
        self, auth_service, test_user_email, cleanup_test_users
    ):
        """Test handling of email service errors."""
        cleanup_test_users.append(test_user_email)

        with patch(
            "app.services.email_service.send_multiuser_token_notification"
        ) as mock_email:
            mock_email.side_effect = EmailServiceError("Email service unavailable")

            # User should still be created even if email fails
            user = await auth_service.add_user(
                email=test_user_email,
                username="Test User",
                is_admin=False,
                send_welcome_email=True,
            )

            assert user is not None
            assert user.email == test_user_email

    @pytest.mark.asyncio
    async def test_invalid_user_token_generation(self, auth_service):
        """Test token generation for invalid user."""
        with pytest.raises(MultiUserAuthError, match="not found"):
            await auth_service.generate_user_token("nonexistent@email.com")

    @pytest.mark.asyncio
    async def test_admin_user_creation(self, auth_service, cleanup_test_users):
        """Test creation of admin users."""
        admin_email = generate_random_test_email("admin")
        cleanup_test_users.append(admin_email)

        with patch(
            "app.services.email_service.send_multiuser_token_notification"
        ) as mock_email:
            mock_email.return_value = True

            admin_user = await auth_service.add_user(
                email=admin_email,
                username="Admin User",
                is_admin=True,
                send_welcome_email=False,
            )

            assert admin_user.is_admin is True
            assert admin_user.email == admin_email

    def test_token_expiry_hours_setting(self, auth_service):
        """Test that token expiry hours is properly set."""
        assert hasattr(auth_service, "token_expiry_hours")
        assert isinstance(auth_service.token_expiry_hours, int)
        assert auth_service.token_expiry_hours > 0
