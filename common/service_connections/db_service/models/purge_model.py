"""
Purge model for data retention schedule management (admin-only operations).

This module provides:
1. PurgeModel: Retention policy configuration for automated data cleanup
2. Admin-only CRUD operations (no regular user access)
3. Query helpers for background purge jobs
4. Purge status tracking (last_purged_at updates after successful purges)
"""

from datetime import datetime, timedelta, timezone
from typing import List, Optional

from pydantic import BaseModel, field_validator
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from common.config import should_validate_write
from common.service_connections.db_service.database.engine import (
    get_database_session as session,
)

from common.service_connections.db_service.database.tables.purge_table import (
    PurgeTable,
)


class PurgeModel(BaseModel):
    """Pydantic model for purge schedule validation.

    Admin-only configuration for automated data retention and cleanup.
    """

    purge_id: Optional[str] = None
    table_name: str
    last_purged_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    purge_interval_days: int = 30

    @field_validator("table_name")
    def validate_table_name(cls, v: str) -> str:
        """Validate table_name length and format."""
        if not should_validate_write():
            return v

        if len(v) > 255:
            raise ValueError(f"table_name exceeds 255 characters: {len(v)}")

        if not v.strip():
            raise ValueError("table_name cannot be empty or whitespace")

        return v

    @field_validator("purge_interval_days")
    def validate_purge_interval(cls, v: int) -> int:
        """Validate purge_interval_days is reasonable (1-3650 days)."""
        if not should_validate_write():
            return v

        if v < 1:
            raise ValueError(f"purge_interval_days must be >= 1, got {v}")

        if v > 3650:  # ~10 years max
            raise ValueError(f"purge_interval_days exceeds maximum of 3650 days: {v}")

        return v


# ============================================================================
# Admin-Only CRUD Operations
# ============================================================================


def insert_purge_schedule(model: PurgeModel, engine: Engine) -> str:
    """Insert new purge schedule (admin only).

    Args:
        model: PurgeModel with schedule configuration
        engine: Database engine

    Returns:
        purge_id of inserted record

    Raises:
        ValueError: If validation fails or table_name already has schedule
        SQLAlchemyError: If database operation fails
    """
    purge_dict = model.model_dump(exclude_unset=True)

    with session() as db_session:
        # Check if schedule already exists for this table
        existing = (
            db_session.query(PurgeTable)
            .filter(PurgeTable.table_name == model.table_name)
            .first()
        )

        if existing:
            raise ValueError(
                f"Purge schedule already exists for table '{model.table_name}'. "
                f"Use update_purge_schedule() to modify."
            )

        new_purge = PurgeTable(**purge_dict)
        db_session.add(new_purge)
        db_session.commit()
        return new_purge.purge_id


def query_purge_schedule_by_id(
    purge_id: str, db_session: Session, engine: Engine
) -> Optional[PurgeModel]:
    """Query purge schedule by purge_id.

    Args:
        purge_id: Purge schedule ID to query
        session: Active database session
        engine: Database engine

    Returns:
        PurgeModel if found, None otherwise
    """
    purge = db_session.get(PurgeTable, purge_id)
    if purge:
        return PurgeModel(**purge.__dict__)
    return None


def query_all_purge_schedules(db_session: Session, engine: Engine) -> List[PurgeModel]:
    purges = db_session.query(PurgeTable).all()
    return [PurgeModel(**purge.__dict__) for purge in purges]


def update_purge_schedule(purge_id: str, updates: PurgeModel, engine: Engine) -> bool:
    """Update purge schedule (admin only).

    Args:
        purge_id: Purge schedule ID to update
        updates: PurgeModel with updated fields
        engine: Database engine

    Returns:
        True if updated, False if not found

    Raises:
        ValueError: If validation fails
        SQLAlchemyError: If database operation fails
    """
    update_dict = updates.model_dump(exclude_unset=True)

    # Add updated_at timestamp
    update_dict["updated_at"] = datetime.now(timezone.utc)

    with session() as db_session:
        purge = db_session.get(PurgeTable, purge_id)
        if not purge:
            return False

        for key, value in update_dict.items():
            setattr(purge, key, value)

        db_session.commit()
        return True


def drop_purge_schedule(purge_id: str, engine: Engine) -> bool:
    """Permanently delete purge schedule (admin only).

    WARNING: Deleting a purge schedule disables automated cleanup for the table.

    Args:
        purge_id: Purge schedule ID to delete
        engine: Database engine
        session: Active database session

    Returns:
        True if deleted, False if not found
    """
    with session() as db_session:
        purge = db_session.get(PurgeTable, purge_id)
        if not purge:
            return False

        db_session.delete(purge)
        db_session.commit()
        return True


# ============================================================================
# Purge Job Query Helpers
# ============================================================================


def query_purge_schedule_by_table(
    table_name: str, db_session: Session, engine: Engine
) -> Optional[PurgeModel]:
    """Query purge schedule for a specific table.

    Args:
        table_name: Table name to query schedule for
        session: Active database session
        engine: Database engine

    Returns:
        PurgeModel if found, None otherwise
    """
    purge = (
        db_session.query(PurgeTable).filter(PurgeTable.table_name == table_name).first()
    )

    if purge:
        return PurgeModel(**purge.__dict__)
    return None


def query_tables_due_for_purge(db_session: Session, engine: Engine) -> List[PurgeModel]:
    current_time = datetime.now(timezone.utc)

    purges = db_session.query(PurgeTable).all()

    due_purges = []
    for purge in purges:
        # PostgreSQL returns timezone-naive datetime, make it aware for comparison
        last_purged = purge.last_purged_at.replace(tzinfo=timezone.utc)
        next_purge_date = last_purged + timedelta(days=purge.purge_interval_days)
        if current_time >= next_purge_date:
            due_purges.append(PurgeModel(**purge.__dict__))

    return due_purges


def update_last_purged_at(
    purge_id: str, purged_at: Optional[datetime], engine: Engine
) -> bool:
    """Update last_purged_at timestamp after successful purge (called by background jobs).

    Args:
        purge_id: Purge schedule ID to update
        purged_at: Timestamp of purge completion (defaults to now)
        engine: Database engine

    Returns:
        True if updated, False if not found

    Raises:
        SQLAlchemyError: If database operation fails
    """
    if purged_at is None:
        purged_at = datetime.now(timezone.utc)

    with session() as db_session:
        purge = db_session.get(PurgeTable, purge_id)
        if not purge:
            return False

        purge.last_purged_at = purged_at
        purge.updated_at = datetime.now(timezone.utc)

        db_session.commit()
        return True


def update_purge_interval(
    table_name: str, new_interval_days: int, engine: Engine
) -> bool:
    """Update purge interval for a table (admin shortcut).

    Args:
        table_name: Table name to update interval for
        new_interval_days: New purge interval in days
        engine: Database engine

    Returns:
        True if updated, False if schedule not found

    Raises:
        ValueError: If interval validation fails
    """
    if new_interval_days < 1 or new_interval_days > 3650:
        raise ValueError(
            f"Invalid purge interval {new_interval_days}. Must be 1-3650 days."
        )

    with session() as db_session:
        purge = (
            db_session.query(PurgeTable)
            .filter(PurgeTable.table_name == table_name)
            .first()
        )

        if not purge:
            return False

        purge.purge_interval_days = new_interval_days
        purge.updated_at = datetime.now(timezone.utc)

        db_session.commit()
        return True


def get_purge_schedule_summary(db_session: Session, engine: Engine) -> List[dict]:
    purges = db_session.query(PurgeTable).all()
    current_time = datetime.now(timezone.utc)

    summary = []
    for purge in purges:
        # PostgreSQL returns timezone-naive datetime, make it aware for comparison
        last_purged = purge.last_purged_at.replace(tzinfo=timezone.utc)
        next_purge_date = last_purged + timedelta(days=purge.purge_interval_days)
        is_due = current_time >= next_purge_date

        summary.append(
            {
                "table_name": purge.table_name,
                "last_purged_at": purge.last_purged_at,
                "purge_interval_days": purge.purge_interval_days,
                "next_purge_date": next_purge_date,
                "is_due_for_purge": is_due,
            }
        )

    # Sort by next_purge_date (soonest first)
    summary.sort(key=lambda x: x["next_purge_date"])

    return summary
