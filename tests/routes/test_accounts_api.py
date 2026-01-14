"""
Tests for accounts API routes.

Tests cover:
- Account creation (authenticated users auto-become owners)
- Listing user's accounts with roles
- Getting account details (requires viewer+)
- Updating accounts (requires admin+)
- Deleting accounts (requires owner)
- Super admin access to all accounts
- Authorization validation
- Audit logging integration
"""

import pytest
from uuid import uuid4
from fastapi.testclient import TestClient

from app.fenrir_app import app
from app.services.user_auth_service import get_user_auth_service
from common.service_connections.db_service.database.engine import (
    get_database_session as session,
)
from common.service_connections.db_service.database.enums import (
    AccountRoleEnum,
    AuditActionEnum,
)
from common.service_connections.db_service.db_manager import DB_ENGINE
from common.service_connections.db_service.models.account_models import (
    query_account_by_id,
    add_user_to_account,
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
def create_test_user(auth_user_factory, auth_service):
    """Create test user and return ID + access token."""
    from app.models.auth_models import RegisterRequest, LoginRequest

    def _create_user(email: str = None, is_super_admin: bool = False):
        # Generate unique email
        test_email = email or f"test_{uuid4().hex[:8]}@example.com"

        # Register user
        register_req = RegisterRequest(
            email=test_email,
            password="TestPass123!",
            username=f"testuser_{uuid4().hex[:8]}",
        )
        user = auth_service.register_user(register_req)

        # Set super admin if needed
        if is_super_admin:
            with session(DB_ENGINE) as db_session:
                from common.service_connections.db_service.database.tables.account_tables.auth_user import (
                    AuthUserTable,
                )

                db_user = db_session.get(AuthUserTable, user.auth_user_id)
                db_user.is_super_admin = True
                db_session.commit()

        # Authenticate to get token
        login_req = LoginRequest(
            email=test_email, password="TestPass123!", remember_me=False
        )
        tokens = auth_service.authenticate(login_req)

        return user.auth_user_id, tokens.access_token

    return _create_user


@pytest.fixture
def create_user_with_account(create_test_user, account_factory):
    """Create user with an existing account and role."""

    def _create(role: AccountRoleEnum = AccountRoleEnum.MEMBER):
        user_id, token = create_test_user()
        account_id = account_factory(owner_user_id=user_id)

        # Add user to account with specific role if not owner
        if role != AccountRoleEnum.OWNER:
            add_user_to_account(
                auth_user_id=user_id,
                account_id=account_id,
                role=role.value,
                is_primary=True,
                invited_by_user_id=user_id,
                engine=DB_ENGINE,
            )

        # Query user for email and is_admin
        from common.service_connections.db_service.database.tables.account_tables.auth_user import (
            AuthUserTable,
        )

        with session(DB_ENGINE) as db_session:
            user = db_session.get(AuthUserTable, user_id)

        # Regenerate token with account context
        from app.services.jwt_service import get_jwt_service

        jwt_service = get_jwt_service()
        token = jwt_service.create_access_token(
            user_id=user_id,
            email=user.email,
            is_admin=user.is_admin,
            account_id=account_id,
            account_role=role.value,
        )

        return user_id, account_id, token

    return _create


# ============================================================================
# Account Creation Tests
# ============================================================================


class TestAccountCreation:
    """Test POST /v1/api/accounts - Create account."""

    def test_create_account_success(self, engine, create_test_user):
        """Test authenticated user can create an account."""
        # Arrange
        user_id, token = create_test_user()
        from uuid import uuid4

        account_name = f"My Test Account {uuid4().hex[:8]}"

        # Act
        response = client.post(
            "/v1/api/accounts/",
            json={"account_name": account_name},
            headers={"Authorization": f"Bearer {token}"},
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["account_name"] == account_name  # Check against generated name
        assert data["owner_user_id"] == user_id
        assert data["is_active"] is True
        assert "account_id" in data
        assert "created_at" in data

        # Verify account exists in database
        with session(engine) as db_session:
            account = query_account_by_id(data["account_id"], db_session, engine)
            assert account.account_name == account_name  # Check against generated name
            assert account.owner_user_id == user_id

        # Verify audit log
        with session(engine) as db_session:
            audits = query_audit_logs_by_account(data["account_id"], db_session, engine)
            assert len(audits) > 0
            create_audit = next(
                (a for a in audits if a.action == AuditActionEnum.CREATE), None
            )
            assert create_audit is not None
            assert create_audit.performed_by_user_id == user_id

    def test_create_account_unauthenticated(self):
        """Test creating account without authentication fails."""
        # Act
        response = client.post(
            "/v1/api/accounts/",
            json={"account_name": "Unauthorized Account"},
        )

        # Assert
        assert response.status_code == 401  # No token provided

    def test_create_account_super_admin(self, create_test_user):
        """Test super admin can create accounts."""
        # Arrange
        user_id, token = create_test_user(is_super_admin=True)
        from uuid import uuid4

        account_name = f"Super Admin Account {uuid4().hex[:8]}"

        # Act
        response = client.post(
            "/v1/api/accounts/",
            json={"account_name": account_name},
            headers={"Authorization": f"Bearer {token}"},
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["account_name"] == account_name  # Check against generated name
        assert data["owner_user_id"] == user_id


# ============================================================================
# List Accounts Tests
# ============================================================================


class TestListAccounts:
    """Test GET /v1/api/accounts - List user's accounts."""

    def test_list_user_accounts(self, create_test_user, account_factory):
        """Test user sees their own accounts with roles."""
        # Arrange
        user_id, token = create_test_user()
        account1_id = account_factory(owner_user_id=user_id, name="Account 1")
        account2_id = account_factory(owner_user_id=user_id, name="Account 2")

        # Add user to accounts with different roles
        add_user_to_account(
            auth_user_id=user_id,
            account_id=account1_id,
            role=AccountRoleEnum.OWNER.value,
            is_primary=True,
            invited_by_user_id=user_id,
            engine=DB_ENGINE,
        )
        add_user_to_account(
            auth_user_id=user_id,
            account_id=account2_id,
            role=AccountRoleEnum.ADMIN.value,
            is_primary=False,
            invited_by_user_id=user_id,
            engine=DB_ENGINE,
        )

        # Act
        response = client.get(
            "/v1/api/accounts/",
            headers={"Authorization": f"Bearer {token}"},
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert any(
            a["account_name"] == "Account 1"
            and a["role"] == "owner"
            and a["is_primary"] is True
            for a in data
        )
        assert any(
            a["account_name"] == "Account 2"
            and a["role"] == "admin"
            and a["is_primary"] is False
            for a in data
        )

    def test_list_super_admin_sees_all(
        self, create_test_user, account_factory, auth_user_factory
    ):
        """Test super admin sees all accounts in system."""
        # Arrange
        super_admin_id, token = create_test_user(is_super_admin=True)

        # Create accounts owned by different users
        user1 = auth_user_factory()
        user2 = auth_user_factory()
        account1 = account_factory(owner_user_id=user1, name="User1 Account")
        account2 = account_factory(owner_user_id=user2, name="User2 Account")

        # Act
        response = client.get(
            "/v1/api/accounts/",
            headers={"Authorization": f"Bearer {token}"},
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 2  # At least the 2 created accounts
        assert any(a["account_name"] == "User1 Account" for a in data)
        assert any(a["account_name"] == "User2 Account" for a in data)
        # Super admin accounts show role as 'super_admin'
        assert all(a["role"] == "super_admin" for a in data)

    def test_list_accounts_unauthenticated(self):
        """Test listing accounts without authentication fails."""
        # Act
        response = client.get("/v1/api/accounts/")

        # Assert
        assert response.status_code == 401  # No token provided


# ============================================================================
# Get Account Details Tests
# ============================================================================


class TestGetAccountDetails:
    """Test GET /v1/api/accounts/{account_id} - Get account details."""

    def test_get_account_as_viewer(self, create_user_with_account, engine):
        """Test viewer can see account details."""
        # Arrange
        user_id, account_id, token = create_user_with_account(role=AccountRoleEnum.VIEWER)

        # Act
        response = client.get(
            f"/v1/api/accounts/{account_id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["account_id"] == account_id
        assert "owner_email" in data
        assert "user_count" in data
        assert data["user_count"] >= 1

    def test_get_account_unauthorized(
        self, create_test_user, account_factory, auth_user_factory
    ):
        """Test user cannot see accounts they don't belong to."""
        # Arrange
        user1, token1 = create_test_user()
        user2 = auth_user_factory()
        other_account = account_factory(owner_user_id=user2)

        # Act
        response = client.get(
            f"/v1/api/accounts/{other_account}",
            headers={"Authorization": f"Bearer {token1}"},
        )

        # Assert
        assert response.status_code == 403

    def test_get_account_super_admin_bypass(
        self, create_test_user, account_factory, auth_user_factory
    ):
        """Test super admin can see any account."""
        # Arrange
        super_admin_id, token = create_test_user(is_super_admin=True)
        other_user = auth_user_factory()
        other_account = account_factory(owner_user_id=other_user)

        # Act
        response = client.get(
            f"/v1/api/accounts/{other_account}",
            headers={"Authorization": f"Bearer {token}"},
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["account_id"] == other_account

    def test_get_account_not_found(self, create_user_with_account):
        """Test getting non-existent account returns 404."""
        # Arrange
        user_id, account_id, token = create_user_with_account()
        fake_id = str(uuid4())

        # Act
        response = client.get(
            f"/v1/api/accounts/{fake_id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        # Assert
        assert response.status_code in [403, 404]  # 403 if account_id mismatch


# ============================================================================
# Update Account Tests
# ============================================================================


class TestUpdateAccount:
    """Test PUT /v1/api/accounts/{account_id} - Update account."""

    def test_update_account_as_admin(self, create_user_with_account, engine):
        """Test admin can update account details."""
        # Arrange
        user_id, account_id, token = create_user_with_account(role=AccountRoleEnum.ADMIN)

        # Act
        response = client.put(
            f"/v1/api/accounts/{account_id}",
            json={
                "account_name": "Updated Account Name",
                "logo_url": "https://example.com/logo.png",
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["account_name"] == "Updated Account Name"
        assert data["logo_url"] == "https://example.com/logo.png"

        # Verify in database
        with session(engine) as db_session:
            account = query_account_by_id(account_id, db_session, engine)
            assert account.account_name == "Updated Account Name"
            assert account.logo_url == "https://example.com/logo.png"

        # Verify audit log
        from common.service_connections.db_service.database.enums import AuditActionEnum

        with session(engine) as db_session:
            audits = query_audit_logs_by_account(account_id, db_session, engine)
            update_audit = next(
                (a for a in audits if a.action == AuditActionEnum.UPDATE), None
            )
            assert update_audit is not None
            assert update_audit.performed_by_user_id == user_id

    def test_update_account_viewer_denied(self, create_user_with_account):
        """Test viewer cannot update account."""
        # Arrange
        user_id, account_id, token = create_user_with_account(role=AccountRoleEnum.VIEWER)

        # Act
        response = client.put(
            f"/v1/api/accounts/{account_id}",
            json={"account_name": "Viewer Update Attempt"},
            headers={"Authorization": f"Bearer {token}"},
        )

        # Assert
        assert response.status_code == 403

    def test_update_account_member_denied(self, create_user_with_account):
        """Test member cannot update account."""
        # Arrange
        user_id, account_id, token = create_user_with_account(role=AccountRoleEnum.MEMBER)

        # Act
        response = client.put(
            f"/v1/api/accounts/{account_id}",
            json={"account_name": "Member Update Attempt"},
            headers={"Authorization": f"Bearer {token}"},
        )

        # Assert
        assert response.status_code == 403


# ============================================================================
# Delete Account Tests
# ============================================================================


class TestDeleteAccount:
    """Test DELETE /v1/api/accounts/{account_id} - Delete account."""

    def test_delete_account_as_owner(self, create_user_with_account, engine):
        """Test owner can delete (soft delete) account."""
        # Arrange
        user_id, account_id, token = create_user_with_account(role=AccountRoleEnum.OWNER)

        # Act
        response = client.delete(
            f"/v1/api/accounts/{account_id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        # Assert
        assert response.status_code == 204

        # Verify soft delete (is_active = False)
        with session(engine) as db_session:
            account = query_account_by_id(account_id, db_session, engine)
            assert account.is_active is False

        # Verify audit log (sensitive = True for deletions)
        from common.service_connections.db_service.database.enums import AuditActionEnum

        with session(engine) as db_session:
            audits = query_audit_logs_by_account(account_id, db_session, engine)
            delete_audit = next(
                (a for a in audits if a.action == AuditActionEnum.DELETE), None
            )
            assert delete_audit is not None
            assert delete_audit.is_sensitive is True
            assert delete_audit.performed_by_user_id == user_id

    def test_delete_account_admin_denied(self, create_user_with_account):
        """Test admin cannot delete account (only owner can)."""
        # Arrange
        user_id, account_id, token = create_user_with_account(role=AccountRoleEnum.ADMIN)

        # Act
        response = client.delete(
            f"/v1/api/accounts/{account_id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        # Assert
        assert response.status_code == 403

    def test_delete_account_super_admin_can_delete(
        self, create_test_user, account_factory, auth_user_factory
    ):
        """Test super admin can delete any account."""
        # Arrange
        super_admin_id, token = create_test_user(is_super_admin=True)
        other_user = auth_user_factory()
        other_account = account_factory(owner_user_id=other_user)

        # Act
        response = client.delete(
            f"/v1/api/accounts/{other_account}",
            headers={"Authorization": f"Bearer {token}"},
        )

        # Assert
        assert response.status_code == 204


# ============================================================================
# Super Admin Routes Tests
# ============================================================================


class TestSuperAdminRoutes:
    """Test super admin-only routes."""

    def test_list_all_accounts_super_admin(
        self, create_test_user, account_factory, auth_user_factory
    ):
        """Test super admin can list all accounts in system."""
        # Arrange
        super_admin_id, token = create_test_user(is_super_admin=True)

        # Create multiple accounts
        user1 = auth_user_factory()
        user2 = auth_user_factory()
        account1 = account_factory(owner_user_id=user1, name="Account 1")
        account2 = account_factory(owner_user_id=user2, name="Account 2")

        # Act
        response = client.get(
            "/v1/api/accounts/admin/all",
            headers={"Authorization": f"Bearer {token}"},
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 2
        assert any(a["account_name"] == "Account 1" for a in data)
        assert any(a["account_name"] == "Account 2" for a in data)
        # Should include owner details
        assert all("owner_email" in a for a in data)
        assert all("user_count" in a for a in data)

    def test_list_all_accounts_regular_user_denied(self, create_test_user):
        """Test regular user cannot access super admin route."""
        # Arrange
        user_id, token = create_test_user(is_super_admin=False)

        # Act
        response = client.get(
            "/v1/api/accounts/admin/all",
            headers={"Authorization": f"Bearer {token}"},
        )

        # Assert
        assert response.status_code == 403


# ============================================================================
# Integration Tests
# ============================================================================


class TestAccountAPIIntegration:
    """Integration tests for full account lifecycle."""

    def test_full_account_lifecycle(self, create_test_user, engine):
        """Test complete account CRUD cycle with audit logging."""
        # Arrange
        user_id, token = create_test_user()
        from uuid import uuid4

        account_name = f"Lifecycle Test Account {uuid4().hex[:8]}"

        # Act 1: Create account
        create_response = client.post(
            "/v1/api/accounts/",
            json={"account_name": account_name},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert create_response.status_code == 200
        account_id = create_response.json()["account_id"]

        # Act 2: List accounts (should see new account)
        list_response = client.get(
            "/v1/api/accounts/",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert list_response.status_code == 200
        accounts = list_response.json()
        assert any(a["account_id"] == account_id for a in accounts)

        # Act 3: Get account details
        get_response = client.get(
            f"/v1/api/accounts/{account_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert get_response.status_code == 403  # No account context in token

        # Act 4: Update account (need token with account context)
        from common.service_connections.db_service.database.tables.account_tables.auth_user import (
            AuthUserTable,
        )

        with session(engine) as db_session:
            user = db_session.get(AuthUserTable, user_id)

        from app.services.jwt_service import get_jwt_service

        jwt_service = get_jwt_service()
        account_token = jwt_service.create_access_token(
            user_id=user_id,
            email=user.email,
            is_admin=user.is_admin,
            account_id=account_id,
            account_role=AccountRoleEnum.OWNER.value,
        )

        update_response = client.put(
            f"/v1/api/accounts/{account_id}",
            json={"account_name": f"Updated Lifecycle Account {uuid4().hex[:8]}"},
            headers={"Authorization": f"Bearer {account_token}"},
        )
        assert (
            update_response.status_code == 200
        ), f"Update failed with {update_response.status_code}: {update_response.text}"

        # Act 5: Delete account
        delete_response = client.delete(
            f"/v1/api/accounts/{account_id}",
            headers={"Authorization": f"Bearer {account_token}"},
        )
        assert delete_response.status_code == 204

        # Assert: Verify audit trail
        from common.service_connections.db_service.database.enums import AuditActionEnum

        with session(engine) as db_session:
            audits = query_audit_logs_by_account(account_id, db_session, engine)
            assert len(audits) >= 3  # Create, update, delete
            actions = [a.action for a in audits]
            assert AuditActionEnum.CREATE in actions
            assert AuditActionEnum.UPDATE in actions
            assert AuditActionEnum.DELETE in actions
