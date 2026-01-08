"""
The page model is the table that stores page information, how to get to that page,
which environments it is available in, and the element identifiers associated with
that page.
"""

import logging
from typing import List, Optional
from datetime import datetime

from sqlalchemy import Engine
from sqlalchemy.orm import Session
from pydantic import BaseModel

from common.fenrir_enums import EnvironmentEnum
from common.service_connections.db_service.database import PageTable, IdentifierTable
from common.service_connections.db_service.models.identifier_model import IdentifierModel


# Use the centralized PageTable from database.py
# Remove the local Base and PageTable definitions


class PageModel(BaseModel):
    """
    PageModel represents a page with its metadata and environments.
    Fields match PageTable database schema.

    Fields:
    - page_id (int): The unique identifier for the page.
    - page_name (str): The name of the page.
    - page_url (str): The URL of the page.
    - environments (dict): JSONB dict of environment configurations
    - is_active (bool): Soft delete flag
    - deactivated_at (datetime | None): Soft delete timestamp
    - deactivated_by_user_id (str | None): Who deactivated
    - created_at (datetime): The creation timestamp of the page.
    - updated_at (datetime): The update timestamp of the page.
    - identifiers (List[IdentifierModel]): A list of identifiers associated with the page.
    """

    page_id: Optional[int] = None
    page_name: str
    page_url: str
    environments: dict = {}
    is_active: bool = True
    deactivated_at: Optional[datetime] = None
    deactivated_by_user_id: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    identifiers: List[IdentifierModel] = []

    @property
    def useable_environments(self) -> List[EnvironmentEnum]:
        return [EnvironmentEnum[env] for env in self.environments]


################ Page Queries ################


def insert_page(page: PageModel, engine: Engine, session: Session) -> PageModel:
    """Insert a new page with its identifiers into the database."""
    if page.id:
        page.id = None
        logging.error("Page ID must be None to insert a new page.")
    with session() as db_session:
        # Create PageTable without identifiers first
        page_data = page.model_dump(exclude={"identifiers"})
        page_data["created_at"] = datetime.now()
        db_page = PageTable(**page_data)
        db_session.add(db_page)
        db_session.flush()  # Get the ID without committing

        # Create identifiers if any
        for identifier in page.identifiers:

            identifier_data = identifier.model_dump(exclude={"id"})
            identifier_data["page_id"] = db_page.id
            identifier_data["created_at"] = datetime.now()
            db_identifier = IdentifierTable(**identifier_data)
            db_session.add(db_identifier)

        db_session.commit()
        db_session.refresh(db_page)

        # Convert back to PageModel with identifiers while session is still active
        return _convert_page_table_to_model(db_page)


def query_page_by_id(page_id: int, engine: Engine, session: Session) -> PageModel:
    """Query a page by its ID."""
    with session() as db_session:
        page = db_session.query(PageTable).filter(PageTable.id == page_id).first()
        if not page:
            raise ValueError(f"Page with ID {page_id} not found.")
        return _convert_page_table_to_model(page)


def query_all_pages(engine: Engine, session: Session) -> List[PageModel]:
    """Query all pages from the database."""
    with session() as db_session:
        pages = db_session.query(PageTable).all()
        return [_convert_page_table_to_model(page) for page in pages]


def _convert_page_table_to_model(page_table: PageTable) -> PageModel:
    """Convert PageTable to PageModel, handling the identifiers relationship."""
    # Convert identifiers relationship to IdentifierModel list
    identifiers = []
    for db_identifier in page_table.identifiers:
        identifier_dict = {
            "id": db_identifier.id,
            "page_id": db_identifier.page_id,
            "element_name": db_identifier.element_name,
            "locator_strategy": db_identifier.locator_strategy,
            "locator_query": db_identifier.locator_query,
            "action": db_identifier.action,
            "environments": db_identifier.environments,
            "created_at": db_identifier.created_at,
        }
        identifiers.append(IdentifierModel(**identifier_dict))

    return PageModel(
        id=page_table.id,
        page_name=page_table.page_name,
        page_url=page_table.page_url,
        created_at=page_table.created_at.isoformat(),
        identifiers=identifiers,
        environments=page_table.environments,
    )


def update_page_by_id(
    page_id: int, page: PageModel, engine: Engine, session: Session
) -> PageModel:
    """Update a page by its ID."""
    with session() as db_session:
        db_page = db_session.get(PageTable, page_id)
        if not db_page:
            raise ValueError(f"Page with ID {page_id} not found.")

        db_page.updated_at = datetime.now()

        # Update basic page fields (excluding identifiers)
        page_data = page.model_dump(
            exclude={"identifiers", "id", "created_at"}, exclude_unset=True
        )
        for key, value in page_data.items():
            setattr(db_page, key, value)

        # Handle identifiers relationship update if provided
        if hasattr(page, "identifiers") and page.identifiers is not None:
            # Remove existing identifiers
            for existing_identifier in db_page.identifiers[:]:
                db_session.delete(existing_identifier)

            # Add new identifiers
            for identifier in page.identifiers:
                identifier_data = identifier.model_dump(exclude={"id"})
                identifier_data["page_id"] = db_page.id
                if "created_at" not in identifier_data:
                    identifier_data["created_at"] = datetime.now()
                db_identifier = IdentifierTable(**identifier_data)
                db_session.add(db_identifier)

        db_session.commit()
        db_session.refresh(db_page)

    return _convert_page_table_to_model(db_page)


def drop_page_by_id(page_id: int, engine: Engine, session: Session) -> int:
    """Delete a page by its ID."""
    with session() as db_session:
        page = db_session.get(PageTable, page_id)
        if not page:
            raise ValueError(f"Page with ID {page_id} not found.")
        db_session.delete(page)
        db_session.commit()
        logging.info("Page ID %s deleted.", page_id)
    return 1


def query_page_by_name(page_name: str, engine: Engine, session: Session) -> PageTable:
    """Query a page by its name."""
    with session() as db_session:
        return (
            db_session.query(PageTable).filter(PageTable.page_name == page_name).first()
        )


def query_page_by_environment(
    environment: str, engine: Engine, session: Session
) -> PageTable:
    """Query pages by environment."""
    with session() as db_session:
        return (
            db_session.query(PageTable)
            .filter(PageTable.environments == environment)
            .all()
        )
