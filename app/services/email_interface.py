"""
Email service interface and factory.

Provides abstraction for email sending with support for:
- Production SMTP (Gmail, Office365, etc.)
- MailHog for local development and testing
"""

from abc import ABC, abstractmethod
from typing import Optional

from app.config import BaseAppConfig


class EmailServiceInterface(ABC):
    """Abstract interface for email services."""

    @abstractmethod
    def send_email(
        self,
        to_email: str,
        subject: str,
        body: str,
        from_email: Optional[str] = None,
    ) -> None:
        """
        Send an email.

        Args:
            to_email: Recipient email address
            subject: Email subject line
            body: Email body text
            from_email: Optional sender email (uses configured default if None)

        Raises:
            EmailServiceError: If email sending fails
        """
        pass

    @abstractmethod
    def send_token_notification(
        self,
        user_email: str,
        token: str,
        username: Optional[str] = None,
        is_new_user: bool = False,
    ) -> None:
        """
        Send authentication token notification email.

        Args:
            user_email: Recipient email address
            token: Authentication token
            username: Optional username for personalization
            is_new_user: Whether this is a welcome email
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """
        Check if email service is properly configured and available.

        Returns:
            True if service can send emails, False otherwise
        """
        pass


def get_email_service(config: Optional[BaseAppConfig] = None) -> EmailServiceInterface:
    """
    Factory function to get appropriate email service implementation.

    Args:
        config: Optional configuration object (fetches if not provided)

    Returns:
        EmailServiceInterface implementation (MailHogService or SMTPService)
    """
    if config is None:
        from app.config import get_config

        config = get_config()

    if config.use_mailhog:
        from app.services.mailhog_service import MailHogService

        return MailHogService(config)
    else:
        from app.services.smtp_service import SMTPService

        return SMTPService(config)
