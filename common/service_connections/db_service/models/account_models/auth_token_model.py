"""
Database model functions for JWT refresh tokens.
"""

from datetime import datetime, timedelta
from typing import Optional, List
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy.engine import Engine

from common.service_connections.db_service.database.tables.account_tables.auth_token import (
    AuthTokenTable,
)
from common.service_connections.db_service.database.engine import (
    get_database_session as session,
)


class AuthTokenModel(BaseModel):
    """
    Pydantic model for JWT refresh token with rotation tracking.

    Fields match AuthTokenTable database schema.
    """

    token_id: str | None = None
    auth_user_id: str
    refresh_token_hash: str  # Bcrypt hash of refresh token
    access_token_jti: str  # JWT ID of corresponding access token
    token_family_id: str  # UUID identifying rotation chain
    previous_token_id: str | None = None  # Previous token in rotation chain
    token_expires_at: datetime
    device_info: str | None = None
    ip_address: str | None = None
    last_used_at: datetime | None = None
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    revoked_at: datetime | None = None


def insert_auth_token(token: AuthTokenModel, engine: Engine) -> str:
    """
    Insert a new refresh token into the database.

    Args:
        token: Token data to insert
        engine: Database engine

    Returns:
        Token ID string
    """
    with session(engine) as db_session:
        db_token = AuthTokenTable(**token.model_dump(exclude={"token_id"}))
        db_session.add(db_token)
        db_session.commit()
        db_session.refresh(db_token)
        return db_token.token_id


def query_auth_token_by_hash(
    refresh_token_hash: str, db_session: Session, engine: Engine
) -> Optional[AuthTokenModel]:
    """
    Query a refresh token by its bcrypt hash.

    Args:
        refresh_token_hash: Bcrypt hash to search for
        db_session: Active database session
        engine: Database engine

    Returns:
        AuthTokenModel if found, None otherwise
    """
    db_token = (
        db_session.query(AuthTokenTable)
        .filter(AuthTokenTable.refresh_token_hash == refresh_token_hash)
        .first()
    )
    if db_token:
        return AuthTokenModel(**db_token.__dict__)
    return None


def query_auth_token_by_id(
    token_id: str, db_session: Session, engine: Engine
) -> Optional[AuthTokenModel]:
    """
    Query a refresh token by its ID.

    Args:
        token_id: Token ID to search for
        db_session: Active database session
        engine: Database engine

    Returns:
        AuthTokenModel if found, None otherwise
    """
    db_token = db_session.get(AuthTokenTable, token_id)
    if db_token:
        return AuthTokenModel(**db_token.__dict__)
    return None


def query_active_tokens_by_user(
    user_id: str, db_session: Session, engine: Engine
) -> List[AuthTokenModel]:
    """
    Query all active refresh tokens for a user (for device management UI).

    Args:
        user_id: User ID to search for
        db_session: Active database session
        engine: Database engine

    Returns:
        List of active AuthTokenModel objects
    """
    db_tokens = (
        db_session.query(AuthTokenTable)
        .filter(
            AuthTokenTable.auth_user_id == user_id,
            AuthTokenTable.is_active == True,
        )
        .order_by(AuthTokenTable.created_at.desc())
        .all()
    )
    return [AuthTokenModel(**token.__dict__) for token in db_tokens]


def query_tokens_by_family(
    family_id: str, db_session: Session, engine: Engine
) -> List[AuthTokenModel]:
    """
    Query all tokens in a rotation family (for reuse detection).

    Args:
        family_id: Token family ID
        db_session: Active database session
        engine: Database engine

    Returns:
        List of AuthTokenModel objects in the family
    """
    db_tokens = (
        db_session.query(AuthTokenTable)
        .filter(AuthTokenTable.token_family_id == family_id)
        .order_by(AuthTokenTable.created_at.desc())
        .all()
    )
    return [AuthTokenModel(**token.__dict__) for token in db_tokens]


def update_token_inactive(token_id: str, engine: Engine) -> bool:
    """
    Mark a token as inactive (after successful rotation or logout).

    Args:
        token_id: Token ID to deactivate
        engine: Database engine

    Returns:
        True if successful
    """
    with session(engine) as db_session:
        db_token = db_session.get(AuthTokenTable, token_id)
        if db_token:
            db_token.is_active = False
            db_token.revoked_at = datetime.utcnow()
            db_session.commit()
            return True
        return False


def update_all_user_tokens_inactive(user_id: str, engine: Engine) -> int:
    """
    Mark all tokens for a user as inactive (logout all devices).

    Args:
        user_id: User ID
        engine: Database engine

    Returns:
        Number of tokens deactivated
    """
    with session(engine) as db_session:
        now = datetime.utcnow()
        result = (
            db_session.query(AuthTokenTable)
            .filter(
                AuthTokenTable.auth_user_id == user_id,
                AuthTokenTable.is_active == True,
            )
            .update(
                {
                    "is_active": False,
                    "revoked_at": now,
                },
                synchronize_session=False,
            )
        )
        db_session.commit()
        return result


def update_all_family_tokens_inactive(family_id: str, engine: Engine) -> int:
    """
    Mark all tokens in a family as inactive (token reuse detected).

    Args:
        family_id: Token family ID
        engine: Database engine

    Returns:
        Number of tokens deactivated
    """
    with session(engine) as db_session:
        now = datetime.utcnow()
        result = (
            db_session.query(AuthTokenTable)
            .filter(
                AuthTokenTable.token_family_id == family_id,
                AuthTokenTable.is_active == True,
            )
            .update(
                {
                    "is_active": False,
                    "revoked_at": now,
                },
                synchronize_session=False,
            )
        )
        db_session.commit()
        return result


def update_token_last_used(token_id: str, engine: Engine) -> bool:
    """
    Update the last_used_at timestamp for a token (on each refresh).

    Args:
        token_id: Token ID to update
        engine: Database engine

    Returns:
        True if successful
    """
    with session(engine) as db_session:
        db_token = db_session.get(AuthTokenTable, token_id)
        if db_token:
            db_token.last_used_at = datetime.utcnow()
            db_session.commit()
            return True
        return False


def delete_inactive_tokens_older_than(days: int, engine: Engine) -> int:
    """
    Delete inactive tokens older than specified days (cleanup job).

    Args:
        days: Age threshold in days
        engine: Database engine

    Returns:
        Number of tokens deleted
    """
    with session(engine) as db_session:
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        result = (
            db_session.query(AuthTokenTable)
            .filter(
                AuthTokenTable.is_active == False,
                AuthTokenTable.revoked_at < cutoff_date,
            )
            .delete()
        )
        db_session.commit()
        return result
