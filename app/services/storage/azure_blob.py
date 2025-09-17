"""
Azure Blob Storage provider for authentication tokens.

Stores tokens as text files in an Azure Blob Storage container.
"""

from azure.storage.blob import BlobServiceClient
from azure.core.exceptions import AzureError
from datetime import datetime
from typing import Optional, Dict, Any

from app.services.storage.base import StorageProvider, StorageError
from common.app_logging import create_logging

logger = create_logging()


class AzureBlobProvider(StorageProvider):
    """
    Azure Blob Storage provider.

    Stores tokens in an Azure Blob Storage container with organized blob naming.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the Azure Blob Storage provider.

        Expected config:
        - connection_string: Azure Storage connection string (preferred)
        OR
        - account_name: Storage account name
        - account_key: Storage account key
        OR
        - account_name: Storage account name
        - sas_token: SAS token

        Additional config:
        - container_name: Blob container name
        - blob_prefix: Optional prefix for all blobs (default: tokens/)
        - create_user_folders: Whether to create per-user blob prefixes
        """
        super().__init__(config)
        self.container_name = config["container_name"]
        self.blob_prefix = config.get("blob_prefix", "tokens/")
        self.create_user_folders = config.get("create_user_folders", True)

        # Initialize Blob Service Client
        if config.get("connection_string"):
            self.blob_service_client = BlobServiceClient.from_connection_string(
                config["connection_string"]
            )
        elif config.get("account_name") and config.get("account_key"):
            account_url = f"https://{config['account_name']}.blob.core.windows.net"
            self.blob_service_client = BlobServiceClient(
                account_url=account_url, credential=config["account_key"]
            )
        elif config.get("account_name") and config.get("sas_token"):
            account_url = f"https://{config['account_name']}.blob.core.windows.net"
            self.blob_service_client = BlobServiceClient(
                account_url=account_url, credential=config["sas_token"]
            )
        else:
            raise StorageError(
                "Azure Blob Storage configuration incomplete. Need connection_string or account_name with account_key/sas_token"
            )

        logger.info(f"AzureBlobProvider initialized for container: {self.container_name}")

    async def store_token(
        self,
        user_email: str,
        token: str,
        expires_at: datetime,
        filename: Optional[str] = None,
    ) -> str:
        """
        Store a token in Azure Blob Storage.

        Args:
            user_email: Email address of the user
            token: The authentication token
            expires_at: When the token expires
            filename: Optional custom filename

        Returns:
            Blob name where the token was stored
        """
        try:
            # Generate blob name
            if filename is None:
                filename = self.generate_token_filename(user_email)

            if self.create_user_folders:
                safe_email = user_email.replace("@", "_at_").replace(".", "_")
                blob_name = f"{self.blob_prefix}{safe_email}/{filename}"
            else:
                blob_name = f"{self.blob_prefix}{filename}"

            # Generate token content
            content = self.generate_token_content(user_email, token, expires_at)

            # Upload to Azure Blob Storage
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name, blob=blob_name
            )

            blob_client.upload_blob(
                data=content.encode("utf-8"),
                content_type="text/plain",
                metadata={
                    "user_email": user_email,
                    "generated_at": datetime.utcnow().isoformat(),
                    "expires_at": expires_at.isoformat(),
                },
                overwrite=True,
            )

            logger.info(f"Token stored successfully in Azure Blob: {blob_name}")
            return blob_name

        except AzureError as e:
            logger.error(f"Azure Blob error storing token for {user_email}: {e}")
            raise StorageError(f"Azure Blob storage failed: {e}")
        except Exception as e:
            logger.error(f"Failed to store token in Azure Blob for {user_email}: {e}")
            raise StorageError(f"Azure Blob storage failed: {e}")

    async def delete_token(self, user_email: str, filename: Optional[str] = None) -> bool:
        """
        Delete a token from Azure Blob Storage.

        Args:
            user_email: Email address of the user
            filename: Optional specific filename to delete

        Returns:
            True if deletion was successful
        """
        try:
            if filename:
                # Delete specific blob
                if self.create_user_folders:
                    safe_email = user_email.replace("@", "_at_").replace(".", "_")
                    blob_name = f"{self.blob_prefix}{safe_email}/{filename}"
                else:
                    blob_name = f"{self.blob_prefix}{filename}"

                blob_client = self.blob_service_client.get_blob_client(
                    container=self.container_name, blob=blob_name
                )
                blob_client.delete_blob()
                logger.info(f"Deleted token from Azure Blob: {blob_name}")
                return True
            else:
                # Delete all tokens for user
                prefix = self._get_user_prefix(user_email)
                container_client = self.blob_service_client.get_container_client(
                    self.container_name
                )

                blobs_to_delete = container_client.list_blobs(name_starts_with=prefix)
                deleted_count = 0

                for blob in blobs_to_delete:
                    if "token_" in blob.name and blob.name.endswith(".txt"):
                        blob_client = self.blob_service_client.get_blob_client(
                            container=self.container_name, blob=blob.name
                        )
                        blob_client.delete_blob()
                        deleted_count += 1

                logger.info(
                    f"Deleted {deleted_count} tokens from Azure Blob for {user_email}"
                )
                return deleted_count > 0

        except AzureError as e:
            logger.error(f"Azure Blob error deleting tokens for {user_email}: {e}")
            raise StorageError(f"Azure Blob deletion failed: {e}")
        except Exception as e:
            logger.error(f"Failed to delete tokens from Azure Blob for {user_email}: {e}")
            raise StorageError(f"Azure Blob deletion failed: {e}")

    async def list_tokens(self, user_email: Optional[str] = None) -> list[str]:
        """
        List stored token files in Azure Blob Storage.

        Args:
            user_email: Optional filter by user email

        Returns:
            List of blob names for token files
        """
        try:
            if user_email:
                prefix = self._get_user_prefix(user_email)
            else:
                prefix = self.blob_prefix

            container_client = self.blob_service_client.get_container_client(
                self.container_name
            )

            blobs = container_client.list_blobs(name_starts_with=prefix)

            # Filter for token files
            token_blobs = [
                blob.name
                for blob in blobs
                if blob.name.endswith(".txt") and "token_" in blob.name
            ]

            return sorted(token_blobs)

        except AzureError as e:
            logger.error(f"Azure Blob error listing tokens: {e}")
            raise StorageError(f"Azure Blob listing failed: {e}")
        except Exception as e:
            logger.error(f"Failed to list tokens from Azure Blob: {e}")
            raise StorageError(f"Azure Blob listing failed: {e}")

    async def health_check(self) -> bool:
        """
        Check if Azure Blob Storage container is accessible.

        Returns:
            True if Azure Blob container is accessible
        """
        try:
            # Try to get container properties (this validates access)
            container_client = self.blob_service_client.get_container_client(
                self.container_name
            )
            container_client.get_container_properties()
            return True

        except AzureError as e:
            logger.error(f"Azure Blob health check failed: {e}")
            return False
        except Exception as e:
            logger.error(f"Azure Blob health check failed: {e}")
            return False

    def _get_user_prefix(self, user_email: str) -> str:
        """Get the blob name prefix for a specific user."""
        if self.create_user_folders:
            safe_email = user_email.replace("@", "_at_").replace(".", "_")
            return f"{self.blob_prefix}{safe_email}/"
        else:
            safe_email = user_email.replace("@", "_at_").replace(".", "_")
            return f"{self.blob_prefix}token_{safe_email}_"
