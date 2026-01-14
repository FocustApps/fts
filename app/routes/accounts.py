"""
Account management REST API routes.

Provides multi-tenant account management endpoints with:
- Account CRUD operations
- Role-based authorization (owner/admin/member/viewer)
- Account-scoped access validation
- Audit logging integration
"""

from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Request, HTTPException, Depends
from starlette.status import (
    HTTP_400_BAD_REQUEST,
    HTTP_404_NOT_FOUND,
)
from pydantic import BaseModel

from app.dependencies.jwt_auth_dependency import get_current_user
from app.dependencies.authorization_dependency import (
    require_owner,
    require_admin,
    require_viewer,
    require_super_admin,
    validate_account_access,
)
from app.models.auth_models import TokenPayload
from app.services.audit_service import (
    log_account_created,
    log_account_updated,
    log_account_deleted,
)
from common.service_connections.db_service.database.engine import (
    get_database_session as get_session,
)
from common.service_connections.db_service.models.account_models import (
    AccountModel,
    insert_account,
    query_account_by_id,
    query_all_accounts,
    query_account_with_owner,
    update_account,
    deactivate_account,
)
from common.service_connections.db_service.models.account_models import (
    add_user_to_account,
)
from common.service_connections.db_service.db_manager import DB_ENGINE
from common.app_logging import create_logging


logger = create_logging()


accounts_api_router = APIRouter(
    prefix="/api/accounts",
    tags=["accounts-api"],
)


# ============================================================================
# Pydantic Models for API
# ============================================================================


class CreateAccountRequest(BaseModel):
    """Request model for creating a new account."""

    account_name: str


class UpdateAccountRequest(BaseModel):
    """Request model for updating an account."""

    account_name: Optional[str] = None
    logo_url: Optional[str] = None
    primary_contact: Optional[str] = None
    subscription_id: Optional[str] = None


class AccountResponse(BaseModel):
    """Response model for basic account data."""

    account_id: str
    account_name: str
    owner_user_id: str
    is_active: bool
    logo_url: Optional[str] = None
    primary_contact: Optional[str] = None
    subscription_id: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


class AccountDetailResponse(BaseModel):
    """Response model for detailed account data with owner info."""

    account_id: str
    account_name: str
    owner_user_id: str
    owner_email: Optional[str] = None
    owner_username: Optional[str] = None
    is_active: bool
    logo_url: Optional[str] = None
    primary_contact: Optional[str] = None
    subscription_id: Optional[str] = None
    user_count: int
    created_at: datetime
    updated_at: Optional[datetime] = None


class UserAccountsResponse(BaseModel):
    """Response model for listing user's accessible accounts."""

    account_id: str
    account_name: str
    role: str
    is_primary: bool
    is_active: bool


# ============================================================================
# API Routes
# ============================================================================


@accounts_api_router.post("/", response_model=AccountResponse)
async def create_account(
    request: Request,
    body: CreateAccountRequest,
    current_user: TokenPayload = Depends(get_current_user),
):
    """
    Create a new account.

    Any authenticated user can create an account - they automatically become the owner.
    A user-account association is also created with 'owner' role and marked as primary.

    Args:
        request: FastAPI request object (for IP tracking)
        body: Account creation data
        current_user: JWT token payload

    Returns:
        AccountResponse: Created account data

    Raises:
        HTTPException: 400 if account name already exists
    """
    try:
        # Create account model
        account = AccountModel(
            account_name=body.account_name,
            owner_user_id=current_user.user_id,
        )

        # Insert account
        account_id = insert_account(account, DB_ENGINE)

        # Add owner to account with 'owner' role and mark as primary
        from common.service_connections.db_service.database.enums import (
            AccountRoleEnum,
        )

        add_user_to_account(
            auth_user_id=current_user.user_id,
            account_id=account_id,
            role=AccountRoleEnum.OWNER.value,
            is_primary=True,
            invited_by_user_id=current_user.user_id,
            engine=DB_ENGINE,
        )

        # Query back to get full data
        with get_session(DB_ENGINE) as db_session:
            created_account = query_account_by_id(account_id, db_session, DB_ENGINE)

        # Log audit event
        log_account_created(
            account_id=account_id,
            account_name=body.account_name,
            owner_user_id=current_user.user_id,
            performed_by_user_id=current_user.user_id,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            engine=DB_ENGINE,
        )

        return AccountResponse(**created_account.model_dump())

    except ValueError as e:
        logger.error(f"Error creating account: {e}")
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=str(e))


@accounts_api_router.get("/", response_model=List[UserAccountsResponse])
async def list_user_accounts(
    include_inactive: bool = False,
    current_user: TokenPayload = Depends(get_current_user),
):
    """
    List all accounts accessible to the current user.

    Args:
        include_inactive: Whether to include inactive accounts
        current_user: JWT token payload

    Returns:
        List[UserAccountsResponse]: List of user's accounts with roles

    Notes:
        - Super admins see all accounts
        - Regular users see only accounts they're associated with
        - Results include role and primary account flag
    """
    try:
        from common.service_connections.db_service.models.account_models import (
            query_accounts_by_user,
            query_account_by_id,
        )

        with get_session(DB_ENGINE) as db_session:
            if current_user.is_super_admin:
                # Super admins see all accounts
                all_accounts = query_all_accounts(
                    db_session, DB_ENGINE, active_only=not include_inactive
                )
                return [
                    UserAccountsResponse(
                        account_id=acc.account_id,
                        account_name=acc.account_name,
                        role="super_admin",
                        is_primary=False,
                        is_active=acc.is_active,
                    )
                    for acc in all_accounts
                ]
            else:
                # Regular users see their accounts
                user_associations = query_accounts_by_user(
                    auth_user_id=current_user.user_id,
                    db_session=db_session,
                    engine=DB_ENGINE,
                    active_only=not include_inactive,
                )

                # Get account details for each association
                result = []
                for assoc in user_associations:
                    account = query_account_by_id(assoc.account_id, db_session, DB_ENGINE)
                    result.append(
                        UserAccountsResponse(
                            account_id=account.account_id,
                            account_name=account.account_name,
                            role=assoc.role,
                            is_primary=assoc.is_primary,
                            is_active=assoc.is_active,
                        )
                    )
                return result

    except Exception as e:
        logger.error(f"Error listing accounts: {e}")
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=str(e))


@accounts_api_router.get("/{account_id}", response_model=AccountDetailResponse)
async def get_account(
    account_id: str,
    current_user: TokenPayload = Depends(require_viewer),
):
    """
    Get detailed account information.

    Requires: Viewer role or higher in the account

    Args:
        account_id: Account ID to retrieve
        current_user: JWT token payload

    Returns:
        AccountDetailResponse: Account details with owner info and user count

    Raises:
        HTTPException: 403 if user doesn't have access to account
        HTTPException: 404 if account not found
    """
    try:
        # Validate account access
        validate_account_access(current_user, account_id, allow_super_admin=True)

        # Query account with owner details
        with get_session(DB_ENGINE) as db_session:
            account = query_account_with_owner(account_id, db_session, DB_ENGINE)

        return AccountDetailResponse(**account.model_dump())

    except ValueError as e:
        logger.error(f"Account not found: {e}")
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving account: {e}")
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=str(e))


@accounts_api_router.put("/{account_id}", response_model=AccountResponse)
async def update_account_details(
    request: Request,
    account_id: str,
    body: UpdateAccountRequest,
    current_user: TokenPayload = Depends(require_admin),
):
    """
    Update account details.

    Requires: Admin role or higher in the account

    Args:
        request: FastAPI request object (for IP tracking)
        account_id: Account ID to update
        body: Updated account data
        current_user: JWT token payload

    Returns:
        AccountResponse: Updated account data

    Raises:
        HTTPException: 403 if user doesn't have admin access
        HTTPException: 404 if account not found
    """
    try:
        # Validate account access
        validate_account_access(current_user, account_id, allow_super_admin=True)

        # Get old values for audit logging
        with get_session(DB_ENGINE) as db_session:
            old_account = query_account_by_id(account_id, db_session, DB_ENGINE)

        # Build update data - only include fields that are being changed
        update_fields = {}
        if body.account_name:
            update_fields["account_name"] = body.account_name
        if body.logo_url is not None:
            update_fields["logo_url"] = body.logo_url
        if body.primary_contact is not None:
            update_fields["primary_contact"] = body.primary_contact
        if body.subscription_id is not None:
            update_fields["subscription_id"] = body.subscription_id

        # Create update model with only changed fields
        update_data = AccountModel(
            account_name=update_fields.get("account_name", old_account.account_name),
            owner_user_id=old_account.owner_user_id,
            logo_url=update_fields.get("logo_url", old_account.logo_url),
            primary_contact=update_fields.get(
                "primary_contact", old_account.primary_contact
            ),
            subscription_id=update_fields.get(
                "subscription_id", old_account.subscription_id
            ),
        )
        update_account(account_id, update_data, DB_ENGINE)

        # Query updated account
        with get_session(DB_ENGINE) as db_session:
            updated_account = query_account_by_id(account_id, db_session, DB_ENGINE)

        # Log audit event with change tracking
        changes = {}
        if body.account_name and body.account_name != old_account.account_name:
            changes["account_name"] = {
                "old": old_account.account_name,
                "new": body.account_name,
            }
        if body.logo_url is not None and body.logo_url != old_account.logo_url:
            changes["logo_url"] = {
                "old": old_account.logo_url,
                "new": body.logo_url,
            }
        if (
            body.primary_contact is not None
            and body.primary_contact != old_account.primary_contact
        ):
            changes["primary_contact"] = {
                "old": old_account.primary_contact,
                "new": body.primary_contact,
            }
        if (
            body.subscription_id is not None
            and body.subscription_id != old_account.subscription_id
        ):
            changes["subscription_id"] = {
                "old": old_account.subscription_id,
                "new": body.subscription_id,
            }

        log_account_updated(
            account_id=account_id,
            performed_by_user_id=current_user.user_id,
            changes=changes,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            engine=DB_ENGINE,
        )

        return AccountResponse(**updated_account.model_dump())

    except ValueError as e:
        logger.error(f"Account not found: {e}")
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating account: {e}")
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=str(e))


@accounts_api_router.delete("/{account_id}", status_code=204)
async def delete_account(
    request: Request,
    account_id: str,
    current_user: TokenPayload = Depends(require_owner),
):
    """
    Delete an account (soft delete).

    Requires: Owner role in the account

    Args:
        request: FastAPI request object (for IP tracking)
        account_id: Account ID to delete
        current_user: JWT token payload

    Raises:
        HTTPException: 403 if user is not the owner
        HTTPException: 404 if account not found

    Notes:
        - This is a soft delete (sets is_active = False)
        - All associated data remains in database
        - Account can be reactivated by support
    """
    try:
        # Validate account access
        validate_account_access(current_user, account_id, allow_super_admin=True)

        # Get account name for audit log
        with get_session(DB_ENGINE) as db_session:
            account = query_account_by_id(account_id, db_session, DB_ENGINE)

        # Soft delete account
        deactivate_account(account_id, DB_ENGINE)

        # Log audit event (sensitive = True for deletions)
        log_account_deleted(
            account_id=account_id,
            account_name=account.account_name,
            performed_by_user_id=current_user.user_id,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            engine=DB_ENGINE,
        )

    except ValueError as e:
        logger.error(f"Account not found: {e}")
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting account: {e}")
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=str(e))


# ============================================================================
# Super Admin Routes
# ============================================================================


@accounts_api_router.get(
    "/admin/all", response_model=List[AccountDetailResponse], tags=["super-admin"]
)
async def list_all_accounts_admin(
    include_inactive: bool = False,
    current_user: TokenPayload = Depends(require_super_admin),
):
    """
    Super admin: List all accounts in the system.

    Requires: Super admin role

    Args:
        include_inactive: Whether to include deactivated accounts
        current_user: JWT token payload

    Returns:
        List[AccountDetailResponse]: All accounts with owner info
    """
    try:
        with get_session(DB_ENGINE) as db_session:
            all_accounts = query_all_accounts(
                db_session, DB_ENGINE, active_only=not include_inactive
            )

            # Get detailed info for each account
            detailed_accounts = []
            for account in all_accounts:
                try:
                    detailed = query_account_with_owner(
                        account.account_id, db_session, DB_ENGINE
                    )
                    detailed_accounts.append(
                        AccountDetailResponse(**detailed.model_dump())
                    )
                except ValueError:
                    # Skip accounts with missing owners
                    continue

            return detailed_accounts

    except Exception as e:
        logger.error(f"Error listing all accounts: {e}")
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=str(e))


__all__ = ["accounts_api_router"]
