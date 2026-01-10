"""Account-related models for authentication and user management."""

from common.service_connections.db_service.models.account_models.auth_user_model import (
    AuthUserModel,
    insert_auth_user,
    query_auth_user_by_email,
    query_auth_user_by_id,
    query_auth_user_by_username,
    query_all_auth_users,
    query_active_auth_users,
    update_auth_user_by_id,
    deactivate_auth_user,
)
from common.service_connections.db_service.models.account_models.user_model import (
    UserModel,
    insert_user,
    query_user_by_id,
    query_all_users,
    update_user_by_id,
    drop_user_by_id,
)

__all__ = [
    # Auth User
    "AuthUserModel",
    "insert_auth_user",
    "query_auth_user_by_email",
    "query_auth_user_by_id",
    "query_auth_user_by_username",
    "query_all_auth_users",
    "query_active_auth_users",
    "update_auth_user_by_id",
    "deactivate_auth_user",
    # User
    "UserModel",
    "insert_user",
    "query_user_by_id",
    "query_all_users",
    "update_user_by_id",
    "drop_user_by_id",
]
