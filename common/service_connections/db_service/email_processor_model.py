from datetime import datetime
import logging
from typing import List

from sqlalchemy.orm import Session
from pydantic import BaseModel

# Import centralized database components
from .database import EmailProcessorTable, SystemEnum


class EmailProcessorModel(BaseModel):
    id: int | None = None
    email_item_id: int
    multi_item_email_ids: List | None = None
    multi_email_flag: bool = False
    multi_attachment_flag: bool = False
    test_name: str | None = None
    requires_processing: bool = False
    system: SystemEnum | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    last_processed_at: datetime | None = None


################ Basic CRUD queries ################


def insert_email_item(
    email_item_id: EmailProcessorModel, session: Session, engine
) -> EmailProcessorModel:
    """
    Creates a work_item in the database
    """
    if email_item_id.id:
        email_item_id.id = None
        logging.warning("Environment ID will only be set by the system")
    with session(engine) as session:
        email_item_id.created_at = datetime.now()
        db_work_item = EmailProcessorTable(**email_item_id.model_dump())
        session.add(db_work_item)
        session.commit()
        session.refresh(db_work_item)
    return EmailProcessorModel(**db_work_item.__dict__)


def query_email_item_by_id(
    email_item_id: int, session: Session, engine
) -> EmailProcessorModel:
    """
    Retrieves a email_item from the database by id
    """
    with session(engine) as session:
        email_item = (
            session.query(EmailProcessorTable)
            .filter(EmailProcessorTable.id == email_item_id)
            .first()
        )
    if not email_item:
        raise ValueError(f"User ID with {email_item_id} not found.")
    unpacked_email_item = EmailProcessorModel(**email_item.__dict__)
    return unpacked_email_item


def query_all_email_items(session: Session, engine) -> List[EmailProcessorModel]:
    """
    Retrieves all email_items from the database
    """
    with session(engine) as session:
        email_items = session.query(EmailProcessorTable).all()
    return [EmailProcessorModel(**email_item.__dict__) for email_item in email_items]


def update_email_item_by_id(
    email_item_id: int, work_item: EmailProcessorModel, session: Session, engine
) -> EmailProcessorModel:
    """
    Updates a work_item in the database
    """
    with session(engine) as session:
        work_item.updated_at = datetime.now()
        work_item_data = work_item.model_dump(exclude_unset=True)

        db_email_item = session.get(EmailProcessorTable, email_item_id)
        if not db_email_item:
            raise ValueError(f"Email Item ID {email_item_id} not found.")

        for key, value in work_item_data.items():
            logging.debug(f"Setting {key} to {value}")
            setattr(db_email_item, key, value)
        session.commit()
        session.refresh(db_email_item)
    return EmailProcessorModel(**db_email_item.__dict__)


def drop_email_item_by_id(email_item_id: int, session: Session, engine) -> int:
    """
    Deletes a work_item in the database
    """
    # TODO: Implement a cascade deletion for the work_item field in the environment table.
    with session(engine) as session:
        work_item = session.get(EmailProcessorTable, email_item_id)
        session.delete(work_item)
        session.commit()
        logging.info(f"User ID {email_item_id} deleted.")
    return 1


def query_email_item_by_email_item_id(
    email_item: str, session: Session, engine
) -> EmailProcessorModel:
    """
    Retrieves a work_item from the database by work_item_id
    """
    with session(engine) as session:
        email_item = (
            session.query(EmailProcessorTable)
            .filter(EmailProcessorTable.email_item_id == email_item)
            .first()
        )
    if not email_item:
        raise ValueError(f"Work Item {email_item} not found.")
    return EmailProcessorModel(**email_item.__dict__)


####################### Special Queries  ############################


def retrieve_unprocessed_email_items(
    engine, session: Session = Session
) -> List[EmailProcessorModel]:
    """
    Retrieves all email_items that require processing from the database
    """
    with session(engine) as session:
        email_items = (
            session.query(EmailProcessorTable)
            .filter(EmailProcessorTable.requires_processing == True)
            .all()
        )
    return [EmailProcessorModel(**email_item.__dict__) for email_item in email_items]


def fetch_item_item_ids(engine) -> List[str]:
    """
    Retrieve email items from the Fenrir database.
    """
    email_item_list = []
    email_items = query_all_email_items(engine=engine, session=Session)
    for email_item in email_items:
        email_item_list.append(email_item.email_item_id.__str__())
    return email_item_list
