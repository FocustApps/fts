"""
AWS S3 storage provider for authentication tokens.

Stores tokens as text files in an S3 bucket with organized key structure.
"""

import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from app.services.storage.base import StorageProvider, StorageError
from common.app_logging import create_logging

logger = create_logging()


class AWSS3Provider(StorageProvider):
    """
    AWS S3 storage provider.

    Stores tokens in an S3 bucket with organized key structure.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the AWS S3 provider.

        Expected config:
        - bucket_name: S3 bucket name
        - aws_access_key_id: AWS access key (optional if using IAM)
        - aws_secret_access_key: AWS secret key (optional if using IAM)
        - aws_region: AWS region (default: us-east-1)
        - key_prefix: Optional prefix for all keys (default: tokens/)
        - create_user_folders: Whether to create per-user key prefixes
        """
        super().__init__(config)
        self.bucket_name = config["bucket_name"]
        self.key_prefix = config.get("key_prefix", "tokens/")
        self.create_user_folders = config.get("create_user_folders", True)

        # Initialize S3 client
        session_config = {"region_name": config.get("aws_region", "us-east-1")}

        if config.get("aws_access_key_id") and config.get("aws_secret_access_key"):
            session_config.update(
                {
                    "aws_access_key_id": config["aws_access_key_id"],
                    "aws_secret_access_key": config["aws_secret_access_key"],
                }
            )

        self.s3_client = boto3.client("s3", **session_config)

        logger.info(f"AWSS3Provider initialized for bucket: {self.bucket_name}")

    async def store_token(
        self,
        user_email: str,
        token: str,
        expires_at: datetime,
        filename: Optional[str] = None,
    ) -> str:
        """
        Store a token in S3.

        Args:
            user_email: Email address of the user
            token: The authentication token
            expires_at: When the token expires
            filename: Optional custom filename

        Returns:
            S3 key where the token was stored
        """
        try:
            # Generate S3 key
            if filename is None:
                filename = self.generate_token_filename(user_email)

            if self.create_user_folders:
                safe_email = user_email.replace("@", "_at_").replace(".", "_")
                s3_key = f"{self.key_prefix}{safe_email}/{filename}"
            else:
                s3_key = f"{self.key_prefix}{filename}"

            # Generate token content
            content = self.generate_token_content(user_email, token, expires_at)

            # Upload to S3
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=content.encode("utf-8"),
                ContentType="text/plain",
                Metadata={
                    "user_email": user_email,
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "expires_at": expires_at.isoformat(),
                },
            )

            logger.info(
                f"Token stored successfully in S3: s3://{self.bucket_name}/{s3_key}"
            )
            return s3_key

        except (ClientError, NoCredentialsError) as e:
            logger.error(f"AWS S3 error storing token for {user_email}: {e}")
            raise StorageError(f"S3 storage failed: {e}")
        except Exception as e:
            logger.error(f"Failed to store token in S3 for {user_email}: {e}")
            raise StorageError(f"S3 storage failed: {e}")

    async def delete_token(self, user_email: str, filename: Optional[str] = None) -> bool:
        """
        Delete a token from S3.

        Args:
            user_email: Email address of the user
            filename: Optional specific filename to delete

        Returns:
            True if deletion was successful
        """
        try:
            if filename:
                # Delete specific file
                if self.create_user_folders:
                    safe_email = user_email.replace("@", "_at_").replace(".", "_")
                    s3_key = f"{self.key_prefix}{safe_email}/{filename}"
                else:
                    s3_key = f"{self.key_prefix}{filename}"

                self.s3_client.delete_object(Bucket=self.bucket_name, Key=s3_key)
                logger.info(f"Deleted token from S3: s3://{self.bucket_name}/{s3_key}")
                return True
            else:
                # Delete all tokens for user
                prefix = self._get_user_prefix(user_email)
                objects = self.s3_client.list_objects_v2(
                    Bucket=self.bucket_name, Prefix=prefix
                )

                if "Contents" not in objects:
                    return True

                delete_keys = [{"Key": obj["Key"]} for obj in objects["Contents"]]

                if delete_keys:
                    self.s3_client.delete_objects(
                        Bucket=self.bucket_name, Delete={"Objects": delete_keys}
                    )
                    logger.info(
                        f"Deleted {len(delete_keys)} tokens from S3 for {user_email}"
                    )

                return len(delete_keys) > 0

        except ClientError as e:
            logger.error(f"AWS S3 error deleting tokens for {user_email}: {e}")
            raise StorageError(f"S3 deletion failed: {e}")
        except Exception as e:
            logger.error(f"Failed to delete tokens from S3 for {user_email}: {e}")
            raise StorageError(f"S3 deletion failed: {e}")

    async def list_tokens(self, user_email: Optional[str] = None) -> list[str]:
        """
        List stored token files in S3.

        Args:
            user_email: Optional filter by user email

        Returns:
            List of S3 keys for token files
        """
        try:
            if user_email:
                prefix = self._get_user_prefix(user_email)
            else:
                prefix = self.key_prefix

            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name, Prefix=prefix
            )

            if "Contents" not in response:
                return []

            # Filter for token files
            token_keys = [
                obj["Key"]
                for obj in response["Contents"]
                if obj["Key"].endswith(".txt") and "token_" in obj["Key"]
            ]

            return sorted(token_keys)

        except ClientError as e:
            logger.error(f"AWS S3 error listing tokens: {e}")
            raise StorageError(f"S3 listing failed: {e}")
        except Exception as e:
            logger.error(f"Failed to list tokens from S3: {e}")
            raise StorageError(f"S3 listing failed: {e}")

    async def health_check(self) -> bool:
        """
        Check if S3 bucket is accessible.

        Returns:
            True if S3 bucket is accessible
        """
        try:
            # Try to list objects (this validates bucket access)
            self.s3_client.list_objects_v2(Bucket=self.bucket_name, MaxKeys=1)
            return True

        except ClientError as e:
            logger.error(f"S3 health check failed: {e}")
            return False
        except Exception as e:
            logger.error(f"S3 health check failed: {e}")
            return False

    def _get_user_prefix(self, user_email: str) -> str:
        """Get the S3 key prefix for a specific user."""
        if self.create_user_folders:
            safe_email = user_email.replace("@", "_at_").replace(".", "_")
            return f"{self.key_prefix}{safe_email}/"
        else:
            safe_email = user_email.replace("@", "_at_").replace(".", "_")
            return f"{self.key_prefix}token_{safe_email}_"
