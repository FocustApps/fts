"""
Authentication user management routes.

Provides admin interface for managing multi-user authentication:
- Adding new authenticated users
- Listing and viewing user details
- Generating and rotating tokens
- Deactivating users
"""

from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, Request, Form, HTTPException, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from starlette.status import HTTP_400_BAD_REQUEST, HTTP_404_NOT_FOUND
from pydantic import BaseModel, EmailStr

from app.dependencies.multi_user_auth_dependency import (
    verify_admin_auth_token,
    AuthContext,
)
from app.services.multi_user_auth_service import (
    get_multi_user_auth_service,
    MultiUserAuthError,
)
from common.service_connections.db_service.database import AuthUserTable
from common.app_logging import create_logging

logger = create_logging()

# Create routers for API and view endpoints
auth_users_api_router = APIRouter(prefix="/api/auth-users", tags=["auth-users-api"])
auth_users_views_router = APIRouter(
    prefix="/auth-users", tags=["auth-users-views"], include_in_schema=False
)

# Template configuration
templates = Jinja2Templates(directory="app/templates")


# Pydantic models for API requests
class AddUserRequest(BaseModel):
    email: EmailStr
    username: Optional[str] = None
    is_admin: bool = False


class UserResponse(BaseModel):
    id: int
    email: str
    username: Optional[str]
    is_admin: bool
    is_active: bool
    has_token: bool
    token_expires_at: Optional[datetime]
    last_login_at: Optional[datetime]
    created_at: datetime
    updated_at: Optional[datetime]

    @classmethod
    def from_auth_user(cls, user: AuthUserTable) -> "UserResponse":
        """Convert AuthUserTable to API response model."""
        return cls(
            id=user.id,
            email=user.email,
            username=user.username,
            is_admin=user.is_admin,
            is_active=user.is_active,
            has_token=user.current_token is not None,
            token_expires_at=user.token_expires_at,
            last_login_at=user.last_login_at,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )


################ VIEW ROUTES ################


@auth_users_views_router.get("/", response_class=HTMLResponse)
async def get_auth_users_view(
    request: Request, auth_context: AuthContext = Depends(verify_admin_auth_token)
):
    """Display the auth users management page."""
    try:
        auth_service = get_multi_user_auth_service()
        users = auth_service.list_users(include_inactive=True)

        # Prepare data for table display
        user_data = []
        for user in users:
            user_info = {
                "id": user.id,
                "email": user.email,
                "username": user.username or "—",
                "is_admin": "✓" if user.is_admin else "—",
                "is_active": "✓" if user.is_active else "—",
                "has_token": "✓" if user.current_token else "—",
                "last_login": (
                    user.last_login_at.strftime("%Y-%m-%d %H:%M")
                    if user.last_login_at
                    else "Never"
                ),
                "created_at": user.created_at.strftime("%Y-%m-%d %H:%M"),
            }
            user_data.append(user_info)

        # Headers for the table
        headers = [
            "ID",
            "Email",
            "Username",
            "Admin",
            "Active",
            "Has Token",
            "Last Login",
            "Created",
        ]

        return templates.TemplateResponse(
            "table.html",
            {
                "title": "Authentication Users",
                "request": request,
                "headers": headers,
                "table_rows": user_data,
                "view_url": "get_auth_users_view",
                "view_record_url": "view_auth_user",
                "add_url": "new_auth_user_view",
                "delete_url": "deactivate_auth_user_view",
            },
        )

    except Exception as e:
        logger.error(f"Error loading auth users view: {e}")
        return templates.TemplateResponse(
            "error.html",
            {
                "request": request,
                "error_message": "Failed to load authentication users",
                "error_details": str(e),
            },
        )


@auth_users_views_router.get("/{user_id}", response_class=HTMLResponse)
async def view_auth_user(
    request: Request,
    user_id: int,
    auth_context: AuthContext = Depends(verify_admin_auth_token),
):
    """Display details for a specific auth user."""
    try:
        auth_service = get_multi_user_auth_service()
        users = auth_service.list_users(include_inactive=True)

        user = next((u for u in users if u.id == user_id), None)
        if not user:
            raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="User not found")

        user_data = {
            "ID": user.id,
            "Email": user.email,
            "Username": user.username or "—",
            "Is Admin": "Yes" if user.is_admin else "No",
            "Is Active": "Yes" if user.is_active else "No",
            "Has Current Token": "Yes" if user.current_token else "No",
            "Token Expires": (
                user.token_expires_at.strftime("%Y-%m-%d %H:%M UTC")
                if user.token_expires_at
                else "—"
            ),
            "Last Login": (
                user.last_login_at.strftime("%Y-%m-%d %H:%M UTC")
                if user.last_login_at
                else "Never"
            ),
            "Created": user.created_at.strftime("%Y-%m-%d %H:%M UTC"),
            "Updated": (
                user.updated_at.strftime("%Y-%m-%d %H:%M UTC") if user.updated_at else "—"
            ),
        }

        return templates.TemplateResponse(
            "auth_users/user_detail.html",
            {
                "request": request,
                "record": user_data,
                "view_url": "get_auth_users_view",
                "title": f"Auth User: {user.email}",
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error viewing auth user {user_id}: {e}")
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=str(e))


@auth_users_views_router.get("/new/", response_class=HTMLResponse)
async def new_auth_user_view(
    request: Request, auth_context: AuthContext = Depends(verify_admin_auth_token)
):
    """Display form for adding a new auth user."""
    return templates.TemplateResponse(
        "auth_users/new_user.html",
        {
            "request": request,
            "view_url": "get_auth_users_view",
        },
    )


@auth_users_views_router.post("/new", response_class=HTMLResponse)
async def create_auth_user_view(
    request: Request,
    email: str = Form(...),
    username: str = Form(""),
    is_admin: bool = Form(False),
    auth_context: AuthContext = Depends(verify_admin_auth_token),
):
    """Handle form submission for creating a new auth user."""
    try:
        auth_service = get_multi_user_auth_service()

        # Clean up form data
        username = username.strip() if username else None

        # Add the user
        new_user = await auth_service.add_user(
            email=email,
            username=username,
            is_admin=is_admin,
            send_welcome_email=True,  # Send welcome email with token
        )

        logger.info(f"Created new auth user: {email} (ID: {new_user.id})")

        return """
        <div class="alert alert-success alert-dismissible fade show" role="alert">
            <strong>Success!</strong> User created successfully and welcome email sent with authentication token.
            <a href="/auth-users/{}" class="alert-link">View user details</a>
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
        """.format(
            new_user.id
        )

    except MultiUserAuthError as e:
        logger.warning(f"Failed to create auth user {email}: {e}")
        return f"""
        <div class="alert alert-danger alert-dismissible fade show" role="alert">
            <strong>Error!</strong> {str(e)}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
        """
    except Exception as e:
        logger.error(f"Unexpected error creating auth user {email}: {e}")
        return """
        <div class="alert alert-danger alert-dismissible fade show" role="alert">
            <strong>Error!</strong> Failed to create user. Please try again.
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
        """


@auth_users_views_router.post("/{user_id}/generate-token", response_class=HTMLResponse)
async def generate_token_view(
    request: Request,
    user_id: int,
    auth_context: AuthContext = Depends(verify_admin_auth_token),
):
    """Generate a new token for a user (HTMX endpoint)."""
    try:
        auth_service = get_multi_user_auth_service()
        users = auth_service.list_users(include_inactive=True)

        user = next((u for u in users if u.id == user_id), None)
        if not user:
            return """
            <div class="alert alert-danger alert-dismissible fade show" role="alert">
                <strong>Error!</strong> User not found.
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
            """

        if not user.is_active:
            return """
            <div class="alert alert-warning alert-dismissible fade show" role="alert">
                <strong>Warning!</strong> Cannot generate token for inactive user.
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
            """

        new_token = await auth_service.generate_user_token(user.email, send_email=True)
        logger.info(f"Generated new token for user: {user.email}")

        return f"""
        <div class="alert alert-success alert-dismissible fade show" role="alert">
            <strong>Success!</strong> New token generated and emailed to {user.email}.
            <br><strong>Token:</strong> <code>{new_token}</code>
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
        """

    except MultiUserAuthError as e:
        logger.error(f"Failed to generate token for user {user_id}: {e}")
        return f"""
        <div class="alert alert-danger alert-dismissible fade show" role="alert">
            <strong>Error!</strong> {str(e)}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
        """


@auth_users_views_router.post("/{user_id}/deactivate", response_class=HTMLResponse)
async def deactivate_auth_user_view(
    request: Request,
    user_id: int,
    auth_context: AuthContext = Depends(verify_admin_auth_token),
):
    """Deactivate a user (HTMX endpoint)."""
    try:
        auth_service = get_multi_user_auth_service()
        users = auth_service.list_users(include_inactive=True)

        user = next((u for u in users if u.id == user_id), None)
        if not user:
            return """
            <div class="alert alert-danger alert-dismissible fade show" role="alert">
                <strong>Error!</strong> User not found.
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
            """

        success = auth_service.deactivate_user(user.email)
        if success:
            logger.info(f"Deactivated auth user: {user.email}")
            return f"""
            <div class="alert alert-success alert-dismissible fade show" role="alert">
                <strong>Success!</strong> User {user.email} has been deactivated.
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
            """
        else:
            return """
            <div class="alert alert-danger alert-dismissible fade show" role="alert">
                <strong>Error!</strong> Failed to deactivate user.
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
            """

    except Exception as e:
        logger.error(f"Error deactivating user {user_id}: {e}")
        return """
        <div class="alert alert-danger alert-dismissible fade show" role="alert">
            <strong>Error!</strong> Failed to deactivate user. Please try again.
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
        """


################ API ROUTES ################


@auth_users_api_router.get("/users", response_model=List[UserResponse])
async def list_users_api(
    include_inactive: bool = False,
    auth_context: AuthContext = Depends(verify_admin_auth_token),
):
    """List all authenticated users."""
    try:
        auth_service = get_multi_user_auth_service()
        users = auth_service.list_users(include_inactive=include_inactive)

        return [UserResponse.from_auth_user(user) for user in users]

    except Exception as e:
        logger.error(f"Error listing users: {e}")
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=str(e))


@auth_users_api_router.get("/users/{user_id}", response_model=UserResponse)
async def get_user_api(
    user_id: int, auth_context: AuthContext = Depends(verify_admin_auth_token)
):
    """Get a specific user by ID."""
    try:
        auth_service = get_multi_user_auth_service()
        users = auth_service.list_users(include_inactive=True)

        user = next((u for u in users if u.id == user_id), None)
        if not user:
            raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="User not found")

        return UserResponse.from_auth_user(user)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user {user_id}: {e}")
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=str(e))


@auth_users_api_router.post("/users", response_model=UserResponse)
async def create_user_api(
    user_request: AddUserRequest,
    auth_context: AuthContext = Depends(verify_admin_auth_token),
):
    """Create a new authenticated user."""
    try:
        auth_service = get_multi_user_auth_service()

        new_user = await auth_service.add_user(
            email=user_request.email,
            username=user_request.username,
            is_admin=user_request.is_admin,
            send_welcome_email=True,
        )

        logger.info(f"Created new auth user via API: {user_request.email}")
        return UserResponse.from_auth_user(new_user)

    except MultiUserAuthError as e:
        logger.warning(f"Failed to create user via API: {e}")
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error creating user via API: {e}")
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST, detail="Failed to create user"
        )


@auth_users_api_router.post("/users/{user_id}/generate-token")
async def generate_token_api(
    user_id: int, auth_context: AuthContext = Depends(verify_admin_auth_token)
):
    """Generate a new token for a user."""
    try:
        auth_service = get_multi_user_auth_service()
        users = auth_service.list_users(include_inactive=True)

        user = next((u for u in users if u.id == user_id), None)
        if not user:
            raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="User not found")

        if not user.is_active:
            raise HTTPException(
                status_code=HTTP_400_BAD_REQUEST,
                detail="Cannot generate token for inactive user",
            )

        new_token = await auth_service.generate_user_token(user.email, send_email=True)
        logger.info(f"Generated new token via API for user: {user.email}")

        return {
            "message": "Token generated successfully and emailed to user",
            "user_email": user.email,
            "token": new_token,
            "expires_at": (datetime.utcnow() + timedelta(hours=24)).isoformat(),
        }

    except HTTPException:
        raise
    except MultiUserAuthError as e:
        logger.error(f"Failed to generate token via API for user {user_id}: {e}")
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error generating token via API for user {user_id}: {e}")
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST, detail="Failed to generate token"
        )


@auth_users_api_router.delete("/users/{user_id}")
async def deactivate_user_api(
    user_id: int, auth_context: AuthContext = Depends(verify_admin_auth_token)
):
    """Deactivate a user."""
    try:
        auth_service = get_multi_user_auth_service()
        users = auth_service.list_users(include_inactive=True)

        user = next((u for u in users if u.id == user_id), None)
        if not user:
            raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="User not found")

        success = auth_service.deactivate_user(user.email)
        if success:
            logger.info(f"Deactivated user via API: {user.email}")
            return {"message": "User deactivated successfully", "user_email": user.email}
        else:
            raise HTTPException(
                status_code=HTTP_400_BAD_REQUEST, detail="Failed to deactivate user"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deactivating user {user_id} via API: {e}")
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST, detail="Failed to deactivate user"
        )


@auth_users_api_router.post("/maintenance/clean-expired-tokens")
async def clean_expired_tokens_api(
    auth_context: AuthContext = Depends(verify_admin_auth_token),
):
    """Clean up expired tokens from all users."""
    try:
        auth_service = get_multi_user_auth_service()
        cleaned_count = auth_service.clean_expired_tokens()

        logger.info(f"Cleaned {cleaned_count} expired tokens via API")
        return {"message": "Token cleanup completed", "tokens_cleaned": cleaned_count}

    except Exception as e:
        logger.error(f"Error cleaning expired tokens via API: {e}")
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST, detail="Failed to clean expired tokens"
        )
