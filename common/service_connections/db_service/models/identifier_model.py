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


class IdentifierModel(BaseModel):
    """
    IdentifierModel is a Pydantic model that represents an identifier for a web element.

    Fields:
    - id (int): The unique identifier for the model.
    - page_id (int): The identifier for the page to which the element belongs.
    - element_name (str): The name of the web element.
    - created_at (datetime): The timestamp when the identifier was created.
    - locator_strategy (str): The strategy used to locate the web element (e.g., CSS selector, XPath, ID, etc.).
    - locator_query (str): The query used to locate the web element.
    - action (Optional[str]): The action to be performed on the element (e.g., click, type, hover).
    - environments (List): A list of environments where the identifier is applicable.
    """

    id: Optional[int] = None
    page_id: int
    element_name: str
    created_at: Optional[datetime] = None
    locator_strategy: str
    locator_query: str
    action: Optional[str] = None
    environments: List


################ Identifier Queries ################


def query_all_identifiers(engine: Engine, session: Session) -> List[IdentifierModel]:
    """Query all identifiers from the database."""
    with session() as db_session:
        db_identifiers = db_session.query(IdentifierTable).all()
        return [
            _convert_identifier_table_to_model(identifier)
            for identifier in db_identifiers
        ]


def query_identifier_by_id(
    identifier_id: int, engine: Engine, session: Session
) -> IdentifierModel:
    """Query an identifier by its ID."""
    with session() as db_session:
        db_identifier = (
            db_session.query(IdentifierTable)
            .filter(IdentifierTable.id == identifier_id)
            .first()
        )
        if not db_identifier:
            raise ValueError(f"Identifier with ID {identifier_id} not found.")
        return _convert_identifier_table_to_model(db_identifier)


def insert_identifier(
    identifier: IdentifierModel, engine: Engine, session: Session
) -> IdentifierModel:
    """Insert a new identifier into the database."""
    with session() as db_session:
        # Create IdentifierTable from IdentifierModel
        identifier_data = identifier.model_dump(exclude={"id"})
        if "created_at" not in identifier_data or identifier_data["created_at"] is None:
            identifier_data["created_at"] = datetime.now()
        db_identifier = IdentifierTable(**identifier_data)
        db_session.add(db_identifier)
        db_session.commit()
        db_session.refresh(db_identifier)
        return _convert_identifier_table_to_model(db_identifier)


def _convert_identifier_table_to_model(
    identifier_table: IdentifierTable,
) -> IdentifierModel:
    """Convert IdentifierTable to IdentifierModel."""
    return IdentifierModel(
        id=identifier_table.id,
        page_id=identifier_table.page_id,
        element_name=identifier_table.element_name,
        locator_strategy=identifier_table.locator_strategy,
        locator_query=identifier_table.locator_query,
        action=identifier_table.action,
        environments=identifier_table.environments,
        created_at=identifier_table.created_at,
    )


def drop_identifier_by_id(identifier_id: int, engine: Engine, session: Session) -> int:
    """Delete an identifier by its ID."""
    with session() as db_session:
        identifier = (
            db_session.query(IdentifierTable)
            .filter(IdentifierTable.id == identifier_id)
            .first()
        )
        if not identifier:
            raise ValueError(f"Identifier with ID {identifier_id} not found.")
        db_session.delete(identifier)
        db_session.commit()
        return 1


def update_identifier_by_id(
    identifier_id: int,
    identifier_update: IdentifierModel,
    engine: Engine,
    session: Session,
) -> IdentifierModel:
    """Update an identifier by its ID."""
    with session() as db_session:
        db_identifier = (
            db_session.query(IdentifierTable)
            .filter(IdentifierTable.id == identifier_id)
            .first()
        )
        if not db_identifier:
            raise ValueError(f"Identifier with ID {identifier_id} not found.")

        # Update fields from the model
        update_data = identifier_update.model_dump(
            exclude={"id", "created_at"}, exclude_unset=True
        )
        for key, value in update_data.items():
            setattr(db_identifier, key, value)

        db_identifier.updated_at = datetime.now()
        db_session.commit()
        db_session.refresh(db_identifier)
        return _convert_identifier_table_to_model(db_identifier)


def query_identifier_by_element_name(
    element_name: str, engine: Engine, session: Session
) -> Optional[IdentifierModel]:
    """Query an identifier by its element name."""
    with session() as db_session:
        db_identifier = (
            db_session.query(IdentifierTable)
            .filter(IdentifierTable.element_name == element_name)
            .first()
        )
        if not db_identifier:
            return None
        return _convert_identifier_table_to_model(db_identifier)


def query_identifier_by_identifier_value(
    identifier_value: str, engine: Engine, session: Session
) -> Optional[IdentifierModel]:
    """Query an identifier by its locator query value."""
    with session() as db_session:
        db_identifier = (
            db_session.query(IdentifierTable)
            .filter(IdentifierTable.locator_query == identifier_value)
            .first()
        )
        if not db_identifier:
            return None
        return _convert_identifier_table_to_model(db_identifier)
