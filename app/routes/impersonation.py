"""
Impersonation routes for super admins to impersonate other users.

Provides endpoints for:
- Starting impersonation session
- Stopping impersonation session
- Getting current impersonation status

Security:
- Only super admins can impersonate
- All impersonation actions are audit logged (sensitive=True)
- Impersonation tokens have limited validity
- Original admin user ID tracked in token
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from starlette.status import (
    HTTP_400_BAD_REQUEST,
    HTTP_404_NOT_FOUND,
)

from app.dependencies.authorization_dependency import require_super_admin
from app.dependencies.jwt_auth_dependency import get_current_user
from app.models.auth_models import TokenPayload
from app.services.jwt_service import get_jwt_service
from app.services.audit_service import (
    log_user_impersonation_started,
    log_user_impersonation_ended,
)
from common.service_connections.db_service.database.engine import (
    get_database_session as get_session,
)
from common.service_connections.db_service.database.tables.account_tables.auth_user import (
    AuthUserTable,
)
from common.service_connections.db_service.db_manager import DB_ENGINE
from common.service_connections.db_service.models.account_models import (
    query_user_primary_account,
    query_account_by_id,
)


logger = logging.getLogger(__name__)

impersonation_api_router = APIRouter(
    prefix="/api/impersonation",
    tags=["api"],
)


# ============================================================================
# Request/Response Models
# ============================================================================


class StartImpersonationRequest(BaseModel):
    """Request model for starting impersonation."""

    target_user_id: str
    reason: str  # Required for compliance/audit


class ImpersonationResponse(BaseModel):
    """Response model for impersonation actions."""

    success: bool
    access_token: Optional[str] = None
    impersonated_user_id: Optional[str] = None
    impersonated_user_email: Optional[str] = None
    account_id: Optional[str] = None
    account_name: Optional[str] = None
    message: str


class ImpersonationStatusResponse(BaseModel):
    """Response model for impersonation status check."""

    is_impersonating: bool
    impersonated_user_id: Optional[str] = None
    impersonated_user_email: Optional[str] = None
    impersonated_by: Optional[str] = None
    started_at: Optional[datetime] = None


# ============================================================================
# Impersonation Endpoints
# ============================================================================


@impersonation_api_router.post(
    "/start",
    response_model=ImpersonationResponse,
)
async def start_impersonation(
    body: StartImpersonationRequest,
    current_user: TokenPayload = Depends(require_super_admin),
):
    """
    Start impersonating another user (super admin only).

    Creates a new access token with the target user's context
    but tracks the original super admin who initiated impersonation.

    Args:
        body: Target user ID and reason for impersonation
        current_user: JWT token payload (must be super admin)

    Returns:
        ImpersonationResponse: New access token and impersonated user details

    Raises:
        HTTPException: 404 if user not found, 403 if not super admin
    """
    try:
        # Cannot impersonate while already impersonating
        if current_user.impersonated_by:
            raise HTTPException(
                status_code=HTTP_400_BAD_REQUEST,
                detail="Cannot impersonate while already in an impersonation session",
            )

        # Validate reason provided
        if not body.reason or len(body.reason.strip()) < 10:
            raise HTTPException(
                status_code=HTTP_400_BAD_REQUEST,
                detail="Reason must be at least 10 characters for compliance",
            )

        # Get target user from auth_users table
        with get_session(DB_ENGINE) as db_session:
            target_user_db = db_session.get(AuthUserTable, body.target_user_id)

        if not target_user_db:
            raise HTTPException(
                status_code=HTTP_404_NOT_FOUND,
                detail=f"User {body.target_user_id} not found",
            )

        target_user_email = target_user_db.email

        # Get target user's primary account
        with get_session(DB_ENGINE) as db_session:
            primary_assoc = query_user_primary_account(
                auth_user_id=body.target_user_id,
                db_session=db_session,
                engine=DB_ENGINE,
            )

        account_id = None
        account_role = None
        account_name = None

        if primary_assoc:
            account_id = primary_assoc.account_id
            account_role = primary_assoc.role

            # Get account name
            with get_session(DB_ENGINE) as db_session:
                account = query_account_by_id(
                    account_id=account_id,
                    db_session=db_session,
                    engine=DB_ENGINE,
                )
                account_name = account.account_name if account else None

        # Create impersonation token
        jwt_service = get_jwt_service()
        impersonation_started = datetime.now(timezone.utc)

        access_token = jwt_service.create_access_token(
            user_id=body.target_user_id,
            email=target_user_email,
            is_admin=target_user_db.is_admin,
            is_super_admin=False,  # Impersonation tokens don't have super admin privileges
            account_id=account_id,
            account_role=account_role,
            impersonated_by=current_user.user_id,
            impersonation_started_at=impersonation_started,
        )

        # Log impersonation start
        log_user_impersonation_started(
            super_admin_user_id=current_user.user_id,
            super_admin_email=current_user.email,
            target_user_id=body.target_user_id,
            target_user_email=target_user_email,
            target_account_id=account_id,
            reason=body.reason,
            engine=DB_ENGINE,
        )

        logger.info(
            f"Super admin {current_user.user_id} started impersonating user {body.target_user_id}"
        )

        return ImpersonationResponse(
            success=True,
            access_token=access_token,
            impersonated_user_id=body.target_user_id,
            impersonated_user_email=target_user_email,
            account_id=account_id,
            account_name=account_name,
            message=f"Now impersonating user: {target_user_email}",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting impersonation: {e}")
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=str(e))


@impersonation_api_router.post(
    "/stop",
    response_model=ImpersonationResponse,
)
async def stop_impersonation(
    current_user: TokenPayload = Depends(require_super_admin),
):
    """
    Stop current impersonation session and return to super admin identity.

    Only works if currently impersonating. Returns a new token
    with the original super admin's context.

    Args:
        current_user: JWT token payload (must be impersonating)

    Returns:
        ImpersonationResponse: New access token with admin's identity

    Raises:
        HTTPException: 400 if not currently impersonating
    """
    try:
        # Must be impersonating to stop
        if not current_user.impersonated_by:
            raise HTTPException(
                status_code=HTTP_400_BAD_REQUEST,
                detail="Not currently impersonating any user",
            )

        # Calculate impersonation duration
        duration_seconds = 0
        if current_user.impersonation_started_at:
            duration = datetime.now(timezone.utc) - current_user.impersonation_started_at
            duration_seconds = int(duration.total_seconds())

        # Get original admin user from auth_users table
        with get_session(DB_ENGINE) as db_session:
            admin_user_db = db_session.get(AuthUserTable, current_user.impersonated_by)

        if not admin_user_db:
            raise HTTPException(
                status_code=HTTP_404_NOT_FOUND,
                detail=f"Original admin user {current_user.impersonated_by} not found",
            )

        admin_user_email = admin_user_db.email

        # Get admin's primary account
        with get_session(DB_ENGINE) as db_session:
            primary_assoc = query_user_primary_account(
                auth_user_id=current_user.impersonated_by,
                db_session=db_session,
                engine=DB_ENGINE,
            )

        account_id = None
        account_role = None

        if primary_assoc:
            account_id = primary_assoc.account_id
            account_role = primary_assoc.role

        # Create regular admin token (no impersonation)
        jwt_service = get_jwt_service()
        access_token = jwt_service.create_access_token(
            user_id=current_user.impersonated_by,
            email=admin_user_email,
            is_admin=admin_user_db.is_admin,
            is_super_admin=admin_user_db.is_super_admin,
            account_id=account_id,
            account_role=account_role,
        )

        # Log impersonation end
        log_user_impersonation_ended(
            super_admin_user_id=current_user.impersonated_by,
            target_user_id=current_user.user_id,
            duration_seconds=duration_seconds,
            engine=DB_ENGINE,
        )

        logger.info(
            f"Super admin {current_user.impersonated_by} stopped impersonating user {current_user.user_id}"
        )

        return ImpersonationResponse(
            success=True,
            access_token=access_token,
            message=f"Stopped impersonating, returned to admin identity",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error stopping impersonation: {e}")
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=str(e))


@impersonation_api_router.get(
    "/status",
    response_model=ImpersonationStatusResponse,
)
async def get_impersonation_status(
    current_user: TokenPayload = Depends(get_current_user),
):
    """
    Get current impersonation status.

    Returns information about whether the current token
    is an impersonation session and who is being impersonated.

    Args:
        current_user: JWT token payload

    Returns:
        ImpersonationStatusResponse: Impersonation status details
    """
    is_impersonating = current_user.impersonated_by is not None

    return ImpersonationStatusResponse(
        is_impersonating=is_impersonating,
        impersonated_user_id=current_user.user_id if is_impersonating else None,
        impersonated_user_email=current_user.email if is_impersonating else None,
        impersonated_by=current_user.impersonated_by,
        started_at=current_user.impersonation_started_at,
    )


__all__ = ["impersonation_api_router"]
