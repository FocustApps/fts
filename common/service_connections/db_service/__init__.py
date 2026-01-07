# Legacy model imports (for backward compatibility)
from common.service_connections.db_service.models.identifier_model import IdentifierTable
from common.service_connections.db_service.models.user_model import (
    SystemUnderTestUserTable,
)
from common.service_connections.db_service.models.environment_model import (
    EnvironmentTable,
)
from common.service_connections.db_service.models.page_model import PageTable
from common.service_connections.db_service.models.email_processor_model import (
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
    SystemUnderTestUserTable.__table__,
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
