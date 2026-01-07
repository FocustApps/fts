"""
Database-related enumerations.

This module contains enums used across the database models for Fenrir Testing System.
All enums should be defined here for consistency and reusability across table definitions.
"""

from enum import StrEnum


class SystemEnum(StrEnum):
    """Enumeration of supported systems for email processing."""

    MINER_OCR = "miner_ocr"
    TRUE_SOURCE_OCR = "true_source_ocr"

    @staticmethod
    def get_valid_systems():
        return [system.value for system in SystemEnum]

    @staticmethod
    def is_valid_system(system: str):
        return system in SystemEnum.get_valid_systems()


class AccountRoleEnum(StrEnum):
    """Enumeration of user roles within an account."""

    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"


class SubscriptionTierEnum(StrEnum):
    """Enumeration of subscription tiers."""

    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"
    BIG_AF = "big_af"


class BillingCycleEnum(StrEnum):
    """Enumeration of billing cycle options."""

    MONTHLY = "monthly"
    YEARLY = "yearly"
    PERPETUAL = "perpetual"


class PaymentMethodEnum(StrEnum):
    """Enumeration of payment methods."""

    CREDIT_CARD = "credit_card"
    PAYPAL = "paypal"
    BANK_TRANSFER = "bank_transfer"
    SYSTEM = "system"


class TagCategoryEnum(StrEnum):
    """Enumeration of tag categories for organizing tags."""

    FUNCTIONAL = "functional"
    PRIORITY = "priority"
    AUTOMATION_TYPE = "automation_type"
    ENVIRONMENT = "environment"
    REGRESSION = "regression"
    SMOKE = "smoke"
    API = "api"
    UI = "ui"
    DATABASE = "database"
    INTEGRATION = "integration"
    MANUAL = "manual"
    DEPRECATED = "deprecated"


class EntityTypeEnum(StrEnum):
    """Enumeration of entity types that can be tagged."""

    SUITE = "suite"
    TEST_CASE = "test_case"
    ACTION_CHAIN = "action_chain"
    PLAN = "plan"
    API_ACTION = "api_action"
    DATABASE_ACTION = "database_action"
    REPOSITORY_ACTION = "repository_action"
    INFRASTRUCTURE_ACTION = "infrastructure_action"
    USER_INTERFACE_ACTION = "user_interface_action"


class HttpMethodEnum(StrEnum):
    """Enumeration of HTTP methods for API actions."""

    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"


class TestTypeEnum(StrEnum):
    """Enumeration of test case types."""

    FUNCTIONAL = "functional"
    INTEGRATION = "integration"
    REGRESSION = "regression"
    SMOKE = "smoke"
    PERFORMANCE = "performance"
    SECURITY = "security"


class AnalysisTypeEnum(StrEnum):
    """Enumeration of repository analysis types."""

    CODE_QUALITY = "code_quality"
    SECURITY_SCAN = "security_scan"
    COVERAGE = "coverage"
    DEPENDENCY_CHECK = "dependency_check"
    LINT = "lint"


class DatabaseTypeEnum(StrEnum):
    """Enumeration of database types for database actions."""

    POSTGRESQL = "postgresql"
    MSSQL = "mssql"
    MYSQL = "mysql"
    SQLITE = "sqlite"
    ORACLE = "oracle"

    @staticmethod
    def get_database_type(database_type: str) -> "DatabaseTypeEnum":
        """Convert string to DatabaseTypeEnum."""
        try:
            return DatabaseTypeEnum(database_type.lower())
        except ValueError:
            raise ValueError(
                f"Invalid database type: {database_type}. "
                f"Valid types are: {[dt.value for dt in DatabaseTypeEnum]}"
            )


class CloudProviderEnum(StrEnum):
    """Enumeration of cloud providers for infrastructure actions."""

    AZURE = "azure"
    AWS = "aws"
    GCP = "gcp"
    DOCKER = "docker"
    KUBERNETES = "kubernetes"


class InfrastructureOperationEnum(StrEnum):
    """Enumeration of infrastructure operations."""

    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    START = "start"
    STOP = "stop"
    RESTART = "restart"
    SCALE = "scale"


class AuditActionEnum(StrEnum):
    """Enumeration of audit log actions."""

    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    ACTIVATE = "activate"
    DEACTIVATE = "deactivate"
    LOGIN = "login"
    LOGOUT = "logout"
    TOKEN_REVOKE = "token_revoke"
    PASSWORD_CHANGE = "password_change"
    TOKEN_VALIDATION = "token_validation"
    ACCOUNT_CONTEXT_SWITCH = "account_context_switch"


__all__ = [
    "SystemEnum",
    "AccountRoleEnum",
    "SubscriptionTierEnum",
    "BillingCycleEnum",
    "PaymentMethodEnum",
    "TagCategoryEnum",
    "EntityTypeEnum",
    "HttpMethodEnum",
    "TestTypeEnum",
    "AnalysisTypeEnum",
    "DatabaseTypeEnum",
    "CloudProviderEnum",
    "InfrastructureOperationEnum",
    "AuditActionEnum",
]
