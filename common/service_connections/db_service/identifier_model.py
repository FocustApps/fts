from typing import List
from datetime import datetime

from sqlalchemy import Engine
from sqlalchemy.orm import Session
from pydantic import BaseModel

# Import centralized database components
from .database import IdentifierTable


class IdentifierModel(BaseModel):
    """
    IdentifierModel is a Pydantic model that represents an identifier for a web element.

    Fields:
    - id (int): The unique identifier for the model.
    - page_id (int): The identifier for the page to which the element belongs.
    - element_name (str): The name of the web element.
    - created_at (datetime): The timestamp when the identifier was created.
    - locator_strategy (str): The strategy used to locate the web element (e.g., XPath, CSS selector).
    - locator_query (str): The query used to locate the web element.
    - environments (List): A list of environments where the identifier is applicable.
    """
    
    id: int
    page_id: int
    element_name: str
    created_at: datetime
    locator_strategy: str
    locator_query: str
    environments: List


################ Identifier Queries ################


def query_all_identifiers(engine: Engine, session: Session) -> List[IdentifierTable]:
    with session(engine) as session:
        return session.query(IdentifierTable).all()


def query_identifier_by_id(
    identifier_id: int, engine: Engine, session: Session
) -> IdentifierTable:
    with session(engine) as session:
        return (
            session.query(IdentifierTable)
            .filter(IdentifierTable.id == identifier_id)
            .first()
        )


def insert_identifier(
    identifier: IdentifierTable, engine: Engine, session: Session
) -> IdentifierTable:
    with session(engine) as session:
        session.add(identifier)
        session.commit()
        session.refresh(identifier)
        return identifier


def drop_identifier_by_id(
    identifier_id: int, engine: Engine, session: Session
) -> IdentifierTable:
    with session(engine) as session:
        identifier = (
            session.query(IdentifierTable)
            .filter(IdentifierTable.id == identifier_id)
            .first()
        )
        session.delete(identifier)
        session.commit()
        return identifier


def update_identifier_by_id(
    identifier_id: int, engine: Engine, session: Session
) -> IdentifierTable:
    with session(engine) as session:
        identifier = (
            session.query(IdentifierTable)
            .filter(IdentifierTable.id == identifier_id)
            .first()
        )
        session.commit()
        return identifier


def query_identifier_by_element_name(
    element_name: str, engine: Engine, session: Session
) -> IdentifierTable:
    with session(engine) as session:
        return (
            session.query(IdentifierTable)
            .filter(IdentifierTable.element_name == element_name)
            .first()
        )


def query_identifier_by_identifier_value(
    identifier_value: str, engine: Engine, session: Session
) -> IdentifierTable:
    with session(engine) as session:
        return (
            session.query(IdentifierTable)
            .filter(IdentifierTable.locator_query == identifier_value)
            .first()
        )
