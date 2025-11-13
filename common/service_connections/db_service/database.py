"""
Centralized database models and configuration for the FTS application.

This module serves as the single source of truth for all database table definitions,
using SQLAlchemy ORM with Alembic for migration management.
"""

from datetime import datetime, timezone
from enum import StrEnum
from typing import List, Optional

import sqlalchemy as sql
from sqlalchemy import create_engine
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    declarative_base,
    sessionmaker,
    relationship,
)


# Single declarative base for all models
Base = declarative_base()


class SystemEnum(StrEnum):
    """Enumeration of supported systems for email processing."""

    MINER_OCR = "miner_ocr"
    TRUE_SOURCE_OCR = "true_source_ocr"

    @staticmethod
    def get_valid_systems():
        return [system.value for system in SystemEnum]

    @staticmethod
    def is_valid_system(system: str):
        return system in SystemEnum.get_valid_systems()


from datetime import datetime
from typing import Dict, List, Optional
import sqlalchemy as sql
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, Session, sessionmaker
from sqlalchemy.dialects.postgresql import JSONB


class Base(DeclarativeBase):
    """Base class for all database models."""

    pass


# =====================================
# Core Database Models
# =====================================


class PageTable(Base):
    """Page model representing web pages for Selenium automation."""

    __tablename__ = "page"

    id: Mapped[int] = mapped_column(sql.Integer, primary_key=True)
    page_name: Mapped[str] = mapped_column(sql.String(96), unique=True, nullable=False)
    page_url: Mapped[str] = mapped_column(sql.String(1024), nullable=False)
    environments: Mapped[Dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        sql.DateTime, nullable=False, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        sql.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # One-to-many relationship with identifiers
    identifiers: Mapped[List["IdentifierTable"]] = relationship(
        "IdentifierTable", back_populates="page", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Page(id={self.id}, name='{self.page_name}', url='{self.page_url}')>"


class EnvironmentTable(Base):
    """Environment model representing deployment environments."""

    __tablename__ = "environment"

    id: Mapped[int] = mapped_column(sql.Integer, primary_key=True)
    name: Mapped[str] = mapped_column(sql.String(96), unique=True, nullable=False)
    environment_designation: Mapped[str] = mapped_column(sql.String(80), nullable=False)
    url: Mapped[str] = mapped_column(sql.String(512), nullable=False)
    api_url: Mapped[Optional[str]] = mapped_column(sql.String(512))
    status: Mapped[str] = mapped_column(sql.String(96), nullable=False)
    users: Mapped[List] = mapped_column(JSONB, default=list)
    created_at: Mapped[datetime] = mapped_column(
        sql.DateTime, nullable=False, default=datetime.utcnow
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(sql.DateTime)

    def __repr__(self) -> str:
        return f"<Environment(id={self.id}, name='{self.name}', designation='{self.environment_designation}')>"


class UserTable(Base):
    """User model representing test users for different environments."""

    __tablename__ = "user"

    id: Mapped[int] = mapped_column(sql.Integer, primary_key=True)
    username: Mapped[str] = mapped_column(sql.String(96), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(sql.String(96), nullable=False)
    password: Mapped[Optional[str]] = mapped_column(sql.String(96))
    secret_provider: Mapped[Optional[str]] = mapped_column(sql.String(96))
    secret_url: Mapped[Optional[str]] = mapped_column(sql.String(1024))
    secret_name: Mapped[Optional[str]] = mapped_column(sql.String(1024))
    environment_id: Mapped[int] = mapped_column(
        sql.Integer, sql.ForeignKey("environment.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        sql.DateTime, nullable=False, default=datetime.now(timezone.utc)
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(sql.DateTime)

    def __repr__(self) -> str:
        return f"<User(id={self.id}, username='{self.username}', email='{self.email}')>"


class IdentifierTable(Base):
    """Identifier model representing page element locators."""

    __tablename__ = "identifier"

    id: Mapped[int] = mapped_column(sql.Integer, primary_key=True)
    page_id: Mapped[int] = mapped_column(
        sql.Integer, sql.ForeignKey("page.id", ondelete="CASCADE"), nullable=False
    )
    element_name: Mapped[str] = mapped_column(sql.String(96), unique=True, nullable=False)
    locator_strategy: Mapped[str] = mapped_column(sql.String(96), nullable=False)
    locator_query: Mapped[str] = mapped_column(sql.String(96), nullable=False)
    action: Mapped[Optional[str]] = mapped_column(sql.String(96), nullable=True)
    environments: Mapped[List] = mapped_column(JSONB, default=list)
    created_at: Mapped[datetime] = mapped_column(
        sql.DateTime, nullable=False, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        sql.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Many-to-one relationship with page
    page: Mapped["PageTable"] = relationship("PageTable", back_populates="identifiers")

    def __repr__(self) -> str:
        return f"<Identifier(id={self.id}, element='{self.element_name}', page_id={self.page_id}, action='{self.action}')>"


class ActionTable(Base):
    """Action model representing actions to be performed on page elements."""

    __tablename__ = "action"

    id: Mapped[int] = mapped_column(sql.Integer, primary_key=True)
    action_method: Mapped[Optional[str]] = mapped_column(sql.String(255))
    action_documentation: Mapped[Optional[str]] = mapped_column(sql.String(1024))
    created_at: Mapped[datetime] = mapped_column(
        sql.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        sql.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    def __repr__(self) -> str:
        return f"<Action(id={self.id}, method='{self.action_method}', created_at={self.created_at})>"


class EmailProcessorTable(Base):
    """Email processor model for handling email automation tasks."""

    __tablename__ = "emailProcessorTable"

    id: Mapped[int] = mapped_column(sql.Integer, primary_key=True)
    email_item_id: Mapped[int] = mapped_column(sql.Integer, unique=True, nullable=False)
    multi_item_email_ids: Mapped[Optional[List]] = mapped_column(JSONB)
    multi_email_flag: Mapped[bool] = mapped_column(sql.Boolean, default=False)
    multi_attachment_flag: Mapped[bool] = mapped_column(sql.Boolean, default=False)
    system: Mapped[Optional[str]] = mapped_column(sql.String(96))
    test_name: Mapped[Optional[str]] = mapped_column(sql.String(255))
    requires_processing: Mapped[bool] = mapped_column(sql.Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        sql.DateTime, nullable=False, default=datetime.utcnow
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(sql.DateTime)
    last_processed_at: Mapped[Optional[datetime]] = mapped_column(sql.DateTime)

    def __repr__(self) -> str:
        return f"<EmailProcessor(id={self.id}, email_item_id={self.email_item_id}, system='{self.system}')>"


class AuthUserTable(Base):
    """Authentication users table for system access control."""

    __tablename__ = "auth_users"

    id: Mapped[int] = mapped_column(sql.Integer, primary_key=True)
    email: Mapped[str] = mapped_column(sql.String(255), unique=True, nullable=False)
    username: Mapped[Optional[str]] = mapped_column(sql.String(96))
    current_token: Mapped[Optional[str]] = mapped_column(sql.String(64))
    token_expires_at: Mapped[Optional[datetime]] = mapped_column(sql.DateTime)
    is_active: Mapped[bool] = mapped_column(sql.Boolean, default=True, nullable=False)
    is_admin: Mapped[bool] = mapped_column(sql.Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        sql.DateTime, nullable=False, default=datetime.utcnow
    )
    last_login_at: Mapped[Optional[datetime]] = mapped_column(sql.DateTime)
    updated_at: Mapped[Optional[datetime]] = mapped_column(sql.DateTime)

    def __repr__(self) -> str:
        return (
            f"<AuthUser(id={self.id}, email='{self.email}', is_active={self.is_active})>"
        )

    def is_token_valid(self) -> bool:
        """Check if the current token is valid and not expired."""
        if not self.current_token or not self.token_expires_at:
            return False
        return datetime.now(timezone.utc) < self.token_expires_at

    def update_last_login(self) -> None:
        """Update the last login timestamp to now."""
        self.last_login_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)


# =====================================
# Database Engine and Session Management
# =====================================


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


# =====================================
# Database Initialization
# =====================================


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


# =====================================
# Migration Utilities
# =====================================


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


from contextlib import contextmanager
from typing import Generator


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


# Export commonly used items
__all__ = [
    "Base",
    "PageTable",
    "EnvironmentTable",
    "UserTable",
    "ActionTable",
    "IdentifierTable",
    "EmailProcessorTable",
    "AuthUserTable",
    "create_database_engine",
    "create_session_factory",
    "create_all_tables",
    "drop_all_tables",
    "initialize_database",
    "get_database_url_from_config",
    "get_database_session",
]
