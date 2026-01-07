"""
Tests for AuditLog model with insert-only operations and JSONB change tracking.

Tests cover:
- Insert-only audit log operations (no update/delete)
- AuditChangeModel JSONB validation
- Query patterns (by entity, account, user, date range)
- Bulk insert operations
- Sensitivity levels
"""

from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from common.service_connections.db_service.models.audit_log_model import (
    AuditLogModel,
    AuditChangeModel,
    insert_audit_log,
    query_audit_logs_by_entity,
    query_audit_logs_by_account,
    query_audit_logs_by_user,
    bulk_insert_audit_logs,
)


class TestAuditLogInsertOnly:
    """Test that audit logs are insert-only (no updates or deletes)."""

    def test_insert_audit_log_basic(
        self, audit_log_factory, account_factory, engine: Engine, session: Session
    ):
        """Test basic audit log insertion."""
        # Arrange
        account_id = account_factory()

        # Act
        log_id = audit_log_factory(
            account_id=account_id,
            entity_type="test_case",
            entity_id="test-123",
            action="created",
            performed_by_user_id="user-456",
        )

        # Assert
        with session(engine) as db_session:
            log = db_session.query(AuditLogModel).filter_by(audit_log_id=log_id).first()

        assert log is not None
        assert log.entity_type == "test_case"
        assert log.action == "created"
        assert log.performed_by_user_id == "user-456"

    def test_audit_log_has_no_update_function(self):
        """Test that no update function exists for audit logs."""
        # Audit logs should be immutable - verify no update function exists
        from common.service_connections.db_service.models import audit_log_model

        # Should not have update_audit_log function
        assert not hasattr(audit_log_model, "update_audit_log")
        assert not hasattr(audit_log_model, "delete_audit_log")

    def test_insert_audit_log_with_changes(self, account_factory, engine: Engine):
        """Test audit log with before/after changes."""
        # Arrange
        account_id = account_factory()

        changes = AuditChangeModel(
            field_name="status", old_value="draft", new_value="published"
        )

        # Act
        log_id = insert_audit_log(
            account_id=account_id,
            entity_type="suite",
            entity_id="suite-789",
            action="updated",
            performed_by_user_id="editor-user",
            changes=changes,
            engine=engine,
        )

        # Assert
        with session(engine) as db_session:
            log = db_session.query(AuditLogModel).filter_by(audit_log_id=log_id).first()

        assert log.changes is not None
        assert log.changes.field_name == "status"
        assert log.changes.old_value == "draft"
        assert log.changes.new_value == "published"


class TestAuditChangeModelJSONB:
    """Test AuditChangeModel JSONB validation and serialization."""

    def test_audit_change_model_validation(self):
        """Test AuditChangeModel validates required fields."""
        # Act - Create valid change model
        change = AuditChangeModel(
            field_name="priority", old_value="low", new_value="high"
        )

        # Assert
        assert change.field_name == "priority"
        assert change.old_value == "low"
        assert change.new_value == "high"

    def test_audit_change_with_null_old_value(self):
        """Test change model with None old_value (field creation)."""
        # Act - Field didn't exist before (creation)
        change = AuditChangeModel(
            field_name="description", old_value=None, new_value="New description text"
        )

        # Assert
        assert change.old_value is None
        assert change.new_value == "New description text"

    def test_audit_change_with_null_new_value(self):
        """Test change model with None new_value (field deletion)."""
        # Act - Field was cleared
        change = AuditChangeModel(
            field_name="notes", old_value="Old notes", new_value=None
        )

        # Assert
        assert change.old_value == "Old notes"
        assert change.new_value is None

    def test_audit_log_with_multiple_changes(self, account_factory, engine: Engine):
        """Test audit log can store complex change objects."""
        # Arrange
        account_id = account_factory()

        # Multiple field changes could be represented as nested structure
        complex_changes = AuditChangeModel(
            field_name="metadata",
            old_value={"version": 1, "tags": ["old"]},
            new_value={"version": 2, "tags": ["new", "updated"]},
        )

        # Act
        log_id = insert_audit_log(
            account_id=account_id,
            entity_type="plan",
            entity_id="plan-complex",
            action="updated",
            performed_by_user_id="admin",
            changes=complex_changes,
            engine=engine,
        )

        # Assert
        with session(engine) as db_session:
            log = db_session.query(AuditLogModel).filter_by(audit_log_id=log_id).first()

        assert isinstance(log.changes.old_value, dict)
        assert isinstance(log.changes.new_value, dict)
        assert log.changes.new_value["version"] == 2


class TestAuditLogQueries:
    """Test various query patterns for audit logs."""

    def test_query_logs_by_entity(
        self, audit_log_factory, account_factory, engine: Engine
    ):
        """Test querying all logs for a specific entity."""
        # Arrange
        account_id = account_factory()
        entity_id = "suite-audit-test"

        # Create multiple logs for same entity
        log1 = audit_log_factory(
            account_id=account_id,
            entity_type="suite",
            entity_id=entity_id,
            action="created",
        )

        log2 = audit_log_factory(
            account_id=account_id,
            entity_type="suite",
            entity_id=entity_id,
            action="updated",
        )

        log3 = audit_log_factory(
            account_id=account_id,
            entity_type="suite",
            entity_id=entity_id,
            action="published",
        )

        # Act
        with session(engine) as db_session:
            logs = query_audit_logs_by_entity(
                entity_type="suite",
                entity_id=entity_id,
                account_id=account_id,
                session=db_session,
                engine=engine,
            )

        # Assert - Should get chronological history
        assert len(logs) >= 3
        log_ids = {log.audit_log_id for log in logs}
        assert log1 in log_ids
        assert log2 in log_ids
        assert log3 in log_ids

    def test_query_logs_by_account(
        self, audit_log_factory, account_factory, engine: Engine
    ):
        """Test querying all logs for an account."""
        # Arrange
        account1 = account_factory()
        account2 = account_factory()

        log1 = audit_log_factory(account_id=account1, action="action1")
        log2 = audit_log_factory(account_id=account1, action="action2")
        log3 = audit_log_factory(account_id=account2, action="action3")

        # Act
        with session(engine) as db_session:
            account1_logs = query_audit_logs_by_account(
                account_id=account1, session=db_session, engine=engine
            )

        # Assert - Multi-tenant isolation
        account1_ids = {log.audit_log_id for log in account1_logs}
        assert log1 in account1_ids
        assert log2 in account1_ids
        assert log3 not in account1_ids

    def test_query_logs_by_user(self, audit_log_factory, account_factory, engine: Engine):
        """Test querying all actions by a specific user."""
        # Arrange
        account_id = account_factory()

        user1_log1 = audit_log_factory(
            account_id=account_id, performed_by_user_id="user-alpha", action="created"
        )

        user1_log2 = audit_log_factory(
            account_id=account_id, performed_by_user_id="user-alpha", action="updated"
        )

        user2_log = audit_log_factory(
            account_id=account_id, performed_by_user_id="user-beta", action="deleted"
        )

        # Act
        with session(engine) as db_session:
            user_alpha_logs = query_audit_logs_by_user(
                performed_by_user_id="user-alpha",
                account_id=account_id,
                session=db_session,
                engine=engine,
            )

        # Assert
        user_alpha_ids = {log.audit_log_id for log in user_alpha_logs}
        assert user1_log1 in user_alpha_ids
        assert user1_log2 in user_alpha_ids
        assert user2_log not in user_alpha_ids

    def test_query_logs_by_sensitivity(self, account_factory, engine: Engine):
        """Test querying logs by sensitivity level."""
        # Arrange
        account_id = account_factory()

        # Create logs with different sensitivity
        normal_log = insert_audit_log(
            account_id=account_id,
            entity_type="test_case",
            entity_id="test-1",
            action="viewed",
            performed_by_user_id="user-1",
            is_sensitive=False,
            engine=engine,
        )

        sensitive_log = insert_audit_log(
            account_id=account_id,
            entity_type="test_case",
            entity_id="test-2",
            action="credentials_accessed",
            performed_by_user_id="admin",
            is_sensitive=True,
            engine=engine,
        )

        # Act - Query all logs and filter by sensitivity
        with session(engine) as db_session:
            all_logs = query_audit_logs_by_account(
                account_id=account_id,
                session=db_session,
                engine=engine,
            )

        # Assert
        sensitive_logs = [log for log in all_logs if log.is_sensitive]
        non_sensitive_logs = [log for log in all_logs if not log.is_sensitive]

        assert len(sensitive_logs) >= 1
        assert len(non_sensitive_logs) >= 1
        assert sensitive_log in [log.audit_log_id for log in sensitive_logs]
        assert normal_log in [log.audit_log_id for log in non_sensitive_logs]


class TestBulkAuditOperations:
    """Test bulk insert operations for audit logs."""

    def test_bulk_insert_audit_logs(self, account_factory, engine: Engine):
        """Test inserting multiple audit logs in a single transaction."""
        # Arrange
        account_id = account_factory()

        log_data = [
            {
                "account_id": account_id,
                "entity_type": "test_case",
                "entity_id": f"test-{i}",
                "action": "bulk_created",
                "performed_by_user_id": "bulk-user",
            }
            for i in range(5)
        ]

        # Act
        log_ids = bulk_insert_audit_logs(audit_logs=log_data, engine=engine)

        # Assert
        assert len(log_ids) == 5

        with session(engine) as db_session:
            logs = query_audit_logs_by_account(
                account_id=account_id, session=db_session, engine=engine
            )

        bulk_logs = [log for log in logs if log.action == "bulk_created"]
        assert len(bulk_logs) >= 5
