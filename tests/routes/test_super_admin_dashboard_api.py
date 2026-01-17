"""
Tests for super admin dashboard API routes.

Tests cover:
- Listing all users with pagination and filtering
- System metrics retrieval
- User status management (suspend/activate)
- Super admin access control
"""

import pytest
from fastapi.testclient import TestClient

from app.fenrir_app import app
from app.services.jwt_service import get_jwt_service
from common.service_connections.db_service.database.engine import (
    get_database_session as session,
)
from common.service_connections.db_service.database.tables.account_tables.auth_user import (
    AuthUserTable,
)
from common.service_connections.db_service.db_manager import DB_ENGINE
from common.service_connections.db_service.models.audit_log_model import (
    query_audit_logs_by_user,
)


client = TestClient(app)


@pytest.fixture
def engine():
    """Provide database engine."""
    return DB_ENGINE


@pytest.fixture
def jwt_service():
    """Provide JWT service."""
    return get_jwt_service()


@pytest.fixture
def create_test_user(auth_user_factory, jwt_service, engine):
    """Factory to create test users and get their JWT tokens."""

    def _create_user(is_super_admin=False, is_admin=False, is_active=True):
        """Create a user and return (user_id, token)."""
        user_id = auth_user_factory(
            is_super_admin=is_super_admin,
            is_admin=is_admin,
        )

        # If creating inactive user, deactivate after creation
        if not is_active:
            with session(engine) as db_session:
                user = db_session.get(AuthUserTable, user_id)
                user.is_active = False
                db_session.commit()

        # Get user details for token
        with session(engine) as db_session:
            user = db_session.get(AuthUserTable, user_id)
            email = user.email

        # Create JWT token
        token = jwt_service.create_access_token(
            user_id=user_id,
            email=email,
            is_admin=is_admin,
            is_super_admin=is_super_admin,
        )

        return user_id, token

    return _create_user


class TestListAllUsers:
    """Test GET /api/admin/users - List all users."""

    def test_list_all_users_success(self, create_test_user, account_factory, engine):
        """Super admin can list all users."""
        # Create super admin
        admin_id, admin_token = create_test_user(is_super_admin=True)

        # Create several users
        user1_id, _ = create_test_user()
        user2_id, _ = create_test_user()
        user3_id, _ = create_test_user()

        # List users
        response = client.get(
            "/v1/api/admin/users",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == 200
        data = response.json()

        # Verify structure
        assert "users" in data
        assert "total" in data
        assert "page" in data
        assert "page_size" in data
        assert "total_pages" in data

        # Should include all created users
        assert data["total"] >= 4  # admin + 3 users
        user_ids = [u["auth_user_id"] for u in data["users"]]
        assert admin_id in user_ids
        assert user1_id in user_ids
        assert user2_id in user_ids

        # Verify user fields
        for user in data["users"]:
            assert "auth_user_id" in user
            assert "email" in user
            assert "is_active" in user
            assert "is_super_admin" in user
            assert "account_count" in user

    def test_list_users_pagination(self, create_test_user):
        """Pagination works correctly."""
        admin_id, admin_token = create_test_user(is_super_admin=True)

        # Request with specific page size
        response = client.get(
            "/v1/api/admin/users?page=1&page_size=2",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["page"] == 1
        assert data["page_size"] == 2
        assert len(data["users"]) <= 2

    def test_list_users_exclude_inactive(self, create_test_user):
        """Inactive users excluded by default."""
        admin_id, admin_token = create_test_user(is_super_admin=True)
        inactive_id, _ = create_test_user(is_active=False)

        # List without include_inactive
        response = client.get(
            "/v1/api/admin/users",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == 200
        data = response.json()

        # Inactive user should not be in list
        user_ids = [u["auth_user_id"] for u in data["users"]]
        assert inactive_id not in user_ids

        # All returned users should be active
        assert all(u["is_active"] for u in data["users"])

    def test_list_users_include_inactive(self, create_test_user):
        """Can include inactive users with flag."""
        admin_id, admin_token = create_test_user(is_super_admin=True)
        inactive_id, _ = create_test_user(is_active=False)

        # List with include_inactive=true
        response = client.get(
            "/v1/api/admin/users?include_inactive=true",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == 200
        data = response.json()

        # Inactive user should be in list
        user_ids = [u["auth_user_id"] for u in data["users"]]
        assert inactive_id in user_ids

    def test_list_users_search_by_email(self, create_test_user):
        """Can search users by email."""
        admin_id, admin_token = create_test_user(is_super_admin=True)

        # Get admin email
        response = client.get(
            "/v1/api/admin/users",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        data = response.json()
        admin_user = next(u for u in data["users"] if u["auth_user_id"] == admin_id)
        admin_email_part = admin_user["email"].split("@")[0][:5]

        # Search
        response = client.get(
            f"/v1/api/admin/users?search={admin_email_part}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == 200
        data = response.json()

        # Should find admin
        user_ids = [u["auth_user_id"] for u in data["users"]]
        assert admin_id in user_ids

    def test_list_users_requires_super_admin(self, create_test_user):
        """Regular users cannot list all users."""
        user_id, token = create_test_user(is_super_admin=False)

        response = client.get(
            "/v1/api/admin/users",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 403
        assert "super admin" in response.json()["detail"].lower()


class TestSystemMetrics:
    """Test GET /api/admin/metrics - System statistics."""

    def test_get_metrics_success(self, create_test_user, account_factory):
        """Super admin can retrieve system metrics."""
        admin_id, admin_token = create_test_user(is_super_admin=True)

        # Create some data
        user1_id, _ = create_test_user()
        user2_id, _ = create_test_user()
        account1 = account_factory(owner_user_id=user1_id, name="Account 1")
        account2 = account_factory(owner_user_id=user2_id, name="Account 2")

        response = client.get(
            "/v1/api/admin/metrics",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == 200
        data = response.json()

        # Verify all metric categories present
        assert "total_users" in data
        assert "active_users" in data
        assert "inactive_users" in data
        assert "super_admins" in data
        assert "users_created_last_30_days" in data

        assert "total_accounts" in data
        assert "active_accounts" in data
        assert "inactive_accounts" in data
        assert "accounts_created_last_30_days" in data

        assert "total_audit_logs" in data
        assert "audit_logs_last_24_hours" in data
        assert "sensitive_actions_last_7_days" in data

        # Verify counts make sense
        assert data["total_users"] >= 3  # admin + 2 users
        assert data["active_users"] >= 3
        assert data["super_admins"] >= 1
        assert data["total_accounts"] >= 2

    def test_metrics_user_counts_correct(self, create_test_user):
        """User metrics are accurate."""
        admin_id, admin_token = create_test_user(is_super_admin=True)

        # Create active and inactive users
        active1, _ = create_test_user(is_active=True)
        active2, _ = create_test_user(is_active=True)
        inactive1, _ = create_test_user(is_active=False)

        response = client.get(
            "/v1/api/admin/metrics",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == 200
        data = response.json()

        # Verify counts
        assert data["total_users"] == data["active_users"] + data["inactive_users"]
        assert data["inactive_users"] >= 1  # At least our inactive test user

    def test_metrics_requires_super_admin(self, create_test_user):
        """Regular users cannot access metrics."""
        user_id, token = create_test_user(is_super_admin=False)

        response = client.get(
            "/v1/api/admin/metrics",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 403


class TestUpdateUserStatus:
    """Test POST /api/admin/users/{id}/status - Suspend/activate users."""

    def test_suspend_user_success(self, create_test_user, engine):
        """Super admin can suspend a user."""
        admin_id, admin_token = create_test_user(is_super_admin=True)
        target_id, _ = create_test_user(is_active=True)

        # Suspend user
        response = client.post(
            f"/v1/api/admin/users/{target_id}/status",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "is_active": False,
                "reason": "Policy violation - testing system abuse",
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert data["user_id"] == target_id
        assert data["is_active"] is False
        assert "suspended" in data["message"].lower()

        # Verify user is actually suspended in database
        with session(engine) as db_session:
            user = db_session.get(AuthUserTable, target_id)
            assert user.is_active is False

    def test_activate_user_success(self, create_test_user, engine):
        """Super admin can activate a suspended user."""
        admin_id, admin_token = create_test_user(is_super_admin=True)
        target_id, _ = create_test_user(is_active=False)

        # Activate user
        response = client.post(
            f"/v1/api/admin/users/{target_id}/status",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"is_active": True, "reason": "Appeal approved - account restored"},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert data["is_active"] is True
        assert "activated" in data["message"].lower()

        # Verify user is actually activated
        with session(engine) as db_session:
            user = db_session.get(AuthUserTable, target_id)
            assert user.is_active is True

    def test_suspend_creates_audit_log(self, create_test_user, engine):
        """Suspending user creates audit log entry."""
        admin_id, admin_token = create_test_user(is_super_admin=True)
        target_id, _ = create_test_user(is_active=True)

        reason = "Testing audit logging for user suspension"

        response = client.post(
            f"/v1/api/admin/users/{target_id}/status",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"is_active": False, "reason": reason},
        )

        assert response.status_code == 200

        # Check audit log
        with session(engine) as db_session:
            logs = query_audit_logs_by_user(
                user_id=admin_id,
                session=db_session,
                engine=engine,
            )

        # Should have logged the suspension
        suspend_logs = [log for log in logs if log.action == "super_admin_access"]
        assert len(suspend_logs) >= 1
        latest_log = suspend_logs[-1]
        assert latest_log.is_sensitive is True
        assert target_id in latest_log.details.get("accessed_resource_id", "")

    def test_suspend_requires_reason(self, create_test_user):
        """Suspending user requires reason."""
        admin_id, admin_token = create_test_user(is_super_admin=True)
        target_id, _ = create_test_user()

        # Try without reason
        response = client.post(
            f"/v1/api/admin/users/{target_id}/status",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"is_active": False, "reason": ""},
        )

        assert response.status_code == 400
        assert "reason" in response.json()["detail"].lower()

    def test_suspend_requires_long_reason(self, create_test_user):
        """Reason must be at least 10 characters."""
        admin_id, admin_token = create_test_user(is_super_admin=True)
        target_id, _ = create_test_user()

        # Try with short reason
        response = client.post(
            f"/v1/api/admin/users/{target_id}/status",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"is_active": False, "reason": "short"},
        )

        assert response.status_code == 400
        assert "10 characters" in response.json()["detail"]

    def test_cannot_suspend_self(self, create_test_user):
        """Admin cannot suspend themselves."""
        admin_id, admin_token = create_test_user(is_super_admin=True)

        response = client.post(
            f"/v1/api/admin/users/{admin_id}/status",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"is_active": False, "reason": "Testing self-suspension prevention"},
        )

        assert response.status_code == 400
        assert "own account" in response.json()["detail"].lower()

    def test_cannot_suspend_other_super_admin(self, create_test_user):
        """Super admin cannot suspend another super admin."""
        admin1_id, admin1_token = create_test_user(is_super_admin=True)
        admin2_id, admin2_token = create_test_user(is_super_admin=True)

        response = client.post(
            f"/v1/api/admin/users/{admin2_id}/status",
            headers={"Authorization": f"Bearer {admin1_token}"},
            json={"is_active": False, "reason": "Testing super admin protection"},
        )

        assert response.status_code == 400
        assert "super admin" in response.json()["detail"].lower()

    def test_suspend_nonexistent_user(self, create_test_user):
        """Returns 404 for nonexistent user."""
        admin_id, admin_token = create_test_user(is_super_admin=True)

        from uuid import uuid4

        fake_id = str(uuid4())

        response = client.post(
            f"/v1/api/admin/users/{fake_id}/status",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"is_active": False, "reason": "Testing nonexistent user handling"},
        )

        assert response.status_code == 404

    def test_update_status_requires_super_admin(self, create_test_user):
        """Regular users cannot suspend users."""
        user_id, user_token = create_test_user(is_super_admin=False)
        target_id, _ = create_test_user()

        response = client.post(
            f"/v1/api/admin/users/{target_id}/status",
            headers={"Authorization": f"Bearer {user_token}"},
            json={"is_active": False, "reason": "Testing authorization"},
        )

        assert response.status_code == 403
