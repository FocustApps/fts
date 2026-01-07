"""
Configuration module for Fenrir application.
Handles loading environment variables and configuring different services.
"""

import os
from dotenv import load_dotenv
from pydantic import BaseModel


class ConfigException(Exception):
    pass


class MissingExpectedEnviron(ConfigException):
    def __init__(self, environ_name: str):
        super().__init__(f"Missing expected environment variable: {environ_name}")


class BadConfiguration(ConfigException):
    def __init__(self, message: str):
        super().__init__(f"Bad configuration: {message}")


class LoggingConfig(BaseModel):
    log_level: str | None = "INFO"


def get_logging_config() -> LoggingConfig:
    load_dotenv()
    log_level = os.getenv("LOG_LEVEL") or "INFO"
    if not log_level:
        raise MissingExpectedEnviron("LOG_LEVEL")
    return LoggingConfig(
        log_level=log_level.upper(),
    )


class CloudServiceConfig(BaseModel):
    cloud_service: str | None = "LOCAL"
    access_token: str | None = None


def get_cloud_service_config() -> CloudServiceConfig:
    load_dotenv()
    return CloudServiceConfig(
        cloud_service=(os.getenv("CLOUD_SERVICE") or "LOCAL").upper(),
        access_token=os.getenv("ACCESS_TOKEN"),
    )


class ReportingServiceConfig(BaseModel):
    database_type: str | None = None
    database_server_name: str | None = None
    database_name: str | None = None
    database_user: str | None = None
    database_password: str | None = None
    database_pool_size: int | None = None
    database_echo: bool | None = False


def get_reporting_service_config() -> ReportingServiceConfig:
    load_dotenv()
    return ReportingServiceConfig(
        database_type=os.getenv("REPORTING_DATABASE_TYPE") or "mssql",
        database_server_name=os.getenv("REPORTING_DB_SERVER_NAME"),
        database_name=os.getenv("REPORTING_DB_NAME"),
        database_user=os.getenv("REPORTING_DB_USERNAME"),
        database_password=os.getenv("REPORTING_DB_PASSWORD"),
        database_pool_size=int(os.getenv("REPORTING_DB_POOL_SIZE", "20")),
        database_echo=bool(os.getenv("REPORTING_DB_ECHO") == "false"),
    )


class AwsServiceConfig(BaseModel):
    access_key_id: str | None = None
    secret_access_key: str | None = None
    region_name: str | None = None
    bucket_name: str | None = None


def get_aws_service_config() -> AwsServiceConfig:
    load_dotenv()
    return AwsServiceConfig(
        access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        region_name=os.getenv("AWS_REGION_NAME"),
        bucket_name=os.getenv("AWS_BUCKET_NAME"),
    )


class TestingServiceConfig(BaseModel): ...


class AzureDevOpsServiceConfig(BaseModel):
    wiki_token: str | None = None
    base_url: str | None = None


def get_azure_devops_service_config() -> AzureDevOpsServiceConfig:
    load_dotenv()
    return AzureDevOpsServiceConfig(
        wiki_token=os.getenv("AZURE_WIKI_TOKEN"),
        base_url=os.getenv("AZURE_DEVOPS_BASE_URL"),
    )


class EmailServiceConfig(BaseModel):
    email_user: str | None = None
    email_password: str | None = None
    miner_email_recipient: str | None = None
    true_source_email_recipient: str | None = None


def get_email_service_config() -> EmailServiceConfig:
    load_dotenv()
    return EmailServiceConfig(
        email_user=os.getenv("EMAIL_USER"),
        email_password=os.getenv("EMAIL_PASSWORD"),
        miner_email_recipient=os.getenv("MINER_EMAIL_RECIPIENT"),
        true_source_email_recipient=os.getenv("TRUE_SOURCE_EMAIL_RECIPIENT"),
    )


class TestRunnerConfig(BaseModel):
    browser: str | None = "chrome"
    target_environment: str | None = "dev"
    remote_driver: str | None = None


def get_test_runner_config() -> TestRunnerConfig:
    load_dotenv()
    runner = TestRunnerConfig(
        browser=os.getenv("BROWSER"),
        target_environment=os.getenv("TARGET_ENVIRONMENT").lower(),
        remote_driver=os.getenv("REMOTE_DRIVER_URL"),
    )
    if runner.target_environment not in ["dev", "qa", "uat", "staging", "production"]:
        raise BadConfiguration(
            f"Invalid target environment: {runner.target_environment}. "
            "Expected one of: dev, qa, uat, staging, production."
        )
    return runner


class DriverFactoryConfig(BaseModel):
    driver_location: str | None = "local"
    headless: bool | None = False


def get_driver_factory_config() -> DriverFactoryConfig:
    load_dotenv()
    return DriverFactoryConfig(
        driver_location=os.getenv("DRIVER_LOCATION"),
        headless=bool(os.getenv("HEADLESS")),
    )


class PipelineConfig(BaseModel):
    is_ci_job: bool | None = False


def get_pipeline_config() -> PipelineConfig:
    load_dotenv()
    return PipelineConfig(
        is_ci_job=bool(os.getenv("CI_JOB_RUN")),
    )


class ChatServiceConfig(BaseModel):
    chat_service: str | None = "SLACK"
    webhook_url: str | None = None
    channel_name: str | None = None


def get_chat_service_config() -> ChatServiceConfig:
    load_dotenv()
    return ChatServiceConfig(
        chat_service=os.getenv("CHAT_SERVICE"),
        webhook_url=os.getenv("WEBHOOK_URL"),
        channel_name=os.getenv("CHANNEL_NAME"),
    )


class ValidationConfig(BaseModel):
    """
    Configuration for Pydantic model validation in database operations.

    - validate_reads: Enable validation when reading from database (default: False for performance)
    - validate_writes: Enable validation when writing to database (default: True for data integrity)
    """

    validate_reads: bool = False
    validate_writes: bool = True


def get_validation_config() -> ValidationConfig:
    """Get validation configuration from environment variables."""
    load_dotenv()
    return ValidationConfig(
        validate_reads=os.getenv("FTS_VALIDATE_READS", "0").lower()
        in ("1", "true", "yes"),
        validate_writes=os.getenv("FTS_VALIDATE_WRITES", "1").lower()
        in ("1", "true", "yes"),
    )


def should_validate_read() -> bool:
    """
    Check if validation should be performed for read operations.

    Returns False by default for performance on bulk queries.
    Set FTS_VALIDATE_READS=1 to enable.
    """
    return get_validation_config().validate_reads


def should_validate_write() -> bool:
    """
    Check if validation should be performed for write operations.

    Returns True by default to ensure data integrity.
    Set FTS_VALIDATE_WRITES=0 to disable (not recommended).
    """
    return get_validation_config().validate_writes
