"""
MailHog email service implementation.

Provides email testing via MailHog for local development and testing.
MailHog captures emails and provides web UI and API access.
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, List, Dict, Any
import requests

from app.config import BaseAppConfig
from app.services.email_interface import EmailServiceInterface
from common.app_logging import create_logging

logger = create_logging()


class EmailServiceError(Exception):
    """Email service operation error."""

    pass


class MailHogService(EmailServiceInterface):
    """MailHog email service for testing and local development."""

    def __init__(self, config: BaseAppConfig):
        """
        Initialize MailHog email service.

        Args:
            config: Application configuration
        """
        self.config = config

    def is_available(self) -> bool:
        """Check if MailHog service is available."""
        try:
            response = requests.get(
                f"{self.config.mailhog_api_url}/api/v2/messages", timeout=2
            )
            return response.status_code == 200
        except Exception as e:
            logger.debug(f"MailHog not available: {e}")
            return False

    def send_email(
        self,
        to_email: str,
        subject: str,
        body: str,
        from_email: Optional[str] = None,
    ) -> None:
        """
        Send email via MailHog SMTP server.

        Args:
            to_email: Recipient email address
            subject: Email subject line
            body: Email body text
            from_email: Sender email (uses config default if None)

        Raises:
            EmailServiceError: If email sending fails
        """
        try:
            msg = MIMEMultipart()
            msg["From"] = from_email or self.config.smtp_username or "fenrir@local.test"
            msg["To"] = to_email
            msg["Subject"] = subject
            msg.attach(MIMEText(body, "plain"))

            # MailHog doesn't require authentication
            with smtplib.SMTP(self.config.smtp_server, self.config.smtp_port) as server:
                server.sendmail(
                    from_email or self.config.smtp_username or "fenrir@local.test",
                    to_email,
                    msg.as_string(),
                )

            logger.info(f"Email sent successfully via MailHog to {to_email}")

        except Exception as e:
            logger.error(f"Failed to send email via MailHog to {to_email}: {e}")
            raise EmailServiceError(f"MailHog email sending failed: {e}")

    # MailHog-specific helper methods for testing

    def get_all_messages(self) -> List[Dict[str, Any]]:
        """
        Retrieve all messages from MailHog API.

        Returns:
            List of message dictionaries

        Raises:
            EmailServiceError: If API request fails
        """
        try:
            response = requests.get(
                f"{self.config.mailhog_api_url}/api/v2/messages", timeout=5
            )
            response.raise_for_status()
            data = response.json()
            return data.get("items", [])
        except Exception as e:
            logger.error(f"Failed to retrieve MailHog messages: {e}")
            raise EmailServiceError(f"MailHog API request failed: {e}")

    def get_latest_message(
        self, to_email: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get the most recent message, optionally filtered by recipient.

        Args:
            to_email: Optional email address to filter by recipient

        Returns:
            Message dictionary or None if no messages found
        """
        messages = self.get_all_messages()
        if not messages:
            return None

        if to_email:
            for msg in messages:
                recipients = msg.get("To", [])
                for recipient in recipients:
                    if (
                        recipient.get("Mailbox", "") + "@" + recipient.get("Domain", "")
                        == to_email
                    ):
                        return msg
            return None

        return messages[0]

    def search_messages(
        self, subject: Optional[str] = None, to_email: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Search messages by subject or recipient.

        Args:
            subject: Optional subject text to search for
            to_email: Optional recipient email to filter by

        Returns:
            List of matching message dictionaries
        """
        messages = self.get_all_messages()
        results = []

        for msg in messages:
            match = True

            if (
                subject
                and subject.lower()
                not in msg.get("Content", {})
                .get("Headers", {})
                .get("Subject", [""])[0]
                .lower()
            ):
                match = False

            if to_email:
                recipients = msg.get("To", [])
                recipient_match = False
                for recipient in recipients:
                    if (
                        recipient.get("Mailbox", "") + "@" + recipient.get("Domain", "")
                        == to_email
                    ):
                        recipient_match = True
                        break
                if not recipient_match:
                    match = False

            if match:
                results.append(msg)

        return results

    def delete_all_messages(self) -> None:
        """
        Delete all messages from MailHog.

        Raises:
            EmailServiceError: If deletion fails
        """
        try:
            response = requests.delete(
                f"{self.config.mailhog_api_url}/api/v1/messages", timeout=5
            )
            response.raise_for_status()
            logger.info("All MailHog messages deleted")
        except Exception as e:
            logger.error(f"Failed to delete MailHog messages: {e}")
            raise EmailServiceError(f"MailHog message deletion failed: {e}")

    def get_message_body(self, message: Dict[str, Any]) -> str:
        """
        Extract plain text body from a MailHog message.

        Args:
            message: MailHog message dictionary

        Returns:
            Plain text body content
        """
        content = message.get("Content", {})
        body = content.get("Body", "")
        return body
