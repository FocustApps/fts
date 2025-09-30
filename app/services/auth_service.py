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
from app.services.storage import StorageService, create_storage_service, StorageError
from app.config import get_base_app_config, get_storage_config

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

        # Initialize storage service if enabled
        self.storage_service: Optional[StorageService] = None
        try:
            app_config = get_base_app_config()
            if app_config.storage_enabled:
                storage_config = get_storage_config(app_config)
                self.storage_service = create_storage_service(storage_config)
                logger.info(
                    f"Storage service initialized with provider: {storage_config['provider_type']}"
                )
            else:
                logger.info("Storage service disabled, using file-based token storage")
        except Exception as e:
            logger.warning(f"Failed to initialize storage service: {e}")
            logger.info("Falling back to file-based token storage")

        # Ensure token directory exists (for fallback file operations)
        self.token_file_path.parent.mkdir(parents=True, exist_ok=True)

        logger.info(f"AuthService initialized with token file: {self.token_file_path}")

    async def _save_token_to_storage(self, token: str, expires_at: datetime) -> str:
        """
        Save token using storage service if available, otherwise fall back to file.

        Args:
            token: The token to store
            expires_at: When the token expires

        Returns:
            Storage location where token was saved
        """
        if self.storage_service:
            try:
                # Use "system" as user_email for auth service tokens
                location = await self.storage_service.store_user_token(
                    user_email="system",
                    token=token,
                    token_expires_at=expires_at.isoformat(),
                    additional_metadata={
                        "service": "auth_service",
                        "rotation_interval_minutes": str(self.rotation_interval_minutes),
                    },
                )
                logger.debug(f"Token saved to storage: {location}")
                return location
            except StorageError as e:
                logger.warning(f"Storage service failed, falling back to file: {e}")

        # Fallback to file-based storage
        self._save_token_to_file()
        return str(self.token_file_path)

    async def _load_token_from_storage(self) -> bool:
        """
        Load token from storage service if available, otherwise fall back to file.

        Returns:
            True if token was successfully loaded
        """
        if self.storage_service:
            try:
                # List tokens for "system" user
                tokens = await self.storage_service.list_user_tokens("system")
                if tokens:
                    # Get the most recent token file
                    latest_token = sorted(tokens)[-1]

                    # Read token content (this is provider-specific but should work for local provider)
                    token_content = await self._read_token_content_from_storage(
                        latest_token
                    )
                    if token_content:
                        return self._parse_token_content(token_content)

            except StorageError as e:
                logger.warning(f"Storage service failed, falling back to file: {e}")

        # Fallback to file-based loading
        try:
            self._load_token_from_file()
            return True
        except TokenPersistenceError:
            return False

    async def _read_token_content_from_storage(self, token_file: str) -> Optional[str]:
        """Read token content from storage provider."""
        # This is a simple implementation - in a real scenario, you might need
        # provider-specific logic to read file contents
        try:
            if hasattr(self.storage_service.provider, "_get_file_path"):
                # For local filesystem provider
                file_path = self.storage_service.provider._get_file_path(
                    "system", token_file
                )
                with open(file_path, "r") as f:
                    return f.read()
        except Exception as e:
            logger.warning(f"Failed to read token content from storage: {e}")
        return None

    def _parse_token_content(self, content: str) -> bool:
        """Parse token content and extract token information."""
        try:
            lines = content.strip().split("\n")
            token_data = {}

            for line in lines:
                if ":" in line and (
                    "Token:" in line or "Generated:" in line or "Expires:" in line
                ):
                    if line.startswith("Token:"):
                        token_data["token"] = line.split(":", 1)[1].strip()
                    elif line.startswith("Generated:"):
                        gen_time_str = line.split(":", 1)[1].strip().rstrip("Z")
                        token_data["created_at"] = gen_time_str
                    elif line.startswith("Expires:"):
                        exp_time_str = line.split(":", 1)[1].strip().rstrip("Z")
                        token_data["expires_at"] = exp_time_str

            if "token" in token_data and "created_at" in token_data:
                self._current_token = token_data["token"]
                self._token_created_at = datetime.fromisoformat(token_data["created_at"])
                logger.debug(
                    f"Token loaded from storage: {self._current_token[:4]}...{self._current_token[-4:]}"
                )
                return True

        except Exception as e:
            logger.warning(f"Failed to parse token content: {e}")

        return False

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

    def _run_async_in_thread(self, coro):
        """Run async coroutine in a new event loop in a separate thread."""
        import asyncio

        return asyncio.run(coro)

    def get_current_token(self) -> str:
        """Get the current authentication token.

        Returns:
            The current token or generates a new one if none exists
        """
        # Try to load from storage first
        if self.storage_service:
            try:
                # Use asyncio.get_event_loop() to handle existing event loops
                import asyncio

                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # Create a task and wait for it without blocking
                    import concurrent.futures

                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(
                            self._run_async_in_thread, self._load_token_from_storage()
                        )
                        token_loaded = future.result()
                else:
                    token_loaded = asyncio.run(self._load_token_from_storage())

                if token_loaded:
                    return token_loaded
            except Exception as e:
                logger.warning(f"Failed to load token from storage: {e}")
                # Fall back to file-based storage

        # Fallback to file-based storage
        if self.token_file_path.exists():
            try:
                token_content = self.token_file_path.read_text().strip()
                return self._parse_token_content(token_content)
            except Exception as e:
                logger.warning(f"Failed to read token from file: {e}")

        # Generate new token if none exists
        logger.info("No existing token found, generating new one")
        import asyncio

        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(self._run_async_in_thread, self._rotate_token())
                return future.result()
        else:
            return asyncio.run(self._rotate_token())

    def rotate_token(self) -> str:
        """
        Force immediate token rotation.

        Returns:
            New token
        """
        with self._lock:
            import asyncio

            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures

                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        self._run_async_in_thread, self._rotate_token()
                    )
                    return future.result()
            else:
                return asyncio.run(self._rotate_token())

    async def _rotate_token(self) -> str:
        """Internal method to generate and persist a new token."""
        try:
            new_token = self.generate_token()
            self._current_token = new_token
            self._token_created_at = datetime.now(timezone.utc)
            expires_at = self._token_created_at + timedelta(
                minutes=self.rotation_interval_minutes
            )

            # Save to storage (storage service or file fallback)
            storage_location = await self._save_token_to_storage(new_token, expires_at)

            # Trigger external sync if configured
            if self.external_sync_callback:
                try:
                    self.external_sync_callback(new_token, Path(storage_location))
                    logger.info(
                        f"External sync callback executed for token: {new_token[:4]}...{new_token[-4:]}"
                    )
                except Exception as e:
                    logger.error(f"External sync callback failed: {e}")
                    # Don't fail the rotation for external sync issues

            logger.info(f"Token rotated successfully: {new_token[:4]}...{new_token[-4:]}")
            return new_token

        except Exception as e:
            logger.error(f"Token rotation failed: {e}")
            raise AuthTokenError(f"Failed to rotate token: {e}")

    def rotate_token(self) -> str:
        """
        Force immediate token rotation.

        Returns:
            New token
        """
        with self._lock:
            # Since _rotate_token is now async, we need to handle it properly
            import asyncio

            try:
                loop = asyncio.get_event_loop()
                return loop.run_until_complete(self._rotate_token())
            except RuntimeError:
                # No event loop running, create one
                return asyncio.run(self._rotate_token())

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
