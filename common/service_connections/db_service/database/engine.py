"""
Database engine and session management utilities.

This module provides functions for creating database engines, session factories,
and managing database connections.
"""

from contextlib import contextmanager
from typing import Generator, Optional

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from common.service_connections.db_service.database.base import Base


def create_database_engine(database_url: str, echo: bool = False) -> Engine:
    """
    Create and configure database engine.

    Args:
        database_url: Database connection URL
        echo: Whether to echo SQL statements for debugging

    Returns:
        Configured SQLAlchemy engine
    """
    return create_engine(
        database_url,
        echo=echo,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,  # Validate connections before use
        pool_recycle=3600,  # Recycle connections every hour
    )


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    """
    Create session factory for database operations.

    Args:
        engine: SQLAlchemy engine

    Returns:
        Session factory
    """
    return sessionmaker(bind=engine, expire_on_commit=False)


def create_all_tables(engine: Engine) -> None:
    """
    Create all database tables.

    Args:
        engine: SQLAlchemy engine
    """
    Base.metadata.create_all(engine)


def drop_all_tables(engine: Engine) -> None:
    """
    Drop all database tables (use with caution!).

    Args:
        engine: SQLAlchemy engine
    """
    Base.metadata.drop_all(engine)


def initialize_database(
    database_url: str, echo: bool = False
) -> tuple[Engine, sessionmaker[Session]]:
    """
    Initialize database with tables and return engine and session factory.

    Args:
        database_url: Database connection URL
        echo: Whether to echo SQL statements for debugging

    Returns:
        Tuple of (engine, session_factory)
    """
    engine = create_database_engine(database_url, echo=echo)
    create_all_tables(engine)
    session_factory = create_session_factory(engine)

    return engine, session_factory


def get_database_url_from_config() -> str:
    """
    Get database URL from environment configuration.

    Returns:
        Database connection URL
    """
    # Import here to avoid circular imports
    from app.config import get_config

    config = get_config()

    if config.database_type.lower() in ["postgresql", "postgres"]:
        return f"postgresql://{config.postgres_user}:{config.postgres_password}@{config.db_host}:{config.db_port}/{config.postgres_db}"
    elif config.database_type.lower() == "sqlite":
        return f"sqlite:///{config.database_url}"
    else:
        raise ValueError(f"Unsupported database type: {config.database_type}")


# =====================================
# Session Context Manager
# =====================================

# Global session factory - will be initialized when module is imported
_session_factory: Optional[sessionmaker[Session]] = None


def _initialize_session_factory() -> sessionmaker[Session]:
    """Initialize the global session factory using the database URL from config."""
    global _session_factory
    if _session_factory is None:
        database_url = get_database_url_from_config()
        engine = create_database_engine(database_url)
        _session_factory = create_session_factory(engine)
    return _session_factory


@contextmanager
def get_database_session() -> Generator[Session, None, None]:
    """
    Context manager for database sessions.

    Provides a database session with automatic transaction management.
    Commits on success, rolls back on exception.

    Yields:
        Database session

    Example:
        with get_database_session() as session:
            user = session.query(AuthUserTable).filter_by(email="test@example.com").first()
    """
    session_factory = _initialize_session_factory()
    session = session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


__all__ = [
    "create_database_engine",
    "create_session_factory",
    "create_all_tables",
    "drop_all_tables",
    "initialize_database",
    "get_database_url_from_config",
    "get_database_session",
]
