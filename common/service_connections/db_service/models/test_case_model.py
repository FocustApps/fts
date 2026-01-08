"""
Test Case model for managing individual test definitions.

This module provides the TestCaseModel Pydantic model and database operations
for managing test case records in the Fenrir Testing System.
"""

from typing import List, Optional
from datetime import datetime, timezone
import logging

from pydantic import BaseModel, field_validator
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from common.service_connections.db_service.database import TestCaseTable
from common.service_connections.db_service.database.enums import TestTypeEnum
from common.service_connections.db_service.database.engine import (
    get_database_session as session,
)
from common.config import should_validate_write


class TestCaseModel(BaseModel):
    """
    Pydantic model for Test Case data validation and serialization.

    Defines individual test cases with specific test types for granular test management
    and reusability across multiple test suites.

    Fields:
    - test_case_id: str | None - UUID primary key (auto-generated)
    - test_name: str - Unique test case name
    - description: str | None - Optional test description
    - test_type: str - Type of test (functional, integration, regression, smoke, performance, security)
    - sut_id: str - System under test reference
    - owner_user_id: str - Test case owner reference
    - account_id: str - Multi-tenant account ID
    - is_active: bool - Soft delete flag
    - deactivated_at: datetime | None - Soft delete timestamp
    - deactivated_by_user_id: str | None - Who deactivated
    - created_at: datetime - Creation timestamp
    - updated_at: datetime | None - Last update timestamp
    """

    test_case_id: Optional[str] = None
    test_name: str
    description: Optional[str] = None
    test_type: str = "functional"
    sut_id: str
    owner_user_id: str
    account_id: str
    is_active: bool = True
    deactivated_at: Optional[datetime] = None
    deactivated_by_user_id: Optional[str] = None
    created_at: datetime = datetime.now(tz=timezone.utc)
    updated_at: Optional[datetime] = None

    @field_validator("test_name")
    @classmethod
    def validate_test_name(cls, v: str) -> str:
        """Validate test_name is not empty and within length limits."""
        if not should_validate_write():
            return v
        if not v or not v.strip():
            raise ValueError("test_name cannot be empty")
        if len(v) > 255:
            raise ValueError("test_name cannot exceed 255 characters")
        return v.strip()

    @field_validator("test_type")
    @classmethod
    def validate_test_type(cls, v: str) -> str:
        """Validate test_type against TestTypeEnum values."""
        if not should_validate_write():
            return v
        valid_types = [t.value for t in TestTypeEnum]
        if v not in valid_types:
            raise ValueError(
                f"Invalid test_type: {v}. Must be one of: {', '.join(valid_types)}"
            )
        return v


################ Test Case CRUD Operations ################


def insert_test_case(test_case: TestCaseModel, engine: Engine) -> str:
    """Create a new test case in the database.

    Returns:
        test_case_id (str): The ID of the created test case
    """
    if test_case.test_case_id:
        test_case.test_case_id = None
        logging.warning("Test Case ID will only be set by the system")

    with session() as db_session:
        test_case.created_at = datetime.now(timezone.utc)
        db_test_case = TestCaseTable(**test_case.model_dump())
        db_session.add(db_test_case)
        db_session.commit()
        db_session.refresh(db_test_case)
        test_case_id = db_test_case.test_case_id

    return test_case_id


def query_test_case_by_id(
    test_case_id: str, session: Session, engine: Engine
) -> TestCaseModel:
    """Retrieve a test case by ID."""
    db_test_case = (
        session.query(TestCaseTable)
        .filter(TestCaseTable.test_case_id == test_case_id)
        .first()
    )
    if not db_test_case:
        raise ValueError(f"Test Case ID {test_case_id} not found.")

    return TestCaseModel(**db_test_case.__dict__)


def query_all_test_cases(session: Session, engine: Engine) -> List[TestCaseModel]:
    """Retrieve all active test cases."""
    with session() as db_session:
        test_cases = (
            db_session.query(TestCaseTable).filter(TestCaseTable.is_active == True).all()
        )
        return [TestCaseModel(**tc.__dict__) for tc in test_cases]


def update_test_case_by_id(
    test_case_id: str, test_case: TestCaseModel, session: Session, engine: Engine
) -> TestCaseModel:
    """Update an existing test case."""
    with session() as db_session:
        db_test_case = db_session.get(TestCaseTable, test_case_id)
        if not db_test_case:
            raise ValueError(f"Test Case ID {test_case_id} not found.")

        test_case.updated_at = datetime.now(timezone.utc)
        test_case_data = test_case.model_dump(exclude_unset=True)

        for key, value in test_case_data.items():
            setattr(db_test_case, key, value)

        db_session.commit()
        db_session.refresh(db_test_case)

    return TestCaseModel(**db_test_case.__dict__)


def drop_test_case_by_id(test_case_id: str, session: Session, engine: Engine) -> int:
    """Hard delete a test case (use with caution - prefer soft delete)."""
    with session() as db_session:
        db_test_case = db_session.get(TestCaseTable, test_case_id)
        if not db_test_case:
            raise ValueError(f"Test Case ID {test_case_id} not found.")
        db_session.delete(db_test_case)
        db_session.commit()
        logging.info(f"Test Case ID {test_case_id} deleted.")
    return 1


################ Multi-Tenant & Soft Delete Operations ################


def query_test_cases_by_account(
    account_id: str, session: Session, engine: Engine
) -> List[TestCaseModel]:
    """Query active test cases filtered by account_id."""
    test_cases = (
        session.query(TestCaseTable)
        .filter(TestCaseTable.account_id == account_id)
        .filter(TestCaseTable.is_active == True)
        .all()
    )
    return [TestCaseModel(**tc.__dict__) for tc in test_cases]


def query_test_cases_by_owner(
    owner_user_id: str, session: Session, engine: Engine
) -> List[TestCaseModel]:
    """Query active test cases owned by a specific user."""
    with session() as db_session:
        test_cases = (
            db_session.query(TestCaseTable)
            .filter(TestCaseTable.owner_user_id == owner_user_id)
            .filter(TestCaseTable.is_active == True)
            .all()
        )
        return [TestCaseModel(**tc.__dict__) for tc in test_cases]


def query_test_cases_by_sut(
    sut_id: str, session: Session, engine: Engine
) -> List[TestCaseModel]:
    """Query active test cases for a specific system under test."""
    test_cases = (
        session.query(TestCaseTable)
        .filter(TestCaseTable.sut_id == sut_id)
        .filter(TestCaseTable.is_active == True)
        .all()
    )
    return [TestCaseModel(**tc.__dict__) for tc in test_cases]


def query_test_cases_by_type(
    test_type: str, account_id: str, session: Session, engine: Engine
) -> List[TestCaseModel]:
    """Query active test cases filtered by test type and account."""
    test_cases = (
        session.query(TestCaseTable)
        .filter(TestCaseTable.test_type == test_type)
        .filter(TestCaseTable.account_id == account_id)
        .filter(TestCaseTable.is_active == True)
        .all()
    )
    return [TestCaseModel(**tc.__dict__) for tc in test_cases]


def deactivate_test_case_by_id(
    test_case_id: str, deactivated_by_user_id: str, session: Session, engine: Engine
) -> TestCaseModel:
    """Soft delete a test case."""
    with session() as db_session:
        db_test_case = db_session.get(TestCaseTable, test_case_id)
        if not db_test_case:
            raise ValueError(f"Test Case ID {test_case_id} not found.")

        db_test_case.is_active = False
        db_test_case.deactivated_at = datetime.now(timezone.utc)
        db_test_case.deactivated_by_user_id = deactivated_by_user_id

        db_session.commit()
        db_session.refresh(db_test_case)

    return TestCaseModel(**db_test_case.__dict__)


def reactivate_test_case_by_id(
    test_case_id: str, session: Session, engine: Engine
) -> TestCaseModel:
    """Reactivate a soft-deleted test case."""
    with session() as db_session:
        db_test_case = db_session.get(TestCaseTable, test_case_id)
        if not db_test_case:
            raise ValueError(f"Test Case ID {test_case_id} not found.")

        db_test_case.is_active = True
        db_test_case.deactivated_at = None
        db_test_case.deactivated_by_user_id = None
        db_test_case.updated_at = datetime.now(timezone.utc)

        db_session.commit()
        db_session.refresh(db_test_case)

    return TestCaseModel(**db_test_case.__dict__)
