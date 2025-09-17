"""
Storage service for managing authentication tokens across different storage providers.

This service provides a unified interface for storing authentication tokens using
various cloud storage backends (AWS S3, Azure Blob Storage, local file system).
"""

import logging
from typing import Dict, Any, Optional, List

from .base import StorageProvider, StorageError
from .local_filesystem import LocalFileSystemProvider
from .aws_s3 import AWSS3Provider
from .azure_blob import AzureBlobProvider


logger = logging.getLogger(__name__)


class StorageService:
    """
    Storage service that manages authentication tokens using a configured storage provider.

    This service acts as a facade for different storage providers, providing a consistent
    interface for token storage operations while abstracting the underlying implementation.
    """

    def __init__(self, provider_config: Dict[str, Any]):
        """
        Initialize the storage service with a provider configuration.

        Args:
            provider_config: Configuration dictionary containing:
                - provider_type: str ("local", "aws_s3", "azure_blob")
                - provider_config: Dict with provider-specific configuration

        Raises:
            StorageError: If provider type is unknown or configuration is invalid
        """
        self.provider_type = provider_config.get("provider_type")
        provider_settings = provider_config.get("provider_config", {})

        try:
            self.provider = self._create_provider(self.provider_type, provider_settings)
            logger.info(
                f"Storage service initialized with provider: {self.provider_type}"
            )
        except Exception as e:
            logger.error(f"Failed to initialize storage service: {e}")
            raise StorageError(f"Storage service initialization failed: {e}")

    def _create_provider(
        self, provider_type: str, config: Dict[str, Any]
    ) -> StorageProvider:
        """
        Create a storage provider instance based on the provider type.

        Args:
            provider_type: Type of storage provider to create
            config: Provider-specific configuration

        Returns:
            StorageProvider: Configured storage provider instance

        Raises:
            StorageError: If provider type is unknown
        """
        if provider_type == "local":
            return LocalFileSystemProvider(config)
        elif provider_type == "aws_s3":
            return AWSS3Provider(config)
        elif provider_type == "azure_blob":
            return AzureBlobProvider(config)
        else:
            raise StorageError(f"Unknown storage provider type: {provider_type}")

    async def store_user_token(
        self,
        user_email: str,
        token: str,
        token_expires_at: Optional[str] = None,
        additional_metadata: Optional[Dict[str, str]] = None,
    ) -> str:
        """
        Store an authentication token for a user.

        Args:
            user_email: Email address of the user
            token: Authentication token to store
            token_expires_at: Optional expiration timestamp
            additional_metadata: Optional additional metadata to include

        Returns:
            str: Identifier or path of the stored token

        Raises:
            StorageError: If storage operation fails
        """
        try:
            logger.info(f"Storing token for user: {user_email}")

            # Build metadata
            metadata = {"user_email": user_email, "provider_type": self.provider_type}
            if token_expires_at:
                metadata["expires_at"] = token_expires_at
            if additional_metadata:
                metadata.update(additional_metadata)

            # Store token using the configured provider
            token_id = await self.provider.store_token(
                user_email=user_email, token=token, metadata=metadata
            )

            logger.info(
                f"Successfully stored token for user {user_email} with ID: {token_id}"
            )
            return token_id

        except Exception as e:
            logger.error(f"Failed to store token for user {user_email}: {e}")
            raise StorageError(f"Token storage failed: {e}")

    async def delete_user_token(self, user_email: str, token_id: str) -> bool:
        """
        Delete a stored authentication token for a user.

        Args:
            user_email: Email address of the user
            token_id: Identifier of the token to delete

        Returns:
            bool: True if token was deleted successfully

        Raises:
            StorageError: If deletion operation fails
        """
        try:
            logger.info(f"Deleting token {token_id} for user: {user_email}")

            success = await self.provider.delete_token(
                user_email=user_email, token_id=token_id
            )

            if success:
                logger.info(
                    f"Successfully deleted token {token_id} for user {user_email}"
                )
            else:
                logger.warning(f"Token {token_id} not found for user {user_email}")

            return success

        except Exception as e:
            logger.error(f"Failed to delete token {token_id} for user {user_email}: {e}")
            raise StorageError(f"Token deletion failed: {e}")

    async def list_user_tokens(self, user_email: str) -> List[Dict[str, Any]]:
        """
        List all stored tokens for a user.

        Args:
            user_email: Email address of the user

        Returns:
            List[Dict[str, Any]]: List of token information dictionaries

        Raises:
            StorageError: If listing operation fails
        """
        try:
            logger.debug(f"Listing tokens for user: {user_email}")

            tokens = await self.provider.list_tokens(user_email=user_email)

            logger.debug(f"Found {len(tokens)} tokens for user {user_email}")
            return tokens

        except Exception as e:
            logger.error(f"Failed to list tokens for user {user_email}: {e}")
            raise StorageError(f"Token listing failed: {e}")

    async def cleanup_expired_tokens(self, user_email: str) -> int:
        """
        Clean up expired tokens for a user.

        Args:
            user_email: Email address of the user

        Returns:
            int: Number of tokens cleaned up

        Raises:
            StorageError: If cleanup operation fails
        """
        try:
            logger.info(f"Cleaning up expired tokens for user: {user_email}")

            # List all tokens for the user
            tokens = await self.list_user_tokens(user_email)

            cleaned_count = 0
            for token_info in tokens:
                # Check if token has expired (implementation depends on metadata structure)
                if self._is_token_expired(token_info):
                    token_id = token_info.get("token_id")
                    if token_id:
                        await self.delete_user_token(user_email, token_id)
                        cleaned_count += 1

            logger.info(
                f"Cleaned up {cleaned_count} expired tokens for user {user_email}"
            )
            return cleaned_count

        except Exception as e:
            logger.error(f"Failed to cleanup expired tokens for user {user_email}: {e}")
            raise StorageError(f"Token cleanup failed: {e}")

    def _is_token_expired(self, token_info: Dict[str, Any]) -> bool:
        """
        Check if a token has expired based on its metadata.

        Args:
            token_info: Token information dictionary

        Returns:
            bool: True if token has expired
        """
        # This is a simplified implementation - in practice you'd want to
        # parse the expires_at timestamp and compare with current time
        expires_at = token_info.get("metadata", {}).get("expires_at")
        if not expires_at:
            return False

        # For now, return False - implement actual expiration logic based on your needs
        # Example: parse expires_at timestamp and compare with datetime.utcnow()
        return False

    async def health_check(self) -> Dict[str, Any]:
        """
        Perform a health check on the storage service.

        Returns:
            Dict[str, Any]: Health check results

        Raises:
            StorageError: If health check fails
        """
        try:
            logger.debug("Performing storage service health check")

            provider_health = await self.provider.health_check()

            health_result = {
                "service": "storage_service",
                "status": "healthy",
                "provider_type": self.provider_type,
                "provider_health": provider_health,
            }

            logger.debug("Storage service health check completed successfully")
            return health_result

        except Exception as e:
            logger.error(f"Storage service health check failed: {e}")
            health_result = {
                "service": "storage_service",
                "status": "unhealthy",
                "provider_type": self.provider_type,
                "error": str(e),
            }
            return health_result

    def get_provider_info(self) -> Dict[str, str]:
        """
        Get information about the current storage provider.

        Returns:
            Dict[str, str]: Provider information
        """
        return {
            "provider_type": self.provider_type,
            "provider_class": type(self.provider).__name__,
        }


# Factory function for creating storage service instances
def create_storage_service(config: Dict[str, Any]) -> StorageService:
    """
    Factory function to create a storage service instance.

    Args:
        config: Storage service configuration

    Returns:
        StorageService: Configured storage service instance

    Raises:
        StorageError: If configuration is invalid
    """
    try:
        return StorageService(config)
    except Exception as e:
        logger.error(f"Failed to create storage service: {e}")
        raise StorageError(f"Storage service creation failed: {e}")


# Default configuration examples for different providers
DEFAULT_CONFIGS = {
    "local": {
        "provider_type": "local",
        "provider_config": {"base_directory": "./data/tokens"},
    },
    "aws_s3": {
        "provider_type": "aws_s3",
        "provider_config": {
            "bucket_name": "fenrir-auth-tokens",
            "prefix": "tokens/",
            "region": "us-east-1",
            # AWS credentials should be provided via environment variables or IAM roles
        },
    },
    "azure_blob": {
        "provider_type": "azure_blob",
        "provider_config": {
            "container_name": "fenrir-auth-tokens",
            "prefix": "tokens/",
            # Azure credentials should be provided via environment variables
        },
    },
}
