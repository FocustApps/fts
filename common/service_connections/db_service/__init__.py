from common.service_connections.db_service.identifier_model import IdentifierTable
from common.service_connections.db_service.user_model import UserTable
from common.service_connections.db_service.environment_model import EnvironmentTable
from common.service_connections.db_service.page_model import PageTable
from common.service_connections.db_service.email_processor_model import (
    EmailProcessorTable,
)


DB_TABLES = [
    EnvironmentTable.__table__,
    UserTable.__table__,
    PageTable.__table__,
    IdentifierTable.__table__,
    EmailProcessorTable.__table__,
]
