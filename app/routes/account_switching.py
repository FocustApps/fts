"""
Account switching routes for users to manage their active account context.

Provides endpoints for:
- Getting current active account
- Switching to a different account
- Listing available accounts to switch to
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

# Router
account_switching_api_router = APIRouter(
    prefix="/api/accounts/switch",
    tags=["account-switching"],
)


# ============================================================================
# Request/Response Models
# ============================================================================


class SwitchAccountRequest(BaseModel):
    """Request model for switching active account."""

    account_id: str


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


class SwitchAccountResponse(BaseModel):
    """Response model for successful account switch."""

    success: bool
    account_id: str
    account_name: str
    message: str


# ============================================================================
# Account Switching Endpoints
# ============================================================================


@account_switching_api_router.get(
    "/current",
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


@account_switching_api_router.get(
    "/available",
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
            associations = query_accounts_by_user(
                auth_user_id=current_user.user_id,
                db_session=db_session,
                engine=DB_ENGINE,
            )

        if not associations:
            return []

        # Get account details for each association
        results = []
        for assoc in associations:
            with get_session(DB_ENGINE) as db_session:
                account = query_account_by_id(
                    account_id=assoc.account_id,
                    db_session=db_session,
                    engine=DB_ENGINE,
                )

            results.append(
                AvailableAccountResponse(
                    account_id=assoc.account_id,
                    account_name=account.account_name,
                    role=assoc.role,
                    is_primary=assoc.is_primary,
                    is_active=assoc.is_active,
                )
            )

        return results

    except Exception as e:
        logger.error(f"Error getting available accounts: {e}")
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=str(e))


@account_switching_api_router.post(
    "",
    response_model=SwitchAccountResponse,
)
async def switch_account(
    body: SwitchAccountRequest,
    current_user: TokenPayload = Depends(get_current_user),
):
    """
    Switch to a different account.

    Sets the specified account as the user's primary/active account.
    User must have access to the account to switch to it.

    Args:
        body: Account ID to switch to
        current_user: JWT token payload

    Returns:
        SwitchAccountResponse: Success confirmation with account details

    Raises:
        HTTPException: 404 if account not found or user doesn't have access
    """
    try:
        # Verify user has access to this account
        with get_session(DB_ENGINE) as db_session:
            user_accounts = query_accounts_by_user(
                auth_user_id=current_user.user_id,
                db_session=db_session,
                engine=DB_ENGINE,
            )

        account_ids = [assoc.account_id for assoc in user_accounts if assoc.is_active]

        if body.account_id not in account_ids:
            raise HTTPException(
                status_code=HTTP_404_NOT_FOUND,
                detail=f"Account {body.account_id} not found or user does not have access",
            )

        # Set as primary account
        set_primary_account(
            auth_user_id=current_user.user_id,
            account_id=body.account_id,
            engine=DB_ENGINE,
        )

        # Get account details for response
        with get_session(DB_ENGINE) as db_session:
            account = query_account_by_id(
                account_id=body.account_id,
                db_session=db_session,
                engine=DB_ENGINE,
            )

        # Create audit log
        audit_log = AuditLogModel(
            account_id=body.account_id,
            performed_by_user_id=current_user.user_id,
            action="account_switch",
            entity_type="account",
            entity_id=body.account_id,
            details={
                "account_name": account.account_name,
                "user_id": current_user.user_id,
            },
        )
        insert_audit_log(audit_log, DB_ENGINE)

        logger.info(f"User {current_user.user_id} switched to account {body.account_id}")

        return SwitchAccountResponse(
            success=True,
            account_id=body.account_id,
            account_name=account.account_name,
            message=f"Successfully switched to account: {account.account_name}",
        )

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Error switching account: {e}")
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=str(e))


__all__ = ["account_switching_api_router"]
