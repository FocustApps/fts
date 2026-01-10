"""
Helper functions for managing plan-suite associations.

Provides high-level operations for composing test plans from suites
with execution order management and bulk operations.
"""

from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, field_validator
from sqlalchemy import and_, func
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from common.config import should_validate_write
from common.service_connections.db_service.database.engine import (
    get_database_session as session,
)
from common.service_connections.db_service.database.tables.plan import PlanTable
from common.service_connections.db_service.database.tables.plan_suite_association import (
    PlanSuiteAssociation,
)
from common.service_connections.db_service.database.tables.suite import SuiteTable


class PlanSuiteAssociationModel(BaseModel):
    """Pydantic model for plan-suite association validation."""

    association_id: Optional[str] = None
    plan_id: str
    suite_id: str
    execution_order: int = 0
    is_active: bool = True
    created_at: Optional[datetime] = None

    @field_validator("execution_order")
    def validate_execution_order(cls, v: int) -> int:
        """Validate execution_order is non-negative."""
        if not should_validate_write():
            return v

        if v < 0:
            raise ValueError(f"execution_order must be >= 0, got {v}")

        return v


class PlanWithSuitesModel(BaseModel):
    """Composite model representing a plan with its suites."""

    plan_id: str
    plan_name: str
    plan_description: Optional[str] = None
    account_id: str
    suites: List[Dict] = []  # List of suite dicts with execution_order


# ============================================================================
# Association Management
# ============================================================================


def add_suite_to_plan(
    plan_id: str,
    suite_id: str,
    execution_order: int,
    engine: Engine,
    is_enabled: bool = True,
) -> str:
    """Add a suite to a plan with specified execution order.

    Args:
        plan_id: Plan to add suite to
        suite_id: Suite to add
        execution_order: Order for execution (0-indexed)
        engine: Database engine
        is_enabled: Whether association is active

    Returns:
        association_id of created record

    Raises:
        ValueError: If validation fails or entities don't exist
        SQLAlchemyError: If database operation fails
    """
    # Validate model
    model = PlanSuiteAssociationModel(
        plan_id=plan_id,
        suite_id=suite_id,
        execution_order=execution_order,
        is_active=is_enabled,
    )

    with session(engine) as db_session:
        # Verify plan exists
        plan = db_session.get(PlanTable, plan_id)
        if not plan:
            raise ValueError(f"Plan not found: {plan_id}")

        # Verify suite exists
        suite = db_session.get(SuiteTable, suite_id)
        if not suite:
            raise ValueError(f"Suite not found: {suite_id}")

        # Create association
        assoc_dict = model.model_dump(exclude_unset=True)
        new_assoc = PlanSuiteAssociation(**assoc_dict)
        db_session.add(new_assoc)
        db_session.commit()

        return new_assoc.association_id


def remove_suite_from_plan(
    plan_id: str,
    suite_id: str,
    engine: Engine,
    db_session: Session,
    soft_delete: bool = True,
) -> bool:
    """Remove a suite from a plan.

    Args:
        plan_id: Plan to remove suite from
        suite_id: Suite to remove
        engine: Database engine
        soft_delete: If True, set is_active=False; if False, hard delete

    Returns:
        True if removed, False if association not found

    Raises:
        SQLAlchemyError: If database operation fails
    """
    with session(engine) as db_session:
        assoc = (
            db_session.query(PlanSuiteAssociation)
            .filter(
                and_(
                    PlanSuiteAssociation.plan_id == plan_id,
                    PlanSuiteAssociation.suite_id == suite_id,
                )
            )
            .first()
        )

        if not assoc:
            return False

        if soft_delete:
            assoc.is_active = False
        else:
            db_session.delete(assoc)

        db_session.commit()
        return True


def reorder_plan_suites(
    plan_id: str, ordered_suite_ids: List[str], engine: Engine
) -> int:
    """Reorder suites in a plan by updating execution_order.

    Args:
        plan_id: Plan to reorder suites for
        ordered_suite_ids: List of suite IDs in desired execution order
        engine: Database engine

    Returns:
        Number of associations updated

    Raises:
        ValueError: If suite IDs don't match existing associations
        SQLAlchemyError: If database operation fails
    """
    with session(engine) as db_session:
        # Get all active associations for plan
        assocs = (
            db_session.query(PlanSuiteAssociation)
            .filter(
                and_(
                    PlanSuiteAssociation.plan_id == plan_id,
                    PlanSuiteAssociation.is_active == True,
                )
            )
            .all()
        )

        # Build lookup map
        assoc_map = {assoc.suite_id: assoc for assoc in assocs}

        # Validate all provided IDs exist
        missing_ids = set(ordered_suite_ids) - set(assoc_map.keys())
        if missing_ids:
            raise ValueError(f"Suite IDs not found in plan associations: {missing_ids}")

        # Update execution order
        update_count = 0
        for new_order, suite_id in enumerate(ordered_suite_ids):
            assoc = assoc_map[suite_id]
            if assoc.execution_order != new_order:
                assoc.execution_order = new_order
                update_count += 1

        db_session.commit()
        return update_count


def update_suite_execution_order(
    plan_id: str,
    suite_id: str,
    new_execution_order: int,
    engine: Engine,
    db_session: Session,
) -> bool:
    """Update execution order for a single suite in a plan.

    Args:
        plan_id: Plan containing suite
        suite_id: Suite to update
        new_execution_order: New execution order value
        engine: Database engine

    Returns:
        True if updated, False if association not found

    Raises:
        ValueError: If validation fails
        SQLAlchemyError: If database operation fails
    """
    if new_execution_order < 0:
        raise ValueError(f"execution_order must be >= 0, got {new_execution_order}")

    with session(engine) as db_session:
        assoc = (
            db_session.query(PlanSuiteAssociation)
            .filter(
                and_(
                    PlanSuiteAssociation.plan_id == plan_id,
                    PlanSuiteAssociation.suite_id == suite_id,
                )
            )
            .first()
        )

        if not assoc:
            return False

        assoc.execution_order = new_execution_order
        db_session.commit()
        return True


# ============================================================================
# Query Helpers
# ============================================================================


def query_plan_with_suites(
    plan_id: str, db_session: Session, engine: Engine, active_only: bool = True
) -> Optional[PlanWithSuitesModel]:
    """Query a plan with all its suites in execution order.

    Args:
        plan_id: Plan ID to query
        session: Active database session
        engine: Database engine
        active_only: If True, only include active suites

    Returns:
        PlanWithSuitesModel with populated suites list, or None if plan not found
    """
    with session(engine) as db_session:
        # Get plan
        plan = db_session.get(PlanTable, plan_id)
        if not plan:
            return None

        # Get associated suites with join
        query = (
            db_session.query(
                SuiteTable,
                PlanSuiteAssociation.execution_order,
                PlanSuiteAssociation.is_active.label("association_is_active"),
            )
            .join(
                PlanSuiteAssociation, PlanSuiteAssociation.suite_id == SuiteTable.suite_id
            )
            .filter(PlanSuiteAssociation.plan_id == plan_id)
            .order_by(PlanSuiteAssociation.execution_order)
        )

        if active_only:
            query = query.filter(
                and_(PlanSuiteAssociation.is_active == True, SuiteTable.is_active == True)
            )

        results = query.all()

        # Build suite list with execution order
        suites = []
        for suite, exec_order, assoc_is_active in results:
            suite_dict = {
                "suite_id": suite.suite_id,
                "suite_name": suite.suite_name,
                "suite_description": suite.description,
                "execution_order": exec_order,
                "is_active": suite.is_active,
                "association_is_active": assoc_is_active,
            }
            suites.append(suite_dict)

        return PlanWithSuitesModel(
            plan_id=plan.plan_id,
            plan_name=plan.plan_name,
            account_id=plan.account_id,
            suites=suites,
        )


def query_suites_for_plan(
    plan_id: str, db_session: Session, engine: Engine, active_only: bool = True
) -> List[str]:
    """Query suite IDs in a plan in execution order.

    Args:
        plan_id: Plan ID to query
        session: Active database session
        engine: Database engine
        active_only: If True, only return active suites

    Returns:
        List of suite_id strings in execution order
    """
    with session(engine) as db_session:
        query = (
            db_session.query(PlanSuiteAssociation.suite_id)
            .filter(PlanSuiteAssociation.plan_id == plan_id)
            .order_by(PlanSuiteAssociation.execution_order)
        )

        if active_only:
            query = query.filter(PlanSuiteAssociation.is_active == True)

        results = query.all()
        return [row[0] for row in results]


def query_plans_for_suite(
    suite_id: str, db_session: Session, engine: Engine, active_only: bool = True
) -> List[str]:
    """Query plan IDs that contain a suite.

    Args:
        suite_id: Suite ID to query
        session: Active database session
        engine: Database engine
        active_only: If True, only return active associations

    Returns:
        List of plan_id strings
    """
    with session(engine) as db_session:
        query = db_session.query(PlanSuiteAssociation.plan_id).filter(
            PlanSuiteAssociation.suite_id == suite_id
        )

        if active_only:
            query = query.filter(PlanSuiteAssociation.is_active == True)

        results = query.all()
        return [row[0] for row in results]


def get_plan_suite_count(
    plan_id: str, db_session: Session, engine: Engine, active_only: bool = True
) -> int:
    """Get count of suites in a plan.

    Args:
        plan_id: Plan ID to count
        session: Active database session
        engine: Database engine
        active_only: If True, only count active suites

    Returns:
        Number of suites in plan
    """
    with session(engine) as db_session:
        query = db_session.query(func.count(PlanSuiteAssociation.association_id)).filter(
            PlanSuiteAssociation.plan_id == plan_id
        )

        if active_only:
            query = query.filter(PlanSuiteAssociation.is_active == True)

        return query.scalar() or 0


# ============================================================================
# Bulk Operations
# ============================================================================


def bulk_add_suites_to_plan(
    plan_id: str,
    suite_ids: List[str],
    engine: Engine,
    starting_order: int = 0,
) -> List[str]:
    """Add multiple suites to a plan in a single transaction.

    Args:
        plan_id: Plan to add suites to
        suite_ids: List of suite IDs to add
        engine: Database engine
        starting_order: Starting execution_order value (increments for each suite)

    Returns:
        List of created association_ids

    Raises:
        ValueError: If plan doesn't exist or any suite doesn't exist
        SQLAlchemyError: If database operation fails
    """
    assoc_ids = []

    with session(engine) as db_session:
        # Verify plan exists
        plan = db_session.get(PlanTable, plan_id)
        if not plan:
            raise ValueError(f"Plan not found: {plan_id}")

        # Verify all suites exist
        for suite_id in suite_ids:
            suite = db_session.get(SuiteTable, suite_id)
            if not suite:
                raise ValueError(f"Suite not found: {suite_id}")

        # Create associations
        for i, suite_id in enumerate(suite_ids):
            model = PlanSuiteAssociationModel(
                plan_id=plan_id, suite_id=suite_id, execution_order=starting_order + i
            )

            new_assoc = PlanSuiteAssociation(**model.model_dump(exclude_unset=True))
            db_session.add(new_assoc)
            assoc_ids.append(new_assoc.association_id)

        db_session.commit()
        return assoc_ids


def replace_plan_suites(
    plan_id: str,
    new_suite_ids: List[str],
    engine: Engine,
    soft_delete_old: bool = True,
) -> Dict[str, List[str]]:
    """Replace all suites in a plan.

    Args:
        plan_id: Plan to update
        new_suite_ids: New list of suite IDs (in execution order)
        engine: Database engine
        soft_delete_old: If True, soft delete old associations; if False, hard delete

    Returns:
        Dict with 'removed' and 'added' association_id lists

    Raises:
        ValueError: If plan doesn't exist or any suite doesn't exist
        SQLAlchemyError: If database operation fails
    """
    result = {"removed": [], "added": []}

    with session(engine) as db_session:
        # Verify plan exists
        plan = db_session.get(PlanTable, plan_id)
        if not plan:
            raise ValueError(f"Plan not found: {plan_id}")

        # Remove old associations
        old_assocs = (
            db_session.query(PlanSuiteAssociation)
            .filter(
                and_(
                    PlanSuiteAssociation.plan_id == plan_id,
                    PlanSuiteAssociation.is_active == True,
                )
            )
            .all()
        )

        for assoc in old_assocs:
            if soft_delete_old:
                assoc.is_active = False
            else:
                db_session.delete(assoc)
            result["removed"].append(assoc.association_id)

        # Add new associations
        for i, suite_id in enumerate(new_suite_ids):
            # Verify suite exists
            suite = db_session.get(SuiteTable, suite_id)
            if not suite:
                raise ValueError(f"Suite not found: {suite_id}")

            model = PlanSuiteAssociationModel(
                plan_id=plan_id, suite_id=suite_id, execution_order=i
            )

            new_assoc = PlanSuiteAssociation(**model.model_dump(exclude_unset=True))
            db_session.add(new_assoc)
            result["added"].append(new_assoc.association_id)

        db_session.commit()
        return result
