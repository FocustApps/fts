"""
Authentication API routes for JWT-based authentication.

Handles user registration, login, token refresh, logout, password reset,
and session management.
"""

import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import get_base_app_config
from app.models.auth_models import (
    RegisterRequest,
    LoginRequest,
    RefreshRequest,
    TokenResponse,
    PasswordResetRequest,
    PasswordReset,
    SessionInfo,
)
from app.dependencies.jwt_auth_dependency import get_current_user
from app.services.user_auth_service import get_user_auth_service
from common.service_connections.db_service.db_manager import DB_ENGINE

logger = logging.getLogger(__name__)

# Get config for rate limiting
config = get_base_app_config()

# Create router
auth_api_router = APIRouter(prefix="/api/auth", tags=["authentication"])

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)


# Helper to conditionally apply rate limiting
def conditional_limit(limit_string: str):
    """Apply rate limit only if enabled in config."""

    def decorator(func):
        if config.rate_limit_enabled:
            return limiter.limit(limit_string)(func)
        return func

    return decorator


@auth_api_router.post(
    "/register", response_model=dict, include_in_schema=True, status_code=201
)
@conditional_limit("5/hour")
async def register(request: Request, register_data: RegisterRequest):
    """
    Register a new user account.

    Rate limited to 5 requests per hour per IP to prevent abuse.

    Returns:
        Success message with user email

    Raises:
        400: Email already exists or password too weak
    """
    auth_service = get_user_auth_service(DB_ENGINE)
    user = auth_service.register_user(register_data)
    logger.info(f"User registered: {user.email}")
    return {
        "message": "User registered successfully",
        "email": user.email,
        "username": user.username,
    }


@auth_api_router.post("/login", response_model=TokenResponse, include_in_schema=True)
@conditional_limit("10/minute")
async def login(request: Request, login_data: LoginRequest):
    """
    Authenticate user and return JWT tokens.

    Rate limited to 10 requests per minute per IP to prevent brute force.

    Returns:
        TokenResponse with access_token, refresh_token, and metadata

    Raises:
        401: Invalid credentials or inactive account
    """
    # Extract device info and IP
    device_info = request.headers.get("user-agent")
    ip_address = request.client.host if request.client else None

    auth_service = get_user_auth_service(DB_ENGINE)
    return auth_service.authenticate(login_data, device_info, ip_address)


@auth_api_router.post("/refresh", response_model=TokenResponse, include_in_schema=True)
@conditional_limit("30/minute")
async def refresh(request: Request, refresh_data: RefreshRequest):
    """
    Refresh access and refresh tokens.

    Implements token rotation - old refresh token is invalidated and new one issued.
    Detects token reuse attacks and revokes entire token family if detected.

    Rate limited to 30 requests per minute per IP.

    Returns:
        TokenResponse with new tokens and previous_refresh_token for client update

    Raises:
        401: Invalid, expired, or reused token
    """
    device_info = request.headers.get("user-agent")
    ip_address = request.client.host if request.client else None

    auth_service = get_user_auth_service(DB_ENGINE)
    return auth_service.refresh_tokens(
        refresh_data.refresh_token, device_info, ip_address
    )


@auth_api_router.post("/logout", response_model=dict, include_in_schema=True)
async def logout(request: Request, refresh_data: RefreshRequest):
    """
    Logout from current device.

    Revokes the provided refresh token and corresponding access token.

    Returns:
        Success message

    Raises:
        401: Token not found
    """
    auth_service = get_user_auth_service(DB_ENGINE)
    auth_service.logout(refresh_data.refresh_token)
    return {"message": "Logged out successfully"}


@auth_api_router.post("/logout-all", response_model=dict, include_in_schema=True)
async def logout_all(current_user=Depends(get_current_user)):
    """
    Logout from all devices.

    Requires authentication. Revokes all refresh tokens and access tokens for the user.

    Returns:
        Success message with count of revoked sessions

    Raises:
        401: Not authenticated
    """
    auth_service = get_user_auth_service(DB_ENGINE)
    count = auth_service.logout_all(current_user.user_id)
    return {
        "message": "Logged out from all devices",
        "sessions_revoked": count,
    }


@auth_api_router.get(
    "/sessions", response_model=List[SessionInfo], include_in_schema=True
)
async def get_sessions(current_user=Depends(get_current_user)):
    """
    Get all active sessions for current user.

    Returns list of sessions with device info, IP, creation time, and last used time.
    Used for device management UI.

    Returns:
        List of SessionInfo objects

    Raises:
        401: Not authenticated
    """
    auth_service = get_user_auth_service(DB_ENGINE)
    return auth_service.get_user_sessions(current_user.user_id)


@auth_api_router.delete(
    "/sessions/{token_id}", response_model=dict, include_in_schema=True
)
async def revoke_session(token_id: str, current_user=Depends(get_current_user)):
    """
    Revoke a specific session.

    Allows users to remotely logout from a specific device.

    Args:
        token_id: ID of the token to revoke

    Returns:
        Success message

    Raises:
        401: Not authenticated
        404: Session not found or doesn't belong to user
    """
    auth_service = get_user_auth_service(DB_ENGINE)
    auth_service.revoke_session(current_user.user_id, token_id)
    return {"message": "Session revoked successfully"}


@auth_api_router.post(
    "/password-reset-request", response_model=dict, include_in_schema=True
)
@conditional_limit("3/hour")
async def password_reset_request(request: Request, reset_data: PasswordResetRequest):
    """
    Request a password reset.

    Generates a reset token and sends it via email (email sending not yet implemented).
    Rate limited to 3 requests per hour per IP.

    Returns:
        Success message (doesn't reveal if email exists)

    Note:
        Currently returns the token in response for testing.
        In production, token should only be sent via email.
    """
    auth_service = get_user_auth_service(DB_ENGINE)
    try:
        reset_token = auth_service.request_password_reset(reset_data.email)
        # TODO: Send email with reset_token using EmailService
        logger.info(f"Password reset requested for: {reset_data.email}")

        # TEMPORARY: Return token in response for testing
        # Remove this in production - token should only be in email
        return {
            "message": "If email exists, password reset link has been sent",
            "reset_token": reset_token,  # TODO: Remove in production
        }
    except HTTPException:
        # Return same message whether email exists or not (security)
        return {
            "message": "If email exists, password reset link has been sent",
        }


@auth_api_router.post("/password-reset", response_model=dict, include_in_schema=True)
@conditional_limit("5/hour")
async def password_reset(request: Request, reset_data: PasswordReset):
    """
    Complete password reset with token.

    Validates reset token and updates user password.
    Revokes all existing sessions (forces re-login).
    Rate limited to 5 requests per hour per IP.

    Returns:
        Success message

    Raises:
        400: Invalid or expired token, or password too weak
    """
    auth_service = get_user_auth_service(DB_ENGINE)
    auth_service.reset_password(reset_data.reset_token, reset_data.new_password)
    return {"message": "Password reset successfully. Please login with new password."}
