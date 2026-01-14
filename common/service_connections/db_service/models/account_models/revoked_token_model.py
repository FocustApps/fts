"""
Database model functions for revoked tokens.
"""

from datetime import UTC, datetime
from sqlalchemy.orm import Session
from sqlalchemy.engine import Engine

from common.service_connections.db_service.database.tables.account_tables.revoked_token import (
    RevokedTokenTable,
)
from common.service_connections.db_service.database.engine import (
    get_database_session as session,
)


def insert_revoked_token(jti: str, expires_at: datetime, engine: Engine):
    """
    Insert a revoked token into the database.

    Args:
        jti: JWT token ID
        expires_at: When the token would naturally expire
        engine: Database engine
    """
    with session(engine) as db_session:
        revoked_token = RevokedTokenTable(
            jti=jti,
            expires_at=expires_at,
        )
        db_session.add(revoked_token)
        db_session.commit()


def is_token_revoked(jti: str, db_session: Session, engine: Engine) -> bool:
    """
    Check if a token has been revoked.

    Args:
        jti: JWT token ID to check
        db_session: Active database session
        engine: Database engine

    Returns:
        True if token is revoked, False otherwise
    """
    revoked = (
        db_session.query(RevokedTokenTable).filter(RevokedTokenTable.jti == jti).first()
    )
    return revoked is not None


def delete_expired_revoked_tokens(engine: Engine) -> int:
    """
    Delete expired revoked tokens (cleanup job).

    Args:
        engine: Database engine

    Returns:
        Number of deleted records
    """
    with session(engine) as db_session:
        now = datetime.now(UTC)
        result = (
            db_session.query(RevokedTokenTable)
            .filter(RevokedTokenTable.expires_at < now)
            .delete()
        )
        db_session.commit()
        return result
