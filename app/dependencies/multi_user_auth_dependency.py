"""
Multi-user authentication dependency for FastAPI.

Provides authentication dependencies that support both the legacy single-user
token system and the new multi-user email-based authentication system.
"""

from fastapi import HTTPException, Request, status
from typing import Optional
from dataclasses import dataclass

from app.services.auth_service import get_auth_service, AuthTokenError
from app.services.multi_user_auth_service import (
    get_multi_user_auth_service,
    MultiUserAuthError,
)
from common.app_logging import create_logging

logger = create_logging()


@dataclass
class AuthContext:
    """Authentication context containing user and token information."""

    token: str
    user_email: Optional[str] = None
    user_id: Optional[int] = None
    username: Optional[str] = None
    is_admin: bool = False
    is_legacy_token: bool = False


async def verify_multi_user_auth_token(request: Request) -> AuthContext:
    """
    FastAPI dependency that validates tokens in multi-user authentication system.

    Supports both legacy single-user tokens and new multi-user email-based tokens.
    Priority order:
    1. Multi-user tokens (database-backed, email-specific)
    2. Legacy single-user tokens (file-based, global)

    Args:
        request: FastAPI request object

    Returns:
        AuthContext with user and token information

    Raises:
        HTTPException: 401 if authentication fails, 500 if service error
    """
    try:
        # Extract token from various sources
        auth_token = _extract_token_from_request(request)

        if not auth_token:
            logger.debug("Authentication failed: No token provided")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication token required. Provide token in X-Auth-Token header, Bearer token, or login via web interface.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Try multi-user authentication first
        auth_context = await _validate_multi_user_token(auth_token, request)
        if auth_context:
            return auth_context

        # Fallback to legacy single-user authentication
        auth_context = await _validate_legacy_token(auth_token, request)
        if auth_context:
            return auth_context

        # No valid authentication found
        logger.debug(
            f"Authentication failed: Invalid token from {_get_client_host(request)}"
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    except HTTPException:
        raise
    except (AuthTokenError, MultiUserAuthError) as e:
        logger.error(f"Auth service error during validation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication service temporarily unavailable.",
        )
    except Exception as e:
        logger.error(f"Unexpected error during authentication: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal authentication error.",
        )


async def verify_admin_auth_token(request: Request) -> AuthContext:
    """
    FastAPI dependency that validates tokens and requires admin privileges.

    Args:
        request: FastAPI request object

    Returns:
        AuthContext for admin user

    Raises:
        HTTPException: 401 if authentication fails, 403 if not admin
    """
    auth_context = await verify_multi_user_auth_token(request)

    # Legacy tokens are considered admin for backward compatibility
    if auth_context.is_legacy_token:
        logger.debug(
            f"Admin access granted via legacy token from {_get_client_host(request)}"
        )
        return auth_context

    # Check admin privileges for multi-user tokens
    if not auth_context.is_admin:
        logger.warning(
            f"Admin access denied for user {auth_context.user_email} from {_get_client_host(request)}"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required for this operation.",
        )

    logger.debug(
        f"Admin access granted for user {auth_context.user_email} from {_get_client_host(request)}"
    )
    return auth_context


async def verify_multi_user_auth_token_optional(
    request: Request,
) -> Optional[AuthContext]:
    """
    Optional multi-user authentication dependency that doesn't raise errors.

    Args:
        request: FastAPI request object

    Returns:
        AuthContext if authenticated, None if not
    """
    try:
        return await verify_multi_user_auth_token(request)
    except HTTPException:
        return None


def _extract_token_from_request(request: Request) -> Optional[str]:
    """Extract authentication token from request headers or cookies."""
    # Check X-Auth-Token header (preferred method)
    auth_token = request.headers.get("X-Auth-Token")

    if not auth_token:
        # Check Authorization header (Bearer format)
        authorization = request.headers.get("Authorization")
        if authorization and authorization.startswith("Bearer "):
            auth_token = authorization[7:]  # Remove "Bearer " prefix

    if not auth_token:
        # Check cookies (for web interface)
        auth_token = request.cookies.get("auth_token")

    return auth_token


async def _validate_multi_user_token(
    token: str, request: Request
) -> Optional[AuthContext]:
    """
    Validate token against multi-user authentication system.

    Returns AuthContext if valid, None if not found/invalid.
    """
    try:
        multi_user_service = get_multi_user_auth_service()

        # Check if we have user email from cookie (for targeted validation)
        user_email = request.cookies.get("user_email")
        if user_email:
            # Direct validation for specific user (much more efficient)
            if multi_user_service.validate_user_token(user_email, token):
                user = multi_user_service.get_user_by_email(user_email)
                if user and user.is_active:
                    logger.debug(
                        f"Multi-user authentication successful for {user.email} from {_get_client_host(request)}"
                    )
                    return AuthContext(
                        token=token,
                        user_email=user.email,
                        user_id=user.id,
                        username=user.username,
                        is_admin=user.is_admin,
                        is_legacy_token=False,
                    )
            return None

        # Fallback: If no email context, check all users (for backward compatibility)
        # This should only happen during the transition period or for API calls without cookies
        users = multi_user_service.list_users(include_inactive=False)

        for user in users:
            if multi_user_service.validate_user_token(user.email, token):
                logger.debug(
                    f"Multi-user authentication successful for {user.email} from {_get_client_host(request)} (fallback method)"
                )
                return AuthContext(
                    token=token,
                    user_email=user.email,
                    user_id=user.id,
                    username=user.username,
                    is_admin=user.is_admin,
                    is_legacy_token=False,
                )

        # Token didn't match any user
        return None

    except MultiUserAuthError as e:
        logger.debug(f"Multi-user token validation failed: {e}")
        return None
    except Exception as e:
        logger.debug(f"Error during multi-user token validation: {e}")
        return None


async def _validate_legacy_token(token: str, request: Request) -> Optional[AuthContext]:
    """
    Validate token against legacy single-user authentication system.

    Returns AuthContext if valid, None if not valid.
    """
    try:
        auth_service = get_auth_service()

        if auth_service.validate_token(token):
            logger.debug(
                f"Legacy authentication successful from {_get_client_host(request)}"
            )
            return AuthContext(
                token=token,
                user_email=None,  # Legacy system doesn't track email
                user_id=None,
                username="Legacy User",
                is_admin=True,  # Legacy tokens have admin privileges
                is_legacy_token=True,
            )

        return None

    except AuthTokenError as e:
        logger.debug(f"Legacy token validation failed: {e}")
        return None
    except Exception as e:
        logger.debug(f"Error during legacy token validation: {e}")
        return None


def _get_client_host(request: Request) -> str:
    """Get client host from request, with fallback."""
    return request.client.host if request.client else "unknown"


# Backward compatibility aliases
async def verify_auth_token(request: Request) -> str:
    """
    Backward compatibility alias for existing code.

    Returns just the token string like the original dependency.
    """
    auth_context = await verify_multi_user_auth_token(request)
    return auth_context.token


async def verify_auth_token_optional(request: Request) -> Optional[str]:
    """
    Backward compatibility alias for existing code.

    Returns just the token string or None.
    """
    auth_context = await verify_multi_user_auth_token_optional(request)
    return auth_context.token if auth_context else None
