"""
Helper functions for managing suite-test case associations.

Provides high-level operations for composing test suites from test cases
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

from common.service_connections.db_service.database.tables.suite import SuiteTable
from common.service_connections.db_service.database.tables.suite_test_case_association import (
    SuiteTestCaseAssociation,
)
from common.service_connections.db_service.database.tables.test_case import (
    TestCaseTable,
)


class SuiteTestCaseAssociationModel(BaseModel):
    """Pydantic model for suite-test case association validation."""

    association_id: Optional[str] = None
    suite_id: str
    test_case_id: str
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


class SuiteWithTestCasesModel(BaseModel):
    """Composite model representing a suite with its test cases."""

    suite_id: str
    suite_name: str
    suite_description: Optional[str] = None
    account_id: str
    test_cases: List[Dict] = []  # List of test case dicts with execution_order


# ============================================================================
# Association Management
# ============================================================================


def add_test_case_to_suite(
    suite_id: str,
    test_case_id: str,
    execution_order: int,
    engine: Engine,
    is_enabled: bool = True,
) -> str:
    """Add a test case to a suite with specified execution order.

    Args:
        suite_id: Suite to add test case to
        test_case_id: Test case to add
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
    model = SuiteTestCaseAssociationModel(
        suite_id=suite_id,
        test_case_id=test_case_id,
        execution_order=execution_order,
        is_active=is_enabled,
    )

    with session() as db_session:
        # Verify suite exists
        suite = db_session.get(SuiteTable, suite_id)
        if not suite:
            raise ValueError(f"Suite not found: {suite_id}")

        # Verify test case exists
        test_case = db_session.get(TestCaseTable, test_case_id)
        if not test_case:
            raise ValueError(f"Test case not found: {test_case_id}")

        # Create association
        assoc_dict = model.model_dump(exclude_unset=True)
        new_assoc = SuiteTestCaseAssociation(**assoc_dict)
        db_session.add(new_assoc)
        db_session.commit()

        return new_assoc.association_id


def remove_test_case_from_suite(
    suite_id: str,
    test_case_id: str,
    engine: Engine,
    db_session: Session,
    soft_delete: bool = True,
) -> bool:
    """Remove a test case from a suite.

    Args:
        suite_id: Suite to remove test case from
        test_case_id: Test case to remove
        engine: Database engine
        session: Active database session
        soft_delete: If True, set is_active=False; if False, hard delete

    Returns:
        True if removed, False if association not found

    Raises:
        SQLAlchemyError: If database operation fails
    """
    with session() as db_session:
        assoc = (
            db_session.query(SuiteTestCaseAssociation)
            .filter(
                and_(
                    SuiteTestCaseAssociation.suite_id == suite_id,
                    SuiteTestCaseAssociation.test_case_id == test_case_id,
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


def reorder_suite_test_cases(
    suite_id: str, ordered_test_case_ids: List[str], engine: Engine
) -> int:
    """Reorder test cases in a suite by updating execution_order.

    Args:
        suite_id: Suite to reorder test cases for
        ordered_test_case_ids: List of test case IDs in desired execution order
        engine: Database engine
        session: Active database session

    Returns:
        Number of associations updated

    Raises:
        ValueError: If test case IDs don't match existing associations
        SQLAlchemyError: If database operation fails
    """
    with session() as db_session:
        # Get all active associations for suite
        assocs = (
            db_session.query(SuiteTestCaseAssociation)
            .filter(
                and_(
                    SuiteTestCaseAssociation.suite_id == suite_id,
                    SuiteTestCaseAssociation.is_active == True,
                )
            )
            .all()
        )

        # Build lookup map
        assoc_map = {assoc.test_case_id: assoc for assoc in assocs}

        # Validate all provided IDs exist
        missing_ids = set(ordered_test_case_ids) - set(assoc_map.keys())
        if missing_ids:
            raise ValueError(
                f"Test case IDs not found in suite associations: {missing_ids}"
            )

        # Update execution order
        update_count = 0
        for new_order, test_case_id in enumerate(ordered_test_case_ids):
            assoc = assoc_map[test_case_id]
            if assoc.execution_order != new_order:
                assoc.execution_order = new_order
                update_count += 1

        db_session.commit()
        return update_count


def update_test_case_execution_order(
    suite_id: str,
    test_case_id: str,
    new_execution_order: int,
    engine: Engine,
    db_session: Session,
) -> bool:
    """Update execution order for a single test case in a suite.

    Args:
        suite_id: Suite containing test case
        test_case_id: Test case to update
        new_execution_order: New execution order value
        engine: Database engine
        session: Active database session

    Returns:
        True if updated, False if association not found

    Raises:
        ValueError: If validation fails
        SQLAlchemyError: If database operation fails
    """
    if new_execution_order < 0:
        raise ValueError(f"execution_order must be >= 0, got {new_execution_order}")

    with session() as db_session:
        assoc = (
            db_session.query(SuiteTestCaseAssociation)
            .filter(
                and_(
                    SuiteTestCaseAssociation.suite_id == suite_id,
                    SuiteTestCaseAssociation.test_case_id == test_case_id,
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


def query_suite_with_test_cases(
    suite_id: str, db_session: Session, engine: Engine, active_only: bool = True
) -> Optional[SuiteWithTestCasesModel]:
    """Query a suite with all its test cases in execution order.

    Args:
        suite_id: Suite ID to query
        session: Active database session
        engine: Database engine
        active_only: If True, only include active test cases

    Returns:
        SuiteWithTestCasesModel with populated test_cases list, or None if suite not found
    """
    with session() as db_session:
        # Get suite
        suite = db_session.get(SuiteTable, suite_id)
        if not suite:
            return None

        # Get associated test cases with join
        query = (
            db_session.query(
                TestCaseTable,
                SuiteTestCaseAssociation.execution_order,
                SuiteTestCaseAssociation.is_active.label("association_is_active"),
            )
            .join(
                SuiteTestCaseAssociation,
                SuiteTestCaseAssociation.test_case_id == TestCaseTable.test_case_id,
            )
            .filter(SuiteTestCaseAssociation.suite_id == suite_id)
            .order_by(SuiteTestCaseAssociation.execution_order)
        )

        if active_only:
            query = query.filter(
                and_(
                    SuiteTestCaseAssociation.is_active == True,
                    TestCaseTable.is_active == True,
                )
            )

        results = query.all()

        # Build test case list with execution order
        test_cases = []
        for test_case, exec_order, assoc_is_active in results:
            test_case_dict = {
                "test_case_id": test_case.test_case_id,
                "test_case_name": test_case.test_name,
                "test_type": test_case.test_type,
                "execution_order": exec_order,
                "is_active": test_case.is_active,
                "association_is_active": assoc_is_active,
            }
            test_cases.append(test_case_dict)

        return SuiteWithTestCasesModel(
            suite_id=suite.suite_id,
            suite_name=suite.suite_name,
            suite_description=suite.description,
            account_id=suite.account_id,
            test_cases=test_cases,
        )


def query_test_cases_for_suite(
    suite_id: str, db_session: Session, engine: Engine, active_only: bool = True
) -> List[str]:
    """Query test case IDs in a suite in execution order.

    Args:
        suite_id: Suite ID to query
        session: Active database session
        engine: Database engine
        active_only: If True, only return active test cases

    Returns:
        List of test_case_id strings in execution order
    """
    with session() as db_session:
        query = (
            db_session.query(SuiteTestCaseAssociation.test_case_id)
            .filter(SuiteTestCaseAssociation.suite_id == suite_id)
            .order_by(SuiteTestCaseAssociation.execution_order)
        )

        if active_only:
            query = query.filter(SuiteTestCaseAssociation.is_active == True)

        results = query.all()
        return [row[0] for row in results]


def query_suites_for_test_case(
    test_case_id: str, db_session: Session, engine: Engine, active_only: bool = True
) -> List[str]:
    """Query suite IDs that contain a test case.

    Args:
        test_case_id: Test case ID to query
        session: Active database session
        engine: Database engine
        active_only: If True, only return active associations

    Returns:
        List of suite_id strings
    """
    with session() as db_session:
        query = db_session.query(SuiteTestCaseAssociation.suite_id).filter(
            SuiteTestCaseAssociation.test_case_id == test_case_id
        )

        if active_only:
            query = query.filter(SuiteTestCaseAssociation.is_active == True)

        results = query.all()
        return [row[0] for row in results]


def get_suite_test_count(
    suite_id: str, db_session: Session, engine: Engine, active_only: bool = True
) -> int:
    """Get count of test cases in a suite.

    Args:
        suite_id: Suite ID to count
        session: Active database session
        engine: Database engine
        active_only: If True, only count active test cases

    Returns:
        Number of test cases in suite
    """
    with session() as db_session:
        query = db_session.query(
            func.count(SuiteTestCaseAssociation.association_id)
        ).filter(SuiteTestCaseAssociation.suite_id == suite_id)

        if active_only:
            query = query.filter(SuiteTestCaseAssociation.is_active == True)

        return query.scalar() or 0


# ============================================================================
# Bulk Operations
# ============================================================================


def bulk_add_test_cases_to_suite(
    suite_id: str,
    test_case_ids: List[str],
    engine: Engine,
    starting_order: int = 0,
) -> List[str]:
    """Add multiple test cases to a suite in a single transaction.

    Args:
        suite_id: Suite to add test cases to
        test_case_ids: List of test case IDs to add
        engine: Database engine
        session: Active database session
        starting_order: Starting execution_order value (increments for each test case)

    Returns:
        List of created association_ids

    Raises:
        ValueError: If suite doesn't exist or any test case doesn't exist
        SQLAlchemyError: If database operation fails
    """
    assoc_ids = []

    with session() as db_session:
        # Verify suite exists
        suite = db_session.get(SuiteTable, suite_id)
        if not suite:
            raise ValueError(f"Suite not found: {suite_id}")

        # Verify all test cases exist
        for test_case_id in test_case_ids:
            test_case = db_session.get(TestCaseTable, test_case_id)
            if not test_case:
                raise ValueError(f"Test case not found: {test_case_id}")

        # Create associations
        for i, test_case_id in enumerate(test_case_ids):
            model = SuiteTestCaseAssociationModel(
                suite_id=suite_id,
                test_case_id=test_case_id,
                execution_order=starting_order + i,
            )

            new_assoc = SuiteTestCaseAssociation(**model.model_dump(exclude_unset=True))
            db_session.add(new_assoc)
            assoc_ids.append(new_assoc.association_id)

        db_session.commit()
        return assoc_ids


def replace_suite_test_cases(
    suite_id: str,
    new_test_case_ids: List[str],
    engine: Engine,
    soft_delete_old: bool = True,
) -> Dict[str, List[str]]:
    """Replace all test cases in a suite.

    Args:
        suite_id: Suite to update
        new_test_case_ids: New list of test case IDs (in execution order)
        engine: Database engine
        db_session: Session active database session
        soft_delete_old: If True, soft delete old associations; if False, hard delete

    Returns:
        Dict with 'removed' and 'added' association_id lists

    Raises:
        ValueError: If suite doesn't exist or any test case doesn't exist
        SQLAlchemyError: If database operation fails
    """
    result = {"removed": [], "added": []}

    with session() as db_session:
        # Verify suite exists
        suite = db_session.get(SuiteTable, suite_id)
        if not suite:
            raise ValueError(f"Suite not found: {suite_id}")

        # Remove old associations
        old_assocs = (
            db_session.query(SuiteTestCaseAssociation)
            .filter(
                and_(
                    SuiteTestCaseAssociation.suite_id == suite_id,
                    SuiteTestCaseAssociation.is_active == True,
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
        for i, test_case_id in enumerate(new_test_case_ids):
            # Verify test case exists
            test_case = db_session.get(TestCaseTable, test_case_id)
            if not test_case:
                raise ValueError(f"Test case not found: {test_case_id}")

            model = SuiteTestCaseAssociationModel(
                suite_id=suite_id, test_case_id=test_case_id, execution_order=i
            )

            new_assoc = SuiteTestCaseAssociation(**model.model_dump(exclude_unset=True))
            db_session.add(new_assoc)
            result["added"].append(new_assoc.association_id)

        db_session.commit()
        return result
