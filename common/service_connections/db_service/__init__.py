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


DB_TABLES = [
    EnvironmentTable.__table__,
    SystemUnderTestUserTable.__table__,
    PageTable.__table__,
    IdentifierTable.__table__,
    EmailProcessorTable.__table__,
]
