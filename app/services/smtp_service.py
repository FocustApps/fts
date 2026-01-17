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
