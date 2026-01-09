"""
Test configuration for pytest.

Provides common fixtures and test utilities for authentication tests.
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Load environment variables for database connection
load_dotenv()

from common.service_connections.db_service.db_manager import DB_ENGINE

# Import database model fixtures
pytest_plugins = [
    "tests.fixtures.db_model_fixtures",
    "tests.fixtures.composite_fixtures",  # Domain-based composite fixtures
]


@pytest.fixture(scope="session")
def engine() -> Engine:
    """Provide database engine for tests using db_manager configuration."""
    return DB_ENGINE


@pytest.fixture(scope="function")
def session(engine: Engine):
    """Provide sessionmaker for database tests."""
    return sessionmaker(bind=engine)


@pytest.fixture
def temp_auth_dir():
    """Create a temporary directory for auth-related files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def temp_token_file(temp_auth_dir):
    """Create a temporary token file path."""
    return temp_auth_dir / "test_token.txt"


@pytest.fixture
def mock_auth_config():
    """Create a mock authentication configuration."""
    config = MagicMock()
    config.auth_token_file_path = Path("test_token.txt")
    config.auth_rotation_interval_minutes = 30
    config.auth_external_sync_enabled = False
    config.auth_external_sync_url = ""
    return config


@pytest.fixture
def clean_environment():
    """Provide a clean environment without auth-related variables."""
    auth_env_vars = [
        "AUTH_TOKEN_FILE_PATH",
        "AUTH_ROTATION_INTERVAL_MINUTES",
        "AUTH_EXTERNAL_SYNC_ENABLED",
        "AUTH_EXTERNAL_SYNC_URL",
    ]

    # Store original values
    original_values = {}
    for var in auth_env_vars:
        if var in os.environ:
            original_values[var] = os.environ[var]
            del os.environ[var]

    yield

    # Restore original values
    for var, value in original_values.items():
        os.environ[var] = value


@pytest.fixture
def mock_logger():
    """Create a mock logger for testing."""
    with patch("app.services.auth_service.logger") as mock_log:
        yield mock_log


@pytest.fixture(autouse=True)
def cleanup_auth_service():
    """Automatically cleanup auth service after each test."""
    yield

    # Cleanup global auth service if it exists
    try:
        from app.services.auth_service import shutdown_auth_service

        shutdown_auth_service()
    except (RuntimeError, ImportError):
        # Service not initialized or module not available
        pass


@pytest.fixture(scope="function")
def mailhog():
    """
    Provide MailHog test helper for email testing.

    Automatically clears emails before each test.
    Only works when USE_MAILHOG=true environment variable is set.
    """
    try:
        from tests.fixtures.mailhog_helper import MailHogTestHelper

        helper = MailHogTestHelper()
        helper.clear_all_emails()  # Clean slate for each test
        yield helper
    except RuntimeError as e:
        pytest.skip(f"MailHog not available: {e}")


@pytest.fixture(scope="session")
def mailhog_available():
    """
    Check if MailHog is available for testing.

    Returns:
        bool: True if MailHog is configured and reachable
    """
    try:
        from tests.fixtures.mailhog_helper import MailHogTestHelper

        helper = MailHogTestHelper()
        return helper.mailhog.is_available()
    except Exception:
        return False


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "integration: mark test as integration test")
    config.addinivalue_line("markers", "unit: mark test as unit test")
    config.addinivalue_line("markers", "auth: mark test as authentication-related")


# Test data for reuse across test modules
VALID_TEST_TOKENS = [
    "0123456789abcdef",
    "fedcba9876543210",
    "1a2b3c4d5e6f7890",
    "abcdef0123456789",
]

INVALID_TEST_TOKENS = [
    "",
    None,
    "short",
    "toolongtoken12345",
    "invalid_chars!@#",
    "0123456789ABCDEF",  # uppercase
    "0123456789abcdeg",  # invalid hex char
]

TEST_CONFIG_ENVIRONMENTS = [
    {
        "AUTH_TOKEN_FILE_PATH": "/tmp/test_token.txt",
        "AUTH_ROTATION_INTERVAL_MINUTES": "15",
        "AUTH_EXTERNAL_SYNC_ENABLED": "true",
        "AUTH_EXTERNAL_SYNC_URL": "https://example.com/sync",
    },
    {
        "AUTH_TOKEN_FILE_PATH": "relative/token.txt",
        "AUTH_ROTATION_INTERVAL_MINUTES": "60",
        "AUTH_EXTERNAL_SYNC_ENABLED": "false",
        "AUTH_EXTERNAL_SYNC_URL": "",
    },
]
