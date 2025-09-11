import os
from pathlib import Path
from dotenv import load_dotenv
from pydantic import BaseModel


class BaseAppConfig(BaseModel):
    environment: str = "local"
    api_version: str = "v1"
    htmx_version: str = "2.0.4"
    jquery_version: str = "3.7.1"
    bootstrap_version: str = "5.3.3"

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
    )


# Alias for easier import
get_config = get_base_app_config
