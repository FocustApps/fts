"""
Tests for account switching routes.

Tests cover:
- Getting current/primary account
- Listing available accounts
- Switching between accounts
- Authorization validation
- Audit logging
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
    query_audit_logs_by_account,
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


class TestAccountSwitching:
    """Test account switching endpoints."""

    def test_get_current_account_no_primary(self, create_test_user, engine):
        """GET /api/accounts/switch/current returns 404 when no primary account set."""
        user_id, token = create_test_user()

        response = client.get(
            "/v1/api/accounts/switch/current",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 404
        assert "no primary account" in response.json()["detail"].lower()

    def test_get_available_accounts_empty(self, create_test_user):
        """GET /api/accounts/switch/available returns empty list when no accounts."""
        user_id, token = create_test_user()

        response = client.get(
            "/v1/api/accounts/switch/available",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        assert response.json() == []

    def test_switch_account_success(self, create_test_user, account_factory, engine):
        """POST /api/accounts/switch switches account and sets as primary."""
        user_id, token = create_test_user()

        # Create two accounts
        account1_id = account_factory(name="Account One", owner_user_id=user_id)
        account2_id = account_factory(name="Account Two", owner_user_id=user_id)

        # Add user to both accounts
        add_user_to_account(
            auth_user_id=user_id,
            account_id=account1_id,
            role="owner",
            is_primary=False,
            invited_by_user_id=user_id,
            engine=engine,
        )
        add_user_to_account(
            auth_user_id=user_id,
            account_id=account2_id,
            role="member",
            is_primary=False,
            invited_by_user_id=user_id,
            engine=engine,
        )

        # Switch to account 2
        response = client.post(
            "/v1/api/accounts/switch",
            headers={"Authorization": f"Bearer {token}"},
            json={"account_id": account2_id},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["account_id"] == account2_id
        assert data["account_name"] == "Account Two"
        assert "successfully switched" in data["message"].lower()

        # Verify it's now the current account
        response = client.get(
            "/v1/api/accounts/switch/current",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert response.json()["account_id"] == account2_id
        assert response.json()["is_primary"] is True

    def test_get_available_accounts_multiple(
        self, create_test_user, account_factory, engine
    ):
        """GET /api/accounts/switch/available lists all user accounts."""
        user_id, token = create_test_user()

        # Create three accounts
        account1_id = account_factory(name="Account Alpha", owner_user_id=user_id)
        account2_id = account_factory(name="Account Beta", owner_user_id=user_id)
        account3_id = account_factory(name="Account Gamma", owner_user_id=user_id)

        # Add user to all accounts
        add_user_to_account(
            auth_user_id=user_id,
            account_id=account1_id,
            role="owner",
            invited_by_user_id=user_id,
            engine=engine,
        )
        add_user_to_account(
            auth_user_id=user_id,
            account_id=account2_id,
            role="admin",
            invited_by_user_id=user_id,
            engine=engine,
        )
        add_user_to_account(
            auth_user_id=user_id,
            account_id=account3_id,
            role="member",
            invited_by_user_id=user_id,
            engine=engine,
        )

        # Set account1 as primary
        set_primary_account(user_id, account1_id, engine)

        response = client.get(
            "/v1/api/accounts/switch/available",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        accounts = response.json()
        assert len(accounts) == 3

        # Find each account in response
        account_names = {acc["account_name"] for acc in accounts}
        assert "Account Alpha" in account_names
        assert "Account Beta" in account_names
        assert "Account Gamma" in account_names

        # Check primary flag
        primary_accounts = [acc for acc in accounts if acc["is_primary"]]
        assert len(primary_accounts) == 1
        assert primary_accounts[0]["account_id"] == account1_id

    def test_switch_to_nonexistent_account(self, create_test_user):
        """POST /api/accounts/switch returns 404 for nonexistent account."""
        user_id, token = create_test_user()
        fake_account_id = str(uuid4())

        response = client.post(
            "/v1/api/accounts/switch",
            headers={"Authorization": f"Bearer {token}"},
            json={"account_id": fake_account_id},
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_switch_to_unauthorized_account(
        self, create_test_user, account_factory, engine
    ):
        """POST /api/accounts/switch returns 404 for account user doesn't have access to."""
        user_id, token = create_test_user()
        other_user_id, _ = create_test_user()

        # Create account owned by other user
        other_account_id = account_factory(
            name="Other Account", owner_user_id=other_user_id
        )
        add_user_to_account(
            auth_user_id=other_user_id,
            account_id=other_account_id,
            role="owner",
            invited_by_user_id=other_user_id,
            engine=engine,
        )

        # Try to switch to it
        response = client.post(
            "/v1/api/accounts/switch",
            headers={"Authorization": f"Bearer {token}"},
            json={"account_id": other_account_id},
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_switch_account_creates_audit_log(
        self, create_test_user, account_factory, engine
    ):
        """POST /api/accounts/switch creates audit log entry."""
        user_id, token = create_test_user()

        # Create account
        account_id = account_factory(name="Test Account", owner_user_id=user_id)
        add_user_to_account(
            auth_user_id=user_id,
            account_id=account_id,
            role="owner",
            invited_by_user_id=user_id,
            engine=engine,
        )

        # Switch to account
        response = client.post(
            "/v1/api/accounts/switch",
            headers={"Authorization": f"Bearer {token}"},
            json={"account_id": account_id},
        )
        assert response.status_code == 200

        # Check audit log
        with session(engine) as db_session:
            logs = query_audit_logs_by_account(
                account_id=account_id,
                session=db_session,
                engine=engine,
            )

        switch_logs = [log for log in logs if log.action == "account_switch"]
        assert len(switch_logs) >= 1
        assert switch_logs[-1].performed_by_user_id == user_id
        assert switch_logs[-1].details.get("account_name") == "Test Account"

    def test_switch_account_requires_auth(self):
        """Account switching endpoints require authentication."""
        fake_account_id = str(uuid4())

        # No token
        response = client.get("/v1/api/accounts/switch/current")
        assert response.status_code == 401

        response = client.get("/v1/api/accounts/switch/available")
        assert response.status_code == 401

        response = client.post(
            "/v1/api/accounts/switch", json={"account_id": fake_account_id}
        )
        assert response.status_code == 401

    def test_get_current_account_shows_role(
        self, create_test_user, account_factory, engine
    ):
        """GET /api/accounts/switch/current includes user's role in account."""
        user_id, token = create_test_user()

        # Create account and add user as admin
        account_id = account_factory(name="Test Account", owner_user_id=user_id)
        add_user_to_account(
            auth_user_id=user_id,
            account_id=account_id,
            role="admin",
            invited_by_user_id=user_id,
            engine=engine,
        )
        set_primary_account(user_id, account_id, engine)

        response = client.get(
            "/v1/api/accounts/switch/current",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["account_id"] == account_id
        assert data["role"] == "admin"
        assert data["is_primary"] is True
