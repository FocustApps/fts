"""
Backward compatibility module for database imports.

This module re-exports all components from the new database package structure.
All definitions have been moved to the database/ directory for better organization.

New imports should use:
    from common.service_connections.db_service.database import (
        Base, PageTable, get_database_session, ...
    )

This file is maintained for backward compatibility with existing code.
"""

# Re-export everything from the new package structure
from common.service_connections.db_service.database import (
    # Base
    Base,
    # Enums
    SystemEnum,
    # Existing tables
    PageTable,
    EnvironmentTable,
    TestEnvUserAccountsTable,
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
    # Junction tables
    AuthUserAccountAssociation,
    PageFenrirActionAssociation,
    PlanSuiteAssociation,
    SuiteTestCaseAssociation,
    SystemEnvironmentAssociation,
    # Engine utilities
    create_database_engine,
    create_session_factory,
    create_all_tables,
    drop_all_tables,
    initialize_database,
    get_database_url_from_config,
    get_database_session,
)


__all__ = [
    "Base",
    "SystemEnum",
    # Existing tables
    "PageTable",
    "EnvironmentTable",
    "TestEnvUserAccountsTable",
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
