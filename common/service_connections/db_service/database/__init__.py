"""
Database package for FTS application.

This package provides centralized database models and configuration,
using SQLAlchemy ORM with Alembic for migration management.

Usage:
    from common.service_connections.db_service.database import (
        Base,
        PageTable,
        EnvironmentTable,
        UserTable,
        IdentifierTable,
        EmailProcessorTable,
        AuthUserTable,
        SystemEnum,
        create_database_engine,
        get_database_session,
    )
"""

# Base class
from common.service_connections.db_service.database.base import Base

# Enums
from common.service_connections.db_service.database.enums import SystemEnum

# Table models
from common.service_connections.db_service.database.tables import (
    PageTable,
    EnvironmentTable,
    SystemUnderTestUserTable,
    IdentifierTable,
    EmailProcessorTable,
    AuthUserTable,
)

# Engine and session utilities
from common.service_connections.db_service.database.engine import (
    create_database_engine,
    create_session_factory,
    create_all_tables,
    drop_all_tables,
    initialize_database,
    get_database_url_from_config,
    get_database_session,
)


__all__ = [
    # Base
    "Base",
    # Enums
    "SystemEnum",
    # Tables
    "PageTable",
    "EnvironmentTable",
    "SystemUnderTestUserTable",
    "IdentifierTable",
    "EmailProcessorTable",
    "AuthUserTable",
    # Engine utilities
    "create_database_engine",
    "create_session_factory",
    "create_all_tables",
    "drop_all_tables",
    "initialize_database",
    "get_database_url_from_config",
    "get_database_session",
]
