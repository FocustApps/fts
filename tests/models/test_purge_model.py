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
from datetime import timedelta, datetime, UTC
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from common.service_connections.db_service.database.engine import (
    get_database_session as session,
)
from common.service_connections.db_service.models.purge_model import (
    insert_purge_schedule,
    query_purge_schedule_by_id,
    query_purge_schedule_by_table,
    query_all_purge_schedules,
    query_tables_due_for_purge,
    update_purge_schedule,
    update_last_purged_at,
    get_purge_schedule_summary,
    drop_purge_schedule,
    PurgeModel,
)


class TestPurgeScheduleCRUD:
    """Test CRUD operations for purge schedules."""

    def test_insert_purge_schedule(self, purge_schedule_factory, engine: Engine):
        """Test creating a new purge schedule."""
        # Act - Create schedule for audit_logs table
        schedule_id = purge_schedule_factory(
            table_name="audit_logs",
            purge_interval_days=90,
        )

        # Assert
        with session(engine) as db_session:
            schedule = query_purge_schedule_by_id(schedule_id, db_session, engine)

        assert schedule.table_name == "audit_logs"
        assert schedule.purge_interval_days == 90

    def test_query_purge_schedule_by_table(
        self, purge_schedule_factory, engine: Engine
    ):
        """Test querying purge schedule for specific table."""
        # Arrange
        schedule_id = purge_schedule_factory(
            table_name="test_executions", purge_interval_days=30
        )

        # Act
        with session(engine) as db_session:
            schedule = query_purge_schedule_by_table(
                table_name="test_executions",
                db_session=db_session,
                engine=engine,
            )

        # Assert
        assert schedule is not None
        assert schedule.purge_id == schedule_id
        assert schedule.purge_interval_days == 30

    def test_query_all_purge_schedules(
        self, purge_schedule_factory, engine: Engine
    ):
        """Test querying all purge schedules (system-wide, no multi-tenancy)."""
        # Arrange - Create 3 schedules
        sched1 = purge_schedule_factory(table_name="table1", purge_interval_days=60)

        sched2 = purge_schedule_factory(table_name="table2", purge_interval_days=90)

        sched3 = purge_schedule_factory(table_name="table3", purge_interval_days=30)

        # Act
        with session(engine) as db_session:
            all_schedules = query_all_purge_schedules(
                db_session=db_session, engine=engine
            )

        # Assert - All schedules returned (system-wide query)
        schedule_ids = {s.purge_id for s in all_schedules}
        assert sched1 in schedule_ids
        assert sched2 in schedule_ids
        assert sched3 in schedule_ids

    def test_update_purge_schedule(
        self, purge_schedule_factory, engine: Engine
    ):
        """Test updating retention days for a schedule."""
        # Arrange
        schedule_id = purge_schedule_factory(table_name="logs", purge_interval_days=60)

        # Act - Update retention policy
        updates = PurgeModel(table_name="logs", purge_interval_days=120)
        result = update_purge_schedule(
            purge_id=schedule_id,
            updates=updates,
            engine=engine,
        )

        # Assert
        assert result is True

        with session(engine) as db_session:
            schedule = query_purge_schedule_by_id(schedule_id, db_session, engine)

        assert schedule.purge_interval_days == 120

    def test_deactivate_purge_schedule(
        self, purge_schedule_factory, engine: Engine
    ):
        """Test deleting a purge schedule."""
        # Arrange
        schedule_id = purge_schedule_factory(table_name="temp_data")

        # Act
        result = drop_purge_schedule(purge_id=schedule_id, engine=engine)

        # Assert
        assert result is True

        # Verify schedule was deleted
        with session(engine) as db_session:
            schedule = query_purge_schedule_by_id(schedule_id, db_session, engine)

        assert schedule is None


class TestPurgeDueCalculations:
    """Test calculations for tables due for purge."""

    def test_query_tables_due_for_purge(
        self, purge_schedule_factory, engine: Engine
    ):
        """Test identifying tables that need purging based on last_purged_at."""
        # Arrange - Create schedules using factory
        overdue_schedule = purge_schedule_factory(
            table_name="overdue_table",
            purge_interval_days=30,
        )

        current_schedule = purge_schedule_factory(
            table_name="current_table",
            purge_interval_days=30,
        )

        # Factory creates schedules with last_purged_at = now, so manually update to test logic
        # Overdue: last purged 40 days ago (30 day interval -> DUE)
        from datetime import datetime, timezone
        from common.service_connections.db_service.database.tables.purge_table import (
            PurgeTable,
        )

        with session(engine) as db_session:
            overdue = db_session.get(PurgeTable, overdue_schedule)
            overdue.last_purged_at = datetime.now(timezone.utc) - timedelta(days=40)
            db_session.commit()

        # Act
        with session(engine) as db_session:
            due_tables = query_tables_due_for_purge(db_session=db_session, engine=engine)

        # Assert
        due_table_names = {schedule.table_name for schedule in due_tables}

        assert "overdue_table" in due_table_names  # Overdue
        assert "current_table" not in due_table_names  # Not due yet (just purged)

    def test_update_last_purged_at_after_purge(
        self, purge_schedule_factory, engine: Engine
    ):
        """Test updating last_purged_at timestamp after successful purge."""
        # Arrange
        from datetime import datetime

        schedule_id = purge_schedule_factory(
            table_name="audit_logs", purge_interval_days=90
        )

        # Act - Simulate purge operation completing
        # Note: PostgreSQL returns timezone-naive datetimes
        before_purge = datetime.now(UTC)

        result = update_last_purged_at(
            purge_id=schedule_id, purged_at=None, engine=engine
        )

        after_purge = datetime.now(UTC)

        # Assert
        assert result is True

        with session(engine) as db_session:
            schedule = query_purge_schedule_by_id(schedule_id, db_session, engine)

        assert schedule.last_purged_at is not None
        # Compare as timezone-naive (PostgreSQL returns naive datetimes)
        assert before_purge <= schedule.last_purged_at <= after_purge


class TestPurgeScheduleSummary:
    """Test purge schedule summary with next_purge_date calculations."""

    def test_get_purge_schedule_summary(
        self, purge_schedule_factory, engine: Engine
    ):
        """Test getting summary with calculated next purge dates."""
        # Arrange - Create schedules
        from datetime import datetime, timezone
        from common.service_connections.db_service.database.tables.purge_table import (
            PurgeTable,
        )

        schedule1 = purge_schedule_factory(
            table_name="logs",
            purge_interval_days=30,
        )

        schedule2 = purge_schedule_factory(
            table_name="temp_data",
            purge_interval_days=7,
        )

        # Update schedule1 to be purged 15 days ago
        with session(engine) as db_session:
            sched1 = db_session.get(PurgeTable, schedule1)
            sched1.last_purged_at = datetime.now(timezone.utc) - timedelta(days=15)
            db_session.commit()

        # Act
        with session(engine) as db_session:
            summary = get_purge_schedule_summary(db_session=db_session, engine=engine)

        # Assert
        assert len(summary) >= 2

        # Find our schedules in summary
        logs_summary = next((s for s in summary if s["table_name"] == "logs"), None)
        temp_summary = next((s for s in summary if s["table_name"] == "temp_data"), None)

        assert logs_summary is not None
        assert temp_summary is not None

        # Logs purged 15 days ago, retention 30 days -> next purge ~15 days from now
        assert logs_summary["next_purge_date"] is not None
        assert not logs_summary["is_due_for_purge"]  # Not due yet

    def test_summary_includes_metadata(
        self, purge_schedule_factory, engine: Engine
    ):
        """Test that summary includes all relevant metadata."""
        # Arrange
        schedule_id = purge_schedule_factory(
            table_name="test_table", purge_interval_days=60
        )

        # Act
        with session(engine) as db_session:
            summary = get_purge_schedule_summary(db_session=db_session, engine=engine)

        # Assert
        test_summary = next((s for s in summary if s["table_name"] == "test_table"), None)
        assert test_summary is not None

        # Should include key fields
        assert "table_name" in test_summary
        assert "purge_interval_days" in test_summary
        assert "last_purged_at" in test_summary
        assert "next_purge_date" in test_summary
        assert "is_due_for_purge" in test_summary


class TestRetentionPolicyEdgeCases:
    """Test edge cases in retention policy logic."""

    def test_zero_retention_days_not_allowed(self, engine: Engine):
        """Test that retention_days must be positive."""
        # Act & Assert - Should raise validation error
        with pytest.raises(Exception):  # Pydantic validation
            model = PurgeModel(
                table_name="invalid",
                purge_interval_days=0,  # Invalid
            )
            insert_purge_schedule(
                model=model,
                engine=engine,
            )

    def test_negative_retention_days_not_allowed(self, engine: Engine):
        """Test that negative retention days are rejected."""
        # Act & Assert
        with pytest.raises(Exception):
            model = PurgeModel(
                table_name="invalid",
                purge_interval_days=-30,  # Invalid
            )
            insert_purge_schedule(
                model=model,
                engine=engine,
            )

    def test_very_long_retention_period(
        self, purge_schedule_factory, engine: Engine
    ):
        """Test handling of very long retention periods (e.g., 10 years)."""
        # Act - 10 year retention
        schedule_id = purge_schedule_factory(
            table_name="long_term_storage",
            purge_interval_days=3650,  # ~10 years
        )

        # Assert
        with session(engine) as db_session:
            schedule = query_purge_schedule_by_id(schedule_id, db_session, engine)

        assert schedule.purge_interval_days == 3650
