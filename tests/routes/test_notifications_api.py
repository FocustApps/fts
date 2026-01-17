"""
Tests for notification routes.

Tests notification preferences management, in-app notifications,
and admin notification creation endpoints.
"""

import pytest
from uuid import uuid4
from fastapi.testclient import TestClient

from app.fenrir_app import app
from app.services.user_auth_service import get_user_auth_service
from app.services.jwt_service import get_jwt_service
from common.service_connections.db_service.database.engine import (
    get_database_session as session,
)
from common.service_connections.db_service.database.tables.account_tables.auth_user import (
    AuthUserTable,
)
from common.service_connections.db_service.db_manager import DB_ENGINE


# Test client
client = TestClient(app)


@pytest.fixture
def engine():
    """Provide database engine."""
    return DB_ENGINE


@pytest.fixture
def auth_service(engine):
    """Provide authentication service."""
    return get_user_auth_service(engine)


@pytest.fixture
def jwt_service():
    """Provide JWT service."""
    return get_jwt_service()


@pytest.fixture
def create_test_user(auth_service, jwt_service, engine):
    """Fixture to create authenticated test users."""

    def _create_user(email: str = None, is_admin: bool = False):
        """Create and return user_id and access token."""
        email = email or f"test.user.{uuid4().hex[:8]}@example.com"

        # Register user
        from app.models.auth_models import RegisterRequest

        user_data = RegisterRequest(
            email=email,
            username=email.split("@")[0],
            password="TestPassword123!",
        )

        user_model = auth_service.register_user(user_data)
        user_id = user_model.auth_user_id

        # Set admin flag if needed
        if is_admin:
            with session(engine) as db_session:
                user = db_session.get(AuthUserTable, user_id)
                user.is_admin = True
                user.is_super_admin = True
                db_session.commit()

        # Authenticate to get token
        with session(engine) as db_session:
            user = db_session.get(AuthUserTable, user_id)
            token = jwt_service.create_access_token(
                user_id=user_id,
                email=user.email,
                is_admin=user.is_admin,
            )

        return user_id, token

    return _create_user


@pytest.fixture
def regular_user(create_test_user):
    """Create regular user and get auth token."""
    return create_test_user(is_admin=False)  # Let it auto-generate unique email


@pytest.fixture
def admin_user(create_test_user):
    """Create admin user and get auth token."""
    return create_test_user(is_admin=True)  # Let it auto-generate unique email


class TestNotificationPreferences:
    """Test notification preferences endpoints."""

    def test_get_preferences_creates_defaults(self, regular_user: tuple[str, str]):
        """GET /api/users/me/notification-preferences creates defaults."""
        user_id, token = regular_user

        response = client.get(
            "/v1/api/users/me/notification-preferences",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["auth_user_id"] == user_id
        # Check some key fields
        assert "account_added_email" in data
        assert "role_changed_email" in data
        assert "bulk_operation_email" in data

    def test_update_preferences_partial(self, regular_user: tuple[str, str]):
        """PUT /api/users/me/notification-preferences supports partial updates."""
        user_id, token = regular_user

        # Get defaults first
        response = client.get(
            "/v1/api/users/me/notification-preferences",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200

        # Update only some fields
        response = client.put(
            "/v1/api/users/me/notification-preferences",
            headers={"Authorization": f"Bearer {token}"},
            json={"account_added_email": False, "role_changed_email": False},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["account_added_email"] is False
        assert data["role_changed_email"] is False

    def test_preferences_requires_auth(self):
        """Preferences endpoints require authentication."""
        # No token
        response = client.get("/v1/api/users/me/notification-preferences")
        assert response.status_code == 401

        response = client.put(
            "/v1/api/users/me/notification-preferences",
            json={"account_added_email": False},
        )
        assert response.status_code == 401


class TestNotificationCRUD:
    """Test notification CRUD endpoints."""

    def test_get_notifications_empty(self, regular_user: tuple[str, str]):
        """GET /api/users/me/notifications returns empty list initially."""
        user_id, token = regular_user

        response = client.get(
            "/v1/api/users/me/notifications", headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        assert response.json() == []

    def test_get_unread_count_zero(self, regular_user: tuple[str, str]):
        """GET /api/users/me/notifications/unread-count returns 0 initially."""
        user_id, token = regular_user

        response = client.get(
            "/v1/api/users/me/notifications/unread-count",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["unread_count"] == 0

    def test_create_and_read_notification(
        self, regular_user: tuple[str, str], admin_user: tuple[str, str]
    ):
        """Admin creates notification, user can read it."""
        user_id, user_token = regular_user
        admin_id, admin_token = admin_user

        # Admin creates notification
        response = client.post(
            "/v1/api/notifications",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "auth_user_id": user_id,
                "notification_type": "test_notification",
                "title": "Test Title",
                "message": "Test message content",
            },
        )

        assert response.status_code == 200
        notification_id = response.json()["notification_id"]

        # User gets notifications
        response = client.get(
            "/v1/api/users/me/notifications",
            headers={"Authorization": f"Bearer {user_token}"},
        )

        assert response.status_code == 200
        notifications = response.json()
        assert len(notifications) == 1
        assert notifications[0]["notification_id"] == notification_id
        assert notifications[0]["title"] == "Test Title"
        assert notifications[0]["message"] == "Test message content"
        assert notifications[0]["is_read"] is False

    def test_mark_notification_as_read(
        self, regular_user: tuple[str, str], admin_user: tuple[str, str]
    ):
        """PUT /api/users/me/notifications/{id}/read marks as read."""
        user_id, user_token = regular_user
        admin_id, admin_token = admin_user

        # Create notification
        response = client.post(
            "/v1/api/notifications",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "auth_user_id": user_id,
                "notification_type": "test_mark_read",
                "title": "Mark Read Test",
                "message": "Test message",
            },
        )
        notification_id = response.json()["notification_id"]

        # Mark as read
        response = client.put(
            f"/v1/api/users/me/notifications/{notification_id}/read",
            headers={"Authorization": f"Bearer {user_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["notification_id"] == notification_id
        assert data["is_read"] is True

        # Verify unread count is 0
        response = client.get(
            "/v1/api/users/me/notifications/unread-count",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert response.json()["unread_count"] == 0

    def test_mark_all_as_read(
        self, regular_user: tuple[str, str], admin_user: tuple[str, str]
    ):
        """PUT /api/users/me/notifications/read-all marks all as read."""
        user_id, user_token = regular_user
        admin_id, admin_token = admin_user

        # Create multiple notifications
        for i in range(3):
            client.post(
                "/v1/api/notifications",
                headers={"Authorization": f"Bearer {admin_token}"},
                json={
                    "auth_user_id": user_id,
                    "notification_type": "bulk_test",
                    "title": f"Notification {i+1}",
                    "message": f"Message {i+1}",
                },
            )

        # Verify unread count
        response = client.get(
            "/v1/api/users/me/notifications/unread-count",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert response.json()["unread_count"] == 3

        # Mark all as read
        response = client.put(
            "/v1/api/users/me/notifications/read-all",
            headers={"Authorization": f"Bearer {user_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["marked_count"] == 3

        # Verify unread count is 0
        response = client.get(
            "/v1/api/users/me/notifications/unread-count",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert response.json()["unread_count"] == 0

    def test_delete_notification(
        self, regular_user: tuple[str, str], admin_user: tuple[str, str]
    ):
        """DELETE /api/users/me/notifications/{id} removes notification."""
        user_id, user_token = regular_user
        admin_id, admin_token = admin_user

        # Create notification
        response = client.post(
            "/v1/api/notifications",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "auth_user_id": user_id,
                "notification_type": "delete_test",
                "title": "To Delete",
                "message": "Will be deleted",
            },
        )
        notification_id = response.json()["notification_id"]

        # Delete notification
        response = client.delete(
            f"/v1/api/users/me/notifications/{notification_id}",
            headers={"Authorization": f"Bearer {user_token}"},
        )

        assert response.status_code == 200
        assert response.json()["success"] is True

        # Verify notification is gone
        response = client.get(
            "/v1/api/users/me/notifications",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        notifications = response.json()
        assert notification_id not in [n["notification_id"] for n in notifications]

    def test_cannot_mark_others_notification(
        self, regular_user: tuple[str, str], admin_user: tuple[str, str], create_test_user
    ):
        """Cannot mark another user's notification as read."""
        user_id, user_token = regular_user
        admin_id, admin_token = admin_user

        # Create another user
        other_user_id, _ = create_test_user(email="other_notif_user@test.com")

        # Admin creates notification for other user
        response = client.post(
            "/v1/api/notifications",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "auth_user_id": other_user_id,
                "notification_type": "ownership_test",
                "title": "Not Yours",
                "message": "Belongs to other user",
            },
        )
        notification_id = response.json()["notification_id"]

        # Try to mark as read with wrong user
        response = client.put(
            f"/v1/api/users/me/notifications/{notification_id}/read",
            headers={"Authorization": f"Bearer {user_token}"},
        )

        assert response.status_code == 404

    def test_notification_pagination(
        self, regular_user: tuple[str, str], admin_user: tuple[str, str]
    ):
        """GET /api/users/me/notifications supports pagination."""
        user_id, user_token = regular_user
        admin_id, admin_token = admin_user

        # Create 10 notifications
        for i in range(10):
            client.post(
                "/v1/api/notifications",
                headers={"Authorization": f"Bearer {admin_token}"},
                json={
                    "auth_user_id": user_id,
                    "notification_type": "pagination_test",
                    "title": f"Notification {i+1}",
                    "message": f"Message {i+1}",
                },
            )

        # Get first page (limit 3)
        response = client.get(
            "/v1/api/users/me/notifications?limit=3&offset=0",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert response.status_code == 200
        page1 = response.json()
        assert len(page1) == 3

        # Get second page
        response = client.get(
            "/v1/api/users/me/notifications?limit=3&offset=3",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert response.status_code == 200
        page2 = response.json()
        assert len(page2) == 3

        # Verify different notifications
        page1_ids = {n["notification_id"] for n in page1}
        page2_ids = {n["notification_id"] for n in page2}
        assert page1_ids.isdisjoint(page2_ids)

    def test_include_read_notifications(
        self, regular_user: tuple[str, str], admin_user: tuple[str, str]
    ):
        """GET /api/users/me/notifications?include_read=true shows read notifications."""
        user_id, user_token = regular_user
        admin_id, admin_token = admin_user

        # Create notification and mark as read
        response = client.post(
            "/v1/api/notifications",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "auth_user_id": user_id,
                "notification_type": "read_filter_test",
                "title": "Read Test",
                "message": "Test message",
            },
        )
        notification_id = response.json()["notification_id"]

        client.put(
            f"/v1/api/users/me/notifications/{notification_id}/read",
            headers={"Authorization": f"Bearer {user_token}"},
        )

        # Without include_read, should be empty
        response = client.get(
            "/v1/api/users/me/notifications",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert len(response.json()) == 0

        # With include_read=true, should see notification
        response = client.get(
            "/v1/api/users/me/notifications?include_read=true",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        notifications = response.json()
        assert len(notifications) == 1
        assert notifications[0]["notification_id"] == notification_id
        assert notifications[0]["is_read"] is True


class TestAdminNotificationCreation:
    """Test admin notification creation endpoints."""

    def test_create_notification_admin_only(self, regular_user: tuple[str, str]):
        """POST /api/notifications requires admin role."""
        user_id, token = regular_user

        response = client.post(
            "/v1/api/notifications",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "auth_user_id": user_id,
                "notification_type": "test",
                "title": "Test",
                "message": "Test",
            },
        )

        assert response.status_code == 403

    def test_bulk_create_notifications(
        self, admin_user: tuple[str, str], create_test_user
    ):
        """POST /api/notifications/bulk creates for multiple users."""
        admin_id, admin_token = admin_user

        # Create multiple users
        user_ids = []
        for i in range(3):
            user_id, _ = create_test_user(email=f"bulk_user_{i}@test.com")
            user_ids.append(user_id)

        # Bulk create
        response = client.post(
            "/v1/api/notifications/bulk",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "user_ids": user_ids,
                "notification_type": "system_announcement",
                "title": "System Maintenance",
                "message": "System will be down for maintenance",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["created_count"] == 3
        assert len(data["notification_ids"]) == 3

    def test_bulk_create_requires_admin(self, regular_user: tuple[str, str]):
        """POST /api/notifications/bulk requires admin role."""
        user_id, token = regular_user

        response = client.post(
            "/v1/api/notifications/bulk",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "user_ids": [user_id],
                "notification_type": "test",
                "title": "Test",
                "message": "Test",
            },
        )

        assert response.status_code == 403

    def test_create_notification_validates_type(self, admin_user: tuple[str, str]):
        """POST /api/notifications validates notification_type is not empty."""
        admin_id, admin_token = admin_user

        response = client.post(
            "/v1/api/notifications",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "auth_user_id": admin_id,
                "notification_type": "",  # Empty string
                "title": "Test",
                "message": "Test",
            },
        )

        assert response.status_code == 400
        assert "notification type" in response.json()["detail"].lower()
