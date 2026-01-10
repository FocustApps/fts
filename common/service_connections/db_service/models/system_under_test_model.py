"""
System Under Test model for managing tested systems.

This module provides the SystemUnderTestModel Pydantic model and database operations
for managing system under test records in the Fenrir Testing System.
"""

from typing import List, Optional
from datetime import datetime, timezone
import logging

from pydantic import BaseModel, field_validator
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from common.service_connections.db_service.database import SystemUnderTestTable
from common.service_connections.db_service.database.engine import (
    get_database_session as session,
)
from common.config import should_validate_write


class SystemUnderTestModel(BaseModel):
    """
    Pydantic model for System Under Test data validation and serialization.

    Represents complete application systems under test, encompassing multiple code
    repositories and environments for comprehensive test coverage.

    Fields:
    - sut_id: str | None - UUID primary key (auto-generated)
    - system_name: str - Unique system name
    - description: str | None - Optional system description
    - wiki_url: str | None - Optional documentation URL
    - account_id: str - Multi-tenant account ID
    - owner_user_id: str - System owner reference
    - is_active: bool - Soft delete flag
    - deactivated_at: datetime | None - Soft delete timestamp
    - deactivated_by_user_id: str | None - Who deactivated
    - created_at: datetime - Creation timestamp
    - updated_at: datetime | None - Last update timestamp
    """

    sut_id: Optional[str] = None
    system_name: str
    description: Optional[str] = None
    wiki_url: Optional[str] = None
    account_id: str
    owner_user_id: str
    is_active: bool = True
    deactivated_at: Optional[datetime] = None
    deactivated_by_user_id: Optional[str] = None
    created_at: datetime = datetime.now(tz=timezone.utc)
    updated_at: Optional[datetime] = None

    @field_validator("system_name")
    @classmethod
    def validate_system_name(cls, v: str) -> str:
        """Validate system_name is not empty and within length limits."""
        if not should_validate_write():
            return v
        if not v or not v.strip():
            raise ValueError("system_name cannot be empty")
        if len(v) > 96:
            raise ValueError("system_name cannot exceed 96 characters")
        return v.strip()


################ System Under Test CRUD Operations ################


def insert_system_under_test(
    system_under_test: SystemUnderTestModel, session: Session, engine: Engine
) -> SystemUnderTestModel:
    """Create a new system under test in the database."""
    if system_under_test.sut_id:
        system_under_test.sut_id = None
        logging.warning("System Under Test ID will only be set by the system")

    with session(engine) as db_session:
        system_under_test.created_at = datetime.now(timezone.utc)
        db_sut = SystemUnderTestTable(**system_under_test.model_dump())
        db_session.add(db_sut)
        db_session.commit()
        db_session.refresh(db_sut)

    return SystemUnderTestModel(**db_sut.__dict__)


def query_system_under_test_by_id(
    sut_id: str, session: Session, engine: Engine
) -> SystemUnderTestModel:
    """Retrieve a system under test by ID."""
    db_sut = (
        session.query(SystemUnderTestTable)
        .filter(SystemUnderTestTable.sut_id == sut_id)
        .first()
    )
    if not db_sut:
        raise ValueError(f"System Under Test ID {sut_id} not found.")

    return SystemUnderTestModel(**db_sut.__dict__)


def query_all_systems_under_test(
    session: Session, engine: Engine
) -> List[SystemUnderTestModel]:
    """Retrieve all active systems under test."""
    systems = (
        session.query(SystemUnderTestTable)
        .filter(SystemUnderTestTable.is_active == True)
        .all()
    )
    return [SystemUnderTestModel(**sut.__dict__) for sut in systems]


def update_system_under_test_by_id(
    sut_id: str, system_under_test: SystemUnderTestModel, engine: Engine
) -> bool:
    """Update an existing system under test.

    Returns:
        bool: True if successful
    """
    with session(engine) as db_session:
        db_sut = db_session.get(SystemUnderTestTable, sut_id)
        if not db_sut:
            raise ValueError(f"System Under Test ID {sut_id} not found.")

        system_under_test.updated_at = datetime.now(timezone.utc)
        sut_data = system_under_test.model_dump(exclude_unset=True)

        for key, value in sut_data.items():
            setattr(db_sut, key, value)

        db_session.commit()
        db_session.refresh(db_sut)

    return True


def drop_system_under_test_by_id(sut_id: str, session: Session, engine: Engine) -> int:
    """Hard delete a system under test (use with caution - prefer soft delete)."""
    db_sut = session.get(SystemUnderTestTable, sut_id)
    if not db_sut:
        raise ValueError(f"System Under Test ID {sut_id} not found.")
    session.delete(db_sut)
    session.commit()
    logging.info(f"System Under Test ID {sut_id} deleted.")
    return 1


################ Multi-Tenant & Soft Delete Operations ################


def query_systems_under_test_by_account(
    account_id: str, session: Session, engine: Engine
) -> List[SystemUnderTestModel]:
    """Query active systems under test filtered by account_id."""
    systems = (
        session.query(SystemUnderTestTable)
        .filter(SystemUnderTestTable.account_id == account_id)
        .filter(SystemUnderTestTable.is_active == True)
        .all()
    )
    return [SystemUnderTestModel(**sut.__dict__) for sut in systems]


def query_systems_under_test_by_owner(
    owner_user_id: str, session: Session, engine: Engine
) -> List[SystemUnderTestModel]:
    """Query active systems under test owned by a specific user."""
    systems = (
        session.query(SystemUnderTestTable)
        .filter(SystemUnderTestTable.owner_user_id == owner_user_id)
        .filter(SystemUnderTestTable.is_active == True)
        .all()
    )
    return [SystemUnderTestModel(**sut.__dict__) for sut in systems]


def query_systems_under_test_by_account_and_owner(
    account_id: str, owner_user_id: str, session: Session, engine: Engine
) -> List[SystemUnderTestModel]:
    """Query active systems under test by account and owner (combined filter)."""
    systems = (
        session.query(SystemUnderTestTable)
        .filter(SystemUnderTestTable.account_id == account_id)
        .filter(SystemUnderTestTable.owner_user_id == owner_user_id)
        .filter(SystemUnderTestTable.is_active == True)
        .all()
    )
    return [SystemUnderTestModel(**sut.__dict__) for sut in systems]


def deactivate_system_under_test_by_id(
    sut_id: str, deactivated_by_user_id: str, engine: Engine
) -> bool:
    """Soft delete a system under test.

    Returns:
        bool: True if successful
    """
    with session(engine) as db_session:
        db_sut = db_session.get(SystemUnderTestTable, sut_id)
        if not db_sut:
            raise ValueError(f"System Under Test ID {sut_id} not found.")

        db_sut.is_active = False
        db_sut.deactivated_at = datetime.now(timezone.utc)
        db_sut.deactivated_by_user_id = deactivated_by_user_id

        db_session.commit()
        db_session.refresh(db_sut)

    return True


def reactivate_system_under_test_by_id(sut_id: str, engine: Engine) -> bool:
    """Reactivate a previously soft-deleted system under test.

    Returns:
        bool: True if successful
    """
    with session(engine) as db_session:
        db_sut = db_session.get(SystemUnderTestTable, sut_id)
        if not db_sut:
            raise ValueError(f"System Under Test ID {sut_id} not found.")

        db_sut.is_active = True
        db_sut.deactivated_at = None
        db_sut.deactivated_by_user_id = None
        db_sut.updated_at = datetime.now(timezone.utc)

        db_session.commit()
        db_session.refresh(db_sut)

    return True
