"""
Suite model for managing test suite collections.

This module provides the SuiteModel Pydantic model and database operations
for managing test suite records in the Fenrir Testing System.
"""

from typing import List, Optional
from datetime import datetime, timezone
import logging

from pydantic import BaseModel, field_validator
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from common.service_connections.db_service.database import SuiteTable
from common.config import should_validate_write


class SuiteModel(BaseModel):
    """
    Pydantic model for Suite data validation and serialization.

    Groups related test cases for batch execution with support for multiple test plans.

    Fields:
    - suite_id: str | None - UUID primary key (auto-generated)
    - suite_name: str - Unique suite name
    - description: str | None - Optional suite description
    - sut_id: str - System under test reference
    - owner_user_id: str - Suite owner reference
    - account_id: str - Multi-tenant account ID
    - is_active: bool - Soft delete flag
    - deactivated_at: datetime | None - Soft delete timestamp
    - deactivated_by_user_id: str | None - Who deactivated
    - created_at: datetime - Creation timestamp
    - updated_at: datetime | None - Last update timestamp
    """

    suite_id: Optional[str] = None
    suite_name: str
    description: Optional[str] = None
    sut_id: str
    owner_user_id: str
    account_id: str
    is_active: bool = True
    deactivated_at: Optional[datetime] = None
    deactivated_by_user_id: Optional[str] = None
    created_at: datetime = datetime.now(tz=timezone.utc)
    updated_at: Optional[datetime] = None

    @field_validator("suite_name")
    @classmethod
    def validate_suite_name(cls, v: str) -> str:
        """Validate suite_name is not empty and within length limits."""
        if not should_validate_write():
            return v
        if not v or not v.strip():
            raise ValueError("suite_name cannot be empty")
        if len(v) > 255:
            raise ValueError("suite_name cannot exceed 255 characters")
        return v.strip()


################ Suite CRUD Operations ################


def insert_suite(suite: SuiteModel, session: Session, engine: Engine) -> SuiteModel:
    """Create a new suite in the database."""
    if suite.suite_id:
        suite.suite_id = None
        logging.warning("Suite ID will only be set by the system")

    with session() as db_session:
        suite.created_at = datetime.now(timezone.utc)
        db_suite = SuiteTable(**suite.model_dump())
        db_session.add(db_suite)
        db_session.commit()
        db_session.refresh(db_suite)

    return SuiteModel(**db_suite.__dict__)


def query_suite_by_id(suite_id: str, session: Session, engine: Engine) -> SuiteModel:
    """Retrieve a suite by ID."""
    with session() as db_session:
        db_suite = (
            db_session.query(SuiteTable).filter(SuiteTable.suite_id == suite_id).first()
        )
        if not db_suite:
            raise ValueError(f"Suite ID {suite_id} not found.")

    return SuiteModel(**db_suite.__dict__)


def query_all_suites(session: Session, engine: Engine) -> List[SuiteModel]:
    """Retrieve all active suites."""
    with session() as db_session:
        suites = db_session.query(SuiteTable).filter(SuiteTable.is_active == True).all()
        return [SuiteModel(**suite.__dict__) for suite in suites]


def update_suite_by_id(
    suite_id: str, suite: SuiteModel, session: Session, engine: Engine
) -> SuiteModel:
    """Update an existing suite."""
    with session() as db_session:
        db_suite = db_session.get(SuiteTable, suite_id)
        if not db_suite:
            raise ValueError(f"Suite ID {suite_id} not found.")

        suite.updated_at = datetime.now(timezone.utc)
        suite_data = suite.model_dump(exclude_unset=True)

        for key, value in suite_data.items():
            setattr(db_suite, key, value)

        db_session.commit()
        db_session.refresh(db_suite)

    return SuiteModel(**db_suite.__dict__)


def drop_suite_by_id(suite_id: str, session: Session, engine: Engine) -> int:
    """Hard delete a suite (use with caution - prefer soft delete)."""
    with session() as db_session:
        db_suite = db_session.get(SuiteTable, suite_id)
        if not db_suite:
            raise ValueError(f"Suite ID {suite_id} not found.")
        db_session.delete(db_suite)
        db_session.commit()
        logging.info(f"Suite ID {suite_id} deleted.")
    return 1


################ Multi-Tenant & Soft Delete Operations ################


def query_suites_by_account(
    account_id: str, session: Session, engine: Engine
) -> List[SuiteModel]:
    """Query active suites filtered by account_id."""
    with session() as db_session:
        suites = (
            db_session.query(SuiteTable)
            .filter(SuiteTable.account_id == account_id)
            .filter(SuiteTable.is_active == True)
            .all()
        )
        return [SuiteModel(**suite.__dict__) for suite in suites]


def query_suites_by_owner(
    owner_user_id: str, session: Session, engine: Engine
) -> List[SuiteModel]:
    """Query active suites owned by a specific user."""
    with session() as db_session:
        suites = (
            db_session.query(SuiteTable)
            .filter(SuiteTable.owner_user_id == owner_user_id)
            .filter(SuiteTable.is_active == True)
            .all()
        )
        return [SuiteModel(**suite.__dict__) for suite in suites]


def query_suites_by_sut(
    sut_id: str, session: Session, engine: Engine
) -> List[SuiteModel]:
    """Query active suites for a specific system under test."""
    with session() as db_session:
        suites = (
            db_session.query(SuiteTable)
            .filter(SuiteTable.sut_id == sut_id)
            .filter(SuiteTable.is_active == True)
            .all()
        )
        return [SuiteModel(**suite.__dict__) for suite in suites]


def deactivate_suite_by_id(
    suite_id: str, deactivated_by_user_id: str, session: Session, engine: Engine
) -> SuiteModel:
    """Soft delete a suite."""
    with session() as db_session:
        db_suite = db_session.get(SuiteTable, suite_id)
        if not db_suite:
            raise ValueError(f"Suite ID {suite_id} not found.")

        db_suite.is_active = False
        db_suite.deactivated_at = datetime.now(timezone.utc)
        db_suite.deactivated_by_user_id = deactivated_by_user_id

        db_session.commit()
        db_session.refresh(db_suite)

    return SuiteModel(**db_suite.__dict__)


def reactivate_suite_by_id(suite_id: str, session: Session, engine: Engine) -> SuiteModel:
    """Reactivate a soft-deleted suite."""
    with session() as db_session:
        db_suite = db_session.get(SuiteTable, suite_id)
        if not db_suite:
            raise ValueError(f"Suite ID {suite_id} not found.")

        db_suite.is_active = True
        db_suite.deactivated_at = None
        db_suite.deactivated_by_user_id = None
        db_suite.updated_at = datetime.now(timezone.utc)

        db_session.commit()
        db_session.refresh(db_suite)

    return SuiteModel(**db_suite.__dict__)
