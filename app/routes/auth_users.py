"""
Authentication user management routes.

Provides admin interface for managing JWT-authenticated users:
- Adding new authenticated users with account assignments
- Listing and viewing user details
- Deactivating/reactivating users
"""

from datetime import UTC, datetime
from typing import List, Optional
from fastapi import APIRouter, Request, Form, HTTPException, Depends

from starlette.status import HTTP_400_BAD_REQUEST, HTTP_404_NOT_FOUND
from pydantic import BaseModel, EmailStr

from app.dependencies.jwt_auth_dependency import require_admin
from app.models.auth_models import TokenPayload, RegisterRequest
from app.services.user_auth_service import get_user_auth_service
from common.service_connections.db_service.database.engine import (
    get_database_session as get_session,
)
from common.service_connections.db_service.database.tables.account_tables.auth_user import (
    AuthUserTable,
)
from common.service_connections.db_service.database.tables.account_tables.account import (
    AccountTable,
)
from common.service_connections.db_service.db_manager import DB_ENGINE
from common.app_logging import create_logging


logger = create_logging()


auth_users_api_router = APIRouter(
    prefix="/api/auth-users",
    tags=["auth-users-api"],
)

# Pydantic Models
class AddUserRequest(BaseModel):
    """Request model for adding a new user."""

    email: EmailStr
    username: Optional[str] = None
    password: str
    account_id: str
    is_admin: bool = False


class UserResponse(BaseModel):
    """Response model for user data."""

    auth_user_id: str
    email: str
    username: Optional[str]
    is_admin: bool
    is_active: bool
    account_id: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime]


class AuthUserDisplay:
    """Display object for auth users that works with templates."""

    def __init__(self, user: AuthUserTable, account_name: Optional[str] = None):
        self.auth_user_id = str(user.auth_user_id)
        self.email = user.email
        self.username = user.username or "—"
        self.is_admin = "Yes" if user.is_admin else "No"
        self.is_active = "Active" if user.is_active else "Inactive"
        self.account_name = account_name or "—"
        self.created_at = user.created_at.strftime("%Y-%m-%d %H:%M UTC")
        self.updated_at = (
            user.updated_at.strftime("%Y-%m-%d %H:%M UTC") if user.updated_at else "—"
        )

    def get_display_name(self) -> str:
        """Get display name for UI."""
        return self.username if self.username != "—" else self.email

################ API ROUTES ################


@auth_users_api_router.get("/users", response_model=List[UserResponse])
async def list_users_api(
    include_inactive: bool = False,
    account_id: Optional[str] = None,
    current_user: TokenPayload = Depends(require_admin),
):
    """List all authenticated users."""
    try:
        with get_session(DB_ENGINE) as db_session:
            query = db_session.query(AuthUserTable)

            # Filter by active status
            if not include_inactive:
                query = query.filter(AuthUserTable.is_active == True)

            # Filter by account if provided
            if account_id:
                query = query.filter(AuthUserTable.account_id == account_id)

            users = query.all()

            return [
                UserResponse(
                    auth_user_id=str(user.auth_user_id),
                    email=user.email,
                    username=user.username,
                    is_admin=user.is_admin,
                    is_active=user.is_active,
                    account_id=str(user.account_id) if user.account_id else None,
                    created_at=user.created_at,
                    updated_at=user.updated_at,
                )
                for user in users
            ]

    except Exception as e:
        logger.error(f"Error listing users: {e}")
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=str(e))


@auth_users_api_router.get("/users/{user_id}", response_model=UserResponse)
async def get_user_api(
    user_id: str,
    current_user: TokenPayload = Depends(require_admin),
):
    """Get a specific user by ID."""
    try:
        with get_session(DB_ENGINE) as db_session:
            user = db_session.get(AuthUserTable, user_id)

            if not user:
                raise HTTPException(
                    status_code=HTTP_404_NOT_FOUND, detail="User not found"
                )

            return UserResponse(
                auth_user_id=str(user.auth_user_id),
                email=user.email,
                username=user.username,
                is_admin=user.is_admin,
                is_active=user.is_active,
                account_id=str(user.account_id) if user.account_id else None,
                created_at=user.created_at,
                updated_at=user.updated_at,
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user {user_id}: {e}")
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=str(e))


@auth_users_api_router.post("/users", response_model=UserResponse)
async def create_user_api(
    user_request: AddUserRequest,
    current_user: TokenPayload = Depends(require_admin),
):
    """Create a new authenticated user."""
    try:
        # Validate account exists
        with get_session(DB_ENGINE) as db_session:
            account = db_session.get(AccountTable, user_request.account_id)
            if not account:
                raise HTTPException(
                    status_code=HTTP_400_BAD_REQUEST, detail="Selected account not found"
                )

        # Register user
        auth_service = get_user_auth_service(DB_ENGINE)
        register_request = RegisterRequest(
            email=user_request.email,
            password=user_request.password,
            username=user_request.username,
        )

        user = auth_service.register_user(register_request)

        # Update user with account_id and admin status
        with get_session(DB_ENGINE) as db_session:
            db_user = db_session.get(AuthUserTable, user.auth_user_id)
            db_user.account_id = user_request.account_id
            db_user.is_admin = user_request.is_admin
            db_session.commit()
            db_session.refresh(db_user)

            logger.info(
                f"Created new auth user via API: {user_request.email} "
                f"(account: {user_request.account_id})"
            )

            return UserResponse(
                auth_user_id=str(db_user.auth_user_id),
                email=db_user.email,
                username=db_user.username,
                is_admin=db_user.is_admin,
                is_active=db_user.is_active,
                account_id=str(db_user.account_id) if db_user.account_id else None,
                created_at=db_user.created_at,
                updated_at=db_user.updated_at,
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error creating user via API: {e}")
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST, detail=f"Failed to create user: {str(e)}"
        )


@auth_users_api_router.patch("/users/{user_id}/status")
async def toggle_user_status_api(
    user_id: str,
    is_active: bool,
    current_user: TokenPayload = Depends(require_admin),
):
    """Activate or deactivate a user."""
    try:
        with get_session(DB_ENGINE) as db_session:
            user = db_session.get(AuthUserTable, user_id)

            if not user:
                raise HTTPException(
                    status_code=HTTP_404_NOT_FOUND, detail="User not found"
                )

            user.is_active = is_active
            user.updated_at = datetime.now(UTC)
            db_session.commit()

            status = "activated" if is_active else "deactivated"
            logger.info(f"{status.capitalize()} user via API: {user.email}")

            return {
                "message": f"User {status} successfully",
                "user_email": user.email,
                "is_active": user.is_active,
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating user {user_id} status via API: {e}")
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST, detail="Failed to update user status"
        )


@auth_users_api_router.delete("/users/{user_id}")
async def deactivate_user_api(
    user_id: str,
    current_user: TokenPayload = Depends(require_admin),
):
    """Deactivate a user (convenience endpoint)."""
    return await toggle_user_status_api(
        user_id, is_active=False, current_user=current_user
    )
