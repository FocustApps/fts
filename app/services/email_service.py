"""
Email service for sending authentication token notifications.

Provides SMTP email functionality for notifying administrators
of rotating authentication tokens.
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path

from app.config import get_config
from common.app_logging import create_logging

logger = create_logging()


class EmailServiceError(Exception):
    """Base exception for email service operations."""

    pass


def send_token_notification(token: str, file_path: Path) -> None:
    """
    Send email notification with the current authentication token.

    This function serves as the external sync callback for the auth service.
    Uses Gmail SMTP_SSL for secure email delivery (based on proven implementation).

    Args:
        token: The new authentication token
        file_path: Path to the token file (for reference)

    Raises:
        EmailServiceError: If email sending fails
    """
    config = get_config()

    if not config.email_notification_enabled:
        logger.debug("Email notifications disabled, skipping token notification")
        return

    if not config.email_recipient:
        logger.warning("Email recipient not configured, cannot send token notification")
        return

    if not config.smtp_username or not config.smtp_password:
        logger.warning("SMTP credentials not configured, cannot send token notification")
        return

    try:
        # Create message
        msg = MIMEMultipart()
        msg["From"] = config.smtp_username
        msg["To"] = config.email_recipient
        msg["Subject"] = config.email_subject

        # Email body
        body = f"""
Fenrir Authentication Token Update

A new authentication token has been generated for the Fenrir Testing System.

Token: {token}
Generated at: {file_path}
Environment: {config.environment}

This token is valid for {config.auth_rotation_interval_minutes} minutes.

Use this token in the X-Auth-Token header or as a Bearer token when making API requests.

---
Fenrir Testing System
Automated Token Notification
        """.strip()

        msg.attach(MIMEText(body, "plain"))

        # Use Gmail SMTP_SSL for secure connection (port 465)
        with smtplib.SMTP_SSL(config.smtp_server, config.smtp_port) as server:
            server.login(config.smtp_username, config.smtp_password)
            server.sendmail(config.smtp_username, config.email_recipient, msg.as_string())

        logger.info(
            f"Token notification email sent successfully to {config.email_recipient}"
        )

    except Exception as e:
        logger.error(f"Failed to send token notification email: {e}")
        raise EmailServiceError(f"Email sending failed: {e}")


def test_email_configuration() -> bool:
    """
    Test the email configuration by attempting to connect to SMTP server.
    Uses Gmail SMTP_SSL for secure connection testing.

    Returns:
        True if configuration is valid and connection successful
    """
    config = get_config()

    if not config.email_notification_enabled:
        logger.info("Email notifications disabled")
        return False

    if not config.smtp_username or not config.smtp_password:
        logger.warning("SMTP credentials not configured")
        return False

    try:
        # Test Gmail SMTP_SSL connection (port 465)
        with smtplib.SMTP_SSL(config.smtp_server, config.smtp_port) as server:
            server.login(config.smtp_username, config.smtp_password)

        logger.info("Email configuration test successful")
        return True

    except Exception as e:
        logger.error(f"Email configuration test failed: {e}")
        return False
