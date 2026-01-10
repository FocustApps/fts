"""User interface models for page objects and identifiers."""

from common.service_connections.db_service.models.user_interface_models.identifier_model import (
    IdentifierModel,
    insert_identifier,
    query_identifier_by_id,
    query_all_identifiers,
    update_identifier_by_id,
    drop_identifier_by_id,
)
from common.service_connections.db_service.models.user_interface_models.page_model import (
    PageModel,
    insert_page,
    query_page_by_id,
    query_all_pages,
    update_page_by_id,
    drop_page_by_id,
)

__all__ = [
    # Identifier
    "IdentifierModel",
    "insert_identifier",
    "query_identifier_by_id",
    "query_all_identifiers",
    "update_identifier_by_id",
    "drop_identifier_by_id",
    # Page
    "PageModel",
    "insert_page",
    "query_page_by_id",
    "query_all_pages",
    "update_page_by_id",
    "drop_page_by_id",
]
