import logging
from typing import List
from datetime import datetime

from pydantic import BaseModel
from sqlalchemy import Engine
from sqlalchemy.orm import Session

# Import centralized database components
from common.service_connections.db_service.database import (
    EnvironmentTable,
    SystemUnderTestUserTable,
)
from common.service_connections.db_service.models.user_model import UserModel


class EnvironmentModel(BaseModel):
    """
    Schema for representing an environment.
    Fields match EnvironmentTable database schema.

    Fields:
    - environment_id: str | None - UUID primary key
    - environment_name: str | None - Unique environment name
    - environment_designation: str | None - Environment designation (dev, qa, staging, prod)
    - environment_base_url: str | None - Base URL for the environment
    - api_base_url: str | None - API base URL
    - environment_status: str | None - Environment status
    - users_in_environment: List | None - JSONB list of users
    - is_active: bool - Soft delete flag
    - deactivated_at: datetime | None - Soft delete timestamp
    - deactivated_by_user_id: str | None - Who deactivated
    - created_at: datetime | None - Creation timestamp
    - updated_at: datetime | None - Update timestamp
    """

    environment_id: str | None = None
    environment_name: str | None = None
    environment_designation: str | None = None
    environment_base_url: str | None = None
    api_base_url: str | None = None
    environment_status: str | None = None
    users_in_environment: List | None = None
    is_active: bool = True
    deactivated_at: datetime | None = None
    deactivated_by_user_id: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


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
    with session() as session:
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
    with session() as session:
        return (
            session.query(EnvironmentTable).filter(EnvironmentTable.name == name).first()
        )


def query_environment_by_id(
    environment_id: int, session: Session, engine: Engine
) -> EnvironmentModel:
    """
    Retrieves an environment from the database by id
    """
    with session() as session:
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
                        **session.query(SystemUnderTestUserTable)
                        .filter(SystemUnderTestUserTable.sut_user_id == user[0])
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
    with session() as session:
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
    with session() as session:
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
    with session() as session:
        environment = session.get(EnvironmentTable, environment_id)
        session.delete(environment)
        session.commit()
        logging.info(f"Environment ID {environment_id} deleted.")
    return 1


def deactivate_environment_by_id(
    environment_id: int, session: Session, engine: Engine
) -> EnvironmentModel:
    """
    Soft delete an environment by setting status=False (deactivated).

    Args:
        environment_id: Environment ID to deactivate
        session: Database session context manager
        engine: Database engine

    Returns:
        Updated EnvironmentModel with status=False

    Raises:
        ValueError: If environment not found
    """
    with session() as db_session:
        environment = db_session.get(EnvironmentTable, environment_id)
        if not environment:
            raise ValueError(f"Environment ID {environment_id} not found.")

        environment.status = False
        environment.updated_at = datetime.now()

        db_session.commit()
        db_session.refresh(environment)

        logging.info(f"Environment ID {environment_id} deactivated (status=False).")

    return EnvironmentModel(**environment.__dict__)


def query_active_environments_by_account(
    account_id: str, session: Session, engine: Engine
) -> List[EnvironmentModel]:
    """
    Query all active environments for a specific account.

    NOTE: EnvironmentTable may not have account_id field in current schema.
    This function assumes account relationship through system_under_test or
    other linking table. Adjust query logic based on actual schema.

    Args:
        account_id: Account ID to filter by
        session: Database session context manager
        engine: Database engine

    Returns:
        List of active EnvironmentModel instances

    TODO: Verify EnvironmentTable schema has account_id or proper relationship
    """
    with session() as db_session:
        # NOTE: This query assumes EnvironmentTable has account_id field
        # If not present, this will need to join through SystemUnderTestTable
        # or other linking table to filter by account
        envs = (
            db_session.query(EnvironmentTable)
            .filter(EnvironmentTable.status == True)
            .all()
        )

        # TODO: Add account filtering when schema relationship is confirmed
        # .filter(EnvironmentTable.account_id == account_id)

        return [EnvironmentModel(**env.__dict__) for env in envs]


def query_environment_systems(
    environment_id: int, session: Session, engine: Engine
) -> List[dict]:
    """
    Query all systems under test associated with an environment.

    NOTE: This assumes a relationship exists between EnvironmentTable and
    SystemUnderTestTable. Adjust join logic based on actual schema.

    Args:
        environment_id: Environment ID to query systems for
        session: Database session context manager
        engine: Database engine

    Returns:
        List of dicts with system information (sut_id, sut_name, account_id)

    TODO: Verify actual relationship between Environment and SystemUnderTest tables
    """
    with session() as db_session:
        # Verify environment exists
        environment = db_session.get(EnvironmentTable, environment_id)
        if not environment:
            raise ValueError(f"Environment ID {environment_id} not found.")

        # TODO: Implement actual query once schema relationship is confirmed
        # This is a placeholder that needs the proper join through
        # SystemUnderTestTable or association table

        # Example query structure (adjust based on actual schema):
        # from common.service_connections.db_service.database import SystemUnderTestTable
        #
        # systems = (
        #     db_session.query(SystemUnderTestTable)
        #     .filter(SystemUnderTestTable.environment_id == environment_id)
        #     .all()
        # )
        #
        # return [
        #     {
        #         'sut_id': system.sut_id,
        #         'sut_name': system.sut_name,
        #         'account_id': system.account_id
        #     }
        #     for system in systems
        # ]

        logging.warning(
            f"query_environment_systems() not fully implemented. "
            f"Schema relationship between Environment and SystemUnderTest needs verification."
        )

        return []
