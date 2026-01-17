"""
MailHog test utilities.

Helper functions for tests to interact with MailHog email service.
"""

from typing import Optional, List, Dict, Any
import time

from app.services.email_interface import get_email_service
from app.services.mailhog_service import MailHogService
from app.config import get_config


class MailHogTestHelper:
    """Helper class for MailHog operations in tests."""

    def __init__(self):
        """Initialize MailHog test helper."""
        self.config = get_config()
        email_service = get_email_service(self.config)

        if not isinstance(email_service, MailHogService):
            raise RuntimeError("MailHog service not configured. Set USE_MAILHOG=true")

        self.mailhog = email_service

    def clear_all_emails(self) -> None:
        """Clear all emails from MailHog."""
        self.mailhog.delete_all_messages()

    def wait_for_email(
        self,
        to_email: Optional[str] = None,
        subject: Optional[str] = None,
        timeout: int = 10,
        poll_interval: float = 0.5,
    ) -> Optional[Dict[str, Any]]:
        """
        Wait for an email to arrive in MailHog.

        Args:
            to_email: Optional recipient email to filter by
            subject: Optional subject text to search for
            timeout: Maximum seconds to wait
            poll_interval: Seconds between polling attempts

        Returns:
            Message dictionary if found, None if timeout
        """
        start_time = time.time()

        while time.time() - start_time < timeout:
            messages = self.mailhog.search_messages(subject=subject, to_email=to_email)

            if messages:
                return messages[0]

            time.sleep(poll_interval)

        return None

    def get_latest_email(
        self, to_email: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get the most recent email.

        Args:
            to_email: Optional recipient email to filter by

        Returns:
            Message dictionary or None
        """
        return self.mailhog.get_latest_message(to_email)

    def get_all_emails(self) -> List[Dict[str, Any]]:
        """
        Get all emails from MailHog.

        Returns:
            List of message dictionaries
        """
        return self.mailhog.get_all_messages()

    def search_emails(
        self, subject: Optional[str] = None, to_email: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for emails matching criteria.

        Args:
            subject: Optional subject text to search for
            to_email: Optional recipient email to filter by

        Returns:
            List of matching message dictionaries
        """
        return self.mailhog.search_messages(subject=subject, to_email=to_email)

    def get_email_body(self, message: Dict[str, Any]) -> str:
        """
        Extract plain text body from email message.

        Args:
            message: MailHog message dictionary

        Returns:
            Plain text body content
        """
        return self.mailhog.get_message_body(message)

    def extract_token_from_email(self, message: Dict[str, Any]) -> Optional[str]:
        """
        Extract authentication token from email body.

        Args:
            message: MailHog message dictionary

        Returns:
            Token string if found, None otherwise
        """
        body = self.get_email_body(message)

        # Look for "Token: <token>" pattern
        import re

        match = re.search(r"Token:\s*([a-zA-Z0-9]+)", body)
        if match:
            return match.group(1)

        return None

    def assert_email_sent(
        self,
        to_email: str,
        subject: Optional[str] = None,
        timeout: int = 10,
    ) -> Dict[str, Any]:
        """
        Assert that an email was sent to the specified recipient.

        Args:
            to_email: Recipient email address
            subject: Optional subject to verify
            timeout: Maximum seconds to wait

        Returns:
            The found message dictionary

        Raises:
            AssertionError: If email not found within timeout
        """
        message = self.wait_for_email(to_email=to_email, subject=subject, timeout=timeout)

        if not message:
            raise AssertionError(
                f"Email not found for {to_email}"
                + (f" with subject '{subject}'" if subject else "")
            )

        return message

    def assert_token_email_sent(
        self,
        to_email: str,
        timeout: int = 10,
    ) -> tuple[Dict[str, Any], str]:
        """
        Assert that a token notification email was sent and extract the token.

        Args:
            to_email: Recipient email address
            timeout: Maximum seconds to wait

        Returns:
            Tuple of (message, token)

        Raises:
            AssertionError: If email not found or token not extracted
        """
        message = self.assert_email_sent(
            to_email=to_email,
            subject="Token",  # Matches both welcome and token emails
            timeout=timeout,
        )

        token = self.extract_token_from_email(message)

        if not token:
            raise AssertionError(
                f"Could not extract token from email body: {self.get_email_body(message)}"
            )

        return message, token
