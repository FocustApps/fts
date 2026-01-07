"""
Tests for Purge Schedule model with retention policies.

Tests cover:
- Retention schedule CRUD operations
- Query tables due for purge based on timedelta
- Update last_purged_at after successful purge
- Get purge schedule summary with next_purge_date calculations
- Admin-only operations
"""

import pytest
from datetime import datetime, timedelta
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from common.service_connections.db_service.models.purge_model import (
    insert_purge_schedule,
    query_purge_schedule_by_id,
    query_purge_schedule_by_table,
    query_all_purge_schedules,
    query_tables_due_for_purge,
    update_purge_schedule,
    update_last_purged_at,
    get_purge_schedule_summary,
)


class TestPurgeScheduleCRUD:
    """Test CRUD operations for purge schedules."""

    def test_insert_purge_schedule(
        self, purge_schedule_factory, account_factory, engine: Engine, session: Session
    ):
        """Test creating a new purge schedule."""
        # Arrange
        account_id = account_factory()

        # Act - Create schedule for audit_logs table
        schedule_id = purge_schedule_factory(
            account_id=account_id,
            table_name="audit_logs",
            retention_days=90,
            created_by_user_id="admin-user",
        )

        # Assert
        with session(engine) as db_session:
            schedule = query_purge_schedule_by_id(schedule_id, db_session, engine)

        assert schedule.table_name == "audit_logs"
        assert schedule.retention_days == 90
        assert schedule.is_active is True

    def test_query_purge_schedule_by_table(
        self, purge_schedule_factory, account_factory, engine: Engine, session: Session
    ):
        """Test querying purge schedule for specific table."""
        # Arrange
        account_id = account_factory()

        schedule_id = purge_schedule_factory(
            account_id=account_id, table_name="test_executions", retention_days=30
        )

        # Act
        with session(engine) as db_session:
            schedule = query_purge_schedule_by_table(
                table_name="test_executions",
                account_id=account_id,
                session=db_session,
                engine=engine,
            )

        # Assert
        assert schedule is not None
        assert schedule.purge_schedule_id == schedule_id
        assert schedule.retention_days == 30

    def test_query_all_purge_schedules(
        self, purge_schedule_factory, account_factory, engine: Engine, session: Session
    ):
        """Test querying all purge schedules for an account."""
        # Arrange
        account1 = account_factory()
        account2 = account_factory()

        sched1 = purge_schedule_factory(
            account_id=account1, table_name="table1", retention_days=60
        )

        sched2 = purge_schedule_factory(
            account_id=account1, table_name="table2", retention_days=90
        )

        sched3 = purge_schedule_factory(
            account_id=account2, table_name="table3", retention_days=30
        )

        # Act
        with session(engine) as db_session:
            account1_schedules = query_all_purge_schedules(
                account_id=account1, session=db_session, engine=engine
            )

        # Assert - Multi-tenant isolation
        schedule_ids = {s.purge_schedule_id for s in account1_schedules}
        assert sched1 in schedule_ids
        assert sched2 in schedule_ids
        assert sched3 not in schedule_ids

    def test_update_purge_schedule(
        self, purge_schedule_factory, account_factory, engine: Engine, session: Session
    ):
        """Test updating retention days for a schedule."""
        # Arrange
        account_id = account_factory()
        schedule_id = purge_schedule_factory(
            account_id=account_id, table_name="logs", retention_days=60
        )

        # Act - Update retention policy
        result = update_purge_schedule(
            schedule_id=schedule_id,
            updated_by_user_id="admin",
            retention_days=120,  # Extend retention
            engine=engine,
        )

        # Assert
        assert result is True

        with session(engine) as db_session:
            schedule = query_purge_schedule_by_id(schedule_id, db_session, engine)

        assert schedule.retention_days == 120
        assert schedule.updated_by_user_id == "admin"

    def test_deactivate_purge_schedule(
        self, purge_schedule_factory, account_factory, engine: Engine, session: Session
    ):
        """Test disabling a purge schedule."""
        # Arrange
        account_id = account_factory()
        schedule_id = purge_schedule_factory(
            account_id=account_id, table_name="temp_data"
        )

        # Act
        result = deactivate_purge_schedule(
            schedule_id=schedule_id, deactivated_by_user_id="admin", engine=engine
        )

        # Assert
        assert result is True

        with session(engine) as db_session:
            schedule = query_purge_schedule_by_id(schedule_id, db_session, engine)

        assert schedule.is_active is False
        assert schedule.deactivated_by_user_id == "admin"
        assert schedule.deactivated_at is not None


class TestPurgeDueCalculations:
    """Test calculations for tables due for purge."""

    def test_query_tables_due_for_purge(
        self, purge_schedule_factory, account_factory, engine: Engine
    ):
        """Test identifying tables that need purging based on last_purged_at."""
        # Arrange
        account_id = account_factory()

        # Schedule that was purged 40 days ago (retention 30 days -> overdue)
        overdue_schedule = insert_purge_schedule(
            account_id=account_id,
            table_name="overdue_table",
            retention_days=30,
            created_by_user_id="admin",
            last_purged_at=datetime.utcnow() - timedelta(days=40),
            engine=engine,
        )

        # Schedule that was purged 10 days ago (retention 30 days -> not due)
        current_schedule = insert_purge_schedule(
            account_id=account_id,
            table_name="current_table",
            retention_days=30,
            created_by_user_id="admin",
            last_purged_at=datetime.utcnow() - timedelta(days=10),
            engine=engine,
        )

        # Schedule never purged (always due)
        never_purged = insert_purge_schedule(
            account_id=account_id,
            table_name="never_purged_table",
            retention_days=60,
            created_by_user_id="admin",
            last_purged_at=None,  # Never purged
            engine=engine,
        )

        # Act
        with session(engine) as db_session:
            due_tables = query_tables_due_for_purge(
                account_id=account_id, session=db_session, engine=engine
            )

        # Assert
        due_table_names = {schedule.table_name for schedule in due_tables}

        assert "overdue_table" in due_table_names  # Overdue
        assert "never_purged_table" in due_table_names  # Never purged
        assert "current_table" not in due_table_names  # Not due yet

    def test_update_last_purged_at_after_purge(
        self, purge_schedule_factory, account_factory, engine: Engine
    ):
        """Test updating last_purged_at timestamp after successful purge."""
        # Arrange
        account_id = account_factory()
        schedule_id = purge_schedule_factory(
            account_id=account_id, table_name="audit_logs", retention_days=90
        )

        # Act - Simulate purge operation completing
        before_purge = datetime.utcnow()

        result = update_last_purged_at(
            schedule_id=schedule_id, updated_by_user_id="purge-service", engine=engine
        )

        after_purge = datetime.utcnow()

        # Assert
        assert result is True

        with session(engine) as db_session:
            schedule = query_purge_schedule_by_id(schedule_id, db_session, engine)

        assert schedule.last_purged_at is not None
        assert before_purge <= schedule.last_purged_at <= after_purge
        assert schedule.updated_by_user_id == "purge-service"


class TestPurgeScheduleSummary:
    """Test purge schedule summary with next_purge_date calculations."""

    def test_get_purge_schedule_summary(
        self, purge_schedule_factory, account_factory, engine: Engine
    ):
        """Test getting summary with calculated next purge dates."""
        # Arrange
        account_id = account_factory()

        # Create schedules with different states
        schedule1 = insert_purge_schedule(
            account_id=account_id,
            table_name="logs",
            retention_days=30,
            created_by_user_id="admin",
            last_purged_at=datetime.utcnow() - timedelta(days=15),
            engine=engine,
        )

        schedule2 = insert_purge_schedule(
            account_id=account_id,
            table_name="temp_data",
            retention_days=7,
            created_by_user_id="admin",
            last_purged_at=None,  # Never purged
            engine=engine,
        )

        # Act
        summary = get_purge_schedule_summary(account_id=account_id, engine=engine)

        # Assert
        assert len(summary) >= 2

        # Find our schedules in summary
        logs_summary = next(s for s in summary if s["table_name"] == "logs")
        temp_summary = next(s for s in summary if s["table_name"] == "temp_data")

        # Logs purged 15 days ago, retention 30 days -> next purge ~15 days from now
        assert logs_summary["next_purge_date"] is not None
        assert logs_summary["days_until_purge"] > 0

        # Never purged -> should be due immediately
        assert temp_summary["next_purge_date"] is not None
        assert temp_summary["days_until_purge"] <= 0  # Overdue or due now

    def test_summary_includes_metadata(
        self, purge_schedule_factory, account_factory, engine: Engine
    ):
        """Test that summary includes all relevant metadata."""
        # Arrange
        account_id = account_factory()

        schedule_id = purge_schedule_factory(
            account_id=account_id, table_name="test_table", retention_days=60
        )

        # Act
        summary = get_purge_schedule_summary(account_id=account_id, engine=engine)

        # Assert
        test_summary = next(s for s in summary if s["table_name"] == "test_table")

        # Should include key fields
        assert "schedule_id" in test_summary
        assert "table_name" in test_summary
        assert "retention_days" in test_summary
        assert "last_purged_at" in test_summary
        assert "next_purge_date" in test_summary
        assert "days_until_purge" in test_summary
        assert "is_active" in test_summary


class TestRetentionPolicyEdgeCases:
    """Test edge cases in retention policy logic."""

    def test_zero_retention_days_not_allowed(self, account_factory, engine: Engine):
        """Test that retention_days must be positive."""
        # Arrange
        account_id = account_factory()

        # Act & Assert - Should raise validation error
        with pytest.raises(Exception):  # Pydantic validation or DB constraint
            insert_purge_schedule(
                account_id=account_id,
                table_name="invalid",
                retention_days=0,  # Invalid
                created_by_user_id="admin",
                engine=engine,
            )

    def test_negative_retention_days_not_allowed(self, account_factory, engine: Engine):
        """Test that negative retention days are rejected."""
        # Arrange
        account_id = account_factory()

        # Act & Assert
        with pytest.raises(Exception):
            insert_purge_schedule(
                account_id=account_id,
                table_name="invalid",
                retention_days=-30,  # Invalid
                created_by_user_id="admin",
                engine=engine,
            )

    def test_very_long_retention_period(
        self, purge_schedule_factory, account_factory, engine: Engine
    ):
        """Test handling of very long retention periods (e.g., 10 years)."""
        # Arrange
        account_id = account_factory()

        # Act - 10 year retention
        schedule_id = purge_schedule_factory(
            account_id=account_id,
            table_name="long_term_storage",
            retention_days=3650,  # ~10 years
        )

        # Assert
        with session(engine) as db_session:
            schedule = query_purge_schedule_by_id(schedule_id, db_session, engine)

        assert schedule.retention_days == 3650
