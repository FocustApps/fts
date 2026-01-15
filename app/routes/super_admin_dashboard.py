"""
Super admin dashboard routes for system-wide management and monitoring.

Provides endpoints for:
- Listing all users across accounts
- Viewing system-wide metrics and statistics
- Managing user accounts (suspend/activate)

Security:
- All endpoints require super admin privileges
- All actions are audit logged
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from starlette.status import (
    HTTP_400_BAD_REQUEST,
    HTTP_404_NOT_FOUND,
)

from app.dependencies.authorization_dependency import require_super_admin
from app.models.auth_models import TokenPayload
from app.services.audit_service import log_super_admin_access
from common.service_connections.db_service.database.engine import (
    get_database_session as get_session,
)
from common.service_connections.db_service.database.tables.account_tables.auth_user import (
    AuthUserTable,
)
from common.service_connections.db_service.database.tables.account_tables.account import (
    AccountTable,
)
from common.service_connections.db_service.database.tables.account_tables.auth_user_account_association import (
    AuthUserAccountAssociation,
)
from common.service_connections.db_service.database.tables.audit_log import (
    AuditLogTable,
)
from common.service_connections.db_service.db_manager import DB_ENGINE


logger = logging.getLogger(__name__)

# Router definition
super_admin_dashboard_api_router = APIRouter(
    prefix="/api/admin",
    tags=["super-admin"],
)


# ============================================================================
# Response Models
# ============================================================================


class UserListItem(BaseModel):
    """User item in list response."""

    auth_user_id: str
    email: str
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    is_admin: bool
    is_super_admin: bool
    is_active: bool
    created_at: datetime
    last_login_at: Optional[datetime] = None
    account_count: int  # Number of accounts user belongs to
    primary_account_name: Optional[str] = None


class UserListResponse(BaseModel):
    """Paginated list of users."""

    users: List[UserListItem]
    total: int
    page: int
    page_size: int
    total_pages: int


class SystemMetrics(BaseModel):
    """System-wide statistics for super admin dashboard."""

    # User metrics
    total_users: int
    active_users: int
    inactive_users: int
    super_admins: int
    users_created_last_30_days: int

    # Account metrics
    total_accounts: int
    active_accounts: int
    inactive_accounts: int
    accounts_created_last_30_days: int

    # Activity metrics
    total_audit_logs: int
    audit_logs_last_24_hours: int
    sensitive_actions_last_7_days: int


class UserSuspendRequest(BaseModel):
    """Request to suspend or activate a user."""

    is_active: bool
    reason: str  # Reason for status change


class UserSuspendResponse(BaseModel):
    """Response after user suspension/activation."""

    success: bool
    user_id: str
    email: str
    is_active: bool
    message: str


# ============================================================================
# Routes
# ============================================================================


@super_admin_dashboard_api_router.get(
    "/users",
    response_model=UserListResponse,
)
async def list_all_users(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    include_inactive: bool = Query(False, description="Include inactive users"),
    search: Optional[str] = Query(None, description="Search by email or name"),
    current_user: TokenPayload = Depends(require_super_admin),
):
    """
    List all users across all accounts (super admin only).

    Returns paginated list of users with account associations and activity info.
    Supports filtering by active status and searching by email/name.

    Args:
        page: Page number (1-indexed)
        page_size: Number of users per page
        include_inactive: Whether to include deactivated users
        search: Search term for email or name
        current_user: JWT token payload (must be super admin)

    Returns:
        UserListResponse: Paginated list of users with metadata
    """
    try:
        with get_session(DB_ENGINE) as db_session:
            # Base query
            query = db_session.query(AuthUserTable)

            # Filter by active status
            if not include_inactive:
                query = query.filter(AuthUserTable.is_active == True)

            # Search filter
            if search:
                search_pattern = f"%{search}%"
                query = query.filter(
                    (AuthUserTable.email.ilike(search_pattern))
                    | (AuthUserTable.username.ilike(search_pattern))
                    | (AuthUserTable.first_name.ilike(search_pattern))
                    | (AuthUserTable.last_name.ilike(search_pattern))
                )

            # Get total count
            total = query.count()

            # Pagination
            offset = (page - 1) * page_size
            users_db = (
                query.order_by(AuthUserTable.created_at.desc())
                .offset(offset)
                .limit(page_size)
                .all()
            )

            # Build response with account associations
            users_list = []
            for user_db in users_db:
                # Count active account associations
                account_count = (
                    db_session.query(AuthUserAccountAssociation)
                    .filter(
                        AuthUserAccountAssociation.auth_user_id == user_db.auth_user_id,
                        AuthUserAccountAssociation.is_active == True,
                    )
                    .count()
                )

                # Get primary account name
                primary_assoc = (
                    db_session.query(AuthUserAccountAssociation, AccountTable)
                    .join(
                        AccountTable,
                        AuthUserAccountAssociation.account_id == AccountTable.account_id,
                    )
                    .filter(
                        AuthUserAccountAssociation.auth_user_id == user_db.auth_user_id,
                        AuthUserAccountAssociation.is_primary == True,
                        AuthUserAccountAssociation.is_active == True,
                    )
                    .first()
                )

                primary_account_name = (
                    primary_assoc[1].account_name if primary_assoc else None
                )

                users_list.append(
                    UserListItem(
                        auth_user_id=user_db.auth_user_id,
                        email=user_db.email,
                        username=user_db.username,
                        first_name=user_db.first_name,
                        last_name=user_db.last_name,
                        is_admin=user_db.is_admin,
                        is_super_admin=user_db.is_super_admin,
                        is_active=user_db.is_active,
                        created_at=user_db.created_at,
                        last_login_at=user_db.last_login_at,
                        account_count=account_count,
                        primary_account_name=primary_account_name,
                    )
                )

        total_pages = (total + page_size - 1) // page_size

        logger.info(
            f"Super admin {current_user.user_id} listed {len(users_list)} users (page {page})"
        )

        return UserListResponse(
            users=users_list,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    except Exception as e:
        logger.error(f"Error listing users: {e}")
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=str(e))


@super_admin_dashboard_api_router.get(
    "/metrics",
    response_model=SystemMetrics,
)
async def get_system_metrics(
    current_user: TokenPayload = Depends(require_super_admin),
):
    """
    Get system-wide metrics and statistics (super admin only).

    Returns comprehensive metrics about users, accounts, and system activity
    for the super admin dashboard.

    Args:
        current_user: JWT token payload (must be super admin)

    Returns:
        SystemMetrics: System-wide statistics
    """
    try:
        with get_session(DB_ENGINE) as db_session:
            now = datetime.now(timezone.utc)
            thirty_days_ago = now - timedelta(days=30)
            seven_days_ago = now - timedelta(days=7)
            twenty_four_hours_ago = now - timedelta(hours=24)

            # User metrics
            total_users = db_session.query(AuthUserTable).count()
            active_users = (
                db_session.query(AuthUserTable)
                .filter(AuthUserTable.is_active == True)
                .count()
            )
            inactive_users = total_users - active_users
            super_admins = (
                db_session.query(AuthUserTable)
                .filter(AuthUserTable.is_super_admin == True)
                .count()
            )
            users_created_last_30_days = (
                db_session.query(AuthUserTable)
                .filter(AuthUserTable.created_at >= thirty_days_ago)
                .count()
            )

            # Account metrics
            total_accounts = db_session.query(AccountTable).count()
            active_accounts = (
                db_session.query(AccountTable)
                .filter(AccountTable.is_active == True)
                .count()
            )
            inactive_accounts = total_accounts - active_accounts
            accounts_created_last_30_days = (
                db_session.query(AccountTable)
                .filter(AccountTable.created_at >= thirty_days_ago)
                .count()
            )

            # Activity metrics
            total_audit_logs = db_session.query(AuditLogTable).count()
            audit_logs_last_24_hours = (
                db_session.query(AuditLogTable)
                .filter(AuditLogTable.timestamp >= twenty_four_hours_ago)
                .count()
            )
            sensitive_actions_last_7_days = (
                db_session.query(AuditLogTable)
                .filter(
                    AuditLogTable.timestamp >= seven_days_ago,
                    AuditLogTable.is_sensitive == True,
                )
                .count()
            )

        logger.info(f"Super admin {current_user.user_id} accessed system metrics")

        return SystemMetrics(
            total_users=total_users,
            active_users=active_users,
            inactive_users=inactive_users,
            super_admins=super_admins,
            users_created_last_30_days=users_created_last_30_days,
            total_accounts=total_accounts,
            active_accounts=active_accounts,
            inactive_accounts=inactive_accounts,
            accounts_created_last_30_days=accounts_created_last_30_days,
            total_audit_logs=total_audit_logs,
            audit_logs_last_24_hours=audit_logs_last_24_hours,
            sensitive_actions_last_7_days=sensitive_actions_last_7_days,
        )

    except Exception as e:
        logger.error(f"Error getting system metrics: {e}")
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=str(e))


@super_admin_dashboard_api_router.post(
    "/users/{user_id}/status",
    response_model=UserSuspendResponse,
)
async def update_user_status(
    user_id: str,
    body: UserSuspendRequest,
    current_user: TokenPayload = Depends(require_super_admin),
):
    """
    Suspend or activate a user (super admin only).

    Updates the user's active status. Suspended users cannot log in.
    All actions are audit logged for compliance.

    Args:
        user_id: ID of user to update
        body: Status change request with reason
        current_user: JWT token payload (must be super admin)

    Returns:
        UserSuspendResponse: Confirmation of status change

    Raises:
        HTTPException: 404 if user not found, 400 for invalid operations
    """
    try:
        # Validate reason
        if not body.reason or len(body.reason) < 10:
            raise HTTPException(
                status_code=HTTP_400_BAD_REQUEST,
                detail="Reason must be at least 10 characters",
            )

        # Get user
        with get_session(DB_ENGINE) as db_session:
            user_db = db_session.get(AuthUserTable, user_id)

        if not user_db:
            raise HTTPException(
                status_code=HTTP_404_NOT_FOUND,
                detail=f"User {user_id} not found",
            )

        # Prevent super admin from suspending themselves
        if user_id == current_user.user_id:
            raise HTTPException(
                status_code=HTTP_400_BAD_REQUEST,
                detail="Cannot modify your own account status",
            )

        # Prevent suspending other super admins
        if user_db.is_super_admin and not body.is_active:
            raise HTTPException(
                status_code=HTTP_400_BAD_REQUEST,
                detail="Cannot suspend another super admin",
            )

        # Update status directly
        with get_session(DB_ENGINE) as db_session:
            user = db_session.get(AuthUserTable, user_id)
            if user:
                user.is_active = body.is_active
                user.updated_at = datetime.now(timezone.utc)
                db_session.commit()
                action = "activated" if body.is_active else "suspended"
            else:
                raise HTTPException(
                    status_code=HTTP_404_NOT_FOUND,
                    detail=f"User {user_id} not found",
                )

        # Log the action
        log_super_admin_access(
            super_admin_user_id=current_user.user_id,
            accessed_resource_type="auth_user",
            accessed_resource_id=user_id,
            accessed_account_id=None,
            action=f"user_{action}",
            reason=body.reason,
            engine=DB_ENGINE,
        )

        logger.info(
            f"Super admin {current_user.user_id} {action} user {user_id}: {body.reason}"
        )

        return UserSuspendResponse(
            success=True,
            user_id=user_id,
            email=user_db.email,
            is_active=body.is_active,
            message=f"User {action} successfully",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating user status: {e}")
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=str(e))


__all__ = ["super_admin_dashboard_api_router"]
