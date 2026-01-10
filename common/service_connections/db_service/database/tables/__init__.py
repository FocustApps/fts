"""
Database table models.

This package contains all SQLAlchemy ORM table definitions.
"""

# Existing tables
from common.service_connections.db_service.database.tables.action_tables.user_interface_action.page import (
    PageTable,
)
from common.service_connections.db_service.database.tables.environment import (
    EnvironmentTable,
)
from common.service_connections.db_service.database.tables.system_under_test_user import (
    SystemUnderTestUserTable,
)
from common.service_connections.db_service.database.tables.action_tables.user_interface_action.identifier import (
    IdentifierTable,
)
from common.service_connections.db_service.database.tables.action_tables.user_interface_action.fenrir_actions import (
    FenrirActionsTable,
)
from common.service_connections.db_service.database.tables.email_processor import (
    EmailProcessorTable,
)
from common.service_connections.db_service.database.tables.account_tables.auth_user import (
    AuthUserTable,
)

# New core tables
from common.service_connections.db_service.database.tables.account_tables.account import (
    AccountTable,
)
from common.service_connections.db_service.database.tables.account_tables.auth_token import (
    AuthTokenTable,
)
from common.service_connections.db_service.database.tables.account_tables.revoked_token import (
    RevokedTokenTable,
)
from common.service_connections.db_service.database.tables.audit_log import AuditLogTable
from common.service_connections.db_service.database.tables.system_under_test import (
    SystemUnderTestTable,
)
from common.service_connections.db_service.database.tables.plan import PlanTable
from common.service_connections.db_service.database.tables.suite import SuiteTable
from common.service_connections.db_service.database.tables.test_case import TestCaseTable
from common.service_connections.db_service.database.tables.action_chain import (
    ActionChainTable,
)
from common.service_connections.db_service.database.tables.entity_tag import (
    EntityTagTable,
)
from common.service_connections.db_service.database.tables.purge_table import (
    PurgeTable,
)

# Junction tables
from common.service_connections.db_service.database.tables.account_tables.auth_user_account_association import (
    AuthUserAccountAssociation,
)
from common.service_connections.db_service.database.tables.action_tables.user_interface_action.page_fenrir_action_association import (
    PageFenrirActionAssociation,
)
from common.service_connections.db_service.database.tables.plan_suite_association import (
    PlanSuiteAssociation,
)
from common.service_connections.db_service.database.tables.suite_test_case_association import (
    SuiteTestCaseAssociation,
)
from common.service_connections.db_service.database.tables.system_environment_association import (
    SystemEnvironmentAssociation,
)


__all__ = [
    # Existing tables
    "PageTable",
    "EnvironmentTable",
    "SystemUnderTestUserTable",
    "IdentifierTable",
    "FenrirActionsTable",
    "EmailProcessorTable",
    "AuthUserTable",
    # New core tables
    "AccountTable",
    "AuthTokenTable",
    "RevokedTokenTable",
    "AuditLogTable",
    "SystemUnderTestTable",
    "PlanTable",
    "SuiteTable",
    "TestCaseTable",
    "ActionChainTable",
    "EntityTagTable",
    "PurgeTable",
    # Junction tables
    "AuthUserAccountAssociation",
    "PageFenrirActionAssociation",
    "PlanSuiteAssociation",
    "SuiteTestCaseAssociation",
    "SystemEnvironmentAssociation",
]
