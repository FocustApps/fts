from typing import List
from datetime import datetime
import logging

from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import Engine

# Import centralized database components
from common.service_connections.db_service.database import SystemUnderTestUserTable
from common.service_connections.db_service.database.engine import (
    get_database_session as session,
)


class UserModel(BaseModel):
    """
    Schema for representing a test user.
    Fields match SystemUnderTestUserTable database schema.

    Fields:
    - sut_user_id: int | None - Primary key
    - account_id: str | None - Account reference
    - sut_id: str | None - System under test reference
    - username: str | None - Test user username
    - email: str | None - Test user email
    - password: str | None - Plain password (if not using secret provider)
    - secret_provider: str | None - Cloud secret provider (AWS, Azure)
    - secret_url: str | None - URL to secret in cloud provider
    - secret_name: str | None - Name of secret in cloud provider
    - environment_id: str | None - Environment reference
    - is_active: bool - Soft delete flag
    - deactivated_at: datetime | None - Soft delete timestamp
    - deactivated_by_user_id: str | None - Who deactivated
    - created_at: datetime | None - Creation timestamp
    - updated_at: datetime | None - Update timestamp
    """

    sut_user_id: int | None = None
    account_id: str | None = None
    sut_id: str | None = None
    username: str | None = None
    email: str | None = None
    password: str | None = None
    secret_provider: str | None = None
    secret_url: str | None = None
    secret_name: str | None = None
    environment_id: str | None = None
    is_active: bool = True
    deactivated_at: datetime | None = None
    deactivated_by_user_id: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


############# User Queries #############


def insert_user(user: UserModel, engine: Engine) -> int:
    """
    Creates a user in the database
    """
    if user.sut_user_id:
        user.sut_user_id = None
        logging.warning("User ID will only be set by the system")
    with session(engine) as db_session:
        user.created_at = datetime.now()
        db_user = SystemUnderTestUserTable(**user.model_dump())
        db_session.add(db_user)
        db_session.commit()
        db_session.refresh(db_user)
    return db_user.sut_user_id


def query_user_by_username(username: str, session: Session, engine: Engine) -> UserModel:
    """
    Retrieves a user from the database by username
    """
    user = (
        session.query(SystemUnderTestUserTable)
        .filter(SystemUnderTestUserTable.username == username)
        .first()
    )
    if not user:
        raise ValueError(f"Username {username} not found.")
    return UserModel(**user.__dict__)


def query_user_by_id(user_id: int, session: Session, engine: Engine) -> UserModel:
    """
    Retrieves a user from the database by id
    """
    user = (
        session.query(SystemUnderTestUserTable)
        .filter(SystemUnderTestUserTable.sut_user_id == user_id)
        .first()
    )
    if not user:
        raise ValueError(f"User ID with {user_id} not found.")
    return UserModel(**user.__dict__)


def query_all_users(session: Session, engine: Engine) -> List[SystemUnderTestUserTable]:
    """
    Retrieves all users from the database
    """
    users = session.query(SystemUnderTestUserTable).all()
    return [UserModel(**user.__dict__) for user in users]


def update_user_by_id(user_id: int, user: UserModel, engine: Engine) -> bool:
    """
    Updates a user in the database
    """
    with session(engine) as db_session:
        db_user = db_session.get(SystemUnderTestUserTable, user_id)
        if not db_user:
            raise ValueError(f"User ID {user_id} not found.")
        user.updated_at = datetime.now()
        user_data = user.model_dump(exclude_unset=True)
        for key, value in user_data.items():
            logging.debug(f"Setting {key} to {value}")
            setattr(db_user, key, value)
        db_session.commit()
    return True


def drop_user_by_id(user_id: int, engine: Engine) -> bool:
    """
    Deletes a user in the database
    """
    # TODO: Implement a cascade deletion for the user field in the environment table.
    with session(engine) as db_session:
        user = db_session.get(SystemUnderTestUserTable, user_id)
        db_session.delete(user)
        db_session.commit()
        logging.info(f"User ID {user_id} deleted.")
    return True
