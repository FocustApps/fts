"""
API routes for account-user associations.

Endpoints:
- POST   /accounts/{account_id}/users        - Add user to account (requires admin+)
- GET    /accounts/{account_id}/users        - List users in account (requires viewer+)
- PUT    /accounts/{account_id}/users/{user_id} - Update user role (requires admin+)
- DELETE /accounts/{account_id}/users/{user_id} - Remove user from account (requires admin+)
- PUT    /accounts/{account_id}/users/{user_id}/primary - Set as primary account (self only)
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from starlette.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_204_NO_CONTENT,
    HTTP_400_BAD_REQUEST,
    HTTP_403_FORBIDDEN,
    HTTP_404_NOT_FOUND,
)

from app.dependencies.authorization_dependency import (
    get_current_user,
    require_admin,
    require_viewer,
    validate_account_access,
)
from app.config import get_config
from common.service_connections.db_service.database.engine import (
    get_database_session as get_session,
)
from common.service_connections.db_service.database.enums import AccountRoleEnum
from common.service_connections.db_service.db_manager import DB_ENGINE
from common.service_connections.db_service.models.account_models import (
    add_user_to_account,
    update_user_role,
    remove_user_from_account,
    set_primary_account,
    query_users_by_account,
)
from app.models.auth_models import TokenPayload
from app.services.audit_service import (
    log_user_added_to_account,
    log_user_removed_from_account,
    log_user_role_changed,
)

logger = logging.getLogger(__name__)
BASE_CONFIG = get_config()

# Create router
account_associations_api_router = APIRouter(
    prefix="/api/accounts",
    tags=["api"],
)


# ============================================================================
# Request/Response Models
# ============================================================================


class AddUserRequest(BaseModel):
    """Request model for adding a user to an account."""

    auth_user_id: str
    role: str = AccountRoleEnum.MEMBER.value
    is_primary: bool = False


class UpdateRoleRequest(BaseModel):
    """Request model for updating a user's role."""

    role: str


class AccountUserResponse(BaseModel):
    """Response model for user in account."""

    association_id: str
    auth_user_id: str
    account_id: str
    role: str
    is_primary: bool
    is_active: bool
    user_email: Optional[str] = None
    user_username: Optional[str] = None
    invited_by_user_id: Optional[str] = None
    created_at: str
    updated_at: Optional[str] = None


# ============================================================================
# API Endpoints
# ============================================================================


@account_associations_api_router.post(
    "/{account_id}/users",
    response_model=AccountUserResponse,
    status_code=HTTP_201_CREATED,
)
async def add_user_to_account_endpoint(
    request: Request,
    account_id: str,
    body: AddUserRequest,
    current_user: TokenPayload = Depends(require_admin),
):
    """
    Add a user to an account with a specific role.

    Requires: Admin role or higher in the account

    Args:
        request: FastAPI request object (for IP tracking)
        account_id: Account ID
        body: User and role information
        current_user: JWT token payload

    Returns:
        AccountUserResponse: Created association with user details

    Raises:
        HTTPException: 403 if user doesn't have admin access
        HTTPException: 400 if association already exists or validation fails
    """
    try:
        # Validate account access
        validate_account_access(current_user, account_id, allow_super_admin=True)

        # Validate role
        if body.role not in [role.value for role in AccountRoleEnum]:
            raise ValueError(f"Invalid role: {body.role}")

        # Add user to account
        association_id = add_user_to_account(
            auth_user_id=body.auth_user_id,
            account_id=account_id,
            role=body.role,
            is_primary=body.is_primary,
            invited_by_user_id=current_user.user_id,
            engine=DB_ENGINE,
        )

        # Query back to get full data
        with get_session(DB_ENGINE) as db_session:
            users = query_users_by_account(
                account_id=account_id,
                db_session=db_session,
                engine=DB_ENGINE,
            )
            user_assoc = next(
                (u for u in users if u.association_id == association_id), None
            )

        if not user_assoc:
            raise ValueError("Failed to retrieve created association")

        # Log audit event
        log_user_added_to_account(
            association_id=user_assoc.association_id,
            account_id=account_id,
            target_user_id=body.auth_user_id,
            target_user_email=user_assoc.user_email or "",
            role=body.role,
            performed_by_user_id=current_user.user_id,
            is_primary=body.is_primary,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            engine=DB_ENGINE,
        )

        return AccountUserResponse(
            association_id=user_assoc.association_id,
            auth_user_id=user_assoc.auth_user_id,
            account_id=user_assoc.account_id,
            role=user_assoc.role,
            is_primary=user_assoc.is_primary,
            is_active=user_assoc.is_active,
            user_email=user_assoc.user_email,
            user_username=user_assoc.user_username,
            invited_by_user_id=user_assoc.invited_by_user_id,
            created_at=user_assoc.created_at.isoformat(),
            updated_at=(
                user_assoc.updated_at.isoformat() if user_assoc.updated_at else None
            ),
        )

    except ValueError as e:
        logger.error(f"Validation error adding user to account: {e}")
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding user to account: {e}")
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=str(e))


@account_associations_api_router.get(
    "/{account_id}/users",
    response_model=List[AccountUserResponse],
)
async def list_account_users(
    account_id: str,
    include_inactive: bool = False,
    current_user: TokenPayload = Depends(require_viewer),
):
    """
    List all users in an account with their roles.

    Requires: Viewer role or higher in the account

    Args:
        account_id: Account ID
        include_inactive: Whether to include inactive associations
        current_user: JWT token payload

    Returns:
        List[AccountUserResponse]: List of users with roles and details

    Raises:
        HTTPException: 403 if user doesn't have access to account
        HTTPException: 404 if account not found
    """
    try:
        # Validate account access
        validate_account_access(current_user, account_id, allow_super_admin=True)

        # Query users
        with get_session(DB_ENGINE) as db_session:
            users = query_users_by_account(
                account_id=account_id,
                db_session=db_session,
                engine=DB_ENGINE,
                active_only=not include_inactive,
            )

        return [
            AccountUserResponse(
                association_id=u.association_id,
                auth_user_id=u.auth_user_id,
                account_id=u.account_id,
                role=u.role,
                is_primary=u.is_primary,
                is_active=u.is_active,
                user_email=u.user_email,
                user_username=u.user_username,
                invited_by_user_id=u.invited_by_user_id,
                created_at=u.created_at.isoformat(),
                updated_at=u.updated_at.isoformat() if u.updated_at else None,
            )
            for u in users
        ]

    except ValueError as e:
        logger.error(f"Account not found: {e}")
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing account users: {e}")
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=str(e))


@account_associations_api_router.put(
    "/{account_id}/users/{user_id}",
    response_model=AccountUserResponse,
)
async def update_user_role_endpoint(
    request: Request,
    account_id: str,
    user_id: str,
    body: UpdateRoleRequest,
    current_user: TokenPayload = Depends(require_admin),
):
    """
    Update a user's role in an account.

    Requires: Admin role or higher in the account

    Args:
        request: FastAPI request object (for IP tracking)
        account_id: Account ID
        user_id: User ID to update
        body: New role information
        current_user: JWT token payload

    Returns:
        AccountUserResponse: Updated association with user details

    Raises:
        HTTPException: 403 if user doesn't have admin access
        HTTPException: 400 if validation fails
        HTTPException: 404 if user not found in account
    """
    try:
        # Validate account access
        validate_account_access(current_user, account_id, allow_super_admin=True)

        # Validate role
        if body.role not in [role.value for role in AccountRoleEnum]:
            raise ValueError(f"Invalid role: {body.role}")

        # Get old role for audit logging
        with get_session(DB_ENGINE) as db_session:
            users = query_users_by_account(
                account_id=account_id,
                db_session=db_session,
                engine=DB_ENGINE,
            )
            old_user = next((u for u in users if u.auth_user_id == user_id), None)
            if not old_user:
                raise ValueError(f"User {user_id} not found in account {account_id}")
            old_role = old_user.role

        # Update role
        update_user_role(
            auth_user_id=user_id,
            account_id=account_id,
            new_role=body.role,
            engine=DB_ENGINE,
        )

        # Query back to get updated data
        with get_session(DB_ENGINE) as db_session:
            users = query_users_by_account(
                account_id=account_id,
                db_session=db_session,
                engine=DB_ENGINE,
            )
            updated_user = next((u for u in users if u.auth_user_id == user_id), None)

        if not updated_user:
            raise ValueError("Failed to retrieve updated association")

        # Log audit event
        log_user_role_changed(
            association_id=updated_user.association_id,
            account_id=account_id,
            target_user_id=user_id,
            target_user_email=updated_user.user_email or "",
            old_role=old_role,
            new_role=body.role,
            performed_by_user_id=current_user.user_id,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            engine=DB_ENGINE,
        )

        return AccountUserResponse(
            association_id=updated_user.association_id,
            auth_user_id=updated_user.auth_user_id,
            account_id=updated_user.account_id,
            role=updated_user.role,
            is_primary=updated_user.is_primary,
            is_active=updated_user.is_active,
            user_email=updated_user.user_email,
            user_username=updated_user.user_username,
            invited_by_user_id=updated_user.invited_by_user_id,
            created_at=updated_user.created_at.isoformat(),
            updated_at=(
                updated_user.updated_at.isoformat() if updated_user.updated_at else None
            ),
        )

    except ValueError as e:
        logger.error(f"Validation error updating user role: {e}")
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating user role: {e}")
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=str(e))


@account_associations_api_router.delete(
    "/{account_id}/users/{user_id}",
    status_code=HTTP_204_NO_CONTENT,
)
async def remove_user_from_account_endpoint(
    request: Request,
    account_id: str,
    user_id: str,
    current_user: TokenPayload = Depends(require_admin),
):
    """
    Remove a user from an account.

    Requires: Admin role or higher in the account
    Note: Cannot remove the account owner

    Args:
        request: FastAPI request object (for IP tracking)
        account_id: Account ID
        user_id: User ID to remove
        current_user: JWT token payload

    Raises:
        HTTPException: 403 if user doesn't have admin access or trying to remove owner
        HTTPException: 404 if user not found in account
    """
    try:
        # Validate account access
        validate_account_access(current_user, account_id, allow_super_admin=True)

        # Check if user is the owner (owners can't be removed)
        with get_session(DB_ENGINE) as db_session:
            users = query_users_by_account(
                account_id=account_id,
                db_session=db_session,
                engine=DB_ENGINE,
            )
            user_to_remove = next((u for u in users if u.auth_user_id == user_id), None)
            if not user_to_remove:
                raise ValueError(f"User {user_id} not found in account {account_id}")
            if user_to_remove.role == AccountRoleEnum.OWNER.value:
                raise ValueError("Cannot remove account owner")

        # Remove user
        remove_user_from_account(
            auth_user_id=user_id,
            account_id=account_id,
            engine=DB_ENGINE,
        )

        # Log audit event
        log_user_removed_from_account(
            association_id=user_to_remove.association_id,
            account_id=account_id,
            target_user_id=user_id,
            target_user_email=user_to_remove.user_email or "",
            role=user_to_remove.role,
            performed_by_user_id=current_user.user_id,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            engine=DB_ENGINE,
        )

    except ValueError as e:
        logger.error(f"Validation error removing user from account: {e}")
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing user from account: {e}")
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=str(e))


@account_associations_api_router.put(
    "/{account_id}/users/{user_id}/primary",
    status_code=HTTP_200_OK,
)
async def set_primary_account_endpoint(
    account_id: str,
    user_id: str,
    current_user: TokenPayload = Depends(get_current_user),
):
    """
    Set an account as the user's primary account.

    Users can only set their own primary account.

    Args:
        account_id: Account ID to set as primary
        user_id: User ID (must match current_user.user_id)
        current_user: JWT token payload

    Returns:
        dict: Success message

    Raises:
        HTTPException: 403 if trying to set another user's primary account
        HTTPException: 404 if user not found in account
    """
    try:
        # Users can only set their own primary account
        if user_id != current_user.user_id and not current_user.is_super_admin:
            raise HTTPException(
                status_code=HTTP_403_FORBIDDEN,
                detail="You can only set your own primary account",
            )

        # Set primary account
        set_primary_account(
            auth_user_id=user_id,
            account_id=account_id,
            engine=DB_ENGINE,
        )

        return {"message": "Primary account updated successfully"}

    except ValueError as e:
        logger.error(f"Validation error setting primary account: {e}")
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error setting primary account: {e}")
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=str(e))
