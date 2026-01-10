import logging
from datetime import datetime, timezone

from pydantic import BaseModel
from sqlalchemy import Engine

from common.service_connections.db_service.database import AuthUserTable


class AuthUserModel(BaseModel):
    """
    Schema for representing an authenticated user.

    Fields match AuthUserTable database schema.
    """

    auth_user_id: str | None = None
    email: str | None = None
    username: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    current_token: str | None = None
    token_expires_at: datetime | None = None
    is_active: bool = True
    is_admin: bool = False
    is_super_admin: bool = False
    multi_account_user: bool = False
    account_ids: str | None = None  # DEPRECATED: Use accounts relationship instead
    user_subscription_id: str | None = None
    created_at: datetime = datetime.now(tz=timezone.utc)
    last_login_at: datetime | None = None
    updated_at: datetime | None = None


def insert_auth_user(auth_user: AuthUserModel, session, engine: Engine) -> AuthUserModel:
    """
    Insert a new authenticated user into the database.

    Args:
        auth_user: User data to insert
        session: Database session maker (callable that creates sessions)
        engine: Database engine

    Returns:
        AuthUserModel with populated auth_user_id
    """
    if auth_user.auth_user_id:
        auth_user.auth_user_id = None
        logging.warning("AuthUser ID will only be set by the system")
    with session(engine) as db_session:
        auth_user.created_at = datetime.now()
        db_auth_user = AuthUserTable(**auth_user.model_dump())
        db_session.add(db_auth_user)
        db_session.commit()
        db_session.refresh(db_auth_user)
    return auth_user


def query_auth_user_by_username(username: str, session, engine: Engine) -> AuthUserModel:
    """
    Query an authenticated user by username.

    Args:
        username: Username to search for
        session: Database session maker (callable)
        engine: Database engine
    """
    with session(engine) as db_session:
        db_auth_user = (
            db_session.query(AuthUserTable).filter_by(username=username).first()
        )
        if db_auth_user:
            return AuthUserModel(**db_auth_user.__dict__)
        raise ValueError(f"AuthUser with username {username} not found.")


def query_auth_user_by_email(email: str, session, engine: Engine) -> AuthUserModel | None:
    """
    Query an authenticated user by email address.
    Returns None if user not found.

    Args:
        email: Email address to search for
        session: Database session maker (callable)
        engine: Database engine
    """
    with session(engine) as db_session:
        db_auth_user = db_session.query(AuthUserTable).filter_by(email=email).first()
        if db_auth_user:
            return AuthUserModel(**db_auth_user.__dict__)
        return None


def query_auth_user_by_id(user_id: int, session, engine: Engine) -> AuthUserModel:
    """
    Query an authenticated user by ID.

    Args:
        user_id: User ID to search for
        session: Database session maker (callable)
        engine: Database engine
    """
    with session(engine) as db_session:
        db_auth_user = (
            db_session.query(AuthUserTable).filter_by(auth_user_id=user_id).first()
        )
        if db_auth_user:
            return AuthUserModel(**db_auth_user.__dict__)
        raise ValueError(f"AuthUser with ID {user_id} not found.")


def deactivate_auth_user(user_id: int, session, engine: Engine) -> AuthUserModel:
    """
    Deactivate an authenticated user (soft delete).
    Sets is_active=False and clears token information.

    Args:
        user_id: User ID to deactivate
        session: Database session maker (callable)
        engine: Database engine
    """
    with session(engine) as db_session:
        db_auth_user = (
            db_session.query(AuthUserTable).filter_by(auth_user_id=user_id).first()
        )
        if not db_auth_user:
            raise ValueError(f"AuthUser with ID {user_id} not found.")

        # Deactivate user and clear token data
        db_auth_user.is_active = False
        db_auth_user.current_token = None
        db_auth_user.token_expires_at = None
        db_auth_user.updated_at = datetime.now(timezone.utc)

        db_session.commit()
        db_session.refresh(db_auth_user)
        return AuthUserModel(**db_auth_user.__dict__)


def query_all_auth_users(session, engine: Engine) -> list[AuthUserModel]:
    """
    Query all authenticated users.

    Args:
        session: Database session maker (callable)
        engine: Database engine
    """
    with session(engine) as db_session:
        db_auth_users = db_session.query(AuthUserTable).all()
        return [AuthUserModel(**db_auth_user.__dict__) for db_auth_user in db_auth_users]


def query_active_auth_users(session, engine: Engine) -> list[AuthUserModel]:
    """
    Query all active authenticated users (is_active=True).

    Args:
        session: Database session maker (callable)
        engine: Database engine
    """
    with session(engine) as db_session:
        db_auth_users = db_session.query(AuthUserTable).filter_by(is_active=True).all()
        return [AuthUserModel(**db_auth_user.__dict__) for db_auth_user in db_auth_users]


def check_email_exists(email: str, session, engine: Engine) -> bool:
    """
    Check if a user with the given email address already exists.
    Returns True if email exists, False otherwise.

    Args:
        email: Email address to check
        session: Database session maker (callable)
        engine: Database engine
    """
    with session(engine) as db_session:
        db_auth_user = db_session.query(AuthUserTable).filter_by(email=email).first()
        return db_auth_user is not None


def update_auth_user_by_id(
    user_id: int, auth_user: AuthUserModel, session, engine: Engine
) -> AuthUserModel:
    """
    Update an authenticated user by ID.

    Args:
        user_id: User ID to update
        auth_user: User data to update
        session: Database session maker (callable)
        engine: Database engine
    """
    with session(engine) as db_session:
        db_auth_user = (
            db_session.query(AuthUserTable).filter_by(auth_user_id=user_id).first()
        )
        if not db_auth_user:
            raise ValueError(f"AuthUser ID with {user_id} not found.")
        for key, value in auth_user.model_dump().items():
            setattr(db_auth_user, key, value)
        db_auth_user.updated_at = datetime.now(timezone.utc)
        db_session.commit()
        db_session.refresh(db_auth_user)
    return AuthUserModel(**db_auth_user.__dict__)


def drop_user_by_id(user_id: int, session, engine: Engine) -> int:
    """
    Delete an authenticated user by ID.

    Args:
        user_id: User ID to delete
        session: Database session maker (callable)
        engine: Database engine
    """
    with session(engine) as db_session:
        db_auth_user = (
            db_session.query(AuthUserTable).filter_by(auth_user_id=user_id).first()
        )
        if not db_auth_user:
            raise ValueError(f"AuthUser ID with {user_id} not found.")
        db_session.delete(db_auth_user)
        db_session.commit()
    return user_id
