"""
Base storage provider interface for token storage.

Defines the contract for storing authentication tokens in various storage backends
such as AWS S3, Azure Blob Storage, local file system, or cloud secrets managers.
"""

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Optional, Dict, Any


class StorageError(Exception):
    """Base exception for storage operations."""

    pass


class StorageProvider(ABC):
    """
    Abstract base class for storage providers.

    Provides a consistent interface for storing authentication tokens
    across different storage backends.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the storage provider with configuration.

        Args:
            config: Configuration dictionary specific to the provider
        """
        self.config = config

    @abstractmethod
    async def store_token(
        self,
        user_email: str,
        token: str,
        expires_at: datetime,
        filename: Optional[str] = None,
    ) -> str:
        """
        Store a user authentication token.

        Args:
            user_email: Email address of the user
            token: The authentication token
            expires_at: When the token expires
            filename: Optional custom filename, defaults to generated name

        Returns:
            Storage location/path where the token was stored

        Raises:
            StorageError: If storage operation fails
        """
        pass

    @abstractmethod
    async def delete_token(self, user_email: str, filename: Optional[str] = None) -> bool:
        """
        Delete a stored token file.

        Args:
            user_email: Email address of the user
            filename: Optional specific filename to delete

        Returns:
            True if deletion was successful

        Raises:
            StorageError: If deletion fails
        """
        pass

    @abstractmethod
    async def list_tokens(self, user_email: Optional[str] = None) -> list[str]:
        """
        List stored token files.

        Args:
            user_email: Optional filter by user email

        Returns:
            List of stored token file paths/names

        Raises:
            StorageError: If listing fails
        """
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """
        Check if the storage provider is accessible.

        Returns:
            True if storage is accessible
        """
        pass

    def generate_token_filename(
        self, user_email: str, timestamp: Optional[datetime] = None
    ) -> str:
        """
        Generate a standardized filename for a token file.

        Args:
            user_email: Email address of the user
            timestamp: Optional timestamp, defaults to current time

        Returns:
            Generated filename
        """
        if timestamp is None:
            timestamp = datetime.now(timezone.utc)

        # Create safe filename from email
        safe_email = user_email.replace("@", "_at_").replace(".", "_")
        timestamp_str = timestamp.strftime("%Y%m%d_%H%M%S")

        return f"token_{safe_email}_{timestamp_str}.txt"

    def generate_token_content(
        self,
        user_email: str,
        token: str,
        expires_at: datetime,
        username: Optional[str] = None,
    ) -> str:
        """
        Generate standardized content for a token file.

        Args:
            user_email: Email address of the user
            token: The authentication token
            expires_at: When the token expires
            username: Optional display name

        Returns:
            Formatted token file content
        """
        content = f"""Fenrir Authentication Token
===========================

User Email: {user_email}
Username: {username or 'Not specified'}
Token: {token}
Generated: {datetime.now(timezone.utc).isoformat()}Z
Expires: {expires_at.isoformat()}Z
Valid for: 24 hours

HOW TO USE:
- Web Interface: Use token in login form
- API Access: Include in X-Auth-Token header
- Security: Keep token secure, do not share

This file was generated automatically by the Fenrir Testing System.
"""
        return content
