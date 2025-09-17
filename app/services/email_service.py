"""
Email service for sending authentication token notifications.

Provides SMTP email functionality for notifying administrators and users
of authentication tokens in both single-user and multi-user systems.
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from typing import Optional

from app.config import get_config
from common.app_logging import create_logging

logger = create_logging()


class EmailServiceError(Exception):
    """Base exception for email service operations."""

    pass


def send_user_token_notification(
    user_email: str, token: str, username: Optional[str] = None, is_new_user: bool = False
) -> None:
    """
    Send email notification with authentication token to a specific user.

    Args:
        user_email: Email address of the user receiving the token
        token: The authentication token
        username: Optional display name for the user
        is_new_user: Whether this is a welcome email for a new user

    Raises:
        EmailServiceError: If email sending fails
    """
    config = get_config()

    if not config.email_notification_enabled:
        logger.debug("Email notifications disabled, skipping user token notification")
        return

    if not config.smtp_username or not config.smtp_password:
        logger.warning(
            "SMTP credentials not configured, cannot send user token notification"
        )
        return

    try:
        # Create message
        msg = MIMEMultipart()
        msg["From"] = config.smtp_username
        msg["To"] = user_email

        if is_new_user:
            msg["Subject"] = "Welcome to Fenrir Testing System - Your Access Token"
            greeting = f"Welcome to the Fenrir Testing System{', ' + username if username else ''}!"
            intro = "You have been granted access to the Fenrir Testing System. Below is your authentication token:"
        else:
            msg["Subject"] = "Fenrir Testing System - New Authentication Token"
            greeting = f"Hello{', ' + username if username else ''}!"
            intro = "A new authentication token has been generated for your Fenrir Testing System access:"

        # Email body
        body = f"""
{greeting}

{intro}

Token: {token}
Valid for: 24 hours
Environment: {config.environment}

HOW TO USE YOUR TOKEN:

1. Web Interface:
   - Visit the Fenrir login page
   - Enter your token in the login form

2. API Access:
   - Include in X-Auth-Token header: X-Auth-Token: {token}
   - Or use Bearer token: Authorization: Bearer {token}

IMPORTANT SECURITY NOTES:
- Keep your token secure and do not share it
- Tokens expire after 24 hours for security
- Contact your administrator if you need a new token

For support or questions, please contact your system administrator.

---
Fenrir Testing System
Automated Token Notification
        """.strip()

        msg.attach(MIMEText(body, "plain"))

        # Use Gmail SMTP_SSL for secure connection (port 465)
        with smtplib.SMTP_SSL(config.smtp_server, config.smtp_port) as server:
            server.login(config.smtp_username, config.smtp_password)
            server.sendmail(config.smtp_username, user_email, msg.as_string())

        logger.info(f"User token notification email sent successfully to {user_email}")

    except Exception as e:
        logger.error(f"Failed to send user token notification email to {user_email}: {e}")
        raise EmailServiceError(f"Email sending failed: {e}")


def send_admin_user_notification(
    admin_email: str, user_email: str, action: str, username: Optional[str] = None
) -> None:
    """
    Send admin notification about user management actions.

    Args:
        admin_email: Email address of the admin to notify
        user_email: Email address of the user who was affected
        action: Action that was performed (e.g., "added", "deactivated", "token_generated")
        username: Optional username of the affected user

    Raises:
        EmailServiceError: If email sending fails
    """
    config = get_config()

    if not config.email_notification_enabled:
        logger.debug("Email notifications disabled, skipping admin notification")
        return

    if not config.smtp_username or not config.smtp_password:
        logger.warning("SMTP credentials not configured, cannot send admin notification")
        return

    try:
        # Create message
        msg = MIMEMultipart()
        msg["From"] = config.smtp_username
        msg["To"] = admin_email
        msg["Subject"] = f"Fenrir Admin Alert - User {action.replace('_', ' ').title()}"

        # Email body
        body = f"""
Fenrir Testing System - Admin Notification

A user management action has been performed:

Action: {action.replace('_', ' ').title()}
User Email: {user_email}
Username: {username or 'Not specified'}
Environment: {config.environment}
Timestamp: {Path(__file__).stat().st_mtime}

This is an automated notification from the Fenrir Testing System.

---
Fenrir Testing System
Automated Admin Notification
        """.strip()

        msg.attach(MIMEText(body, "plain"))

        # Use Gmail SMTP_SSL for secure connection (port 465)
        with smtplib.SMTP_SSL(config.smtp_server, config.smtp_port) as server:
            server.login(config.smtp_username, config.smtp_password)
            server.sendmail(config.smtp_username, admin_email, msg.as_string())

        logger.info(f"Admin notification email sent successfully to {admin_email}")

    except Exception as e:
        logger.error(f"Failed to send admin notification email to {admin_email}: {e}")
        raise EmailServiceError(f"Email sending failed: {e}")


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
