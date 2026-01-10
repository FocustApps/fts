"""
Identifier model for managing web element identifiers in the database.

This module provides the IdentifierModel Pydantic model and database operations
for managing web element identifiers that are used in Selenium automation.
"""

from typing import List, Optional
from datetime import datetime

from sqlalchemy import Engine
from sqlalchemy.orm import Session
from pydantic import BaseModel

# Import centralized database components
from common.service_connections.db_service.database import IdentifierTable
from common.service_connections.db_service.database.engine import (
    get_database_session as session,
)


class IdentifierModel(BaseModel):
    """
    IdentifierModel is a Pydantic model that represents an identifier for a web element.
    Fields match IdentifierTable database schema.

    Fields:
    - identifier_id (int): The unique identifier for the model.
    - page_id (int): The identifier for the page to which the element belongs.
    - element_name (str): The name of the web element.
    - locator_strategy (str): The strategy used to locate the web element (e.g., CSS selector, XPath, ID, etc.).
    - locator_query (str): The query used to locate the web element.
    - is_active (bool): Soft delete flag
    - deactivated_at (datetime | None): Soft delete timestamp
    - deactivated_by_user_id (str | None): Who deactivated
    - created_at (datetime): The timestamp when the identifier was created.
    - updated_at (datetime): The timestamp when the identifier was updated.
    """

    identifier_id: Optional[int] = None
    page_id: int
    element_name: str
    locator_strategy: str
    locator_query: str
    is_active: bool = True
    deactivated_at: Optional[datetime] = None
    deactivated_by_user_id: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


################ Identifier Queries ################


def query_all_identifiers(session: Session, engine: Engine) -> List[IdentifierModel]:
    """Query all identifiers from the database."""
    db_identifiers = session.query(IdentifierTable).all()
    return [
        _convert_identifier_table_to_model(identifier) for identifier in db_identifiers
    ]


def query_identifier_by_id(
    identifier_id: int, session: Session, engine: Engine
) -> IdentifierModel:
    """Query an identifier by its ID."""
    db_identifier = (
        session.query(IdentifierTable)
        .filter(IdentifierTable.identifier_id == identifier_id)
        .first()
    )
    if not db_identifier:
        raise ValueError(f"Identifier with ID {identifier_id} not found.")
    return _convert_identifier_table_to_model(db_identifier)


def insert_identifier(identifier: IdentifierModel, engine: Engine) -> int:
    """Insert a new identifier into the database."""
    with session(engine) as db_session:
        # Create IdentifierTable from IdentifierModel
        identifier_data = identifier.model_dump(exclude={"identifier_id"})
        if "created_at" not in identifier_data or identifier_data["created_at"] is None:
            identifier_data["created_at"] = datetime.now()
        db_identifier = IdentifierTable(**identifier_data)
        db_session.add(db_identifier)
        db_session.commit()
        db_session.refresh(db_identifier)
    return db_identifier.identifier_id


def _convert_identifier_table_to_model(
    identifier_table: IdentifierTable,
) -> IdentifierModel:
    """Convert IdentifierTable to IdentifierModel."""
    return IdentifierModel(
        identifier_id=identifier_table.identifier_id,
        page_id=identifier_table.page_id,
        element_name=identifier_table.element_name,
        locator_strategy=identifier_table.locator_strategy,
        locator_query=identifier_table.locator_query,
        is_active=identifier_table.is_active,
        deactivated_at=identifier_table.deactivated_at,
        deactivated_by_user_id=identifier_table.deactivated_by_user_id,
        created_at=identifier_table.created_at,
        updated_at=identifier_table.updated_at,
    )


def drop_identifier_by_id(identifier_id: int, engine: Engine) -> bool:
    """Delete an identifier by its ID."""
    with session(engine) as db_session:
        identifier = (
            db_session.query(IdentifierTable)
            .filter(IdentifierTable.identifier_id == identifier_id)
            .first()
        )
        if not identifier:
            raise ValueError(f"Identifier with ID {identifier_id} not found.")
        db_session.delete(identifier)
        db_session.commit()
    return True


def update_identifier_by_id(
    identifier_id: int,
    identifier_update: IdentifierModel,
    engine: Engine,
) -> bool:
    """Update an identifier by its ID."""
    with session(engine) as db_session:
        db_identifier = (
            db_session.query(IdentifierTable)
            .filter(IdentifierTable.identifier_id == identifier_id)
            .first()
        )
        if not db_identifier:
            raise ValueError(f"Identifier with ID {identifier_id} not found.")

        # Update fields from the model
        update_data = identifier_update.model_dump(
            exclude={"identifier_id", "created_at"}, exclude_unset=True
        )
        for key, value in update_data.items():
            setattr(db_identifier, key, value)

        db_identifier.updated_at = datetime.now()
        db_session.commit()
    return True


def query_identifier_by_element_name(
    element_name: str, session: Session, engine: Engine
) -> Optional[IdentifierModel]:
    """Query an identifier by its element name."""
    db_identifier = (
        session.query(IdentifierTable)
        .filter(IdentifierTable.element_name == element_name)
        .first()
    )
    if not db_identifier:
        return None
    return _convert_identifier_table_to_model(db_identifier)


def query_identifier_by_identifier_value(
    identifier_value: str, session: Session, engine: Engine
) -> Optional[IdentifierModel]:
    """Query an identifier by its locator query value."""
    db_identifier = (
        session.query(IdentifierTable)
        .filter(IdentifierTable.locator_query == identifier_value)
        .first()
    )
    if not db_identifier:
        return None
    return _convert_identifier_table_to_model(db_identifier)
