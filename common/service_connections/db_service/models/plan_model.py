"""
Plan model with legacy suites_ids migration support.

This module provides:
1. PlanModel with @model_validator for migrating legacy suites_ids string to associations
2. Standard CRUD operations with multi-tenant filtering
3. Soft delete operations
4. Plan execution status management
"""

import logging
from datetime import datetime, timezone
from typing import List, Optional

from pydantic import BaseModel, field_validator, model_validator
from sqlalchemy import and_
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from common.config import should_validate_write
from common.service_connections.db_service.database.engine import (
    get_database_session as session,
)
from common.service_connections.db_service.database.tables.plan import PlanTable
from common.service_connections.db_service.models.plan_suite_helpers import (
    add_suite_to_plan,
)

logger = logging.getLogger(__name__)


class PlanModel(BaseModel):
    """Pydantic model for test plan validation and legacy migration.

    Handles migration from legacy suites_ids string field to PlanSuiteAssociation.
    """

    plan_id: Optional[str] = None
    plan_name: str
    suites_ids: Optional[str] = None  # DEPRECATED: Migrated to PlanSuiteAssociation
    suite_tags: Optional[dict] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    status: str = "active"
    owner_user_id: Optional[str] = None
    account_id: Optional[str] = None
    is_active: bool = True
    deactivated_at: Optional[datetime] = None
    deactivated_by_user_id: Optional[str] = None

    # Internal fields for migration tracking
    _migrated_suite_ids: List[str] = []
    _migration_required: bool = False

    @field_validator("plan_name")
    def validate_plan_name(cls, v: str) -> str:
        """Validate plan_name length."""
        if not should_validate_write():
            return v

        if len(v) > 255:
            raise ValueError(f"plan_name exceeds 255 characters: {len(v)}")

        if not v.strip():
            raise ValueError("plan_name cannot be empty or whitespace")

        return v

    @field_validator("status")
    def validate_status(cls, v: str) -> str:
        """Validate status against enum values."""
        if not should_validate_write():
            return v

        valid_statuses = {"active", "inactive"}

        if v not in valid_statuses:
            raise ValueError(
                f"Invalid status '{v}'. Must be one of: {', '.join(sorted(valid_statuses))}"
            )

        return v

    @model_validator(mode="after")
    def migrate_legacy_suites_ids(self):
        """Migrate legacy suites_ids string to suite ID list for association creation.

        Legacy format: Comma-separated UUID string like "uuid1,uuid2,uuid3"
        Migration: Parses into _migrated_suite_ids for use in insert_plan() or update_plan()

        This validator runs after field validation to extract suite IDs from the
        deprecated suites_ids string field. The extracted IDs are stored in
        _migrated_suite_ids for downstream association creation.
        """
        if not should_validate_write():
            return self

        # Check if legacy suites_ids field has data
        if self.suites_ids and self.suites_ids.strip():
            # Parse comma-separated UUIDs
            suite_ids = [
                suite_id.strip()
                for suite_id in self.suites_ids.split(",")
                if suite_id.strip()
            ]

            if suite_ids:
                self._migrated_suite_ids = suite_ids
                self._migration_required = True

                logger.info(
                    f"Detected legacy suites_ids for plan '{self.plan_name}'. "
                    f"Extracted {len(suite_ids)} suite IDs for migration to associations."
                )

        return self


# ============================================================================
# CRUD Operations
# ============================================================================


def insert_plan(model: PlanModel, engine: Engine, migrate_suites: bool = True) -> str:
    """Insert new plan record and optionally migrate legacy suite associations.

    Args:
        model: PlanModel with plan data
        engine: Database engine
        migrate_suites: If True and model has _migrated_suite_ids, create associations

    Returns:
        plan_id of inserted record

    Raises:
        ValueError: If validation fails
        SQLAlchemyError: If database operation fails
    """
    from uuid import uuid4

    plan_dict = model.model_dump(
        exclude_unset=True, exclude={"_migrated_suite_ids", "_migration_required"}
    )

    # Generate plan_id if not provided
    if "plan_id" not in plan_dict or not plan_dict["plan_id"]:
        plan_dict["plan_id"] = str(uuid4())

    with session() as db_session:
        new_plan = PlanTable(**plan_dict)
        db_session.add(new_plan)
        db_session.commit()
        plan_id = new_plan.plan_id

        # Migrate legacy suite IDs to associations if requested
        if migrate_suites and model._migration_required and model._migrated_suite_ids:
            logger.info(
                f"Migrating {len(model._migrated_suite_ids)} legacy suite IDs "
                f"to PlanSuiteAssociation for plan_id={plan_id}"
            )

            for i, suite_id in enumerate(model._migrated_suite_ids):
                try:
                    add_suite_to_plan(
                        plan_id=plan_id,
                        suite_id=suite_id,
                        execution_order=i,
                        engine=engine,
                    )
                except ValueError as e:
                    logger.warning(
                        f"Failed to migrate suite_id={suite_id} for plan_id={plan_id}: {e}"
                    )

            # Clear legacy field after migration
            new_plan.suites_ids = ""
            db_session.commit()

        return plan_id


def query_plan_by_id(
    plan_id: str, db_session: Session, engine: Engine
) -> Optional[PlanModel]:
    """Query plan by plan_id.

    Args:
        plan_id: Plan ID to query
        session: Active database session
        engine: Database engine

    Returns:
        PlanModel if found, None otherwise
    """
    with session() as db_session:
        plan = db_session.get(PlanTable, plan_id)
        if plan:
            return PlanModel(**plan.__dict__)
        return None


def query_all_plans(db_session: Session, engine: Engine) -> List[PlanModel]:
    """Query all plans.

    Args:
        session: Active database session
        engine: Database engine

    Returns:
        List of PlanModel instances
    """
    with session() as db_session:
        plans = db_session.query(PlanTable).all()
        return [PlanModel(**plan.__dict__) for plan in plans]


def update_plan(plan_id: str, updates: PlanModel, engine: Engine) -> bool:
    """Update plan record.

    Args:
        plan_id: Plan ID to update
        updates: PlanModel with updated fields
        engine: Database engine

    Returns:
        True if updated, False if not found

    Raises:
        ValueError: If validation fails
        SQLAlchemyError: If database operation fails
    """
    update_dict = updates.model_dump(
        exclude_unset=True, exclude={"_migrated_suite_ids", "_migration_required"}
    )

    # Add updated_at timestamp
    update_dict["updated_at"] = datetime.now(timezone.utc)

    with session() as db_session:
        plan = db_session.get(PlanTable, plan_id)
        if not plan:
            return False

        for key, value in update_dict.items():
            setattr(plan, key, value)

        db_session.commit()
        return True


def drop_plan(plan_id: str, engine: Engine, db_session: Session) -> bool:
    """Permanently delete plan record.

    CASCADE deletes all PlanSuiteAssociation records via foreign key constraint.

    Args:
        plan_id: Plan ID to delete
        engine: Database engine

    Returns:
        True if deleted, False if not found
    """
    with session() as db_session:
        plan = db_session.get(PlanTable, plan_id)
        if not plan:
            return False

        db_session.delete(plan)
        db_session.commit()
        return True


def deactivate_plan(plan_id: str, deactivated_by_user_id: str, engine: Engine) -> bool:
    """Soft delete plan by setting is_active=False.

    Args:
        plan_id: Plan ID to deactivate
        deactivated_by_user_id: User performing deactivation
        engine: Database engine

    Returns:
        True if deactivated, False if not found
    """
    with session() as db_session:
        plan = db_session.get(PlanTable, plan_id)
        if not plan:
            return False

        plan.is_active = False
        plan.status = "inactive"
        plan.deactivated_at = datetime.now(timezone.utc)
        plan.deactivated_by_user_id = deactivated_by_user_id
        plan.updated_at = datetime.now(timezone.utc)

        db_session.commit()
        return True


def reactivate_plan(plan_id: str, engine: Engine) -> bool:
    """Reactivate soft-deleted plan.

    Args:
        plan_id: Plan ID to reactivate
        engine: Database engine

    Returns:
        True if reactivated, False if not found
    """
    with session() as db_session:
        plan = db_session.get(PlanTable, plan_id)
        if not plan:
            return False

        plan.is_active = True
        plan.status = "active"
        plan.deactivated_at = None
        plan.deactivated_by_user_id = None
        plan.updated_at = datetime.now(timezone.utc)

        db_session.commit()
        return True


# ============================================================================
# Multi-Tenant & Custom Queries
# ============================================================================


def query_plans_by_account(
    account_id: str, db_session: Session, engine: Engine, active_only: bool = True
) -> List[PlanModel]:
    """Query all plans for an account.

    Args:
        account_id: Account ID to filter by
        session: Active database session
        engine: Database engine
        active_only: If True, only return active plans

    Returns:
        List of PlanModel instances
    """
    with session() as db_session:
        query = db_session.query(PlanTable).filter(PlanTable.account_id == account_id)

        if active_only:
            query = query.filter(PlanTable.is_active == True)

        plans = query.all()
        return [PlanModel(**plan.__dict__) for plan in plans]


def query_plans_by_owner(
    owner_user_id: str, db_session: Session, engine: Engine, active_only: bool = True
) -> List[PlanModel]:
    """Query all plans owned by a user.

    Args:
        owner_user_id: Owner user ID to filter by
        session: Active database session
        engine: Database engine
        active_only: If True, only return active plans

    Returns:
        List of PlanModel instances
    """
    with session() as db_session:
        query = db_session.query(PlanTable).filter(
            PlanTable.owner_user_id == owner_user_id
        )

        if active_only:
            query = query.filter(PlanTable.is_active == True)

        plans = query.all()
        return [PlanModel(**plan.__dict__) for plan in plans]


def query_plans_by_status(
    status: str, db_session: Session, engine: Engine, account_id: Optional[str] = None
) -> List[PlanModel]:
    """Query plans by execution status.

    Args:
        status: Plan status ('active' or 'inactive')
        session: Active database session
        engine: Database engine
        account_id: Optional account filter

    Returns:
        List of PlanModel instances
    """
    with session() as db_session:
        filters = [PlanTable.status == status]

        if account_id:
            filters.append(PlanTable.account_id == account_id)

        query = db_session.query(PlanTable).filter(and_(*filters))

        plans = query.all()
        return [PlanModel(**plan.__dict__) for plan in plans]


def update_plan_status(plan_id: str, new_status: str, engine: Engine) -> bool:
    """Update plan execution status.

    Args:
        plan_id: Plan ID to update
        new_status: New status ('active' or 'inactive')
        engine: Database engine
    Returns:
        True if updated, False if not found

    Raises:
        ValueError: If status invalid
    """
    if new_status not in {"active", "inactive"}:
        raise ValueError(f"Invalid status '{new_status}'. Must be 'active' or 'inactive'")

    with session() as db_session:
        plan = db_session.get(PlanTable, plan_id)
        if not plan:
            return False

        plan.status = new_status
        plan.updated_at = datetime.now(timezone.utc)

        db_session.commit()
        return True
