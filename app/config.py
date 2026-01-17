import os
from typing import List
from dotenv import load_dotenv
from pydantic import BaseModel


class BaseAppConfig(BaseModel):
    environment: str = "local"
    api_version: str = "v1"
    htmx_version: str = "2.0.6"
    jquery_version: str = "3.7.1"
    bootstrap_version: str = "5.3.7"

    # JWT Authentication settings
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_hours: int = 24
    jwt_refresh_token_expire_days: int = 7
    enforce_https: bool = False
    cors_allow_origins: List[str] = []
    rate_limit_enabled: bool = True
    admin_email: str = "admin@fenrir.local"
    frontend_url: str = "http://localhost:8080"

    # Password Requirements (configurable)
    password_min_length: int = 8
    password_require_uppercase: bool = True
    password_require_lowercase: bool = True
    password_require_digit: bool = True
    password_require_special: bool = True

    # Email notification settings
    email_notification_enabled: bool = False
    email_recipient: str = ""
    smtp_server: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    email_subject: str = "Fenrir Auth Token"

    # MailHog settings for local development
    use_mailhog: bool = False
    mailhog_api_url: str = "http://mailhog:8025"

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

    # Parse CORS origins from comma-separated string
    cors_origins_str = os.getenv("CORS_ALLOW_ORIGINS", "http://localhost:8080")
    cors_origins = [
        origin.strip() for origin in cors_origins_str.split(",") if origin.strip()
    ]

    return BaseAppConfig(
        environment=os.getenv("ENVIRONMENT", "local"),
        api_version=os.getenv("API_VERSION", "v1"),
        htmx_version=os.getenv("HTMX_VERSION", "2.0.4"),
        jquery_version=os.getenv("JQUERY_VERSION", "3.7.1"),
        bootstrap_version=os.getenv("BOOTSTRAP_VERSION", "5.3.8"),
        # JWT settings
        jwt_secret_key=os.getenv("JWT_SECRET_KEY", ""),
        jwt_algorithm=os.getenv("JWT_ALGORITHM", "HS256"),
        jwt_access_token_expire_hours=int(
            os.getenv("JWT_ACCESS_TOKEN_EXPIRE_HOURS", "24")
        ),
        jwt_refresh_token_expire_days=int(
            os.getenv("JWT_REFRESH_TOKEN_EXPIRE_DAYS", "7")
        ),
        enforce_https=os.getenv("ENFORCE_HTTPS", "false").lower() == "true",
        cors_allow_origins=cors_origins,
        rate_limit_enabled=os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true",
        admin_email=os.getenv("ADMIN_EMAIL", "admin@fenrir.local"),
        frontend_url=os.getenv("FRONTEND_URL", "http://localhost:8080"),
        # Password requirements
        password_min_length=int(os.getenv("PASSWORD_MIN_LENGTH", "8")),
        password_require_uppercase=os.getenv("PASSWORD_REQUIRE_UPPERCASE", "true").lower()
        == "true",
        password_require_lowercase=os.getenv("PASSWORD_REQUIRE_LOWERCASE", "true").lower()
        == "true",
        password_require_digit=os.getenv("PASSWORD_REQUIRE_DIGIT", "true").lower()
        == "true",
        password_require_special=os.getenv("PASSWORD_REQUIRE_SPECIAL", "true").lower()
        == "true",
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
        use_mailhog=os.getenv("USE_MAILHOG", "false").lower() == "true",
        mailhog_api_url=os.getenv("MAILHOG_API_URL", "http://mailhog:8025"),
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
