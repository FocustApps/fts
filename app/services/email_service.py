"""
Email service for sending authentication token notifications.

Provides SMTP email functionality for notifying administrators and users
of authentication tokens in both single-user and multi-user systems.

This module now delegates to the appropriate email service implementation
(SMTP or MailHog) based on configuration.
"""

from pathlib import Path
from typing import Optional

from app.config import get_config
from app.services.email_interface import get_email_service
from common.app_logging import create_logging

logger = create_logging()


class EmailServiceError(Exception):
    """Base exception for email service operations."""

    pass