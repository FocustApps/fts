"""
SMTP email service implementation.

Provides production email sending via SMTP (Gmail, Office365, etc.)
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

from app.config import BaseAppConfig
from app.services.email_interface import EmailServiceInterface
from common.app_logging import create_logging

logger = create_logging()


class EmailServiceError(Exception):
    """Email service operation error."""

    pass


class SMTPService(EmailServiceInterface):
    """SMTP email service for production environments."""

    def __init__(self, config: BaseAppConfig):
        """
        Initialize SMTP email service.

        Args:
            config: Application configuration
        """
        self.config = config

    def is_available(self) -> bool:
        """Check if SMTP service is properly configured."""
        return bool(
            self.config.smtp_username
            and self.config.smtp_password
            and self.config.smtp_server
        )

    def send_email(
        self,
        to_email: str,
        subject: str,
        body: str,
        from_email: Optional[str] = None,
    ) -> None:
        """
        Send email via SMTP.

        Args:
            to_email: Recipient email address
            subject: Email subject line
            body: Email body text
            from_email: Sender email (uses config default if None)

        Raises:
            EmailServiceError: If email sending fails
        """
        if not self.is_available():
            logger.warning("SMTP service not configured, cannot send email")
            raise EmailServiceError("SMTP credentials not configured")

        try:
            msg = MIMEMultipart()
            msg["From"] = from_email or self.config.smtp_username
            msg["To"] = to_email
            msg["Subject"] = subject
            msg.attach(MIMEText(body, "plain"))

            # Use SMTP_SSL for port 465 (Gmail), SMTP with STARTTLS for 587
            if self.config.smtp_port == 465:
                with smtplib.SMTP_SSL(
                    self.config.smtp_server, self.config.smtp_port
                ) as server:
                    server.login(self.config.smtp_username, self.config.smtp_password)
                    server.sendmail(
                        from_email or self.config.smtp_username,
                        to_email,
                        msg.as_string(),
                    )
            else:
                with smtplib.SMTP(
                    self.config.smtp_server, self.config.smtp_port
                ) as server:
                    server.starttls()
                    server.login(self.config.smtp_username, self.config.smtp_password)
                    server.sendmail(
                        from_email or self.config.smtp_username,
                        to_email,
                        msg.as_string(),
                    )

            logger.info(f"Email sent successfully via SMTP to {to_email}")

        except Exception as e:
            logger.error(f"Failed to send email via SMTP to {to_email}: {e}")
            raise EmailServiceError(f"SMTP email sending failed: {e}")

    def send_token_notification(
        self,
        user_email: str,
        token: str,
        username: Optional[str] = None,
        is_new_user: bool = False,
    ) -> None:
        """
        Send authentication token notification via SMTP.

        Args:
            user_email: Recipient email address
            token: Authentication token
            username: Optional username for personalization
            is_new_user: Whether this is a welcome email
        """
        if is_new_user:
            subject = "Welcome to Fenrir Testing System - Your Access Token"
            greeting = f"Welcome to the Fenrir Testing System{', ' + username if username else ''}!"
            intro = "You have been granted access to the Fenrir Testing System. Below is your authentication token:"
        else:
            subject = "Fenrir Testing System - New Authentication Token"
            greeting = f"Hello{', ' + username if username else ''}!"
            intro = "A new authentication token has been generated for your Fenrir Testing System access:"

        body = f"""
{greeting}

{intro}

Token: {token}
Valid for: 24 hours
Environment: {self.config.environment}

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

        self.send_email(user_email, subject, body)
