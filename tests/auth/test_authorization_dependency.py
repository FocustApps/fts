"""
Tests for role-based authorization dependencies.

Tests verify:
- Role hierarchy enforcement (owner > admin > member > viewer)
- Account access validation
- Super admin bypass logic
- Convenience dependencies (require_owner, require_admin, etc.)
"""

import pytest
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from fastapi import HTTPException

from app.models.auth_models import TokenPayload
from app.dependencies.authorization_dependency import (
    validate_account_access,
    require_account_role,
    require_owner,
    require_admin,
    require_member,
    require_viewer,
    require_super_admin,
    ROLE_HIERARCHY,
)
from common.service_connections.db_service.database.enums import AccountRoleEnum


@pytest.fixture
def user_id():
    """Generate user ID."""
    return str(uuid4())


@pytest.fixture
def account_id():
    """Generate account ID."""
    return str(uuid4())


@pytest.fixture
def create_token():
    """Factory for creating test tokens."""

    def _create(
        user_id=None,
        account_id=None,
        account_role=None,
        is_super_admin=False,
        is_admin=False,
    ):
        return TokenPayload(
            user_id=user_id or str(uuid4()),
            email="user@example.com",
            is_admin=is_admin,
            is_super_admin=is_super_admin,
            account_id=account_id,
            account_role=account_role,
            exp=datetime.now(timezone.utc) + timedelta(hours=1),
            jti=str(uuid4()),
        )

    return _create


class TestRoleHierarchy:
    """Test role hierarchy values are correctly defined."""

    def test_role_hierarchy_values(self):
        """Verify role hierarchy ordering."""
        assert ROLE_HIERARCHY[AccountRoleEnum.OWNER.value] == 4
        assert ROLE_HIERARCHY[AccountRoleEnum.ADMIN.value] == 3
        assert ROLE_HIERARCHY[AccountRoleEnum.MEMBER.value] == 2
        assert ROLE_HIERARCHY[AccountRoleEnum.VIEWER.value] == 1

    def test_role_hierarchy_comparison(self):
        """Verify role comparisons work correctly."""
        owner = ROLE_HIERARCHY[AccountRoleEnum.OWNER.value]
        admin = ROLE_HIERARCHY[AccountRoleEnum.ADMIN.value]
        member = ROLE_HIERARCHY[AccountRoleEnum.MEMBER.value]
        viewer = ROLE_HIERARCHY[AccountRoleEnum.VIEWER.value]

        assert owner > admin > member > viewer


class TestValidateAccountAccess:
    """Test account access validation."""

    def test_valid_account_access(self, create_token, account_id):
        """Test user can access their own account."""
        token = create_token(account_id=account_id)
        # Should not raise
        validate_account_access(token, account_id)

    def test_invalid_account_access(self, create_token, account_id):
        """Test user cannot access different account."""
        token = create_token(account_id=account_id)
        other_account_id = str(uuid4())

        with pytest.raises(HTTPException) as exc_info:
            validate_account_access(token, other_account_id)

        assert exc_info.value.status_code == 403
        assert "Access denied" in exc_info.value.detail

    def test_super_admin_bypass(self, create_token, account_id):
        """Test super admin can access any account."""
        token = create_token(is_super_admin=True, account_id=None)
        other_account_id = str(uuid4())

        # Should not raise
        validate_account_access(token, other_account_id, allow_super_admin=True)

    def test_super_admin_bypass_disabled(self, create_token, account_id):
        """Test super admin bypass can be disabled."""
        token = create_token(is_super_admin=True, account_id=account_id)
        other_account_id = str(uuid4())

        with pytest.raises(HTTPException) as exc_info:
            validate_account_access(token, other_account_id, allow_super_admin=False)

        assert exc_info.value.status_code == 403

    def test_no_account_context(self, create_token):
        """Test error when token has no account context."""
        token = create_token(account_id=None)
        requested_account_id = str(uuid4())

        with pytest.raises(HTTPException) as exc_info:
            validate_account_access(token, requested_account_id)

        assert exc_info.value.status_code == 403
        assert "No account context" in exc_info.value.detail


class TestRequireAccountRole:
    """Test require_account_role dependency factory."""

    def test_owner_role_granted(self, create_token, account_id):
        """Test owner role passes owner requirement."""
        token = create_token(
            account_id=account_id, account_role=AccountRoleEnum.OWNER.value
        )
        dependency = require_account_role(AccountRoleEnum.OWNER.value)
        result = dependency(token)
        assert result == token

    def test_admin_role_granted_for_member_requirement(self, create_token, account_id):
        """Test admin role passes member requirement (higher role)."""
        token = create_token(
            account_id=account_id, account_role=AccountRoleEnum.ADMIN.value
        )
        dependency = require_account_role(AccountRoleEnum.MEMBER.value)
        result = dependency(token)
        assert result == token

    def test_viewer_role_denied_for_admin_requirement(self, create_token, account_id):
        """Test viewer role fails admin requirement (lower role)."""
        token = create_token(
            account_id=account_id, account_role=AccountRoleEnum.VIEWER.value
        )
        dependency = require_account_role(AccountRoleEnum.ADMIN.value)

        with pytest.raises(HTTPException) as exc_info:
            dependency(token)

        assert exc_info.value.status_code == 403
        assert "admin role or higher required" in exc_info.value.detail

    def test_super_admin_bypass_role_check(self, create_token):
        """Test super admin bypasses role requirements."""
        token = create_token(is_super_admin=True, account_id=None, account_role=None)
        dependency = require_account_role(
            AccountRoleEnum.OWNER.value, allow_super_admin=True
        )
        result = dependency(token)
        assert result == token

    def test_no_account_role_in_token(self, create_token, account_id):
        """Test error when token has no account role."""
        token = create_token(account_id=account_id, account_role=None)
        dependency = require_account_role(AccountRoleEnum.MEMBER.value)

        with pytest.raises(HTTPException) as exc_info:
            dependency(token)

        assert exc_info.value.status_code == 403
        assert "No account role" in exc_info.value.detail

    def test_invalid_min_role(self, create_token, account_id):
        """Test error with invalid min_role value."""
        token = create_token(
            account_id=account_id, account_role=AccountRoleEnum.ADMIN.value
        )
        dependency = require_account_role("invalid_role")

        with pytest.raises(ValueError) as exc_info:
            dependency(token)

        assert "Invalid min_role" in str(exc_info.value)


class TestConvenienceDependencies:
    """Test convenience dependency functions."""

    def test_require_owner_with_owner_role(self, create_token, account_id):
        """Test require_owner passes for owner."""
        token = create_token(
            account_id=account_id, account_role=AccountRoleEnum.OWNER.value
        )
        result = require_owner(token)
        assert result == token

    def test_require_owner_with_admin_role(self, create_token, account_id):
        """Test require_owner fails for admin."""
        token = create_token(
            account_id=account_id, account_role=AccountRoleEnum.ADMIN.value
        )

        with pytest.raises(HTTPException) as exc_info:
            require_owner(token)

        assert exc_info.value.status_code == 403

    def test_require_admin_with_admin_role(self, create_token, account_id):
        """Test require_admin passes for admin."""
        token = create_token(
            account_id=account_id, account_role=AccountRoleEnum.ADMIN.value
        )
        result = require_admin(token)
        assert result == token

    def test_require_admin_with_owner_role(self, create_token, account_id):
        """Test require_admin passes for owner (higher role)."""
        token = create_token(
            account_id=account_id, account_role=AccountRoleEnum.OWNER.value
        )
        result = require_admin(token)
        assert result == token

    def test_require_admin_with_member_role(self, create_token, account_id):
        """Test require_admin fails for member."""
        token = create_token(
            account_id=account_id, account_role=AccountRoleEnum.MEMBER.value
        )

        with pytest.raises(HTTPException) as exc_info:
            require_admin(token)

        assert exc_info.value.status_code == 403

    def test_require_member_with_member_role(self, create_token, account_id):
        """Test require_member passes for member."""
        token = create_token(
            account_id=account_id, account_role=AccountRoleEnum.MEMBER.value
        )
        result = require_member(token)
        assert result == token

    def test_require_member_with_admin_role(self, create_token, account_id):
        """Test require_member passes for admin (higher role)."""
        token = create_token(
            account_id=account_id, account_role=AccountRoleEnum.ADMIN.value
        )
        result = require_member(token)
        assert result == token

    def test_require_member_with_viewer_role(self, create_token, account_id):
        """Test require_member fails for viewer."""
        token = create_token(
            account_id=account_id, account_role=AccountRoleEnum.VIEWER.value
        )

        with pytest.raises(HTTPException) as exc_info:
            require_member(token)

        assert exc_info.value.status_code == 403

    def test_require_viewer_with_all_roles(self, create_token, account_id):
        """Test require_viewer passes for all roles."""
        roles = [
            AccountRoleEnum.OWNER.value,
            AccountRoleEnum.ADMIN.value,
            AccountRoleEnum.MEMBER.value,
            AccountRoleEnum.VIEWER.value,
        ]

        for role in roles:
            token = create_token(account_id=account_id, account_role=role)
            result = require_viewer(token)
            assert result == token

    def test_require_super_admin_with_super_admin(self, create_token):
        """Test require_super_admin passes for super admin."""
        token = create_token(is_super_admin=True)
        result = require_super_admin(token)
        assert result == token

    def test_require_super_admin_with_regular_user(self, create_token, account_id):
        """Test require_super_admin fails for regular user."""
        token = create_token(
            account_id=account_id,
            account_role=AccountRoleEnum.OWNER.value,
            is_super_admin=False,
        )

        with pytest.raises(HTTPException) as exc_info:
            require_super_admin(token)

        assert exc_info.value.status_code == 403
        assert "Super admin access required" in exc_info.value.detail


class TestRoleHierarchyEnforcement:
    """Test role hierarchy is correctly enforced across all levels."""

    def test_owner_can_access_all_lower_requirements(self, create_token, account_id):
        """Test owner passes admin, member, viewer requirements."""
        token = create_token(
            account_id=account_id, account_role=AccountRoleEnum.OWNER.value
        )

        # Should all pass
        require_owner(token)
        require_admin(token)
        require_member(token)
        require_viewer(token)

    def test_admin_cannot_access_owner_only(self, create_token, account_id):
        """Test admin fails owner requirement but passes lower."""
        token = create_token(
            account_id=account_id, account_role=AccountRoleEnum.ADMIN.value
        )

        # Should fail
        with pytest.raises(HTTPException):
            require_owner(token)

        # Should pass
        require_admin(token)
        require_member(token)
        require_viewer(token)

    def test_member_cannot_access_admin_or_owner(self, create_token, account_id):
        """Test member fails admin/owner requirements but passes lower."""
        token = create_token(
            account_id=account_id, account_role=AccountRoleEnum.MEMBER.value
        )

        # Should fail
        with pytest.raises(HTTPException):
            require_owner(token)
        with pytest.raises(HTTPException):
            require_admin(token)

        # Should pass
        require_member(token)
        require_viewer(token)

    def test_viewer_can_only_access_viewer_requirement(self, create_token, account_id):
        """Test viewer fails all higher requirements."""
        token = create_token(
            account_id=account_id, account_role=AccountRoleEnum.VIEWER.value
        )

        # Should fail
        with pytest.raises(HTTPException):
            require_owner(token)
        with pytest.raises(HTTPException):
            require_admin(token)
        with pytest.raises(HTTPException):
            require_member(token)

        # Should pass
        require_viewer(token)

    def test_super_admin_bypasses_all_role_requirements(self, create_token):
        """Test super admin bypasses all role checks."""
        token = create_token(is_super_admin=True, account_id=None, account_role=None)

        # Should all pass
        require_owner(token)
        require_admin(token)
        require_member(token)
        require_viewer(token)
        require_super_admin(token)
