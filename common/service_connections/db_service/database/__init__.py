"""
Database package for FTS application.

This package provides centralized database models and configuration,
using SQLAlchemy ORM with Alembic for migration management.
It includes base classes, enums, table models, and engine/session utilities.
It consolidates all database-related imports for easy access throughout
the application.
"""

# Base class
from common.service_connections.db_service.database.base import Base

# Enums
from common.service_connections.db_service.database.enums import SystemEnum

# Table models
from common.service_connections.db_service.database.tables import (
    # Existing tables
    PageTable,
    EnvironmentTable,
    SystemUnderTestUserTable,
    IdentifierTable,
    EmailProcessorTable,
    AuthUserTable,
    # New core tables
    AccountTable,
    AuthTokenTable,
    AuditLogTable,
    SystemUnderTestTable,
    PlanTable,
    SuiteTable,
    TestCaseTable,
    ActionChainTable,
    EntityTagTable,
    PurgeTable,
    RevokedTokenTable,
    # Junction tables
    AuthUserAccountAssociation,
    PageFenrirActionAssociation,
    PlanSuiteAssociation,
    SuiteTestCaseAssociation,
    SystemEnvironmentAssociation,
)
from common.service_connections.db_service.database.tables.account_tables.revoked_token import (
    RevokedTokenTable,
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
    # Existing tables
    "PageTable",
    "EnvironmentTable",
    "SystemUnderTestUserTable",
    "IdentifierTable",
    "EmailProcessorTable",
    "AuthUserTable",
    # New core tables
    "AccountTable",
    "AuthTokenTable",
    "AuditLogTable",
    "SystemUnderTestTable",
    "PlanTable",
    "SuiteTable",
    "TestCaseTable",
    "ActionChainTable",
    "EntityTagTable",
    "PurgeTable",
    "RevokedTokenTable",
    # Junction tables
    "AuthUserAccountAssociation",
    "PageFenrirActionAssociation",
    "PlanSuiteAssociation",
    "SuiteTestCaseAssociation",
    "SystemEnvironmentAssociation",
    # Engine utilities
    "create_database_engine",
    "create_session_factory",
    "create_all_tables",
    "drop_all_tables",
    "initialize_database",
    "get_database_url_from_config",
    "get_database_session",
]
