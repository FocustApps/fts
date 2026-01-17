"""
Pydantic models for JWT authentication.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr


class TokenPayload(BaseModel):
    """JWT token payload structure with multi-tenant account context."""

    user_id: str
    email: str
    is_admin: bool
    exp: datetime
    jti: str
    # Multi-tenant fields
    is_super_admin: bool = False
    account_id: Optional[str] = None
    account_role: Optional[str] = None
    # Impersonation tracking
    impersonated_by: Optional[str] = None  # Super admin user_id who is impersonating
    impersonation_started_at: Optional[datetime] = None


class TokenResponse(BaseModel):
    """Response model for authentication endpoints."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds until access token expires
    previous_refresh_token: Optional[str] = None  # for frontend localStorage update


class LoginRequest(BaseModel):
    """Login request payload."""

    email: EmailStr
    password: str
    remember_me: bool = False


class RegisterRequest(BaseModel):
    """User registration request payload."""

    email: EmailStr
    password: str
    username: str


class RefreshRequest(BaseModel):
    """Token refresh request payload."""

    refresh_token: str


class PasswordResetRequest(BaseModel):
    """Password reset request payload."""

    email: EmailStr


class PasswordReset(BaseModel):
    """Password reset completion payload."""

    reset_token: str
    new_password: str


class SessionInfo(BaseModel):
    """Information about an active user session."""

    token_id: str
    device_info: Optional[str]
    ip_address: Optional[str]
    created_at: datetime
    last_used_at: Optional[datetime]
    is_current: bool  # true if this is the session making the request
