"""
JWT authentication dependencies for FastAPI route protection.

Provides Bearer token extraction, verification, and role checking.
"""

from typing import Optional
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.models.auth_models import TokenPayload
from app.services.jwt_service import get_jwt_service

# Bearer token security scheme
bearer_scheme = HTTPBearer(auto_error=False)


def extract_bearer_token(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> str:
    """
    Extract Bearer token from Authorization header.

    Args:
        credentials: HTTP authorization credentials

    Returns:
        JWT token string

    Raises:
        HTTPException: 401 if no token provided
    """
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=401,
            detail="Authorization header missing or invalid",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return credentials.credentials


def verify_jwt_token(token: str = Depends(extract_bearer_token)) -> TokenPayload:
    """
    Verify JWT token and return decoded payload.

    Checks:
    - Valid signature
    - Not expired
    - Not revoked (in revoked_tokens table)

    Args:
        token: JWT token from Authorization header

    Returns:
        TokenPayload with user information

    Raises:
        HTTPException: 401 if token invalid, expired, or revoked
    """
    jwt_service = get_jwt_service()
    return jwt_service.verify_and_decode(token)


def require_admin(payload: TokenPayload = Depends(verify_jwt_token)) -> TokenPayload:
    """
    Require user to be an admin.

    Args:
        payload: Decoded token payload

    Returns:
        TokenPayload if user is admin

    Raises:
        HTTPException: 403 if user is not admin
    """
    if not payload.is_admin:
        raise HTTPException(
            status_code=403,
            detail="Admin access required",
        )
    return payload


def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> Optional[TokenPayload]:
    """
    Get current user from token, but don't require authentication.

    Useful for endpoints that behave differently for authenticated users
    but don't require authentication.

    Args:
        credentials: HTTP authorization credentials (optional)

    Returns:
        TokenPayload if valid token provided, None otherwise
    """
    if not credentials or not credentials.credentials:
        return None

    try:
        jwt_service = get_jwt_service()
        return jwt_service.verify_and_decode(credentials.credentials)
    except HTTPException:
        # Invalid token, treat as anonymous user
        return None


def get_current_user(payload: TokenPayload = Depends(verify_jwt_token)) -> TokenPayload:
    """
    Get current authenticated user.

    Alias for verify_jwt_token for better semantic clarity in routes.

    Args:
        payload: Decoded token payload

    Returns:
        TokenPayload with user information
    """
    return payload
