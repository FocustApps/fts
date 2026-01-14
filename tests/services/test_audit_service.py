"""
Tests for audit logging service.

Tests verify:
- Account lifecycle audit logging (create, update, delete)
- User-account association audit logging (add, remove, role change)
- Account switching and impersonation audit logging
- Super admin action audit logging
- Sensitive data flagging
"""

import pytest
from uuid import uuid4

from app.services.audit_service import (
    AuditAction,
    log_account_created,
    log_account_updated,
    log_account_deleted,
    log_user_added_to_account,
    log_user_removed_from_account,
    log_user_role_changed,
    log_primary_account_changed,
    log_bulk_user_invite,
    log_account_switched,
    log_user_impersonation_started,
    log_user_impersonation_ended,
    log_super_admin_access,
)
from common.service_connections.db_service.models.audit_log_model import (
    query_audit_log_by_id,
    query_audit_logs_by_entity,
    query_audit_logs_by_account,
)
from common.service_connections.db_service.database.engine import (
    get_database_session as session,
)
from common.service_connections.db_service.db_manager import DB_ENGINE


@pytest.fixture
def engine():
    """Database engine fixture."""
    return DB_ENGINE


@pytest.fixture
def user_id(auth_user_factory):
    """Create a test user and return the ID."""
    return (
        auth_user_factory()
    )  # auth_user_factory is a fixture that returns a factory function


@pytest.fixture
def account_id(account_factory):
    """Create a test account and return the ID."""
    return account_factory()


@pytest.fixture
def association_id():
    """Generate association ID."""
    return str(uuid4())


class TestAccountLifecycleAudit:
    """Test audit logging for account lifecycle events."""

    def test_log_account_created(self, engine, account_id, user_id):
        """Test logging account creation."""
        audit_id = log_account_created(
            account_id=account_id,
            account_name="Test Account",
            owner_user_id=user_id,
            performed_by_user_id=user_id,
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
            engine=engine,
        )

        # Verify audit log created
        assert audit_id is not None

        # Query and verify details
        with session(engine) as db_session:
            audit = query_audit_log_by_id(audit_id, db_session, engine)

        assert audit is not None
        assert audit.entity_type == "account"
        assert audit.entity_id == account_id
        assert audit.action == AuditAction.ACCOUNT_CREATE
        assert audit.performed_by_user_id == user_id
        assert audit.account_id == account_id
        assert audit.details["account_name"] == "Test Account"
        assert audit.details["owner_user_id"] == user_id
        assert audit.is_sensitive is False

    def test_log_account_updated(self, engine, account_id, user_id):
        """Test logging account updates with change tracking."""
        changes = {
            "account_name": {"old": "Old Name", "new": "New Name"},
            "is_active": {"old": True, "new": False},
        }

        audit_id = log_account_updated(
            account_id=account_id,
            performed_by_user_id=user_id,
            changes=changes,
            ip_address="192.168.1.1",
            engine=engine,
        )

        # Verify audit log created
        with session(engine) as db_session:
            audit = query_audit_log_by_id(audit_id, db_session, engine)

        assert audit.action == AuditAction.ACCOUNT_UPDATE
        assert audit.details["changes"] == changes
        assert audit.is_sensitive is False

    def test_log_account_deleted(self, engine, account_id, user_id):
        """Test logging account deletion (sensitive)."""
        audit_id = log_account_deleted(
            account_id=account_id,
            account_name="Test Account",
            performed_by_user_id=user_id,
            reason="Account expired",
            ip_address="192.168.1.1",
            engine=engine,
        )

        # Verify audit log created
        with session(engine) as db_session:
            audit = query_audit_log_by_id(audit_id, db_session, engine)

        assert audit.action == AuditAction.ACCOUNT_DELETE
        assert audit.details["account_name"] == "Test Account"
        assert audit.details["reason"] == "Account expired"
        assert audit.is_sensitive is True  # Deletion is sensitive


class TestUserAccountAssociationAudit:
    """Test audit logging for user-account association events."""

    def test_log_user_added_to_account(self, engine, account_id, association_id, user_id):
        """Test logging user being added to account."""
        target_user_id = str(uuid4())

        audit_id = log_user_added_to_account(
            association_id=association_id,
            account_id=account_id,
            target_user_id=target_user_id,
            target_user_email="new.user@example.com",
            role="member",
            performed_by_user_id=user_id,
            is_primary=False,
            ip_address="192.168.1.1",
            engine=engine,
        )

        # Verify audit log
        with session(engine) as db_session:
            audit = query_audit_log_by_id(audit_id, db_session, engine)

        assert audit.entity_type == "account_user_association"
        assert audit.entity_id == association_id
        assert audit.action == AuditAction.USER_ADDED_TO_ACCOUNT
        assert audit.details["target_user_id"] == target_user_id
        assert audit.details["role"] == "member"
        assert audit.is_sensitive is False

    def test_log_user_removed_from_account(
        self, engine, account_id, association_id, user_id
    ):
        """Test logging user removal (sensitive)."""
        target_user_id = str(uuid4())

        audit_id = log_user_removed_from_account(
            association_id=association_id,
            account_id=account_id,
            target_user_id=target_user_id,
            target_user_email="removed.user@example.com",
            role="member",
            performed_by_user_id=user_id,
            reason="User left company",
            ip_address="192.168.1.1",
            engine=engine,
        )

        # Verify audit log
        with session(engine) as db_session:
            audit = query_audit_log_by_id(audit_id, db_session, engine)

        assert audit.action == AuditAction.USER_REMOVED_FROM_ACCOUNT
        assert audit.details["old_role"] == "member"
        assert audit.details["reason"] == "User left company"
        assert audit.is_sensitive is True  # Removal is sensitive

    def test_log_user_role_changed(self, engine, account_id, association_id, user_id):
        """Test logging role change with old/new values."""
        target_user_id = str(uuid4())

        audit_id = log_user_role_changed(
            association_id=association_id,
            account_id=account_id,
            target_user_id=target_user_id,
            target_user_email="user@example.com",
            old_role="member",
            new_role="admin",
            performed_by_user_id=user_id,
            reason="Promoted to admin",
            ip_address="192.168.1.1",
            engine=engine,
        )

        # Verify audit log
        with session(engine) as db_session:
            audit = query_audit_log_by_id(audit_id, db_session, engine)

        assert audit.action == AuditAction.USER_ROLE_CHANGED
        assert audit.details["old_value"] == "member"
        assert audit.details["new_value"] == "admin"
        assert audit.details["field_name"] == "role"
        assert audit.details["change_reason"] == "Promoted to admin"
        assert audit.is_sensitive is False

    def test_log_primary_account_changed(self, engine, account_id, user_id):
        """Test logging primary account change."""
        old_account_id = str(uuid4())
        new_account_id = account_id

        audit_id = log_primary_account_changed(
            account_id=new_account_id,
            target_user_id=user_id,
            old_primary_account_id=old_account_id,
            new_primary_account_id=new_account_id,
            performed_by_user_id=user_id,
            ip_address="192.168.1.1",
            engine=engine,
        )

        # Verify audit log
        with session(engine) as db_session:
            audit = query_audit_log_by_id(audit_id, db_session, engine)

        assert audit.action == AuditAction.PRIMARY_ACCOUNT_CHANGED
        assert audit.details["old_value"] == old_account_id
        assert audit.details["new_value"] == new_account_id
        assert audit.details["field_name"] == "primary_account_id"

    def test_log_bulk_user_invite(self, engine, account_id, user_id):
        """Test logging bulk user invitation operation."""
        audit_id = log_bulk_user_invite(
            account_id=account_id,
            performed_by_user_id=user_id,
            invited_count=10,
            successful_count=8,
            failed_count=2,
            role="member",
            ip_address="192.168.1.1",
            engine=engine,
        )

        # Verify audit log
        with session(engine) as db_session:
            audit = query_audit_log_by_id(audit_id, db_session, engine)

        assert audit.action == AuditAction.BULK_USER_INVITE
        assert audit.details["invited_count"] == 10
        assert audit.details["successful_count"] == 8
        assert audit.details["failed_count"] == 2
        assert audit.details["role"] == "member"


class TestAccountSwitchingAndImpersonationAudit:
    """Test audit logging for account switching and impersonation."""

    def test_log_account_switched(self, engine, account_id, user_id):
        """Test logging user switching active account."""
        old_account_id = str(uuid4())

        audit_id = log_account_switched(
            user_id=user_id,
            old_account_id=old_account_id,
            new_account_id=account_id,
            new_account_name="New Account",
            new_role="admin",
            ip_address="192.168.1.1",
            engine=engine,
        )

        # Verify audit log
        with session(engine) as db_session:
            audit = query_audit_log_by_id(audit_id, db_session, engine)

        assert audit.entity_type == "auth_user"
        assert audit.entity_id == user_id
        assert audit.action == AuditAction.ACCOUNT_SWITCHED
        assert audit.details["old_account_id"] == old_account_id
        assert audit.details["new_account_id"] == account_id
        assert audit.details["new_role"] == "admin"
        assert audit.is_sensitive is False

    def test_log_user_impersonation_started(self, engine, account_id, auth_user_factory):
        """Test logging impersonation start (sensitive)."""
        super_admin_id = auth_user_factory(is_super_admin=True)
        target_user_id = auth_user_factory()

        audit_id = log_user_impersonation_started(
            super_admin_user_id=super_admin_id,
            super_admin_email="admin@example.com",
            target_user_id=target_user_id,
            target_user_email="user@example.com",
            target_account_id=account_id,
            reason="Customer support investigation",
            ip_address="192.168.1.1",
            engine=engine,
        )

        # Verify audit log
        with session(engine) as db_session:
            audit = query_audit_log_by_id(audit_id, db_session, engine)

        assert audit.entity_type == "auth_user"
        assert audit.entity_id == target_user_id
        assert audit.action == AuditAction.USER_IMPERSONATED
        assert audit.performed_by_user_id == super_admin_id
        assert audit.details["target_user_id"] == target_user_id
        assert audit.details["reason"] == "Customer support investigation"
        assert audit.is_sensitive is True  # Impersonation is sensitive

    def test_log_user_impersonation_ended(self, engine, auth_user_factory):
        """Test logging impersonation end (sensitive)."""
        super_admin_id = auth_user_factory(is_super_admin=True)
        target_user_id = auth_user_factory()

        audit_id = log_user_impersonation_ended(
            super_admin_user_id=super_admin_id,
            target_user_id=target_user_id,
            duration_seconds=300,
            ip_address="192.168.1.1",
            engine=engine,
        )

        # Verify audit log
        with session(engine) as db_session:
            audit = query_audit_log_by_id(audit_id, db_session, engine)

        assert audit.action == AuditAction.IMPERSONATION_ENDED
        assert audit.details["duration_seconds"] == 300
        assert audit.is_sensitive is True


class TestSuperAdminAudit:
    """Test audit logging for super admin actions."""

    def test_log_super_admin_access(self, engine, account_id, auth_user_factory):
        """Test logging super admin accessing resources (sensitive)."""
        super_admin_id = auth_user_factory(is_super_admin=True)
        resource_id = str(uuid4())

        audit_id = log_super_admin_access(
            super_admin_user_id=super_admin_id,
            accessed_resource_type="account",
            accessed_resource_id=resource_id,
            accessed_account_id=account_id,
            action="read",
            reason="Security audit",
            ip_address="192.168.1.1",
            engine=engine,
        )

        # Verify audit log
        with session(engine) as db_session:
            audit = query_audit_log_by_id(audit_id, db_session, engine)

        assert audit.entity_type == "account"
        assert audit.entity_id == resource_id
        assert audit.action == AuditAction.SUPER_ADMIN_ACCESS
        assert audit.performed_by_user_id == super_admin_id
        assert audit.details["action_performed"] == "read"
        assert audit.details["reason"] == "Security audit"
        assert audit.is_sensitive is True  # Super admin actions are sensitive


class TestAuditLogQuerying:
    """Test querying audit logs by various criteria."""

    def test_query_audit_logs_by_entity(self, engine, account_id, user_id):
        """Test querying all logs for a specific entity."""
        # Create multiple audit logs for same account
        log_account_created(
            account_id=account_id,
            account_name="Test Account",
            owner_user_id=user_id,
            performed_by_user_id=user_id,
            engine=engine,
        )

        log_account_updated(
            account_id=account_id,
            performed_by_user_id=user_id,
            changes={"account_name": {"old": "Old", "new": "New"}},
            engine=engine,
        )

        # Query all logs for this account entity
        with session(engine) as db_session:
            logs = query_audit_logs_by_entity(
                entity_type="account",
                entity_id=account_id,
                session=db_session,
                engine=engine,
            )

        # Should have at least 2 logs (create + update)
        assert len(logs) >= 2
        assert all(log.entity_type == "account" for log in logs)
        assert all(log.entity_id == account_id for log in logs)

    def test_query_audit_logs_by_account(self, engine, account_id, user_id):
        """Test querying all logs for an account context."""
        # Create multiple logs in account context
        log_account_updated(
            account_id=account_id,
            performed_by_user_id=user_id,
            changes={"test": "value"},
            engine=engine,
        )

        log_user_role_changed(
            association_id=str(uuid4()),
            account_id=account_id,
            target_user_id=str(uuid4()),
            target_user_email="user@example.com",
            old_role="member",
            new_role="admin",
            performed_by_user_id=user_id,
            engine=engine,
        )

        # Query all logs in this account context
        with session(engine) as db_session:
            logs = query_audit_logs_by_account(
                account_id=account_id, session=db_session, engine=engine
            )

        # Should have at least 2 logs
        assert len(logs) >= 2
        assert all(log.account_id == account_id for log in logs)

    def test_sensitive_data_flagging(self, engine, account_id, user_id):
        """Test that sensitive actions are correctly flagged."""
        # Create sensitive logs
        deletion_audit_id = log_account_deleted(
            account_id=account_id,
            account_name="Test",
            performed_by_user_id=user_id,
            engine=engine,
        )

        impersonation_audit_id = log_user_impersonation_started(
            super_admin_user_id=user_id,
            super_admin_email="admin@example.com",
            target_user_id=str(uuid4()),
            target_user_email="user@example.com",
            target_account_id=account_id,
            reason="Support",
            engine=engine,
        )

        # Verify both are marked sensitive
        with session(engine) as db_session:
            deletion_log = query_audit_log_by_id(deletion_audit_id, db_session, engine)
            impersonation_log = query_audit_log_by_id(
                impersonation_audit_id, db_session, engine
            )

        assert deletion_log.is_sensitive is True
        assert impersonation_log.is_sensitive is True


class TestAuditActionConstants:
    """Test audit action constant naming consistency."""

    def test_action_constants_defined(self):
        """Verify all expected action constants are defined."""
        assert hasattr(AuditAction, "ACCOUNT_CREATE")
        assert hasattr(AuditAction, "ACCOUNT_UPDATE")
        assert hasattr(AuditAction, "ACCOUNT_DELETE")
        assert hasattr(AuditAction, "USER_ADDED_TO_ACCOUNT")
        assert hasattr(AuditAction, "USER_REMOVED_FROM_ACCOUNT")
        assert hasattr(AuditAction, "USER_ROLE_CHANGED")
        assert hasattr(AuditAction, "PRIMARY_ACCOUNT_CHANGED")
        assert hasattr(AuditAction, "BULK_USER_INVITE")
        assert hasattr(AuditAction, "ACCOUNT_SWITCHED")
        assert hasattr(AuditAction, "USER_IMPERSONATED")
        assert hasattr(AuditAction, "IMPERSONATION_ENDED")
        assert hasattr(AuditAction, "SUPER_ADMIN_ACCESS")

    def test_action_constant_values(self):
        """Verify action constant values use consistent naming."""
        # Verify snake_case naming convention
        assert AuditAction.ACCOUNT_CREATE == "account_create"
        assert AuditAction.USER_ROLE_CHANGED == "user_role_changed"
        assert AuditAction.USER_IMPERSONATED == "user_impersonated"
