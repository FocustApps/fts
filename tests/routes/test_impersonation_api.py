"""
Tests for impersonation routes.

Tests cover:
- Starting impersonation session (super admin only)
- Stopping impersonation session
- Getting impersonation status
- Authorization validation
- Audit logging
- Edge cases (impersonate while impersonating, invalid users, etc.)
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
from common.service_connections.db_service.models.account_models import (
    add_user_to_account,
    set_primary_account,
)
from common.service_connections.db_service.models.audit_log_model import (
    query_audit_logs_by_user,
)


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

    def _create_user(email: str = None, is_super_admin: bool = False):
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

        # Set super admin flag if needed
        if is_super_admin:
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
                is_super_admin=user.is_super_admin,
            )

        return user_id, token

    return _create_user


class TestImpersonation:
    """Test impersonation endpoints."""

    def test_start_impersonation_success(self, create_test_user, account_factory, engine):
        """POST /api/impersonation/start successfully impersonates user."""
        admin_id, admin_token = create_test_user(is_super_admin=True)
        target_id, _ = create_test_user()

        # Create account for target user
        account_id = account_factory(name="Target Account", owner_user_id=target_id)
        add_user_to_account(
            auth_user_id=target_id,
            account_id=account_id,
            role="owner",
            invited_by_user_id=target_id,
            engine=engine,
        )
        set_primary_account(target_id, account_id, engine)

        # Start impersonation
        response = client.post(
            "/v1/api/impersonation/start",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "target_user_id": target_id,
                "reason": "Testing impersonation functionality for support case #12345",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["impersonated_user_id"] == target_id
        assert data["account_id"] == account_id
        assert data["access_token"] is not None

        # Verify impersonation token works
        impersonation_token = data["access_token"]
        status_response = client.get(
            "/v1/api/impersonation/status",
            headers={"Authorization": f"Bearer {impersonation_token}"},
        )

        assert status_response.status_code == 200
        status = status_response.json()
        assert status["is_impersonating"] is True
        assert status["impersonated_user_id"] == target_id
        assert status["impersonated_by"] == admin_id

    def test_start_impersonation_creates_audit_log(self, create_test_user, engine):
        """POST /api/impersonation/start creates sensitive audit log."""
        admin_id, admin_token = create_test_user(is_super_admin=True)
        target_id, _ = create_test_user()

        response = client.post(
            "/v1/api/impersonation/start",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "target_user_id": target_id,
                "reason": "Support ticket investigation for critical bug",
            },
        )

        assert response.status_code == 200

        # Check audit log
        with session(engine) as db_session:
            logs = query_audit_logs_by_user(
                user_id=admin_id,
                session=db_session,
                engine=engine,
            )

        impersonation_logs = [log for log in logs if log.action == "user_impersonated"]
        assert len(impersonation_logs) >= 1
        assert impersonation_logs[-1].performed_by_user_id == admin_id
        assert impersonation_logs[-1].is_sensitive is True

    def test_start_impersonation_requires_super_admin(self, create_test_user):
        """POST /api/impersonation/start rejects non-super-admin."""
        regular_id, regular_token = create_test_user(is_super_admin=False)
        target_id, _ = create_test_user()

        response = client.post(
            "/v1/api/impersonation/start",
            headers={"Authorization": f"Bearer {regular_token}"},
            json={"target_user_id": target_id, "reason": "Should not be allowed"},
        )

        assert response.status_code == 403

    def test_start_impersonation_requires_reason(self, create_test_user):
        """POST /api/impersonation/start requires valid reason."""
        admin_id, admin_token = create_test_user(is_super_admin=True)
        target_id, _ = create_test_user()

        # No reason
        response = client.post(
            "/v1/api/impersonation/start",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"target_user_id": target_id, "reason": ""},
        )
        assert response.status_code == 400

        # Reason too short
        response = client.post(
            "/v1/api/impersonation/start",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"target_user_id": target_id, "reason": "Short"},
        )
        assert response.status_code == 400

    def test_start_impersonation_nonexistent_user(self, create_test_user):
        """POST /api/impersonation/start returns 404 for invalid user."""
        admin_id, admin_token = create_test_user(is_super_admin=True)

        response = client.post(
            "/v1/api/impersonation/start",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "target_user_id": str(uuid4()),
                "reason": "Testing nonexistent user handling",
            },
        )

        assert response.status_code == 404

    def test_cannot_impersonate_while_impersonating(self, create_test_user, jwt_service):
        """POST /api/impersonation/start rejects nested impersonation."""
        admin_id, _ = create_test_user(is_super_admin=True)
        target1_id, _ = create_test_user()
        target2_id, _ = create_test_user()

        # Create impersonation token (simulate already impersonating)
        from datetime import datetime, timezone

        impersonation_token = jwt_service.create_access_token(
            user_id=target1_id,
            email="target1@example.com",
            is_admin=False,
            is_super_admin=True,  # Still super admin
            impersonated_by=admin_id,
            impersonation_started_at=datetime.now(timezone.utc),
        )

        response = client.post(
            "/v1/api/impersonation/start",
            headers={"Authorization": f"Bearer {impersonation_token}"},
            json={
                "target_user_id": target2_id,
                "reason": "Should not allow nested impersonation",
            },
        )

        assert response.status_code == 400
        assert "already in an impersonation session" in response.json()["detail"]

    def test_stop_impersonation_success(
        self, create_test_user, account_factory, engine, jwt_service
    ):
        """POST /api/impersonation/stop returns to admin identity."""
        admin_id, _ = create_test_user(is_super_admin=True)
        target_id, _ = create_test_user()

        # Create account for admin
        admin_account_id = account_factory(name="Admin Account", owner_user_id=admin_id)
        add_user_to_account(
            auth_user_id=admin_id,
            account_id=admin_account_id,
            role="owner",
            invited_by_user_id=admin_id,
            engine=engine,
        )
        set_primary_account(admin_id, admin_account_id, engine)

        # Create impersonation token
        from datetime import datetime, timezone

        with session(engine) as db_session:
            admin_user = db_session.get(AuthUserTable, admin_id)
            admin_email = admin_user.email

        with session(engine) as db_session:
            target_user = db_session.get(AuthUserTable, target_id)
            target_email = target_user.email

        impersonation_token = jwt_service.create_access_token(
            user_id=target_id,
            email=target_email,
            is_admin=False,
            is_super_admin=True,
            impersonated_by=admin_id,
            impersonation_started_at=datetime.now(timezone.utc),
        )

        # Stop impersonation
        response = client.post(
            "/v1/api/impersonation/stop",
            headers={"Authorization": f"Bearer {impersonation_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["access_token"] is not None

        # Verify returned to admin identity
        admin_token = data["access_token"]
        status_response = client.get(
            "/v1/api/impersonation/status",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert status_response.status_code == 200
        status = status_response.json()
        assert status["is_impersonating"] is False

    def test_stop_impersonation_not_impersonating(self, create_test_user):
        """POST /api/impersonation/stop rejects when not impersonating."""
        admin_id, admin_token = create_test_user(is_super_admin=True)

        response = client.post(
            "/v1/api/impersonation/stop",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == 400
        assert "Not currently impersonating" in response.json()["detail"]

    def test_get_impersonation_status_not_impersonating(self, create_test_user):
        """GET /api/impersonation/status returns false when not impersonating."""
        admin_id, admin_token = create_test_user(is_super_admin=True)

        response = client.get(
            "/v1/api/impersonation/status",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["is_impersonating"] is False
        assert data["impersonated_user_id"] is None
        assert data["impersonated_by"] is None

    def test_impersonation_requires_auth(self):
        """Impersonation endpoints require authentication."""
        # Start impersonation
        response = client.post(
            "/v1/api/impersonation/start",
            json={"target_user_id": str(uuid4()), "reason": "No auth provided"},
        )
        assert response.status_code == 401

        # Stop impersonation
        response = client.post("/v1/api/impersonation/stop")
        assert response.status_code == 401

        # Status
        response = client.get("/v1/api/impersonation/status")
        assert response.status_code == 401
