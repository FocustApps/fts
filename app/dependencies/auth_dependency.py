"""
FastAPI dependency for API authentication.

Provides reusable authentication dependency that validates 64-bit tokens
from request headers following FastAPI dependency injection patterns.
"""

from fastapi import HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional

from app.services.auth_service import get_auth_service, AuthTokenError
from common.app_logging import create_logging

logger = create_logging()

# Optional: Use HTTPBearer for automatic OpenAPI documentation
security = HTTPBearer(auto_error=False)


async def verify_auth_token(request: Request) -> str:
    """
    FastAPI dependency that validates API authentication token.

    Checks for token in X-Auth-Token header, Authorization header, and cookies.

    Args:
        request: FastAPI request object

    Returns:
        Valid token string

    Raises:
        HTTPException: 401 if token missing/invalid, 500 if auth service error
    """
    try:
        # Get token from X-Auth-Token header (preferred method)
        auth_token = request.headers.get("X-Auth-Token")

        if not auth_token:
            # Also check Authorization header as fallback (Bearer format)
            authorization = request.headers.get("Authorization")
            if authorization and authorization.startswith("Bearer "):
                auth_token = authorization[7:]  # Remove "Bearer " prefix

        if not auth_token:
            # Check for token in cookies (for web interface)
            auth_token = request.cookies.get("auth_token")

        if not auth_token:
            logger.debug("Authentication failed: No token provided in headers or cookies")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication token required. Provide token in X-Auth-Token header, Bearer token, or login via web interface.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Get auth service and validate token
        auth_service = get_auth_service()

        if not auth_service.validate_token(auth_token):
            logger.debug(
                f"Authentication failed: Invalid token from {request.client.host if request.client else 'unknown'}"
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired authentication token.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        logger.debug(
            f"Authentication successful for {request.client.host if request.client else 'unknown'}"
        )
        return auth_token

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except AuthTokenError as e:
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


async def verify_auth_token_optional(request: Request) -> Optional[str]:
    """
    Optional authentication dependency that doesn't raise errors.

    Useful for endpoints that have different behavior for authenticated vs anonymous users.

    Args:
        request: FastAPI request object

    Returns:
        Valid token string or None if not authenticated
    """
    try:
        return await verify_auth_token(request)
    except HTTPException:
        return None


# Alternative dependency using HTTPBearer (for OpenAPI documentation)
async def verify_auth_token_bearer(
    request: Request, credentials: Optional[HTTPAuthorizationCredentials] = security
) -> str:
    """
    Alternative auth dependency using FastAPI's HTTPBearer security.

    This version automatically adds Bearer token authentication to OpenAPI docs.

    Args:
        request: FastAPI request object
        credentials: Bearer token credentials from FastAPI security

    Returns:
        Valid token string

    Raises:
        HTTPException: 401 if token missing/invalid, 500 if auth service error
    """
    try:
        # Check for token in standard Bearer format first
        auth_token = None
        if credentials:
            auth_token = credentials.credentials

        # Fallback to X-Auth-Token header
        if not auth_token:
            auth_token = request.headers.get("X-Auth-Token")

        # Check for token in cookies (for web interface)
        if not auth_token:
            auth_token = request.cookies.get("auth_token")

        if not auth_token:
            logger.debug("Authentication failed: No token provided")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication token required. Provide as Bearer token, X-Auth-Token header, or login via web interface.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Validate token
        auth_service = get_auth_service()

        if not auth_service.validate_token(auth_token):
            logger.debug(
                f"Authentication failed: Invalid token from {request.client.host if request.client else 'unknown'}"
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired authentication token.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        logger.debug(
            f"Authentication successful for {request.client.host if request.client else 'unknown'}"
        )
        return auth_token

    except HTTPException:
        raise
    except AuthTokenError as e:
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
