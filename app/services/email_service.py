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


def send_multiuser_token_notification(
    user_email: str, token: str, username: Optional[str] = None, is_new_user: bool = False
) -> None:
    """
    Send email notification with authentication token to a specific user.
    This version bypasses the global email_notification_enabled setting for MultiUserAuthService.

    Args:
        user_email: Email address of the user receiving the token
        token: The authentication token
        username: Optional display name for the user
        is_new_user: Whether this is a welcome email for a new user

    Raises:
        EmailServiceError: If email sending fails
    """
    config = get_config()

    # Get appropriate email service (MailHog or SMTP)
    email_service = get_email_service(config)

    if not email_service.is_available():
        logger.warning(
            "Email service not configured or available, cannot send user token notification"
        )
        return

    try:
        email_service.send_token_notification(
            user_email=user_email, token=token, username=username, is_new_user=is_new_user
        )
        logger.info(
            f"MultiUser token notification email sent successfully to {user_email}"
        )

    except Exception as e:
        logger.error(
            f"Failed to send multiuser token notification email to {user_email}: {e}"
        )
        raise EmailServiceError(f"Email sending failed: {e}")


def send_token_notification(token: str, file_path: Path) -> None:
    """
    Send email notification with the current authentication token.

    This function serves as the external sync callback for the auth service.
    Uses the configured email service (SMTP or MailHog).

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

    # Get appropriate email service (MailHog or SMTP)
    email_service = get_email_service(config)

    if not email_service.is_available():
        logger.warning("Email service not available, cannot send token notification")
        return

    try:
        subject = config.email_subject
        body = f"""
Your Fenrir authentication token has been updated.

Token: {token}
Token File: {file_path}
Environment: {config.environment}

This token is valid for {config.auth_rotation_interval_minutes} minutes.

---
Fenrir Testing System
Automated Token Notification
        """.strip()

        email_service.send_email(
            to_email=config.email_recipient, subject=subject, body=body
        )

        logger.info("Token notification email sent successfully")

    except Exception as e:
        logger.error(f"Failed to send token notification email: {e}")
        raise EmailServiceError(f"Email sending failed: {e}")
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
