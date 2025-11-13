import os
from pathlib import Path
from dotenv import load_dotenv
from pydantic import BaseModel


class BaseAppConfig(BaseModel):
    environment: str = "local"
    api_version: str = "v1"
    htmx_version: str = "2.0.6"
    jquery_version: str = "3.7.1"
    bootstrap_version: str = "5.3.7"

    # Authentication settings
    auth_token_file_path: Path = Path("auth_token.txt")
    auth_rotation_interval_minutes: int = 30
    auth_external_sync_enabled: bool = False
    auth_external_sync_url: str = ""

    # Email notification settings
    email_notification_enabled: bool = False
    email_recipient: str = ""
    smtp_server: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    email_subject: str = "Fenrir Auth Token"

    # Database settings
    database_type: str = "postgresql"
    db_host: str = "localhost"
    db_port: int = 5432
    postgres_db: str = "fenrir"
    postgres_user: str = "fenrir"
    postgres_password: str = "fenrirpass"

    # Storage settings for authentication tokens
    storage_enabled: bool = False
    storage_provider_type: str = "local"  # Options: "local", "aws_s3", "azure_blob"

    # Local storage settings
    storage_local_base_directory: str = "./data/tokens"

    # AWS S3 storage settings
    storage_aws_bucket_name: str = "fenrir-auth-tokens"
    storage_aws_prefix: str = "tokens/"
    storage_aws_region: str = "us-east-1"
    # AWS credentials are handled via environment variables or IAM roles

    # Azure Blob storage settings
    storage_azure_container_name: str = "fenrir-auth-tokens"
    storage_azure_prefix: str = "tokens/"
    storage_azure_connection_string: str = ""
    storage_azure_account_name: str = ""
    storage_azure_account_key: str = ""


def get_base_app_config() -> BaseAppConfig:
    load_dotenv()
    return BaseAppConfig(
        environment=os.getenv("ENVIRONMENT"),
        api_version=os.getenv("API_VERSION"),
        htmx_version=os.getenv("HTMX_VERSION"),
        jquery_version=os.getenv("JQUERY_VERSION"),
        bootstrap_version=os.getenv("BOOTSTRAP_VERSION"),
        auth_token_file_path=Path(os.getenv("AUTH_TOKEN_FILE_PATH", "auth_token.txt")),
        auth_rotation_interval_minutes=int(
            os.getenv("AUTH_ROTATION_INTERVAL_MINUTES", "30")
        ),
        auth_external_sync_enabled=os.getenv(
            "AUTH_EXTERNAL_SYNC_ENABLED", "false"
        ).lower()
        == "true",
        auth_external_sync_url=os.getenv("AUTH_EXTERNAL_SYNC_URL", ""),
        email_notification_enabled=os.getenv(
            "EMAIL_NOTIFICATION_ENABLED", "false"
        ).lower()
        == "true",
        email_recipient=os.getenv("EMAIL_RECIPIENT", ""),
        smtp_server=os.getenv("SMTP_SERVER", "smtp.gmail.com"),
        smtp_port=int(os.getenv("SMTP_PORT", "465")),
        smtp_username=os.getenv("EMAIL_USER", ""),
        smtp_password=os.getenv("EMAIL_PASSWORD", ""),
        email_subject=os.getenv("EMAIL_SUBJECT", "Fenrir Auth Token"),
        # Database settings from environment
        database_type=os.getenv("DATABASE_TYPE", "postgresql"),
        db_host=os.getenv("DB_HOST", "localhost"),
        db_port=int(os.getenv("DB_PORT", "5432")),
        postgres_db=os.getenv("POSTGRES_DB", "fenrir"),
        postgres_user=os.getenv("POSTGRES_USER", "fenrir"),
        postgres_password=os.getenv("POSTGRES_PASSWORD", "fenrirpass"),
        # Storage settings from environment
        storage_enabled=os.getenv("STORAGE_ENABLED", "false").lower() == "true",
        storage_provider_type=os.getenv("STORAGE_PROVIDER_TYPE", "local"),
        # Local storage settings
        storage_local_base_directory=os.getenv(
            "STORAGE_LOCAL_BASE_DIRECTORY", "./data/tokens"
        ),
        # AWS S3 storage settings
        storage_aws_bucket_name=os.getenv(
            "STORAGE_AWS_BUCKET_NAME", "fenrir-auth-tokens"
        ),
        storage_aws_prefix=os.getenv("STORAGE_AWS_PREFIX", "tokens/"),
        storage_aws_region=os.getenv("STORAGE_AWS_REGION", "us-east-1"),
        # Azure Blob storage settings
        storage_azure_container_name=os.getenv(
            "STORAGE_AZURE_CONTAINER_NAME", "fenrir-auth-tokens"
        ),
        storage_azure_prefix=os.getenv("STORAGE_AZURE_PREFIX", "tokens/"),
        storage_azure_connection_string=os.getenv("STORAGE_AZURE_CONNECTION_STRING", ""),
        storage_azure_account_name=os.getenv("STORAGE_AZURE_ACCOUNT_NAME", ""),
        storage_azure_account_key=os.getenv("STORAGE_AZURE_ACCOUNT_KEY", ""),
    )


# Alias for easier import
get_config = get_base_app_config


def get_storage_config(app_config: BaseAppConfig = None) -> dict:
    """
    Build storage configuration from app config.

    Args:
        app_config: App configuration instance. If None, will get fresh config.

    Returns:
        dict: Storage configuration ready for StorageService
    """
    if app_config is None:
        app_config = get_base_app_config()

    # Build provider-specific configuration
    if app_config.storage_provider_type == "local":
        provider_config = {"base_directory": app_config.storage_local_base_directory}
    elif app_config.storage_provider_type == "aws_s3":
        provider_config = {
            "bucket_name": app_config.storage_aws_bucket_name,
            "prefix": app_config.storage_aws_prefix,
            "region": app_config.storage_aws_region,
        }
    elif app_config.storage_provider_type == "azure_blob":
        provider_config = {
            "container_name": app_config.storage_azure_container_name,
            "prefix": app_config.storage_azure_prefix,
        }

        # Add credentials if available (prefer connection string)
        if app_config.storage_azure_connection_string:
            provider_config["connection_string"] = (
                app_config.storage_azure_connection_string
            )
        elif (
            app_config.storage_azure_account_name and app_config.storage_azure_account_key
        ):
            provider_config["account_name"] = app_config.storage_azure_account_name
            provider_config["account_key"] = app_config.storage_azure_account_key
    else:
        # Fallback to local storage for unknown provider types
        provider_config = {"base_directory": "./data/tokens"}
        app_config.storage_provider_type = "local"

    return {
        "provider_type": app_config.storage_provider_type,
        "provider_config": provider_config,
    }
