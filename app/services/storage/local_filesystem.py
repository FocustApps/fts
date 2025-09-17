"""
Local file system storage provider for authentication tokens.

Stores tokens as text files in a local directory structure.
"""

import aiofiles
from datetime import datetime
from typing import Optional, Dict, Any
from pathlib import Path

from app.services.storage.base import StorageProvider, StorageError
from common.app_logging import create_logging

logger = create_logging()


class LocalFileSystemProvider(StorageProvider):
    """
    Local file system storage provider.

    Stores tokens in a local directory with organized folder structure.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the local file system provider.

        Expected config:
        - base_path: Base directory for storing tokens
        - create_user_folders: Whether to create per-user subfolders
        """
        super().__init__(config)
        self.base_path = Path(config.get("base_path", "./token_storage"))
        self.create_user_folders = config.get("create_user_folders", True)

        # Ensure base directory exists
        self.base_path.mkdir(parents=True, exist_ok=True)

        logger.info(
            f"LocalFileSystemProvider initialized with base_path: {self.base_path}"
        )

    async def store_token(
        self,
        user_email: str,
        token: str,
        expires_at: datetime,
        filename: Optional[str] = None,
    ) -> str:
        """
        Store a token in the local file system.

        Args:
            user_email: Email address of the user
            token: The authentication token
            expires_at: When the token expires
            filename: Optional custom filename

        Returns:
            Full path where the token was stored
        """
        try:
            # Determine storage directory
            if self.create_user_folders:
                safe_email = user_email.replace("@", "_at_").replace(".", "_")
                user_dir = self.base_path / safe_email
                user_dir.mkdir(exist_ok=True)
                storage_dir = user_dir
            else:
                storage_dir = self.base_path

            # Generate filename if not provided
            if filename is None:
                filename = self.generate_token_filename(user_email)

            file_path = storage_dir / filename

            # Generate token content
            content = self.generate_token_content(user_email, token, expires_at)

            # Write file asynchronously
            async with aiofiles.open(file_path, "w") as f:
                await f.write(content)

            logger.info(f"Token stored successfully at: {file_path}")
            return str(file_path)

        except Exception as e:
            logger.error(f"Failed to store token for {user_email}: {e}")
            raise StorageError(f"Local storage failed: {e}")

    async def delete_token(self, user_email: str, filename: Optional[str] = None) -> bool:
        """
        Delete a token file from local storage.

        Args:
            user_email: Email address of the user
            filename: Optional specific filename to delete

        Returns:
            True if deletion was successful
        """
        try:
            # Determine storage directory
            if self.create_user_folders:
                safe_email = user_email.replace("@", "_at_").replace(".", "_")
                storage_dir = self.base_path / safe_email
            else:
                storage_dir = self.base_path

            if filename:
                # Delete specific file
                file_path = storage_dir / filename
                if file_path.exists():
                    file_path.unlink()
                    logger.info(f"Deleted token file: {file_path}")
                    return True
                else:
                    logger.warning(f"Token file not found: {file_path}")
                    return False
            else:
                # Delete all token files for user
                if not storage_dir.exists():
                    return True

                deleted_count = 0
                for file_path in storage_dir.glob("token_*.txt"):
                    file_path.unlink()
                    deleted_count += 1

                logger.info(f"Deleted {deleted_count} token files for {user_email}")
                return deleted_count > 0

        except Exception as e:
            logger.error(f"Failed to delete tokens for {user_email}: {e}")
            raise StorageError(f"Local deletion failed: {e}")

    async def list_tokens(self, user_email: Optional[str] = None) -> list[str]:
        """
        List stored token files.

        Args:
            user_email: Optional filter by user email

        Returns:
            List of token file paths
        """
        try:
            token_files = []

            if user_email:
                # List tokens for specific user
                if self.create_user_folders:
                    safe_email = user_email.replace("@", "_at_").replace(".", "_")
                    user_dir = self.base_path / safe_email
                    if user_dir.exists():
                        token_files.extend([str(f) for f in user_dir.glob("token_*.txt")])
                else:
                    # Filter by email in filename
                    safe_email = user_email.replace("@", "_at_").replace(".", "_")
                    pattern = f"token_{safe_email}_*.txt"
                    token_files.extend([str(f) for f in self.base_path.glob(pattern)])
            else:
                # List all tokens
                if self.create_user_folders:
                    for user_dir in self.base_path.iterdir():
                        if user_dir.is_dir():
                            token_files.extend(
                                [str(f) for f in user_dir.glob("token_*.txt")]
                            )
                else:
                    token_files.extend(
                        [str(f) for f in self.base_path.glob("token_*.txt")]
                    )

            return sorted(token_files)

        except Exception as e:
            logger.error(f"Failed to list tokens: {e}")
            raise StorageError(f"Local listing failed: {e}")

    async def health_check(self) -> bool:
        """
        Check if local storage is accessible.

        Returns:
            True if storage directory is accessible
        """
        try:
            # Check if base directory exists and is writable
            if not self.base_path.exists():
                return False

            # Try creating a test file
            test_file = self.base_path / ".health_check"
            test_file.write_text("health_check")
            test_file.unlink()

            return True

        except Exception as e:
            logger.error(f"Local storage health check failed: {e}")
            return False
