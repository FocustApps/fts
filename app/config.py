import os
from dotenv import load_dotenv
from pydantic import BaseModel


class BaseAppConfig(BaseModel):
    environment: str = "local"
    api_version: str = "v1"
    htmx_version: str = "2.0.4"
    jquery_version: str = "3.7.1"
    bootstrap_version: str = "5.3.3"


def get_base_app_config() -> BaseAppConfig:
    load_dotenv()
    return BaseAppConfig(
        environment=os.getenv("ENVIRONMENT"),
        api_version=os.getenv("API_VERSION"),
        htmx_version=os.getenv("HTMX_VERSION"),
        jquery_version=os.getenv("JQUERY_VERSION"),
        bootstrap_version=os.getenv("BOOTSTRAP_VERSION"),
    )