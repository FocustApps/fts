"""
JWT service for creating and validating JSON Web Tokens.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import uuid4

from jose import jwt, JWTError, ExpiredSignatureError
from jose.exceptions import JWTClaimsError
from fastapi import HTTPException

from app.config import BaseAppConfig
from app.models.auth_models import TokenPayload


class JWTService:
    """Service for JWT token operations."""

    def __init__(self, config: BaseAppConfig):
        """
        Initialize JWT service.

        Args:
            config: Application configuration with JWT settings
        """
        self.config = config
        self.secret_key = config.jwt_secret_key
        self.algorithm = config.jwt_algorithm
        self.access_token_expire_hours = config.jwt_access_token_expire_hours

        if not self.secret_key:
            raise ValueError("JWT_SECRET_KEY must be set in environment variables")

    def create_access_token(
        self,
        user_id: str,
        email: str,
        is_admin: bool,
        is_super_admin: bool = False,
        account_id: Optional[str] = None,
        account_role: Optional[str] = None,
    ) -> str:
        """
        Create a new JWT access token with multi-tenant account context.

        Args:
            user_id: User's database ID
            email: User's email address
            is_admin: Whether user has admin privileges (deprecated, use is_super_admin)
            is_super_admin: Whether user is a super admin (can access all accounts)
            account_id: User's active account ID (from primary account or account switch)
            account_role: User's role in the active account (owner/admin/member/viewer)

        Returns:
            Encoded JWT token string
        """
        expires_delta = timedelta(hours=self.access_token_expire_hours)
        expire = datetime.now(timezone.utc) + expires_delta

        payload = {
            "sub": email,
            "user_id": user_id,
            "is_admin": is_admin,
            "is_super_admin": is_super_admin,
            "account_id": account_id,
            "account_role": account_role,
            "exp": expire,
            "jti": str(uuid4()),  # Unique token ID for revocation
        }

        encoded_jwt = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt

    def create_refresh_token(self, user_id: str, token_family_id: str) -> tuple[str, str]:
        """
        Create a new refresh token.

        Args:
            user_id: User's database ID
            token_family_id: UUID for token family (for rotation tracking)

        Returns:
            Tuple of (plaintext_token, bcrypt_hash)
        """
        import secrets
        import bcrypt

        # Generate cryptographically secure random token
        plaintext_token = secrets.token_hex(32)  # 64 characters

        # Hash for database storage
        token_bytes = plaintext_token.encode("utf-8")
        salt = bcrypt.gensalt(rounds=12)
        hashed = bcrypt.hashpw(token_bytes, salt)
        token_hash = hashed.decode("utf-8")

        return plaintext_token, token_hash

    def decode_token(self, token: str) -> dict:
        """
        Decode JWT token without verification.

        Args:
            token: JWT token string

        Returns:
            Decoded token payload dict

        Raises:
            JWTError: If token is malformed
        """
        return jwt.decode(token, self.secret_key, algorithms=[self.algorithm])

    def verify_and_decode(self, token: str, check_revoked: bool = True) -> TokenPayload:
        """
        Verify JWT signature and decode payload.

        Args:
            token: JWT token string
            check_revoked: Whether to check if token is revoked (default True)

        Returns:
            TokenPayload with decoded data

        Raises:
            HTTPException: If token is invalid, expired, or revoked
        """
        try:
            payload = self.decode_token(token)

            # Extract claims
            user_id = payload.get("user_id")
            email = payload.get("sub")
            is_admin = payload.get("is_admin", False)
            is_super_admin = payload.get("is_super_admin", False)
            account_id = payload.get("account_id")
            account_role = payload.get("account_role")
            exp = datetime.fromtimestamp(payload.get("exp"), tz=timezone.utc)
            jti = payload.get("jti")

            if not all([user_id, email, jti]):
                raise HTTPException(status_code=401, detail="Invalid token claims")

            # Check revocation if requested
            if check_revoked:
                from common.service_connections.db_service.db_manager import DB_ENGINE
                from common.service_connections.db_service.database.engine import (
                    get_database_session as session,
                )
                from common.service_connections.db_service.models.account_models.revoked_token_model import (
                    is_token_revoked,
                )

                with session(DB_ENGINE) as db_session:
                    if is_token_revoked(jti, db_session, DB_ENGINE):
                        raise HTTPException(
                            status_code=401, detail="Token has been revoked"
                        )

            return TokenPayload(
                user_id=user_id,
                email=email,
                is_admin=is_admin,
                is_super_admin=is_super_admin,
                account_id=account_id,
                account_role=account_role,
                exp=exp,
                jti=jti,
            )

        except ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token has expired")
        except JWTClaimsError:
            raise HTTPException(status_code=401, detail="Invalid token claims")
        except JWTError:
            raise HTTPException(status_code=401, detail="Invalid token")

    def revoke_token(self, jti: str, expires_at: datetime):
        """
        Revoke a token by adding its JTI to the revoked tokens table.

        Args:
            jti: Token's unique identifier
            expires_at: When the token would naturally expire
        """
        from common.service_connections.db_service.db_manager import DB_ENGINE
        from common.service_connections.db_service.models.account_models.revoked_token_model import (
            insert_revoked_token,
        )

        insert_revoked_token(jti, expires_at, DB_ENGINE)

    def get_token_expiry_hours(self, token: str) -> int:
        """
        Get hours until token expires (for UI display).

        Args:
            token: JWT token string

        Returns:
            Hours until expiry (rounded down)
        """
        try:
            payload = self.decode_token(token)
            exp_timestamp = payload.get("exp")
            if not exp_timestamp:
                return 0

            exp_datetime = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)
            now = datetime.now(timezone.utc)
            delta = exp_datetime - now

            return max(0, int(delta.total_seconds() / 3600))
        except Exception:
            return 0


# Singleton instance
_jwt_service: Optional[JWTService] = None


def get_jwt_service() -> JWTService:
    """Get or create JWT service singleton."""
    global _jwt_service
    if _jwt_service is None:
        from app.config import get_base_app_config

        _jwt_service = JWTService(get_base_app_config())
    return _jwt_service
