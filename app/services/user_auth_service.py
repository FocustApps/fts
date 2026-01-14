"""
User authentication service for JWT-based authentication.

Handles user registration, login, token refresh with rotation,
logout, password reset, and session management.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, List
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy.engine import Engine

from app.config import get_base_app_config
from app.models.auth_models import (
    RegisterRequest,
    LoginRequest,
    TokenResponse,
    SessionInfo,
)
from app.services.jwt_service import get_jwt_service
from app.services.password_service import get_password_service
from common.service_connections.db_service.models.account_models.auth_user_model import (
    AuthUserModel,
    query_auth_user_by_email,
    insert_auth_user,
    check_email_exists,
    update_auth_user_by_id,
)
from common.service_connections.db_service.models.account_models.auth_token_model import (
    AuthTokenModel,
    insert_auth_token,
    query_active_tokens_by_user,
    query_auth_token_by_id,
    update_token_inactive,
    update_all_user_tokens_inactive,
    update_all_family_tokens_inactive,
)
from common.service_connections.db_service.database import AuthTokenTable, AuthUserTable
from common.service_connections.db_service.database.engine import (
    get_database_session as session,
)

logger = logging.getLogger(__name__)


class UserAuthService:
    """Service for user authentication and session management."""

    def __init__(self, engine: Engine):
        self.engine = engine
        self.jwt_service = get_jwt_service()
        self.password_service = get_password_service()
        self.config = get_base_app_config()

    def register_user(self, request: RegisterRequest) -> AuthUserModel:
        """
        Register a new user with email and password.

        Args:
            request: Registration request with email, password, username

        Returns:
            Created AuthUserModel

        Raises:
            HTTPException: 400 if email exists or password invalid
        """
        # Check if email already exists
        if check_email_exists(request.email, session, self.engine):
            raise HTTPException(status_code=400, detail="Email already registered")

        # Validate password strength
        is_valid, error_msg = self.password_service.validate_password_strength(
            request.password
        )
        if not is_valid:
            raise HTTPException(status_code=400, detail=error_msg)

        # Hash password and create user
        password_hash = self.password_service.hash_password(request.password)
        user = AuthUserModel(
            email=request.email,
            username=request.username,
            password_hash=password_hash,
            is_active=True,
            is_admin=False,
            created_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )

        user = insert_auth_user(user, session, self.engine)
        logger.info(f"New user registered: {request.email}")
        return user

    def authenticate(
        self,
        request: LoginRequest,
        device_info: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> TokenResponse:
        """
        Authenticate user with email and password, create JWT tokens.

        Args:
            request: Login request with email, password, remember_me
            device_info: User agent string
            ip_address: Client IP address

        Returns:
            TokenResponse with access and refresh tokens

        Raises:
            HTTPException: 401 if credentials invalid or user inactive
        """
        # Query user by email
        user = query_auth_user_by_email(request.email, session, self.engine)
        if not user:
            raise HTTPException(status_code=401, detail="Invalid email or password")

        # Check if user is active
        if not user.is_active:
            raise HTTPException(status_code=401, detail="Account is inactive")

        # Verify password
        if not self.password_service.verify_password(
            request.password, user.password_hash
        ):
            raise HTTPException(status_code=401, detail="Invalid email or password")

        # Create token family for rotation tracking
        token_family_id = str(uuid4())

        # Generate access and refresh tokens
        access_token = self.jwt_service.create_access_token(
            user_id=user.auth_user_id,
            email=user.email,
            is_admin=user.is_admin,
        )

        # Decode to get JTI
        access_payload = self.jwt_service.decode_token(access_token)
        access_jti = access_payload["jti"]

        # Generate refresh token
        refresh_token, refresh_token_hash = self.jwt_service.create_refresh_token(
            user_id=user.auth_user_id,
            token_family_id=token_family_id,
        )

        # Calculate expiry
        expires_at = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(
            days=self.config.jwt_refresh_token_expire_days
        )

        # Store refresh token in database
        token_model = AuthTokenModel(
            auth_user_id=user.auth_user_id,
            refresh_token_hash=refresh_token_hash,
            access_token_jti=access_jti,
            token_family_id=token_family_id,
            previous_token_id=None,
            token_expires_at=expires_at,
            device_info=device_info,
            ip_address=ip_address,
            is_active=True,
            created_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )

        insert_auth_token(token_model, self.engine)

        # Update user last login
        user.last_login_at = datetime.now(timezone.utc).replace(tzinfo=None)
        update_auth_user_by_id(user.auth_user_id, user, session, self.engine)

        logger.info(f"User authenticated: {user.email}")

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=self.config.jwt_access_token_expire_hours * 3600,
            previous_refresh_token=None,
        )

    def refresh_tokens(
        self,
        refresh_token: str,
        device_info: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> TokenResponse:
        """
        Refresh access and refresh tokens with rotation.

        Implements token family tracking for reuse detection:
        - If token is already inactive but exists in DB, it's a reuse attempt
        - Revokes entire token family to prevent security breach

        Args:
            refresh_token: Current refresh token (plaintext)
            device_info: User agent string
            ip_address: Client IP address

        Returns:
            TokenResponse with new tokens and previous_refresh_token

        Raises:
            HTTPException: 401 if token invalid, expired, or reuse detected
        """
        # Hash the refresh token to query database
        with session(self.engine) as db_session:
            # Try each active token (bcrypt comparison needed)
            user = None
            current_token = None

            # Get user ID from token if it's a valid JWT format (for optimization)
            # Otherwise we need to check all tokens
            all_tokens = db_session.query(AuthTokenTable).filter_by(is_active=True).all()

            for db_token in all_tokens:
                if self.password_service.verify_password(
                    refresh_token, db_token.refresh_token_hash
                ):
                    current_token = AuthTokenModel(**db_token.__dict__)
                    break

            if not current_token:
                # Check if token exists but is inactive (reuse detection)
                all_inactive = (
                    db_session.query(AuthTokenTable).filter_by(is_active=False).all()
                )
                for db_token in all_inactive:
                    if self.password_service.verify_password(
                        refresh_token, db_token.refresh_token_hash
                    ):
                        # Token reuse detected! Revoke entire family
                        logger.warning(
                            f"Token reuse detected for family {db_token.token_family_id}"
                        )
                        update_all_family_tokens_inactive(
                            db_token.token_family_id, self.engine
                        )
                        raise HTTPException(
                            status_code=401,
                            detail="Token reuse detected. All sessions revoked.",
                        )

                # Token not found at all
                raise HTTPException(status_code=401, detail="Invalid refresh token")

            # Check if token is expired
            if current_token.token_expires_at < datetime.now(timezone.utc).replace(
                tzinfo=None
            ):
                update_token_inactive(current_token.token_id, self.engine)
                raise HTTPException(status_code=401, detail="Refresh token expired")

            # Get user
            user_record = db_session.get(AuthUserTable, current_token.auth_user_id)
            if not user_record:
                raise HTTPException(status_code=401, detail="User not found")

            user = query_auth_user_by_email(
                user_record.email,
                session,
                self.engine,
            )

            if not user or not user.is_active:
                raise HTTPException(status_code=401, detail="User not found or inactive")

            # Generate new access and refresh tokens
            new_access_token = self.jwt_service.create_access_token(
                user_id=user.auth_user_id,
                email=user.email,
                is_admin=user.is_admin,
            )

            new_access_payload = self.jwt_service.decode_token(new_access_token)
            new_access_jti = new_access_payload["jti"]

            new_refresh_token, new_refresh_hash = self.jwt_service.create_refresh_token(
                user_id=user.auth_user_id,
                token_family_id=current_token.token_family_id,
            )

            # Calculate new expiry
            new_expires_at = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(
                days=self.config.jwt_refresh_token_expire_days
            )

            # Create new token record with previous_token_id set
            new_token = AuthTokenModel(
                auth_user_id=user.auth_user_id,
                refresh_token_hash=new_refresh_hash,
                access_token_jti=new_access_jti,
                token_family_id=current_token.token_family_id,
                previous_token_id=current_token.token_id,
                token_expires_at=new_expires_at,
                device_info=device_info or current_token.device_info,
                ip_address=ip_address or current_token.ip_address,
                is_active=True,
                created_at=datetime.now(timezone.utc).replace(tzinfo=None),
            )

            insert_auth_token(new_token, self.engine)

            # Mark old token as inactive
            update_token_inactive(current_token.token_id, self.engine)

            logger.info(f"Tokens refreshed for user: {user.email}")

            return TokenResponse(
                access_token=new_access_token,
                refresh_token=new_refresh_token,
                token_type="bearer",
                expires_in=self.config.jwt_access_token_expire_hours * 3600,
                previous_refresh_token=refresh_token,
            )

    def logout(self, refresh_token: str) -> bool:
        """
        Logout user from current device (revoke single refresh token).

        Args:
            refresh_token: Refresh token to revoke

        Returns:
            True if successful

        Raises:
            HTTPException: 401 if token not found
        """
        with session(self.engine) as db_session:
            # Find token by hash
            all_tokens = db_session.query(AuthTokenTable).filter_by(is_active=True).all()
            current_token = None

            for db_token in all_tokens:
                if self.password_service.verify_password(
                    refresh_token, db_token.refresh_token_hash
                ):
                    current_token = AuthTokenModel(**db_token.__dict__)
                    break

            if not current_token:
                raise HTTPException(status_code=401, detail="Token not found")

            # Mark token inactive
            update_token_inactive(current_token.token_id, self.engine)

            # Revoke access token JTI
            access_expiry = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(
                hours=self.config.jwt_access_token_expire_hours
            )
            self.jwt_service.revoke_token(current_token.access_token_jti, access_expiry)

            logger.info(f"User logged out: {current_token.auth_user_id}")
            return True

    def logout_all(self, user_id: str) -> int:
        """
        Logout user from all devices (revoke all refresh tokens).

        Args:
            user_id: User ID

        Returns:
            Number of tokens revoked
        """
        # Get all active tokens for user
        with session(self.engine) as db_session:
            active_tokens = query_active_tokens_by_user(user_id, db_session, self.engine)

            # Revoke all access token JTIs
            access_expiry = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(
                hours=self.config.jwt_access_token_expire_hours
            )
            for token in active_tokens:
                self.jwt_service.revoke_token(token.access_token_jti, access_expiry)

        # Mark all refresh tokens inactive
        count = update_all_user_tokens_inactive(user_id, self.engine)
        logger.info(f"User logged out from all devices: {user_id} ({count} sessions)")
        return count

    def get_user_sessions(self, user_id: str) -> List[SessionInfo]:
        """
        Get all active sessions for a user (for device management UI).

        Args:
            user_id: User ID

        Returns:
            List of SessionInfo objects
        """
        with session(self.engine) as db_session:
            tokens = query_active_tokens_by_user(user_id, db_session, self.engine)

            sessions = []
            for token in tokens:
                sessions.append(
                    SessionInfo(
                        token_id=token.token_id,
                        device_info=token.device_info or "Unknown device",
                        ip_address=token.ip_address or "Unknown",
                        created_at=token.created_at,
                        last_used_at=token.last_used_at or token.created_at,
                        is_current=False,  # Would need current token to determine
                    )
                )

            return sessions

    def revoke_session(self, user_id: str, token_id: str) -> bool:
        """
        Revoke a specific user session (for device management UI).

        Args:
            user_id: User ID (for authorization check)
            token_id: Token ID to revoke

        Returns:
            True if successful

        Raises:
            HTTPException: 404 if token not found or doesn't belong to user
        """
        with session(self.engine) as db_session:
            token = query_auth_token_by_id(token_id, db_session, self.engine)

            if not token or token.auth_user_id != user_id:
                raise HTTPException(status_code=404, detail="Session not found")

            # Revoke the token
            update_token_inactive(token_id, self.engine)

            # Revoke access token JTI
            access_expiry = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(
                hours=self.config.jwt_access_token_expire_hours
            )
            self.jwt_service.revoke_token(token.access_token_jti, access_expiry)

            logger.info(f"Session revoked: {token_id} for user {user_id}")
            return True

    def request_password_reset(self, email: str) -> str:
        """
        Generate and store password reset token for a user.

        Args:
            email: User email address

        Returns:
            Reset token (to be sent via email)

        Raises:
            HTTPException: 404 if user not found
        """
        user = query_auth_user_by_email(email, session, self.engine)
        if not user:
            # Don't reveal if email exists
            logger.warning(f"Password reset requested for non-existent email: {email}")
            raise HTTPException(
                status_code=404, detail="If email exists, reset link sent"
            )

        # Generate reset token
        reset_token = self.password_service.generate_reset_token()
        reset_expires = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(
            hours=1
        )

        # Update user with reset token
        user.password_reset_token = reset_token
        user.password_reset_expires = reset_expires
        update_auth_user_by_id(user.auth_user_id, user, session, self.engine)

        logger.info(f"Password reset token generated for user: {email}")
        return reset_token

    def reset_password(self, reset_token: str, new_password: str) -> bool:
        """
        Reset user password with reset token.

        Args:
            reset_token: Password reset token
            new_password: New password

        Returns:
            True if successful

        Raises:
            HTTPException: 400 if token invalid or expired, or password weak
        """
        # Find user by reset token
        with session(self.engine) as db_session:
            user_table = (
                db_session.query(AuthUserTable)
                .filter_by(password_reset_token=reset_token)
                .first()
            )

            if not user_table:
                raise HTTPException(status_code=400, detail="Invalid reset token")

            user = AuthUserModel(**user_table.__dict__)

            # Check if token is expired
            if (
                not user.password_reset_expires
                or user.password_reset_expires
                < datetime.now(timezone.utc).replace(tzinfo=None)
            ):
                raise HTTPException(status_code=400, detail="Reset token expired")

            # Validate new password
            is_valid, error_msg = self.password_service.validate_password_strength(
                new_password
            )
            if not is_valid:
                raise HTTPException(status_code=400, detail=error_msg)

            # Hash new password and update user
            user.password_hash = self.password_service.hash_password(new_password)
            user.password_reset_token = None
            user.password_reset_expires = None
            update_auth_user_by_id(user.auth_user_id, user, session, self.engine)

            # Revoke all existing tokens (force re-login)
            self.logout_all(user.auth_user_id)

            logger.info(f"Password reset successful for user: {user.email}")
            return True


# Singleton instance
_user_auth_service: Optional[UserAuthService] = None


def get_user_auth_service(engine: Engine) -> UserAuthService:
    """Get or create singleton UserAuthService instance."""
    global _user_auth_service
    if _user_auth_service is None:
        _user_auth_service = UserAuthService(engine)
    return _user_auth_service
