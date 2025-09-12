"""
The page model is the table that stores page information, how to get to that page,
which environments it is available in, and the element identifiers associated with
that page.
"""

import logging
from typing import Dict, List
from datetime import datetime

from sqlalchemy import Engine
from sqlalchemy.orm import (
    Session,
)

from pydantic import BaseModel

from common.fenrir_enums import EnvironmentEnum
from common.service_connections.db_service.database import PageTable


# Use the centralized PageTable from database.py
# Remove the local Base and PageTable definitions


class PageModel(BaseModel):
    """
    PageModel represents a page with its metadata and environments.

    Fields:
    - id (int): The unique identifier for the page.
    - page_name (str): The name of the page.
    - page_url (str): The URL of the page.
    - created_at (str): The creation timestamp of the page.
    - identifiers (Dict): A dictionary of identifiers associated with the page.
    - environments (List[str]): A list of environment names where the page is used.

    Properties:
    - useable_environments (List[EnvironmentEnum]): A list of EnvironmentEnum values derived from the environments attribute.
    """

    id: int
    page_name: str
    page_url: str
    created_at: str
    identifiers: Dict
    environments: List[str]

    @property
    def useable_environments(self) -> List[EnvironmentEnum]:
        return [EnvironmentEnum[env] for env in self.environments]


################ Page Queries ################


def insert_page(page: PageModel, engine: Engine, session: Session) -> PageTable:
    if page.id:
        page.id = None
        logging.error("Page ID must be None to insert a new page.")
    with session(engine) as session:
        page.created_at = datetime.now()
        db_page = PageTable(**page.model_dump())
        session.add(db_page)
        session.commit()
        session.refresh(db_page)
    return PageModel(**db_page.__dict__)


def query_page_by_id(page_id: int, engine: Engine, session: Session) -> PageTable:
    with session(engine) as session:
        page = session.query(PageTable).filter(PageTable.id == page_id).first()
    return PageModel(**page.__dict__)


def query_all_pages(engine: Engine, session: Session) -> List[PageTable]:
    with session(engine) as session:
        pages = session.query(PageTable).all()
    return [PageModel(**page.__dict__) for page in pages]


def update_page_by_id(
    page_id: int, page: PageModel, engine: Engine, session: Session
) -> PageTable:
    with session(engine) as session:
        db_page = session.get(PageTable, page_id)
        if not db_page:
            raise ValueError(f"Page with ID {page_id} not found.")
        db_page.updated_at = datetime.now()
        page_data = page.model_dump(exclude_unset=True)
        db_page.identifiers = db_page.identifiers or {}
        for key, value in page_data.items():
            setattr(db_page, key, value)
        session.commit()
        session.refresh(db_page)
    return PageModel(**db_page.__dict__)


def drop_page_by_id(page_id: int, engine: Engine, session: Session) -> PageTable:
    with session(engine) as session:
        page = session.get(PageTable, page_id)
        session.delete(page)
        session.commit()
        logging.info(f"Page ID {page_id} deleted.")
    return 1


def query_page_by_name(page_name: str, engine: Engine, session: Session) -> PageTable:
    with session(engine) as session:
        return session.query(PageTable).filter(PageTable.page_name == page_name).first()


def query_page_by_environment(
    environment: str, engine: Engine, session: Session
) -> PageTable:
    with session(engine) as session:
        return (
            session.query(PageTable).filter(PageTable.environments == environment).all()
        )
