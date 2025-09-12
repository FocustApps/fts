import logging
from typing import List, Optional
from datetime import datetime

from pydantic import BaseModel
from sqlalchemy import Engine
from sqlalchemy.orm import Session

# Import centralized database components
from .database import EnvironmentTable, UserTable
from .user_model import UserModel


class EnvironmentModel(BaseModel):
    """
    Schema for representing an environment.

    Fields:
    - name: str | None, the name of the environment.
    - environment_designation: EnvironmentEnum | None, the designation of the environment.
    - url: str | None, the URL of the environment.
    - status: bool | None, the status of the environment.
    - users: List[UserSchema] | None, the list of users associated with the environment.
    - created_at: str | None, the creation date of the environment.
    - updated_at: str | None, the update date of the environment.
    """

    id: int | None = None
    name: str | None = None
    environment_designation: str | None = None
    url: str | None = None
    api_url: str | None = None
    status: bool | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    users: List | None = None


############# Environment Queries #############


def insert_environment(
    environment: EnvironmentModel, session: Session, engine: Engine
) -> EnvironmentModel:
    """
    Creates an environment in the database
    """
    if environment.id:
        environment.id = None
        logging.error("Environment ID will only be set by the system")
    if not environment.users:
        environment.users = []
    with session(engine) as session:
        environment.created_at = datetime.now()
        db_environment = EnvironmentTable(**environment.model_dump())
        session.add(db_environment)
        session.commit()
        session.refresh(db_environment)
    return EnvironmentModel(**db_environment.__dict__)


def query_environment_by_name(
    name: str, session: Session, engine: Engine
) -> EnvironmentTable:
    """
    Retrieves an environment from the database by name
    """
    with session(engine) as session:
        return (
            session.query(EnvironmentTable).filter(EnvironmentTable.name == name).first()
        )


def query_environment_by_id(
    environment_id: int, session: Session, engine: Engine
) -> EnvironmentModel:
    """
    Retrieves an environment from the database by id
    """
    with session(engine) as session:
        env = (
            session.query(EnvironmentTable)
            .filter(EnvironmentTable.id == environment_id)
            .first()
        )
        if not env:
            raise ValueError(f"Environment ID {environment_id} not found.")
        if env.users:
            try:
                env.users = [
                    UserModel(
                        **session.query(UserTable)
                        .filter(UserTable.id == user[0])
                        .first()
                        .__dict__
                    )
                    for user in env.users
                ]
            except AttributeError:
                env.users = []
    return EnvironmentModel(**env.__dict__)


def query_all_environments(session: Session, engine) -> List[EnvironmentModel]:
    """
    Retrieves all environments from the database
    """
    with session(engine) as session:
        envs = session.query(EnvironmentTable).all()
        return [EnvironmentModel(**env.__dict__) for env in envs if env.status]


def update_environment_by_id(
    environment_id: int,
    environment: EnvironmentModel,
    session: Session,
    engine: Engine,
) -> EnvironmentModel:
    """
    Updates an environment in the database
    """
    with session(engine) as session:
        db_environment = session.get(EnvironmentTable, environment_id)
        if not db_environment:
            raise ValueError(f"Environment ID {environment_id} not found.")
        environment.updated_at = datetime.now()
        env_data = environment.model_dump(exclude_unset=True)
        db_environment.users = db_environment.users or []
        if env_data.get("users"):
            env_data["users"] = [
                f"{user["id"]}:{user["username"]}" for user in env_data["users"]
            ] + db_environment.users
        for key, value in env_data.items():
            setattr(db_environment, key, value)
        session.commit()
        session.refresh(db_environment)
    return EnvironmentModel(**db_environment.__dict__)


def drop_environment_by_id(environment_id: int, session: Session, engine: Engine) -> int:
    """
    Deletes an environment in the database
    """
    with session(engine) as session:
        environment = session.get(EnvironmentTable, environment_id)
        session.delete(environment)
        session.commit()
        logging.info(f"Environment ID {environment_id} deleted.")
    return 1
