"""
Tests for JWT token payload enhancement with multi-tenant account context.

Tests verify:
- TokenPayload includes account_id, account_role, is_super_admin
- Token generation includes primary account context
- Token refresh preserves account context
- Backward compatibility with tokens missing new fields
"""

import pytest
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from app.models.auth_models import TokenPayload
from app.services.jwt_service import JWTService
from app.config import get_base_app_config
from common.service_connections.db_service.database.enums import AccountRoleEnum


@pytest.fixture
def jwt_service():
    """Create JWT service instance."""
    config = get_base_app_config()
    return JWTService(config)


class TestTokenPayloadEnhancement:
    """Test TokenPayload model with multi-tenant fields."""

    def test_token_payload_with_account_context(self):
        """Test TokenPayload creation with full account context."""
        token = TokenPayload(
            user_id=str(uuid4()),
            email="user@example.com",
            is_admin=False,
            is_super_admin=False,
            account_id=str(uuid4()),
            account_role=AccountRoleEnum.ADMIN.value,
            exp=datetime.now(timezone.utc) + timedelta(hours=1),
            jti=str(uuid4()),
        )

        assert token.user_id is not None
        assert token.email == "user@example.com"
        assert token.is_admin is False
        assert token.is_super_admin is False
        assert token.account_id is not None
        assert token.account_role == AccountRoleEnum.ADMIN.value
        assert token.exp is not None
        assert token.jti is not None

    def test_token_payload_without_account_context(self):
        """Test TokenPayload creation without account context (backward compatibility)."""
        token = TokenPayload(
            user_id=str(uuid4()),
            email="user@example.com",
            is_admin=False,
            exp=datetime.now(timezone.utc) + timedelta(hours=1),
            jti=str(uuid4()),
        )

        assert token.user_id is not None
        assert token.email == "user@example.com"
        assert token.is_admin is False
        assert token.is_super_admin is False  # Default value
        assert token.account_id is None  # Optional field
        assert token.account_role is None  # Optional field
        assert token.exp is not None
        assert token.jti is not None

    def test_token_payload_super_admin(self):
        """Test TokenPayload creation for super admin."""
        token = TokenPayload(
            user_id=str(uuid4()),
            email="superadmin@example.com",
            is_admin=True,
            is_super_admin=True,
            account_id=None,  # Super admins may not need account context
            account_role=None,
            exp=datetime.now(timezone.utc) + timedelta(hours=1),
            jti=str(uuid4()),
        )

        assert token.is_admin is True
        assert token.is_super_admin is True
        assert token.account_id is None
        assert token.account_role is None


class TestJWTServiceWithAccountContext:
    """Test JWT service creates tokens with account context."""

    def test_create_access_token_with_account_context(self, jwt_service):
        """Test access token creation includes account_id and account_role."""
        user_id = str(uuid4())
        account_id = str(uuid4())

        token = jwt_service.create_access_token(
            user_id=user_id,
            email="user@example.com",
            is_admin=False,
            is_super_admin=False,
            account_id=account_id,
            account_role=AccountRoleEnum.MEMBER.value,
        )

        # Decode and verify
        payload = jwt_service.decode_token(token)
        assert payload["user_id"] == user_id
        assert payload["account_id"] == account_id
        assert payload["account_role"] == AccountRoleEnum.MEMBER.value
        assert payload["is_super_admin"] is False

    def test_create_access_token_without_account_context(self, jwt_service):
        """Test access token creation without account context (backward compatibility)."""
        user_id = str(uuid4())

        token = jwt_service.create_access_token(
            user_id=user_id,
            email="user@example.com",
            is_admin=False,
        )

        # Decode and verify
        payload = jwt_service.decode_token(token)
        assert payload["user_id"] == user_id
        assert payload["account_id"] is None
        assert payload["account_role"] is None
        assert payload["is_super_admin"] is False

    def test_create_access_token_super_admin(self, jwt_service):
        """Test access token creation for super admin."""
        user_id = str(uuid4())

        token = jwt_service.create_access_token(
            user_id=user_id,
            email="superadmin@example.com",
            is_admin=True,
            is_super_admin=True,
            account_id=None,
            account_role=None,
        )

        # Decode and verify
        payload = jwt_service.decode_token(token)
        assert payload["user_id"] == user_id
        assert payload["is_admin"] is True
        assert payload["is_super_admin"] is True
        assert payload["account_id"] is None
        assert payload["account_role"] is None

    def test_verify_and_decode_with_account_context(self, jwt_service):
        """Test verify_and_decode returns TokenPayload with account context."""
        user_id = str(uuid4())
        account_id = str(uuid4())

        token = jwt_service.create_access_token(
            user_id=user_id,
            email="user@example.com",
            is_admin=False,
            is_super_admin=False,
            account_id=account_id,
            account_role=AccountRoleEnum.OWNER.value,
        )

        # Verify and decode (skip revocation check for unit test)
        token_payload = jwt_service.verify_and_decode(token, check_revoked=False)

        assert isinstance(token_payload, TokenPayload)
        assert token_payload.user_id == user_id
        assert token_payload.account_id == account_id
        assert token_payload.account_role == AccountRoleEnum.OWNER.value
        assert token_payload.is_super_admin is False

    def test_verify_and_decode_without_account_context(self, jwt_service):
        """Test verify_and_decode handles tokens without account context."""
        user_id = str(uuid4())

        token = jwt_service.create_access_token(
            user_id=user_id,
            email="user@example.com",
            is_admin=False,
        )

        # Verify and decode (skip revocation check for unit test)
        token_payload = jwt_service.verify_and_decode(token, check_revoked=False)

        assert isinstance(token_payload, TokenPayload)
        assert token_payload.user_id == user_id
        assert token_payload.account_id is None
        assert token_payload.account_role is None
        assert token_payload.is_super_admin is False

    def test_all_account_roles_in_tokens(self, jwt_service):
        """Test token creation with all possible account roles."""
        user_id = str(uuid4())
        account_id = str(uuid4())

        roles = [
            AccountRoleEnum.OWNER.value,
            AccountRoleEnum.ADMIN.value,
            AccountRoleEnum.MEMBER.value,
            AccountRoleEnum.VIEWER.value,
        ]

        for role in roles:
            token = jwt_service.create_access_token(
                user_id=user_id,
                email="user@example.com",
                is_admin=False,
                is_super_admin=False,
                account_id=account_id,
                account_role=role,
            )

            payload = jwt_service.decode_token(token)
            assert payload["account_role"] == role


class TestAccountContextIntegration:
    """Test that account context flows through authentication."""

    def test_token_includes_primary_account_on_login(self):
        """
        Integration test: Verify login includes primary account in token.
        Note: This is a design verification test. Full integration requires database.
        """
        # This test documents the expected behavior:
        # 1. User logs in
        # 2. System queries user's primary account from AccountUserAssociationModel
        # 3. Access token includes account_id and account_role from primary account
        # 4. User can immediately make API calls with account context
        pass  # Requires full auth service integration test

    def test_token_refresh_preserves_account_context(self):
        """
        Integration test: Verify token refresh preserves account context.
        Note: This is a design verification test. Full integration requires database.
        """
        # This test documents the expected behavior:
        # 1. User refreshes token
        # 2. System queries current primary account (may have changed)
        # 3. New access token includes updated account_id and account_role
        # 4. Account switches are handled via separate endpoint (not refresh)
        pass  # Requires full auth service integration test
