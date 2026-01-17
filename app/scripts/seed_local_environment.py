#!/usr/bin/env python3
"""
Local Environment Seeding Script

This script seeds test data into the local development environment using API endpoints.
It creates sample data for environments, users, pages, identifiers, and email processor records
to facilitate development and testing.

Usage:
    python app/scripts/seed_local_environment.py

Requirements:
    - Application must be running and accessible at http://localhost:8080
    - ENVIRONMENT variable must be set to 'local'
    - Authentication token will be retrieved from application startup logs
"""

import os
import sys
import time
import logging
import requests
from typing import Dict, List, Optional, Any
from pathlib import Path

# Add project root to path for selenium controller import
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from app.config import get_config
from common.service_connections.db_service.db_manager import DB_ENGINE

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Configuration
BASE_URL = os.getenv("BASE_URL", "http://localhost:8080")
API_VERSION = "v1"
MAX_RETRIES = 3
RETRY_DELAY = 2

engine = DB_ENGINE


class SeedingError(Exception):
    """Custom exception for seeding operations."""

    pass


class APIClient:
    """HTTP client for making API requests to the Fenrir application with JWT auth."""

    def __init__(self, base_url: str, auth_token: Optional[str] = None):
        self.base_url = base_url.rstrip("/")
        self.auth_token = auth_token
        self.session = requests.Session()

        # Set default headers for JWT authentication
        if self.auth_token:
            self.session.headers.update(
                {
                    "Authorization": f"Bearer {self.auth_token}",
                    "Content-Type": "application/json",
                }
            )

    def _make_request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """Make HTTP request with retry logic."""
        url = f"{self.base_url}{endpoint}"

        for attempt in range(MAX_RETRIES):
            try:
                logger.debug(f"Making {method} request to {url} (attempt {attempt + 1})")
                response = self.session.request(method, url, **kwargs)

                if response.status_code in [200, 201]:
                    return response
                elif response.status_code == 404:
                    logger.warning(f"Endpoint not found: {url}")
                    raise SeedingError(f"API endpoint not found: {endpoint}")
                elif response.status_code == 401:
                    logger.error("Authentication failed - invalid token")
                    raise SeedingError("Authentication failed - check auth token")
                else:
                    logger.warning(
                        f"Request failed with status {response.status_code}: {response.text}"
                    )

            except requests.exceptions.ConnectionError:
                logger.warning(f"Connection failed on attempt {attempt + 1}")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY)
                    continue
                else:
                    raise SeedingError(
                        "Failed to connect to application after multiple attempts"
                    )

            except requests.exceptions.RequestException as e:
                logger.error(f"Request error: {e}")
                raise SeedingError(f"Request failed: {e}")

        raise SeedingError(f"Failed to complete request after {MAX_RETRIES} attempts")

    def post(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Make POST request and return JSON response."""
        response = self._make_request("POST", endpoint, json=data)
        return response.json()

    def get(self, endpoint: str) -> Dict[str, Any]:
        """Make GET request and return JSON response."""
        response = self._make_request("GET", endpoint)
        return response.json()


def get_auth_token() -> str:
    """
    Retrieve JWT access token by logging in with admin credentials.

    For local development, uses credentials from .env or defaults.
    """
    # First, try to get token from environment variable (for testing)
    token = os.getenv("FENRIR_JWT_TOKEN")
    if token:
        logger.info("Using JWT token from environment variable")
        return token

    # Get admin credentials from config
    try:
        config = get_config()
        admin_email = config.email_recipient

        if not admin_email:
            logger.warning(
                "EMAIL_RECIPIENT not set in .env, using default admin@example.com"
            )
            admin_email = "admin@example.com"

        # For local development, use env variable or default password
        # Default matches the password used in seed_admin_user.py
        admin_password = os.getenv("ADMIN_PASSWORD", "Admin123!")

        logger.info(f"Attempting to login as: {admin_email}")

        # Call JWT login endpoint
        login_response = requests.post(
            f"{BASE_URL}/v1/api/auth/login",
            json={
                "email": admin_email,
                "password": admin_password,
            },
            timeout=10,
        )

        if login_response.status_code == 200:
            token_data = login_response.json()
            access_token = token_data.get("access_token")

            if access_token:
                logger.info("✓ Successfully obtained JWT access token")
                return access_token
            else:
                logger.error("No access_token in login response")
                raise SeedingError("Failed to get access token from login")
        else:
            logger.error(f"Login failed: {login_response.status_code}")
            logger.error(f"Response: {login_response.text}")
            raise SeedingError(f"Login failed with status {login_response.status_code}")

    except requests.exceptions.ConnectionError:
        logger.error("Could not connect to application - is it running?")
        raise SeedingError("Application not accessible")
    except Exception as e:
        logger.error(f"Error during JWT authentication: {e}")
        raise SeedingError(f"Authentication failed: {e}")


def wait_for_application_ready(client: APIClient, max_wait: int = 60) -> bool:
    """
    Wait for the application to be ready by checking a health endpoint.

    Args:
        client: API client instance
        max_wait: Maximum time to wait in seconds

    Returns:
        True if application is ready, False otherwise
    """
    logger.info("Waiting for application to be ready...")
    start_time = time.time()

    while time.time() - start_time < max_wait:
        try:
            # Try to access the docs endpoint as a health check
            response = requests.get(f"{BASE_URL}/docs", timeout=5)
            if response.status_code == 200:
                logger.info("Application is ready!")
                return True
        except requests.exceptions.RequestException:
            pass

        time.sleep(2)

    logger.error(f"Application not ready after {max_wait} seconds")
    return False


def check_existing_data(client: APIClient) -> Dict[str, bool]:
    """
    Check if seed data already exists to avoid duplicates.

    Returns:
        Dictionary indicating which data types already exist
    """
    existing = {
        "environments": False,
        "users": False,
        "pages": False,
        "identifiers": False,
        "email_processors": False,
        "actions": False,
    }

    try:
        # Check environments
        env_response = client.get("/v1/env/api/")
        if isinstance(env_response, list) and len(env_response) > 0:
            existing["environments"] = True
            logger.info(f"Found {len(env_response)} existing environments")
    except Exception as e:
        logger.debug(f"Could not check environments: {e}")

    try:
        # Check users
        user_response = client.get("/v1/user/api/all-users")
        if isinstance(user_response, list) and len(user_response) > 0:
            existing["users"] = True
            logger.info(f"Found {len(user_response)} existing users")
    except Exception as e:
        logger.debug(f"Could not check users: {e}")

    try:
        # Check pages
        page_response = client.get("/v1/pages/api/")
        if isinstance(page_response, dict) and "data" in page_response:
            pages = page_response["data"]
        elif isinstance(page_response, list):
            pages = page_response
        else:
            pages = []

        if len(pages) > 0:
            existing["pages"] = True
            logger.info(f"Found {len(pages)} existing pages")
    except Exception as e:
        logger.debug(f"Could not check pages: {e}")

    try:
        # Check identifiers
        identifier_response = client.get("/v1/api/identifiers/")
        if isinstance(identifier_response, list) and len(identifier_response) > 0:
            existing["identifiers"] = True
            logger.info(f"Found {len(identifier_response)} existing identifiers")
    except Exception as e:
        logger.debug(f"Could not check identifiers: {e}")

    try:
        # Check actions
        action_response = client.get("/v1/api/actions/")
        if isinstance(action_response, list) and len(action_response) > 0:
            existing["actions"] = True
            logger.info(f"Found {len(action_response)} existing actions")
    except Exception as e:
        logger.debug(f"Could not check actions: {e}")

    return existing


def validate_seeding_results(client: APIClient) -> Dict[str, Any]:
    """
    Validate that seeding was successful by checking created records.

    Returns:
        Dictionary with validation results
    """
    logger.info("Validating seeding results...")

    results = {
        "environments": {"count": 0, "success": False},
        "users": {"count": 0, "success": False},
        "pages": {"count": 0, "success": False},
        "identifiers": {"count": 0, "success": False},
        "actions": {"count": 0, "success": False},
        "overall_success": False,
    }

    try:
        # Validate environments
        env_response = client.get("/v1/env/api/")
        if isinstance(env_response, list):
            results["environments"]["count"] = len(env_response)
            results["environments"]["success"] = (
                len(env_response) >= 4
            )  # We seeded 4 environments
            logger.info(f"✓ Environments validation: {len(env_response)} found")

        # Validate users
        user_response = client.get("/v1/user/api/all-users")
        if isinstance(user_response, list):
            results["users"]["count"] = len(user_response)
            results["users"]["success"] = len(user_response) >= 4  # We seeded 4 users
            logger.info(f"✓ Users validation: {len(user_response)} found")

        # Validate pages
        page_response = client.get("/v1/api/pages/")
        if isinstance(page_response, dict) and "data" in page_response:
            pages = page_response["data"]
        elif isinstance(page_response, list):
            pages = page_response
        else:
            pages = []

        results["pages"]["count"] = len(pages)
        results["pages"]["success"] = len(pages) >= 6  # We seeded 6 pages
        logger.info(f"✓ Pages validation: {len(pages)} found")

        # Validate identifiers
        identifier_response = client.get("/v1/api/identifiers/")
        if isinstance(identifier_response, list):
            results["identifiers"]["count"] = len(identifier_response)
            results["identifiers"]["success"] = (
                len(identifier_response) >= 10
            )  # Expected multiple identifiers
            logger.info(f"✓ Identifiers validation: {len(identifier_response)} found")

        # Validate actions
        action_response = client.get("/v1/api/actions/")
        if isinstance(action_response, list):
            results["actions"]["count"] = len(action_response)
            results["actions"]["success"] = (
                len(action_response) >= 15
            )  # Expected selenium controller methods (18+ methods)
            logger.info(f"✓ Actions validation: {len(action_response)} found")

        # Overall success
        results["overall_success"] = all(
            [
                results["environments"]["success"],
                results["users"]["success"],
                results["pages"]["success"],
                results["identifiers"]["success"],
                results["actions"]["success"],
            ]
        )

        if results["overall_success"]:
            logger.info("🎉 All seeding validation checks passed!")
        else:
            logger.warning("⚠️  Some seeding validation checks failed")

    except Exception as e:
        logger.error(f"Validation failed with error: {e}")
        results["overall_success"] = False

    return results


def seed_environments(client: APIClient) -> List[Dict[str, Any]]:
    """
    Seed sample environments for testing.

    Returns:
        List of created environment records
    """
    logger.info("Seeding environments...")

    sample_environments = [
        {
            "environment_name": "Development",
            "environment_designation": "dev",
            "environment_base_url": "https://dev.example.com",
            "api_base_url": "https://api-dev.example.com",
            "environment_status": "active",
            "users_in_environment": [],
        },
        {
            "environment_name": "Staging",
            "environment_designation": "staging",
            "environment_base_url": "https://staging.example.com",
            "api_base_url": "https://api-staging.example.com",
            "environment_status": "active",
            "users_in_environment": [],
        },
        {
            "environment_name": "QA Testing",
            "environment_designation": "qa",
            "environment_base_url": "https://qa.example.com",
            "api_base_url": "https://api-qa.example.com",
            "environment_status": "active",
            "users_in_environment": [],
        },
        {
            "environment_name": "Local Development",
            "environment_designation": "local",
            "environment_base_url": "http://localhost:3000",
            "api_base_url": "http://localhost:8080",
            "environment_status": "active",
            "users_in_environment": [],
        },
    ]

    created_environments = []

    for env_data in sample_environments:
        try:
            logger.info(f"Creating environment: {env_data['environment_name']}")
            result = client.post("/v1/env/api/", env_data)
            created_environments.append(result)
            logger.info(
                f"✓ Environment '{env_data['environment_name']}' created with ID: {result.get('environment_id')}"
            )

        except SeedingError as e:
            if "already exists" in str(e).lower():
                logger.info(
                    f"Environment '{env_data['environment_name']}' already exists, skipping"
                )
            else:
                logger.error(
                    f"Failed to create environment '{env_data['environment_name']}': {e}"
                )
        except Exception as e:
            logger.error(
                f"Unexpected error creating environment '{env_data['environment_name']}': {e}"
            )

    logger.info(
        f"Environment seeding completed. Created {len(created_environments)} environments."
    )
    return created_environments


def seed_users(
    client: APIClient, environments: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Seed sample users associated with environments.

    Args:
        environments: List of environment records to associate users with

    Returns:
        List of created user records
    """
    logger.info("Seeding users...")

    if not environments:
        logger.warning("No environments available for user seeding")
        return []

    # Create sample users for different environments
    sample_users_templates = [
        {
            "username": "dev_user",
            "email": "dev.user@example.com",
            "password": "dev_password_123",
            "secret_provider": "azure_keyvault",
            "secret_url": "https://dev-keyvault.vault.azure.net/",
            "secret_name": "dev-credentials",
        },
        {
            "username": "qa_tester",
            "email": "qa.tester@example.com",
            "password": "qa_password_123",
            "secret_provider": "azure_keyvault",
            "secret_url": "https://qa-keyvault.vault.azure.net/",
            "secret_name": "qa-credentials",
        },
        {
            "username": "staging_user",
            "email": "staging.user@example.com",
            "password": "staging_password_123",
            "secret_provider": "azure_keyvault",
            "secret_url": "https://staging-keyvault.vault.azure.net/",
            "secret_name": "staging-credentials",
        },
        {
            "username": "local_dev",
            "email": "local.dev@example.com",
            "password": "local_password_123",
            "secret_provider": "local_file",
            "secret_url": "/tmp/local_secrets.json",
            "secret_name": "local-dev-credentials",
        },
    ]

    created_users = []

    # Create users and associate them with environments
    for i, user_template in enumerate(sample_users_templates):
        # Assign user to an environment (cycle through available environments)
        env = environments[i % len(environments)]
        environment_id = env.get("id")

        if not environment_id:
            logger.warning(
                f"Environment missing ID, skipping user: {user_template['username']}"
            )
            continue

        user_data = {**user_template, "environment_id": environment_id}

        try:
            logger.info(
                f"Creating user: {user_data['username']} for environment: {env.get('name')}"
            )
            result = client.post("/v1/user/api/user", user_data)
            created_users.append(result)
            logger.info(
                f"✓ User '{user_data['username']}' created with ID: {result.get('id')}"
            )

        except SeedingError as e:
            if "already exists" in str(e).lower():
                logger.info(f"User '{user_data['username']}' already exists, skipping")
            else:
                logger.error(f"Failed to create user '{user_data['username']}': {e}")
        except Exception as e:
            logger.error(f"Unexpected error creating user '{user_data['username']}': {e}")

    logger.info(f"User seeding completed. Created {len(created_users)} users.")
    return created_users


def seed_pages(
    client: APIClient, environments: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Seed sample pages with realistic URLs and environment associations.

    Args:
        environments: List of environment records to associate pages with

    Returns:
        List of created page records
    """
    logger.info("Seeding pages...")

    if not environments:
        logger.warning("No environments available for page seeding")
        return []

    # Extract environment names for page associations
    env_names = [
        env.get("environment_designation", "dev")
        for env in environments
        if env.get("environment_designation")
    ]
    if not env_names:
        env_names = ["dev"]  # fallback

    sample_pages = [
        {
            "page_name": "Login Page",
            "page_url": "https://app.example.com/login",
            "environments": {"dev": True, "staging": True},  # JSONB dict format
            "identifiers": [],
        },
        {
            "page_name": "Dashboard",
            "page_url": "https://app.example.com/dashboard",
            "environments": {env: True for env in env_names},  # All environments
            "identifiers": [],
        },
        {
            "page_name": "User Profile",
            "page_url": "https://app.example.com/profile",
            "environments": {"dev": True, "staging": True, "qa": True},
            "identifiers": [],
        },
        {
            "page_name": "Settings Page",
            "page_url": "https://app.example.com/settings",
            "environments": {"dev": True, "staging": True},
            "identifiers": [],
        },
        {
            "page_name": "Admin Panel",
            "page_url": "https://app.example.com/admin",
            "environments": {"staging": True, "qa": True},
            "identifiers": [],
        },
        {
            "page_name": "Reports Page",
            "page_url": "https://app.example.com/reports",
            "environments": {env: True for env in env_names},
            "identifiers": [],
        },
    ]

    created_pages = []

    for page_data in sample_pages:
        try:
            logger.info(f"Creating page: {page_data['page_name']}")
            result = client.post("/v1/api/pages/", page_data)
            created_pages.append(result)
            logger.info(
                f"✓ Page '{page_data['page_name']}' created with ID: {result.get('page_id')}"
            )

        except SeedingError as e:
            if "already exists" in str(e).lower():
                logger.info(f"Page '{page_data['page_name']}' already exists, skipping")
            else:
                logger.error(f"Failed to create page '{page_data['page_name']}': {e}")
        except Exception as e:
            logger.error(
                f"Unexpected error creating page '{page_data['page_name']}': {e}"
            )

    logger.info(f"Page seeding completed. Created {len(created_pages)} pages.")
    return created_pages


def seed_identifiers(
    client: APIClient, pages: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Seed sample web element identifiers linked to pages.

    Args:
        pages: List of page records to associate identifiers with

    Returns:
        List of created identifier records
    """
    logger.info("Seeding identifiers...")

    if not pages:
        logger.warning("No pages available for identifier seeding")
        return []

    # Define realistic web element identifiers for different pages
    identifier_templates = {
        "Login Page": [
            {
                "element_name": "username_field",
                "locator_strategy": "id",
                "locator_query": "username",
            },
            {
                "element_name": "password_field",
                "locator_strategy": "id",
                "locator_query": "password",
            },
            {
                "element_name": "login_button",
                "locator_strategy": "xpath",
                "locator_query": "//button[@type='submit' and contains(text(), 'Login')]",
            },
        ],
        "Dashboard": [
            {
                "element_name": "welcome_message",
                "locator_strategy": "css",
                "locator_query": ".welcome-message h1",
            },
            {
                "element_name": "navigation_menu",
                "locator_strategy": "css",
                "locator_query": "nav.main-menu",
            },
            {
                "element_name": "user_profile_link",
                "locator_strategy": "xpath",
                "locator_query": "//a[contains(@href, '/profile')]",
            },
        ],
        "User Profile": [
            {
                "element_name": "edit_profile_button",
                "locator_strategy": "css",
                "locator_query": "button.edit-profile",
            },
            {
                "element_name": "email_field",
                "locator_strategy": "name",
                "locator_query": "email",
            },
        ],
        "Settings Page": [
            {
                "element_name": "save_settings_button",
                "locator_strategy": "css",
                "locator_query": "button[type='submit'].save-settings",
            }
        ],
        "Admin Panel": [
            {
                "element_name": "admin_dashboard_title",
                "locator_strategy": "tag",
                "locator_query": "h1",
            },
            {
                "element_name": "user_management_link",
                "locator_strategy": "xpath",
                "locator_query": "//a[contains(text(), 'User Management')]",
            },
        ],
        "Reports Page": [
            {
                "element_name": "generate_report_button",
                "locator_strategy": "css",
                "locator_query": "button.generate-report",
            },
            {
                "element_name": "date_filter",
                "locator_strategy": "id",
                "locator_query": "date-range-picker",
            },
        ],
    }

    created_identifiers = []

    for page in pages:
        page_name = page.get("page_name")
        page_id = page.get("page_id")

        if not page_id or not page_name:
            logger.warning(f"Page missing required fields: {page}")
            continue

        # Get identifiers for this page type
        identifiers_for_page = identifier_templates.get(page_name, [])

        for identifier_template in identifiers_for_page:
            identifier_data = {
                **identifier_template,
                "page_id": page_id,
            }

            try:
                logger.info(
                    f"Creating identifier: {identifier_data['element_name']} for page: {page_name}"
                )
                result = client.post("/v1/api/identifiers/", identifier_data)
                created_identifiers.append(result)
                logger.info(
                    f"✓ Identifier '{identifier_data['element_name']}' created with ID: {result.get('identifier_id')}"
                )

            except SeedingError as e:
                if "already exists" in str(e).lower():
                    logger.info(
                        f"Identifier '{identifier_data['element_name']}' already exists, skipping"
                    )
                else:
                    logger.error(
                        f"Failed to create identifier '{identifier_data['element_name']}': {e}"
                    )
            except Exception as e:
                logger.error(
                    f"Unexpected error creating identifier '{identifier_data['element_name']}': {e}"
                )

    logger.info(
        f"Identifier seeding completed. Created {len(created_identifiers)} identifiers."
    )
    return created_identifiers


def seed_actions(client: APIClient) -> List[Dict[str, Any]]:
    """
    Seed SeleniumController method documentation as actions.

    NOTE: Temporarily disabled due to JSON serialization issues with MethodDocumentation objects.
    The action_chain_model expects different data structure than what selenium_documentation returns.

    Returns:
        Empty list (seeding disabled)
    """
    logger.info("Actions seeding temporarily disabled - requires data structure update")
    return []

    # DISABLED CODE BELOW - needs refactoring
    # try:
    #     # Get selenium controller method documentation
    #     selenium_methods = get_selenium_controller_methods_documentation()
    #     logger.info(f"Found {len(selenium_methods)} SeleniumController methods to seed")
    #
    #     created_actions = []
    #
    #     for method_name, documentation in selenium_methods.items():
    #         action_data = {
    #             "action_method": method_name,
    #             "action_documentation": documentation,
    #         }
    #
    #         try:
    #             logger.info(f"Creating action: {method_name}")
    #             result = client.post("/v1/api/actions/", action_data)
    #             created_actions.append(result)
    #             logger.info(
    #                 f"✓ Action '{method_name}' created with ID: {result.get('id')}"
    #             )
    #
    #         except SeedingError as e:
    #             if "already exists" in str(e).lower():
    #                 logger.info(f"Action '{method_name}' already exists, skipping")
    #             else:
    #                 logger.error(f"Failed to create action '{method_name}': {e}")
    #         except Exception as e:
    #             logger.error(f"Unexpected error creating action '{method_name}': {e}")
    #
    #     logger.info(f"Action seeding completed. Created {len(created_actions)} actions.")
    #     return created_actions
    #
    # except Exception as e:
    #     logger.error(f"Failed to seed actions: {e}")
    #     return []


def main():
    """Main seeding function."""
    logger.info("Starting local environment seeding...")

    # Get authentication token
    try:
        auth_token = get_auth_token()
        logger.info("Authentication token retrieved")
    except Exception as e:
        logger.error(f"Failed to get authentication token: {e}")
        sys.exit(1)

    # Create API client
    client = APIClient(BASE_URL, auth_token)

    # Wait for application to be ready
    if not wait_for_application_ready(client):
        logger.error("Application not ready - aborting seeding")
        sys.exit(1)

    # Check for existing data
    existing_data = check_existing_data(client)

    try:
        # Step 1: Seed environments (must be first as other entities depend on them)
        environments = []
        if not existing_data["environments"]:
            environments = seed_environments(client)
        else:
            logger.info("Environments already exist, fetching existing ones")
            try:
                env_response = client.get("/v1/env/api/")
                environments = env_response if isinstance(env_response, list) else []
            except Exception as e:
                logger.warning(f"Could not fetch existing environments: {e}")

        # Step 2: Seed users (depends on environments)
        users = []
        if not existing_data["users"] and environments:
            users = seed_users(client, environments)
        else:
            logger.info(
                "Users already exist or no environments available, skipping user seeding"
            )

        # Step 3: Seed pages (depends on environments)
        pages = []
        if not existing_data["pages"] and environments:
            pages = seed_pages(client, environments)
        else:
            logger.info(
                "Pages already exist or no environments available, fetching existing ones"
            )
            try:
                page_response = client.get("/v1/api/pages/")
                # Handle different response formats
                if isinstance(page_response, dict) and "data" in page_response:
                    pages = page_response["data"]
                elif isinstance(page_response, list):
                    pages = page_response
            except Exception as e:
                logger.warning(f"Could not fetch existing pages: {e}")

        # Step 4: Seed identifiers (depends on pages)
        identifiers = []
        if not existing_data["identifiers"] and pages:
            identifiers = seed_identifiers(client, pages)
        else:
            logger.info(
                "Identifiers already exist or no pages available, skipping identifier seeding"
            )

        # Step 5: Seed actions (independent of other data)
        actions = []
        if not existing_data["actions"]:
            actions = seed_actions(client)
        else:
            logger.info("Actions already exist, skipping action seeding")

        # Step 6: Validate seeding results
        validation_results = validate_seeding_results(client)

        if validation_results["overall_success"]:
            logger.info("✅ Local environment seeding completed successfully!")
            logger.info(
                f"Created: {validation_results['environments']['count']} environments, "
                f"{validation_results['users']['count']} users, "
                f"{validation_results['pages']['count']} pages, "
                f"{validation_results['identifiers']['count']} identifiers, "
                f"{validation_results['actions']['count']} actions"
            )
        else:
            logger.warning("⚠️  Seeding completed with some issues - check logs above")
            return 1  # Return error code for debugging

        return 0  # Success

    except Exception as e:
        logger.error(f"Seeding failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
