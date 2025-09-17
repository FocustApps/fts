"""
API endpoint tests for multi-user authentication system.

This test suite focuses on testing the HTTP endpoints and API routes
for the auth users functionality, including proper authentication,
request/response handling, and error conditions.
"""

import random
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.fenrir_app import app
from app.services.multi_user_auth_service import get_multi_user_auth_service
from app.services.email_service import EmailServiceError
from common.app_logging import create_logging
from common.service_connections.db_service.database import (
    get_database_session,
    AuthUserTable,
)

logger = create_logging()


def generate_random_test_email(prefix="test"):
    """Generate a random test email with a 4-digit number for better isolation."""
    random_suffix = random.randint(0, 9999)
    return f"{prefix}{random_suffix:04d}@example.com"


def completely_delete_user(email):
    """Completely delete a user from the database (not just deactivate)."""
    try:
        with get_database_session() as session:
            user = session.query(AuthUserTable).filter_by(email=email).first()
            if user:
                session.delete(user)
                session.commit()
                logger.info(f"Completely deleted user: {email}")
                return True
    except Exception as e:
        logger.warning(f"Error deleting user {email}: {e}")
    return False


class TestAuthUsersAPI:
    """Test cases for auth users API endpoints."""

    @pytest.fixture
    def client(self):
        """Create a test client for FastAPI app."""
        return TestClient(app)

    @pytest.fixture
    def auth_service(self):
        """Get the multi-user auth service."""
        return get_multi_user_auth_service()

    @pytest.fixture
    def test_admin_email(self):
        """Generate a unique test admin email."""
        return generate_random_test_email("admin")

    @pytest.fixture
    def test_user_email(self):
        """Generate a unique test user email."""
        return generate_random_test_email("user")

    @pytest.fixture
    def cleanup_test_users(self):
        """Cleanup test users after each test."""
        test_emails = []
        yield test_emails
        # Cleanup after test
        for email in test_emails:
            completely_delete_user(email)

    @pytest.fixture
    async def admin_user_with_token(
        self, auth_service, test_admin_email, cleanup_test_users
    ):
        """Create an admin user with a valid token for API calls."""
        cleanup_test_users.append(test_admin_email)

        with patch(
            "app.services.email_service.send_user_token_notification"
        ) as mock_email:
            mock_email.return_value = True

            admin_user = await auth_service.add_user(
                email=test_admin_email,
                username="Test Admin",
                is_admin=True,
                send_welcome_email=False,
            )

            token = await auth_service.generate_user_token(
                test_admin_email, send_email=False
            )

            return {"user": admin_user, "token": token, "email": test_admin_email}

    def test_get_auth_users_unauthorized(self, client):
        """Test getting auth users without authentication."""
        response = client.get("/api/v1/auth-users/users")
        assert response.status_code == 401

    def test_get_auth_users_with_invalid_token(self, client):
        """Test getting auth users with invalid token."""
        headers = {"X-Auth-Token": "invalid_token"}
        response = client.get("/api/v1/auth-users/users", headers=headers)
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_auth_users_authorized(self, client, admin_user_with_token):
        """Test getting auth users with valid admin token."""
        headers = {"X-Auth-Token": admin_user_with_token["token"]}
        response = client.get("/api/v1/auth-users/users", headers=headers)
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_create_user_via_api(
        self, client, admin_user_with_token, cleanup_test_users
    ):
        """Test creating a user via API endpoint."""
        new_user_email = generate_random_test_email("api_create")
        cleanup_test_users.append(new_user_email)

        headers = {"X-Auth-Token": admin_user_with_token["token"]}

        with patch(
            "app.services.email_service.send_user_token_notification"
        ) as mock_email:
            mock_email.return_value = True

            user_data = {
                "email": new_user_email,
                "username": "API Created User",
                "is_admin": False,
            }

            response = client.post(
                "/api/v1/auth-users/users", json=user_data, headers=headers
            )
            assert response.status_code == 200

            data = response.json()
            assert data["email"] == new_user_email
            assert data["username"] == "API Created User"
            assert data["is_admin"] is False
            assert data["is_active"] is True

    @pytest.mark.asyncio
    async def test_create_duplicate_user_via_api(
        self, client, admin_user_with_token, cleanup_test_users
    ):
        """Test creating duplicate user via API should fail."""
        user_email = generate_random_test_email("duplicate")
        cleanup_test_users.append(user_email)

        headers = {"X-Auth-Token": admin_user_with_token["token"]}

        with patch(
            "app.services.email_service.send_user_token_notification"
        ) as mock_email:
            mock_email.return_value = True

            user_data = {"email": user_email, "username": "First User", "is_admin": False}

            # Create user first time
            response = client.post(
                "/api/v1/auth-users/users", json=user_data, headers=headers
            )
            assert response.status_code == 200

            # Try to create same user again
            user_data["username"] = "Second User"
            response = client.post(
                "/api/v1/auth-users/users", json=user_data, headers=headers
            )
            assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_generate_token_via_api(
        self, client, admin_user_with_token, auth_service, cleanup_test_users
    ):
        """Test generating token for user via API."""
        user_email = generate_random_test_email("token_gen")
        cleanup_test_users.append(user_email)

        headers = {"X-Auth-Token": admin_user_with_token["token"]}

        with patch(
            "app.services.email_service.send_user_token_notification"
        ) as mock_email:
            mock_email.return_value = True

            # Create user first
            user = await auth_service.add_user(
                email=user_email,
                username="Token Test User",
                is_admin=False,
                send_welcome_email=False,
            )

            # Generate token via API
            response = client.post(
                f"/api/v1/auth-users/users/{user.id}/generate-token", headers=headers
            )
            assert response.status_code == 200

            data = response.json()
            assert "token" in data
            assert "message" in data
            assert len(data["token"]) == 64

    @pytest.mark.asyncio
    async def test_generate_token_for_nonexistent_user(
        self, client, admin_user_with_token
    ):
        """Test generating token for non-existent user."""
        headers = {"X-Auth-Token": admin_user_with_token["token"]}

        # Use a very high ID that shouldn't exist
        response = client.post(
            "/api/v1/auth-users/users/999999/generate-token", headers=headers
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_user_details_via_api(
        self, client, admin_user_with_token, auth_service, cleanup_test_users
    ):
        """Test getting user details via API."""
        user_email = generate_random_test_email("details")
        cleanup_test_users.append(user_email)

        headers = {"X-Auth-Token": admin_user_with_token["token"]}

        with patch(
            "app.services.email_service.send_user_token_notification"
        ) as mock_email:
            mock_email.return_value = True

            # Create user first
            user = await auth_service.add_user(
                email=user_email,
                username="Details Test User",
                is_admin=False,
                send_welcome_email=False,
            )

            # Get user details via API
            response = client.get(f"/api/v1/auth-users/users/{user.id}", headers=headers)
            assert response.status_code == 200

            data = response.json()
            assert data["email"] == user_email
            assert data["username"] == "Details Test User"
            assert data["is_admin"] is False

    @pytest.mark.asyncio
    async def test_delete_user_via_api(
        self, client, admin_user_with_token, auth_service, cleanup_test_users
    ):
        """Test deleting (deactivating) user via API."""
        user_email = generate_random_test_email("delete")
        cleanup_test_users.append(user_email)

        headers = {"X-Auth-Token": admin_user_with_token["token"]}

        with patch(
            "app.services.email_service.send_user_token_notification"
        ) as mock_email:
            mock_email.return_value = True

            # Create user first
            user = await auth_service.add_user(
                email=user_email,
                username="Delete Test User",
                is_admin=False,
                send_welcome_email=False,
            )

            # Delete user via API
            response = client.delete(
                f"/api/v1/auth-users/users/{user.id}", headers=headers
            )
            assert response.status_code == 200

            data = response.json()
            assert "message" in data

            # Verify user is deactivated
            updated_user = auth_service.get_user_by_email(user_email)
            assert updated_user.is_active is False

    def test_create_user_with_invalid_email(self, client, admin_user_with_token):
        """Test creating user with invalid email format."""
        headers = {"X-Auth-Token": admin_user_with_token["token"]}

        user_data = {
            "email": "invalid-email-format",
            "username": "Invalid Email User",
            "is_admin": False,
        }

        response = client.post(
            "/api/v1/auth-users/users", json=user_data, headers=headers
        )
        assert response.status_code == 422  # Validation error

    def test_create_user_missing_required_fields(self, client, admin_user_with_token):
        """Test creating user with missing required fields."""
        headers = {"X-Auth-Token": admin_user_with_token["token"]}

        user_data = {"username": "Missing Email User", "is_admin": False}

        response = client.post(
            "/api/v1/auth-users/users", json=user_data, headers=headers
        )
        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_non_admin_user_access_restriction(
        self, client, auth_service, cleanup_test_users
    ):
        """Test that non-admin users cannot access admin endpoints."""
        user_email = generate_random_test_email("non_admin")
        cleanup_test_users.append(user_email)

        with patch(
            "app.services.email_service.send_user_token_notification"
        ) as mock_email:
            mock_email.return_value = True

            # Create non-admin user
            user = await auth_service.add_user(
                email=user_email,
                username="Non Admin User",
                is_admin=False,
                send_welcome_email=False,
            )

            token = await auth_service.generate_user_token(user_email, send_email=False)
            headers = {"X-Auth-Token": token}

            # Try to access admin endpoint
            response = client.get("/api/v1/auth-users/users", headers=headers)
            assert response.status_code == 403  # Forbidden

    @pytest.mark.asyncio
    async def test_email_service_error_in_api(
        self, client, admin_user_with_token, cleanup_test_users
    ):
        """Test API behavior when email service fails."""
        user_email = generate_random_test_email("email_error")
        cleanup_test_users.append(user_email)

        headers = {"X-Auth-Token": admin_user_with_token["token"]}

        with patch(
            "app.services.email_service.send_user_token_notification"
        ) as mock_email:
            mock_email.side_effect = EmailServiceError("Email service down")

            user_data = {
                "email": user_email,
                "username": "Email Error User",
                "is_admin": False,
            }

            # User should still be created even if email fails
            response = client.post(
                "/api/v1/auth-users/users", json=user_data, headers=headers
            )
            assert response.status_code == 200

            data = response.json()
            assert data["email"] == user_email

    @pytest.mark.asyncio
    async def test_maintenance_endpoint_clean_expired_tokens(
        self, client, admin_user_with_token
    ):
        """Test the maintenance endpoint for cleaning expired tokens."""
        headers = {"X-Auth-Token": admin_user_with_token["token"]}

        response = client.post(
            "/api/v1/auth-users/maintenance/clean-expired-tokens", headers=headers
        )
        assert response.status_code == 200

        data = response.json()
        assert "cleaned_count" in data
        assert isinstance(data["cleaned_count"], int)

    @pytest.mark.asyncio
    async def test_api_response_structure(self, client, admin_user_with_token):
        """Test that API responses have correct structure."""
        headers = {"X-Auth-Token": admin_user_with_token["token"]}

        response = client.get("/api/v1/auth-users/users", headers=headers)
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)

        if data:  # If there are users
            user = data[0]
            required_fields = [
                "id",
                "email",
                "username",
                "is_admin",
                "is_active",
                "created_at",
            ]
            for field in required_fields:
                assert field in user

    def test_api_content_type_requirements(self, client, admin_user_with_token):
        """Test that API endpoints require correct content type."""
        headers = {
            "X-Auth-Token": admin_user_with_token["token"],
            "Content-Type": "text/plain",  # Wrong content type
        }

        user_data = "invalid json data"

        response = client.post(
            "/api/v1/auth-users/users", data=user_data, headers=headers
        )
        # Should fail due to content type or JSON parsing
        assert response.status_code in [400, 422]

    @pytest.mark.asyncio
    async def test_api_rate_limiting_headers(self, client, admin_user_with_token):
        """Test that API responses include appropriate headers."""
        headers = {"X-Auth-Token": admin_user_with_token["token"]}

        response = client.get("/api/v1/auth-users/users", headers=headers)
        assert response.status_code == 200

        # Check that response has appropriate headers
        assert "content-type" in response.headers
        assert response.headers["content-type"] == "application/json"
