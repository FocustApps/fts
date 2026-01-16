"""
Current user (/me) endpoints for authenticated users.

Provides endpoints for:
- Getting current user's accounts
- Getting current active account
- Getting available accounts to switch to
- Switching accounts
"""

import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from starlette.status import HTTP_404_NOT_FOUND, HTTP_400_BAD_REQUEST

from app.dependencies.authorization_dependency import get_current_user
from app.models.auth_models import TokenPayload
from common.service_connections.db_service.db_manager import DB_ENGINE
from common.service_connections.db_service.database.engine import (
    get_database_session as get_session,
)
from common.service_connections.db_service.models.account_models import (
    set_primary_account,
    query_user_primary_account,
    query_accounts_by_user,
    query_account_by_id,
)
from common.service_connections.db_service.models.audit_log_model import (
    insert_audit_log,
    AuditLogModel,
)

logger = logging.getLogger(__name__)

# Router for /users/me endpoints
users_me_api_router = APIRouter(
    prefix="/api/users/me",
    tags=["users-me"],
)


# ============================================================================
# Request/Response Models
# ============================================================================


class UserAccountsResponse(BaseModel):
    """Response model for user's account."""

    account_id: str
    account_name: str
    role: str
    is_primary: bool
    is_active: bool


class CurrentAccountResponse(BaseModel):
    """Response model for current active account."""

    account_id: str
    account_name: str
    role: str
    is_primary: bool


class AvailableAccountResponse(BaseModel):
    """Response model for available account to switch to."""

    account_id: str
    account_name: str
    role: str
    is_primary: bool
    is_active: bool


class SwitchAccountRequest(BaseModel):
    """Request model for switching active account."""

    account_id: str


class SwitchAccountResponse(BaseModel):
    """Response model for successful account switch."""

    success: bool
    account_id: str
    account_name: str
    message: str


# ============================================================================
# /users/me Endpoints
# ============================================================================


@users_me_api_router.get(
    "/accounts",
    response_model=List[UserAccountsResponse],
)
async def get_my_accounts(
    current_user: TokenPayload = Depends(get_current_user),
):
    """
    Get all accounts the current user has access to.

    Returns:
        List[UserAccountsResponse]: List of user's accounts with roles
    """
    try:
        with get_session(DB_ENGINE) as db_session:
            accounts = query_accounts_by_user(
                auth_user_id=current_user.user_id,
                db_session=db_session,
                engine=DB_ENGINE,
            )

        return [
            UserAccountsResponse(
                account_id=acc.account_id,
                account_name=acc.account_name,
                role=acc.role,
                is_primary=acc.is_primary,
                is_active=acc.is_active,
            )
            for acc in accounts
        ]

    except Exception as e:
        logger.error(f"Error getting user accounts: {e}")
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=str(e))


@users_me_api_router.get(
    "/current-account",
    response_model=CurrentAccountResponse,
)
async def get_current_account(
    current_user: TokenPayload = Depends(get_current_user),
):
    """
    Get the current user's active/primary account.

    Returns:
        CurrentAccountResponse: Current active account details

    Raises:
        HTTPException: 404 if no primary account set
    """
    try:
        with get_session(DB_ENGINE) as db_session:
            primary = query_user_primary_account(
                auth_user_id=current_user.user_id,
                db_session=db_session,
                engine=DB_ENGINE,
            )

        if not primary:
            raise HTTPException(
                status_code=HTTP_404_NOT_FOUND,
                detail="No primary account set. Please set a primary account.",
            )

        # Get account details
        with get_session(DB_ENGINE) as db_session:
            account = query_account_by_id(
                account_id=primary.account_id,
                db_session=db_session,
                engine=DB_ENGINE,
            )

        return CurrentAccountResponse(
            account_id=primary.account_id,
            account_name=account.account_name,
            role=primary.role,
            is_primary=primary.is_primary,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting current account: {e}")
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=str(e))


@users_me_api_router.get(
    "/available-accounts",
    response_model=List[AvailableAccountResponse],
)
async def get_available_accounts(
    current_user: TokenPayload = Depends(get_current_user),
):
    """
    Get all accounts available for the current user to switch to.

    Returns:
        List[AvailableAccountResponse]: List of available accounts
    """
    try:
        with get_session(DB_ENGINE) as db_session:
            accounts = query_accounts_by_user(
                auth_user_id=current_user.user_id,
                db_session=db_session,
                engine=DB_ENGINE,
            )

        return [
            AvailableAccountResponse(
                account_id=acc.account_id,
                account_name=acc.account_name,
                role=acc.role,
                is_primary=acc.is_primary,
                is_active=acc.is_active,
            )
            for acc in accounts
        ]

    except Exception as e:
        logger.error(f"Error getting available accounts: {e}")
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=str(e))


@users_me_api_router.post(
    "/switch-account",
    response_model=SwitchAccountResponse,
)
async def switch_account(
    request: SwitchAccountRequest,
    current_user: TokenPayload = Depends(get_current_user),
):
    """
    Switch the current user's active account to a different account.

    Args:
        request: SwitchAccountRequest with target account_id

    Returns:
        SwitchAccountResponse: Details of the switched account

    Raises:
        HTTPException: 404 if account not found or user doesn't have access
    """
    try:
        # Verify user has access to the target account
        with get_session(DB_ENGINE) as db_session:
            accounts = query_accounts_by_user(
                auth_user_id=current_user.user_id,
                db_session=db_session,
                engine=DB_ENGINE,
            )

        target_account = next(
            (acc for acc in accounts if acc.account_id == request.account_id),
            None,
        )

        if not target_account:
            raise HTTPException(
                status_code=HTTP_404_NOT_FOUND,
                detail=f"Account {request.account_id} not found or access denied",
            )

        # Set the new primary account
        set_primary_account(
            auth_user_id=current_user.user_id,
            account_id=request.account_id,
            engine=DB_ENGINE,
        )

        # Log the account switch
        audit_log = AuditLogModel(
            auth_user_id=current_user.user_id,
            action="ACCOUNT_SWITCH",
            entity_type="auth_user_account_association",
            entity_id=request.account_id,
            details=f"Switched to account: {target_account.account_name}",
        )
        insert_audit_log(audit_log=audit_log, engine=DB_ENGINE)

        logger.info(
            f"User {current_user.user_id} switched to account {request.account_id}"
        )

        return SwitchAccountResponse(
            success=True,
            account_id=target_account.account_id,
            account_name=target_account.account_name,
            message=f"Successfully switched to {target_account.account_name}",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error switching account: {e}")
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=str(e))
