"""
Tests for plans API routes with role-based authorization.

Tests cover:
- GET endpoints require member role
- POST/PUT/PATCH/DELETE endpoints require admin role
- Account access validation for account-scoped endpoints
- Super admin bypass logic
"""

import pytest
from uuid import uuid4
from fastapi.testclient import TestClient

from app.fenrir_app import app
from app.services.user_auth_service import get_user_auth_service
from common.service_connections.db_service.database.engine import (
    get_database_session as session,
)
from common.service_connections.db_service.database.enums import AccountRoleEnum
from common.service_connections.db_service.db_manager import DB_ENGINE
from common.service_connections.db_service.models.account_models import (
    add_user_to_account,
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
        test_email = email or f"test_{uuid4().hex[:8]}@example.com"
        register_req = RegisterRequest(
            email=test_email,
            password="TestPass123!",
            username=f"testuser_{uuid4().hex[:8]}",
        )
        user = auth_service.register_user(register_req)

        if is_super_admin:
            with session(DB_ENGINE) as db_session:
                from common.service_connections.db_service.database.tables.account_tables.auth_user import (
                    AuthUserTable,
                )

                db_user = db_session.get(AuthUserTable, user.auth_user_id)
                db_user.is_super_admin = True
                db_session.commit()

        login_req = LoginRequest(
            email=test_email, password="TestPass123!", remember_me=False
        )
        tokens = auth_service.authenticate(login_req)

        return user.auth_user_id, tokens.access_token

    return _create_user


@pytest.fixture
def create_user_with_role(create_test_user, account_factory):
    """Create user with specific role in an account."""

    def _create(role: AccountRoleEnum = AccountRoleEnum.MEMBER):
        user_id, _ = create_test_user()
        account_id = account_factory(owner_user_id=user_id)

        if role != AccountRoleEnum.OWNER:
            add_user_to_account(
                auth_user_id=user_id,
                account_id=account_id,
                role=role.value,
                is_primary=True,
                invited_by_user_id=user_id,
                engine=DB_ENGINE,
            )

        from common.service_connections.db_service.database.tables.account_tables.auth_user import (
            AuthUserTable,
        )

        with session(DB_ENGINE) as db_session:
            user = db_session.get(AuthUserTable, user_id)

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


class TestPlanAuthorizationGET:
    """Test GET endpoints require member role."""

    def test_get_all_plans_requires_member(self, create_test_user):
        """Test GET /v1/api/plans/ requires member role."""
        _, token = create_test_user()
        response = client.get(
            "/v1/api/plans/", headers={"Authorization": f"Bearer {token}"}
        )
        # Without account context, should fail
        assert response.status_code == 403

    def test_get_all_plans_with_member_succeeds(self, create_user_with_role):
        """Test member can get all plans."""
        _, _, token = create_user_with_role(AccountRoleEnum.MEMBER)
        response = client.get(
            "/v1/api/plans/", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200

    def test_get_plans_by_account_validates_access(
        self, create_user_with_role, account_factory
    ):
        """Test account access validation on account-scoped endpoint."""
        user_id, account_id, token = create_user_with_role(AccountRoleEnum.MEMBER)

        # Try to access different account - should fail
        other_account_id = account_factory(owner_user_id=user_id)
        response = client.get(
            f"/v1/api/plans/account/{other_account_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403

        # Access own account - should succeed
        response = client.get(
            f"/v1/api/plans/account/{account_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200


class TestPlanAuthorizationPOST:
    """Test POST endpoints require admin role."""

    def test_create_plan_requires_admin(self, create_user_with_role):
        """Test member cannot create plans."""
        user_id, account_id, token = create_user_with_role(AccountRoleEnum.MEMBER)

        response = client.post(
            "/v1/api/plans/",
            json={
                "plan_name": "Test Plan",
                "account_id": account_id,
                "owner_user_id": user_id,
                "status": "active",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403

    def test_create_plan_admin_succeeds(self, create_user_with_role):
        """Test admin can create plans."""
        user_id, account_id, token = create_user_with_role(AccountRoleEnum.ADMIN)

        response = client.post(
            "/v1/api/plans/",
            json={
                "plan_name": "Test Plan",
                "account_id": account_id,
                "owner_user_id": user_id,
                "status": "active",
                "suites_ids": "",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200


class TestPlanAuthorizationUPDATE:
    """Test PUT/PATCH endpoints require admin role."""

    def test_update_plan_requires_admin(
        self, create_user_with_role, plan_factory, engine
    ):
        """Test member cannot update plans."""
        user_id, account_id, member_token = create_user_with_role(AccountRoleEnum.MEMBER)
        plan_id = plan_factory(account_id=account_id, owner_user_id=user_id)

        response = client.put(
            f"/v1/api/plans/{plan_id}",
            json={
                "plan_name": "Updated Plan",
                "account_id": account_id,
                "owner_user_id": user_id,
                "status": "active",
                "description": "Updated",
            },
            headers={"Authorization": f"Bearer {member_token}"},
        )
        assert response.status_code == 403

    def test_update_plan_admin_succeeds(
        self, create_user_with_role, plan_factory, engine
    ):
        """Test admin can update plans."""
        user_id, account_id, token = create_user_with_role(AccountRoleEnum.ADMIN)
        plan_id = plan_factory(account_id=account_id, owner_user_id=user_id)

        response = client.put(
            f"/v1/api/plans/{plan_id}",
            json={
                "plan_name": "Updated Plan",
                "account_id": account_id,
                "owner_user_id": user_id,
                "status": "active",
                "description": "Updated",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200


class TestPlanAuthorizationDELETE:
    """Test DELETE endpoints require admin role."""

    def test_delete_plan_requires_admin(
        self, create_user_with_role, plan_factory, engine
    ):
        """Test member cannot delete plans."""
        user_id, account_id, member_token = create_user_with_role(AccountRoleEnum.MEMBER)
        plan_id = plan_factory(account_id=account_id, owner_user_id=user_id)

        response = client.delete(
            f"/v1/api/plans/{plan_id}",
            headers={"Authorization": f"Bearer {member_token}"},
        )
        assert response.status_code == 403

    def test_delete_plan_admin_succeeds(
        self, create_user_with_role, plan_factory, engine
    ):
        """Test admin can delete plans."""
        user_id, account_id, token = create_user_with_role(AccountRoleEnum.ADMIN)
        plan_id = plan_factory(account_id=account_id, owner_user_id=user_id)

        response = client.delete(
            f"/v1/api/plans/{plan_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200


class TestSuperAdminBypass:
    """Test super admin can access any account."""

    def test_super_admin_bypasses_account_validation(
        self, create_test_user, create_user_with_role
    ):
        """Test super admin can access any account's plans."""
        # Create super admin
        admin_id, admin_token = create_test_user(is_super_admin=True)

        # Create regular user with account
        user_id, account_id, user_token = create_user_with_role(AccountRoleEnum.MEMBER)

        # Super admin should access without being in account
        response = client.get(
            f"/v1/api/plans/account/{account_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
