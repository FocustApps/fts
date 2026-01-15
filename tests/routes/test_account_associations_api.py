"""
Tests for account associations API routes.

Tests cover:
- Adding users to accounts (requires admin+)
- Listing users in accounts (requires viewer+)
- Updating user roles (requires admin+)
- Removing users from accounts (requires admin+)
- Setting primary accounts (self-service)
- Authorization validation
- Audit logging integration
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
from common.service_connections.db_service.database.enums import (
    AccountRoleEnum,
)
from common.service_connections.db_service.database.tables.account_tables.auth_user import (
    AuthUserTable,
)
from common.service_connections.db_service.db_manager import DB_ENGINE
from common.service_connections.db_service.models.account_models import (
    query_users_by_account,
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
def create_account_with_owner(create_test_user, engine):
    """Fixture to create account with owner."""

    def _create(owner_email: str = None):
        """Create account and return account_id, owner_user_id, owner_token."""
        # Create owner user
        owner_user_id, owner_token = create_test_user(email=owner_email)

        # Create account
        account_name = f"Test Account {uuid4().hex[:8]}"
        response = client.post(
            "/v1/api/accounts/",
            json={"account_name": account_name},
            headers={"Authorization": f"Bearer {owner_token}"},
        )
        assert response.status_code == 200
        account_id = response.json()["account_id"]

        # Create account-scoped token
        with session(engine) as db_session:
            user = db_session.get(AuthUserTable, owner_user_id)

        from app.services.jwt_service import get_jwt_service

        jwt_service = get_jwt_service()
        account_token = jwt_service.create_access_token(
            user_id=owner_user_id,
            email=user.email,
            is_admin=user.is_admin,
            account_id=account_id,
            account_role=AccountRoleEnum.OWNER.value,
        )

        return account_id, owner_user_id, account_token

    return _create


# ============================================================================
# Add User Tests
# ============================================================================


@pytest.mark.usefixtures("engine")
class TestAddUserToAccount:
    """Tests for POST /accounts/{account_id}/users."""

    def test_add_user_as_admin_success(self, create_account_with_owner, create_test_user):
        """Test admin can add a user to account."""
        # Arrange
        account_id, owner_id, owner_token = create_account_with_owner()
        new_user_id, _ = create_test_user()

        # Act
        response = client.post(
            f"/v1/api/accounts/{account_id}/users",
            json={
                "auth_user_id": new_user_id,
                "role": AccountRoleEnum.MEMBER.value,
                "is_primary": False,
            },
            headers={"Authorization": f"Bearer {owner_token}"},
        )

        # Assert
        assert response.status_code == 201
        data = response.json()
        assert data["auth_user_id"] == new_user_id
        assert data["account_id"] == account_id
        assert data["role"] == AccountRoleEnum.MEMBER.value
        assert data["is_primary"] is False
        assert data["invited_by_user_id"] == owner_id

    def test_add_user_requires_authentication(
        self, create_account_with_owner, create_test_user
    ):
        """Test unauthenticated request is rejected."""
        # Arrange
        account_id, _, _ = create_account_with_owner()
        new_user_id, _ = create_test_user()

        # Act
        response = client.post(
            f"/v1/api/accounts/{account_id}/users",
            json={"auth_user_id": new_user_id, "role": "member"},
        )

        # Assert
        assert response.status_code == 401

    def test_add_user_requires_admin_role(
        self, create_account_with_owner, create_test_user, engine
    ):
        """Test member cannot add users (requires admin)."""
        # Arrange
        account_id, owner_id, owner_token = create_account_with_owner()
        member_user_id, _ = create_test_user()

        # Add member to account
        add_user_to_account(
            auth_user_id=member_user_id,
            account_id=account_id,
            role=AccountRoleEnum.MEMBER.value,
            invited_by_user_id=owner_id,
            engine=engine,
        )

        # Create member token
        with session(engine) as db_session:
            user = db_session.get(AuthUserTable, member_user_id)

        from app.services.jwt_service import get_jwt_service

        jwt_service = get_jwt_service()
        member_token = jwt_service.create_access_token(
            user_id=member_user_id,
            email=user.email,
            is_admin=user.is_admin,
            account_id=account_id,
            account_role=AccountRoleEnum.MEMBER.value,
        )

        new_user_id, _ = create_test_user()

        # Act
        response = client.post(
            f"/v1/api/accounts/{account_id}/users",
            json={"auth_user_id": new_user_id, "role": "member"},
            headers={"Authorization": f"Bearer {member_token}"},
        )

        # Assert
        assert response.status_code == 403

    def test_add_user_invalid_role_rejected(
        self, create_account_with_owner, create_test_user
    ):
        """Test invalid role is rejected."""
        # Arrange
        account_id, _, owner_token = create_account_with_owner()
        new_user_id, _ = create_test_user()

        # Act
        response = client.post(
            f"/v1/api/accounts/{account_id}/users",
            json={"auth_user_id": new_user_id, "role": "invalid_role"},
            headers={"Authorization": f"Bearer {owner_token}"},
        )

        # Assert
        assert response.status_code == 400


# ============================================================================
# List Users Tests
# ============================================================================


@pytest.mark.usefixtures("engine")
class TestListAccountUsers:
    """Tests for GET /accounts/{account_id}/users."""

    def test_list_users_as_viewer(
        self, create_account_with_owner, create_test_user, engine
    ):
        """Test viewer can list account users."""
        # Arrange
        account_id, owner_id, _ = create_account_with_owner()
        viewer_id, _ = create_test_user()

        # Add viewer to account
        add_user_to_account(
            auth_user_id=viewer_id,
            account_id=account_id,
            role=AccountRoleEnum.VIEWER.value,
            invited_by_user_id=owner_id,
            engine=engine,
        )

        # Create viewer token
        with session(engine) as db_session:
            user = db_session.get(AuthUserTable, viewer_id)

        from app.services.jwt_service import get_jwt_service

        jwt_service = get_jwt_service()
        viewer_token = jwt_service.create_access_token(
            user_id=viewer_id,
            email=user.email,
            is_admin=user.is_admin,
            account_id=account_id,
            account_role=AccountRoleEnum.VIEWER.value,
        )

        # Act
        response = client.get(
            f"/v1/api/accounts/{account_id}/users",
            headers={"Authorization": f"Bearer {viewer_token}"},
        )

        # Assert
        assert response.status_code == 200
        users = response.json()
        assert len(users) == 2  # Owner + Viewer
        user_ids = [u["auth_user_id"] for u in users]
        assert owner_id in user_ids
        assert viewer_id in user_ids

    def test_list_users_requires_authentication(self, create_account_with_owner):
        """Test unauthenticated request is rejected."""
        # Arrange
        account_id, _, _ = create_account_with_owner()

        # Act
        response = client.get(f"/v1/api/accounts/{account_id}/users")

        # Assert
        assert response.status_code == 401

    def test_list_users_requires_account_access(
        self, create_account_with_owner, create_test_user
    ):
        """Test user without account access is rejected."""
        # Arrange
        account_id, _, _ = create_account_with_owner()
        other_user_id, other_token = create_test_user()

        # Act
        response = client.get(
            f"/v1/api/accounts/{account_id}/users",
            headers={"Authorization": f"Bearer {other_token}"},
        )

        # Assert
        assert response.status_code == 403


# ============================================================================
# Update Role Tests
# ============================================================================


@pytest.mark.usefixtures("engine")
class TestUpdateUserRole:
    """Tests for PUT /accounts/{account_id}/users/{user_id}."""

    def test_update_role_as_admin_success(
        self, create_account_with_owner, create_test_user, engine
    ):
        """Test admin can update user role."""
        # Arrange
        account_id, owner_id, owner_token = create_account_with_owner()
        member_id, _ = create_test_user()

        # Add member
        add_user_to_account(
            auth_user_id=member_id,
            account_id=account_id,
            role=AccountRoleEnum.MEMBER.value,
            invited_by_user_id=owner_id,
            engine=engine,
        )

        # Act - Promote to admin
        response = client.put(
            f"/v1/api/accounts/{account_id}/users/{member_id}",
            json={"role": AccountRoleEnum.ADMIN.value},
            headers={"Authorization": f"Bearer {owner_token}"},
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["role"] == AccountRoleEnum.ADMIN.value

    def test_update_role_requires_admin(
        self, create_account_with_owner, create_test_user, engine
    ):
        """Test member cannot update roles."""
        # Arrange
        account_id, owner_id, _ = create_account_with_owner()
        member1_id, _ = create_test_user()
        member2_id, _ = create_test_user()

        # Add both members
        add_user_to_account(
            auth_user_id=member1_id,
            account_id=account_id,
            role=AccountRoleEnum.MEMBER.value,
            invited_by_user_id=owner_id,
            engine=engine,
        )
        add_user_to_account(
            auth_user_id=member2_id,
            account_id=account_id,
            role=AccountRoleEnum.MEMBER.value,
            invited_by_user_id=owner_id,
            engine=engine,
        )

        # Create member1 token
        with session(engine) as db_session:
            user = db_session.get(AuthUserTable, member1_id)

        from app.services.jwt_service import get_jwt_service

        jwt_service = get_jwt_service()
        member_token = jwt_service.create_access_token(
            user_id=member1_id,
            email=user.email,
            is_admin=user.is_admin,
            account_id=account_id,
            account_role=AccountRoleEnum.MEMBER.value,
        )

        # Act - Try to promote member2
        response = client.put(
            f"/v1/api/accounts/{account_id}/users/{member2_id}",
            json={"role": AccountRoleEnum.ADMIN.value},
            headers={"Authorization": f"Bearer {member_token}"},
        )

        # Assert
        assert response.status_code == 403


# ============================================================================
# Remove User Tests
# ============================================================================


@pytest.mark.usefixtures("engine")
class TestRemoveUserFromAccount:
    """Tests for DELETE /accounts/{account_id}/users/{user_id}."""

    def test_remove_user_as_admin_success(
        self, create_account_with_owner, create_test_user, engine
    ):
        """Test admin can remove users."""
        # Arrange
        account_id, owner_id, owner_token = create_account_with_owner()
        member_id, _ = create_test_user()

        # Add member
        add_user_to_account(
            auth_user_id=member_id,
            account_id=account_id,
            role=AccountRoleEnum.MEMBER.value,
            invited_by_user_id=owner_id,
            engine=engine,
        )

        # Act
        response = client.delete(
            f"/v1/api/accounts/{account_id}/users/{member_id}",
            headers={"Authorization": f"Bearer {owner_token}"},
        )

        # Assert
        assert response.status_code == 204

        # Verify user removed
        with session(engine) as db_session:
            users = query_users_by_account(account_id, db_session, engine)
            user_ids = [u.auth_user_id for u in users]
            assert member_id not in user_ids

    def test_remove_owner_rejected(self, create_account_with_owner):
        """Test cannot remove account owner."""
        # Arrange
        account_id, owner_id, owner_token = create_account_with_owner()

        # Act - Try to remove owner
        response = client.delete(
            f"/v1/api/accounts/{account_id}/users/{owner_id}",
            headers={"Authorization": f"Bearer {owner_token}"},
        )

        # Assert
        assert response.status_code == 400
        assert "owner" in response.json()["detail"].lower()


# ============================================================================
# Set Primary Account Tests
# ============================================================================


@pytest.mark.usefixtures("engine")
class TestSetPrimaryAccount:
    """Tests for PUT /accounts/{account_id}/users/{user_id}/primary."""

    def test_set_primary_account_success(
        self, create_account_with_owner, create_test_user, engine
    ):
        """Test user can set their own primary account."""
        # Arrange
        account_id, owner_id, _ = create_account_with_owner()
        member_id, _ = create_test_user()

        # Add member to account
        add_user_to_account(
            auth_user_id=member_id,
            account_id=account_id,
            role=AccountRoleEnum.MEMBER.value,
            invited_by_user_id=owner_id,
            engine=engine,
        )

        # Create member token
        with session(engine) as db_session:
            user = db_session.get(AuthUserTable, member_id)

        from app.services.jwt_service import get_jwt_service

        jwt_service = get_jwt_service()
        member_token = jwt_service.create_access_token(
            user_id=member_id,
            email=user.email,
            is_admin=user.is_admin,
            account_id=account_id,
            account_role=AccountRoleEnum.MEMBER.value,
        )

        # Act
        response = client.put(
            f"/v1/api/accounts/{account_id}/users/{member_id}/primary",
            headers={"Authorization": f"Bearer {member_token}"},
        )

        # Assert
        assert response.status_code == 200

    def test_set_primary_for_other_user_rejected(
        self, create_account_with_owner, create_test_user, engine
    ):
        """Test user cannot set another user's primary account."""
        # Arrange
        account_id, owner_id, owner_token = create_account_with_owner()
        member_id, _ = create_test_user()

        # Add member
        add_user_to_account(
            auth_user_id=member_id,
            account_id=account_id,
            role=AccountRoleEnum.MEMBER.value,
            invited_by_user_id=owner_id,
            engine=engine,
        )

        # Act - Owner tries to set member's primary
        response = client.put(
            f"/v1/api/accounts/{account_id}/users/{member_id}/primary",
            headers={"Authorization": f"Bearer {owner_token}"},
        )

        # Assert
        assert response.status_code == 403


# ============================================================================
# Integration Tests
# ============================================================================


@pytest.mark.usefixtures("engine")
class TestAccountAssociationsIntegration:
    """End-to-end integration tests."""

    def test_full_user_lifecycle(
        self, create_account_with_owner, create_test_user, engine
    ):
        """Test complete user association lifecycle."""
        # Arrange
        account_id, owner_id, owner_token = create_account_with_owner()
        user_id, _ = create_test_user()

        # Act 1: Add user
        add_response = client.post(
            f"/v1/api/accounts/{account_id}/users",
            json={"auth_user_id": user_id, "role": "member"},
            headers={"Authorization": f"Bearer {owner_token}"},
        )
        assert add_response.status_code == 201

        # Act 2: List users
        list_response = client.get(
            f"/v1/api/accounts/{account_id}/users",
            headers={"Authorization": f"Bearer {owner_token}"},
        )
        assert list_response.status_code == 200
        users = list_response.json()
        assert len(users) == 2

        # Act 3: Update role
        update_response = client.put(
            f"/v1/api/accounts/{account_id}/users/{user_id}",
            json={"role": "admin"},
            headers={"Authorization": f"Bearer {owner_token}"},
        )
        assert update_response.status_code == 200
        assert update_response.json()["role"] == "admin"

        # Act 4: Remove user
        remove_response = client.delete(
            f"/v1/api/accounts/{account_id}/users/{user_id}",
            headers={"Authorization": f"Bearer {owner_token}"},
        )
        assert remove_response.status_code == 204

        # Assert: Verify user removed
        with session(engine) as db_session:
            users = query_users_by_account(account_id, db_session, engine)
            user_ids = [u.auth_user_id for u in users]
            assert user_id not in user_ids
            assert owner_id in user_ids  # Owner still there

    def test_audit_logging(self, create_account_with_owner, create_test_user, engine):
        """Test audit logs are created for association operations."""
        # Arrange
        account_id, owner_id, owner_token = create_account_with_owner()
        user_id, _ = create_test_user()

        # Act: Add and remove user
        client.post(
            f"/v1/api/accounts/{account_id}/users",
            json={"auth_user_id": user_id, "role": "member"},
            headers={"Authorization": f"Bearer {owner_token}"},
        )

        client.put(
            f"/v1/api/accounts/{account_id}/users/{user_id}",
            json={"role": "admin"},
            headers={"Authorization": f"Bearer {owner_token}"},
        )

        client.delete(
            f"/v1/api/accounts/{account_id}/users/{user_id}",
            headers={"Authorization": f"Bearer {owner_token}"},
        )

        # Assert: Verify audit logs
        with session(engine) as db_session:
            audits = query_audit_logs_by_account(account_id, db_session, engine)
            # Should have: account created, user added to account (owner), user added (member), role changed, user removed
            assert len(audits) >= 3
