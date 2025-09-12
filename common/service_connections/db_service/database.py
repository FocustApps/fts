"""
Centralized database configuration and base model for Fenrir.

This module provides:
1. Single source of truth for all database models
2. Base class for all SQLAlchemy models
3. Database initialization and migration support
4. Centralized engine and session management
"""

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
    identifiers: Mapped[Dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        sql.DateTime, nullable=False, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        sql.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
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
        sql.DateTime, nullable=False, default=datetime.utcnow
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
    environments: Mapped[List] = mapped_column(JSONB, default=list)
    created_at: Mapped[datetime] = mapped_column(
        sql.DateTime, nullable=False, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        sql.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    def __repr__(self) -> str:
        return f"<Identifier(id={self.id}, element='{self.element_name}', page_id={self.page_id})>"


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

    if config.database_type.lower() == "postgresql":
        return f"postgresql://{config.postgres_user}:{config.postgres_password}@{config.db_host}:{config.db_port}/{config.postgres_db}"
    elif config.database_type.lower() == "sqlite":
        return f"sqlite:///{config.database_url}"
    else:
        raise ValueError(f"Unsupported database type: {config.database_type}")


# Export commonly used items
__all__ = [
    "Base",
    "PageTable",
    "EnvironmentTable",
    "UserTable",
    "IdentifierTable",
    "EmailProcessorTable",
    "create_database_engine",
    "create_session_factory",
    "create_all_tables",
    "drop_all_tables",
    "initialize_database",
    "get_database_url_from_config",
]
