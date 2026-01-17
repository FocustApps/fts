# Legacy model imports (for backward compatibility)
from common.service_connections.db_service.database.tables.action_tables.user_interface_action.identifier import (
    IdentifierTable,
)
from common.service_connections.db_service.database.tables.environment_user import (
    TestEnvUserAccountsTable,
)
from common.service_connections.db_service.database.tables.environment import (
    EnvironmentTable,
)
from common.service_connections.db_service.database.tables.action_tables.user_interface_action.page import (
    PageTable,
)
from common.service_connections.db_service.database.tables.email_processor import (
    EmailProcessorTable,
)

# Import new tables from database package
from common.service_connections.db_service.database import (
    AuthUserTable,
    AccountTable,
    AuthTokenTable,
    AuditLogTable,
    SystemUnderTestTable,
    PlanTable,
    SuiteTable,
    TestCaseTable,
    ActionChainTable,
    EntityTagTable,
    AuthUserAccountAssociation,
    PageFenrirActionAssociation,
    PlanSuiteAssociation,
    SuiteTestCaseAssociation,
    SystemEnvironmentAssociation,
)


DB_TABLES = [
    # Existing tables
    EnvironmentTable.__table__,
    TestEnvUserAccountsTable.__table__,
    PageTable.__table__,
    IdentifierTable.__table__,
    EmailProcessorTable.__table__,
    AuthUserTable.__table__,
    # New core tables
    AccountTable.__table__,
    AuthTokenTable.__table__,
    AuditLogTable.__table__,
    SystemUnderTestTable.__table__,
    PlanTable.__table__,
    SuiteTable.__table__,
    TestCaseTable.__table__,
    ActionChainTable.__table__,
    EntityTagTable.__table__,
    # Junction tables
    AuthUserAccountAssociation.__table__,
    PageFenrirActionAssociation.__table__,
    PlanSuiteAssociation.__table__,
    SuiteTestCaseAssociation.__table__,
    SystemEnvironmentAssociation.__table__,
]
