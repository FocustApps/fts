"""
Authentication service for API token management.

Provides secure 64-bit token generation, validation, persistence, and rotation
following FTS service patterns with proper error handling and atomic operations.
"""

import os
import secrets
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional, Callable, Any
import tempfile
import shutil

from common.app_logging import create_logging

logger = create_logging()


class AuthTokenError(Exception):
    """Base exception for authentication token operations."""

    pass


class TokenValidationError(AuthTokenError):
    """Raised when token validation fails."""

    pass


class TokenPersistenceError(AuthTokenError):
    """Raised when token file operations fail."""

    pass


class AuthService:
    """
    Manages API authentication tokens with automatic rotation and persistence.

    Features:
    - Cryptographically secure 64-bit token generation
    - Timing-safe token validation
    - Atomic file persistence with backup
    - Configurable external sync hooks
    - Thread-safe operations
    """

    def __init__(
        self,
        token_file_path: Path,
        rotation_interval_minutes: int = 30,
        external_sync_callback: Optional[Callable[[str, Path], None]] = None,
    ):
        """
        Initialize the authentication service.

        Args:
            token_file_path: Path where tokens are persisted
            rotation_interval_minutes: How often tokens rotate (default 30)
            external_sync_callback: Optional callback for external sync (token, file_path)
        """
        self.token_file_path = Path(token_file_path)
        self.rotation_interval_minutes = rotation_interval_minutes
        self.external_sync_callback = external_sync_callback
        self._current_token: Optional[str] = None
        self._token_created_at: Optional[datetime] = None
        self._lock = threading.RLock()

        # Ensure token directory exists
        self.token_file_path.parent.mkdir(parents=True, exist_ok=True)

        logger.info(f"AuthService initialized with token file: {self.token_file_path}")

    def generate_token(self) -> str:
        """
        Generate a cryptographically secure 64-character token.

        Returns:
            Hex-encoded 256-bit token (64 characters)
        """
        # Generate 32 bytes (256 bits) of cryptographically secure random data
        token_bytes = secrets.token_bytes(32)
        token_hex = token_bytes.hex()

        logger.debug(
            f"Generated new 64-character token: {token_hex[:4]}...{token_hex[-4:]}"
        )
        return token_hex

    def validate_token(self, provided_token: str) -> bool:
        """
        Validate a provided token against the current active token.

        Uses timing-safe comparison to prevent timing attacks.

        Args:
            provided_token: Token to validate

        Returns:
            True if token is valid and current, False otherwise
        """
        if not provided_token:
            logger.debug("Token validation failed: empty token provided")
            return False

        current_token = self.get_current_token()
        if not current_token:
            logger.debug("Token validation failed: no current token available")
            return False

        # Use timing-safe comparison to prevent timing attacks
        is_valid = secrets.compare_digest(provided_token, current_token)

        if is_valid:
            logger.debug("Token validation successful")
        else:
            logger.debug("Token validation failed: token mismatch")

        return is_valid

    def get_current_token(self) -> Optional[str]:
        """
        Get the current active token, loading from file if necessary.

        Returns:
            Current token or None if no valid token exists
        """
        with self._lock:
            # Return cached token if still valid
            if self._current_token and self._is_token_current():
                return self._current_token

            # Try to load from file
            try:
                self._load_token_from_file()
                if self._current_token and self._is_token_current():
                    return self._current_token
            except TokenPersistenceError:
                logger.warning("Failed to load token from file, generating new token")

            # Generate new token if none exists or expired
            return self._rotate_token()

    def rotate_token(self) -> str:
        """
        Force immediate token rotation.

        Returns:
            New token
        """
        with self._lock:
            return self._rotate_token()

    def _rotate_token(self) -> str:
        """Internal method to generate and persist a new token."""
        try:
            new_token = self.generate_token()
            self._current_token = new_token
            self._token_created_at = datetime.now(timezone.utc)

            # Persist to file atomically
            self._save_token_to_file()

            # Trigger external sync if configured
            if self.external_sync_callback:
                try:
                    self.external_sync_callback(new_token, self.token_file_path)
                    logger.info("External sync callback executed successfully")
                except Exception as e:
                    logger.error(f"External sync callback failed: {e}")
                    # Don't fail the rotation for external sync issues

            logger.info(f"Token rotated successfully: {new_token[:4]}...{new_token[-4:]}")
            return new_token

        except Exception as e:
            logger.error(f"Token rotation failed: {e}")
            raise AuthTokenError(f"Failed to rotate token: {e}")

    def _is_token_current(self) -> bool:
        """Check if the current token is still within its validity period."""
        if not self._token_created_at:
            return False

        expiry_time = self._token_created_at + timedelta(
            minutes=self.rotation_interval_minutes
        )
        return datetime.now(timezone.utc) < expiry_time

    def _save_token_to_file(self) -> None:
        """
        Atomically save the current token to file.

        Uses atomic write (write to temp file, then move) to prevent corruption.
        """
        if not self._current_token or not self._token_created_at:
            raise TokenPersistenceError("No current token to save")

        try:
            # Create token data
            token_data = {
                "token": self._current_token,
                "created_at": self._token_created_at.isoformat(),
                "expires_at": (
                    self._token_created_at
                    + timedelta(minutes=self.rotation_interval_minutes)
                ).isoformat(),
            }

            # Write to temporary file first (atomic operation)
            temp_dir = self.token_file_path.parent
            with tempfile.NamedTemporaryFile(
                mode="w", dir=temp_dir, delete=False, suffix=".tmp"
            ) as temp_file:
                # Write token data as simple key=value format for easy parsing
                temp_file.write(f"token={token_data['token']}\n")
                temp_file.write(f"created_at={token_data['created_at']}\n")
                temp_file.write(f"expires_at={token_data['expires_at']}\n")
                temp_file_path = temp_file.name

            # Atomic move to final location
            shutil.move(temp_file_path, self.token_file_path)

            # Set restrictive permissions (owner read/write only)
            os.chmod(self.token_file_path, 0o600)

            logger.debug(f"Token saved to file: {self.token_file_path}")

        except Exception as e:
            # Clean up temp file if it exists
            try:
                if "temp_file_path" in locals():
                    os.unlink(temp_file_path)
            except:
                pass
            raise TokenPersistenceError(f"Failed to save token to file: {e}")

    def _load_token_from_file(self) -> None:
        """Load token from file if it exists and is valid."""
        if not self.token_file_path.exists():
            raise TokenPersistenceError("Token file does not exist")

        try:
            with open(self.token_file_path, "r") as f:
                lines = f.read().strip().split("\n")

            # Parse simple key=value format
            token_data = {}
            for line in lines:
                if "=" in line:
                    key, value = line.split("=", 1)
                    token_data[key.strip()] = value.strip()

            if "token" not in token_data or "created_at" not in token_data:
                raise TokenPersistenceError("Invalid token file format")

            self._current_token = token_data["token"]
            self._token_created_at = datetime.fromisoformat(token_data["created_at"])

            logger.debug(
                f"Token loaded from file: {self._current_token[:4]}...{self._current_token[-4:]}"
            )

        except Exception as e:
            raise TokenPersistenceError(f"Failed to load token from file: {e}")

    def get_token_info(self) -> dict[str, Any]:
        """
        Get information about the current token.

        Returns:
            Dictionary with token metadata (excludes actual token for security)
        """
        with self._lock:
            if not self._current_token or not self._token_created_at:
                return {
                    "has_token": False,
                    "created_at": None,
                    "expires_at": None,
                    "is_current": False,
                    "rotation_interval_minutes": self.rotation_interval_minutes,
                }

            expires_at = self._token_created_at + timedelta(
                minutes=self.rotation_interval_minutes
            )

            return {
                "has_token": True,
                "created_at": self._token_created_at.isoformat(),
                "expires_at": expires_at.isoformat(),
                "is_current": self._is_token_current(),
                "rotation_interval_minutes": self.rotation_interval_minutes,
                "token_preview": f"{self._current_token[:4]}...{self._current_token[-4:]}",
            }


# Global auth service instance (will be initialized in main app)
_auth_service: Optional[AuthService] = None


def get_auth_service() -> AuthService:
    """
    Get the global auth service instance.

    Returns:
        AuthService instance

    Raises:
        RuntimeError: If auth service hasn't been initialized
    """
    if _auth_service is None:
        raise RuntimeError(
            "Auth service not initialized. Call initialize_auth_service() first."
        )
    return _auth_service


def initialize_auth_service(
    token_file_path: Path,
    rotation_interval_minutes: int = 30,
    external_sync_callback: Optional[Callable[[str, Path], None]] = None,
) -> AuthService:
    """
    Initialize the global auth service instance.

    Args:
        token_file_path: Path where tokens are persisted
        rotation_interval_minutes: How often tokens rotate (default 30)
        external_sync_callback: Optional callback for external sync

    Returns:
        Initialized AuthService instance
    """
    global _auth_service
    _auth_service = AuthService(
        token_file_path=token_file_path,
        rotation_interval_minutes=rotation_interval_minutes,
        external_sync_callback=external_sync_callback,
    )
    logger.info("Global auth service initialized")
    return _auth_service


def shutdown_auth_service() -> None:
    """Shutdown the global auth service instance."""
    global _auth_service
    if _auth_service:
        logger.info("Auth service shut down")
        _auth_service = None
