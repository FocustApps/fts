from typing import List
from datetime import datetime
import logging

from pydantic import BaseModel
from sqlalchemy.orm import Session

# Import centralized database components
from common.service_connections.db_service.database import SystemUnderTestUserTable


class UserModel(BaseModel):
    """
    Schema for representing a user.

    Fields:
    - id: int | None, the ID of the user.
    - username: str | None, the username of the user.
    - email: str | None, the email of the user.
    - password: str | None, the password of the user.
    - cloud_provider: CloudProviderEnum | None, the cloud provider of the user.
    - secret_url: str | None, the secret URL of the user.
    - environment_id: int | None, the ID of the environment associated with the user.
    - created_at: str | None, the creation date of the user.
    - updated_at: str | None, the update date of the user.
    """

    id: int | None = None
    username: str | None = None
    email: str | None = None
    password: str | None = None
    secret_provider: str | None = None
    secret_url: str | None = None
    secret_name: str | None = None
    environment_id: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


############# User Queries #############


def insert_user(user: UserModel, session: Session, engine) -> UserModel:
    """
    Creates a user in the database
    """
    if user.id:
        user.id = None
        logging.warning("User ID will only be set by the system")
    with session(engine) as session:
        user.created_at = datetime.now()
        db_user = SystemUnderTestUserTable(**user.model_dump())
        session.add(db_user)
        session.commit()
        session.refresh(db_user)
    return UserModel(**db_user.__dict__)


def query_user_by_username(username: str, session: Session, engine) -> UserModel:
    """
    Retrieves a user from the database by username
    """
    with session(engine) as session:
        user = (
            session.query(SystemUnderTestUserTable)
            .filter(SystemUnderTestUserTable.username == username)
            .first()
        )
    if not user:
        raise ValueError(f"Username {username} not found.")
    unpacked_user = UserModel(**user.__dict__)
    return unpacked_user


def query_user_by_id(user_id: int, session: Session, engine) -> UserModel:
    """
    Retrieves a user from the database by id
    """
    with session(engine) as session:
        user = (
            session.query(SystemUnderTestUserTable)
            .filter(SystemUnderTestUserTable.sut_user_id == user_id)
            .first()
        )
    if not user:
        raise ValueError(f"User ID with {user_id} not found.")
    unpacked_user = UserModel(**user.__dict__)
    return unpacked_user


def query_all_users(session: Session, engine) -> List[SystemUnderTestUserTable]:
    """
    Retrieves all users from the database
    """
    with session(engine) as session:
        users = session.query(SystemUnderTestUserTable).all()
        return [UserModel(**user.__dict__) for user in users]


def update_user_by_id(
    user_id: int, user: UserModel, session: Session, engine
) -> UserModel:
    """
    Updates a user in the database
    """
    with session(engine) as session:
        db_user = session.get(SystemUnderTestUserTable, user_id)
        if not db_user:
            raise ValueError(f"Environment ID {user_id} not found.")
        user.updated_at = datetime.now()
        user_data = user.model_dump(exclude_unset=True)
        for key, value in user_data.items():
            logging.debug(f"Setting {key} to {value}")
            setattr(db_user, key, value)
        session.commit()
        session.refresh(db_user)
    return UserModel(**db_user.__dict__)


def drop_user_by_id(user_id: int, session: Session, engine) -> int:
    """
    Deletes a user in the database
    """
    # TODO: Implement a cascade deletion for the user field in the environment table.
    with session(engine) as session:
        user = session.get(SystemUnderTestUserTable, user_id)
        session.delete(user)
        session.commit()
        logging.info(f"User ID {user_id} deleted.")
    return 1
