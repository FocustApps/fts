"""
Password service for hashing, verification, and validation.
"""

import secrets
import string
from typing import Tuple

import bcrypt

from app.config import BaseAppConfig


class PasswordService:
    """Service for password operations."""

    def __init__(self, config: BaseAppConfig):
        """
        Initialize password service.

        Args:
            config: Application configuration with password requirements
        """
        self.config = config
        self.min_length = config.password_min_length
        self.require_uppercase = config.password_require_uppercase
        self.require_lowercase = config.password_require_lowercase
        self.require_digit = config.password_require_digit
        self.require_special = config.password_require_special

    def hash_password(self, password: str) -> str:
        """
        Hash a password using bcrypt.

        Args:
            password: Plaintext password

        Returns:
            Bcrypt hash string
        """
        # Convert password to bytes and hash with bcrypt
        password_bytes = password.encode("utf-8")
        salt = bcrypt.gensalt(rounds=12)
        hashed = bcrypt.hashpw(password_bytes, salt)
        return hashed.decode("utf-8")

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """
        Verify a password against its hash.

        Args:
            plain_password: Plaintext password to verify
            hashed_password: Bcrypt hash to check against

        Returns:
            True if password matches, False otherwise
        """
        password_bytes = plain_password.encode("utf-8")
        hashed_bytes = hashed_password.encode("utf-8")
        return bcrypt.checkpw(password_bytes, hashed_bytes)

    def generate_secure_password(self, length: int = 16) -> str:
        """
        Generate a cryptographically secure random password.

        Ensures at least one character from each required type.

        Args:
            length: Desired password length (minimum 8)

        Returns:
            Secure random password string
        """
        if length < max(8, self.min_length):
            length = max(8, self.min_length)

        # Character sets
        lowercase_chars = string.ascii_lowercase
        uppercase_chars = string.ascii_uppercase
        digit_chars = string.digits
        special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"

        # Build character pool and ensure requirements
        password_chars = []
        available_chars = lowercase_chars  # Always include lowercase

        if self.require_uppercase:
            password_chars.append(secrets.choice(uppercase_chars))
            available_chars += uppercase_chars

        if self.require_lowercase:
            password_chars.append(secrets.choice(lowercase_chars))

        if self.require_digit:
            password_chars.append(secrets.choice(digit_chars))
            available_chars += digit_chars

        if self.require_special:
            password_chars.append(secrets.choice(special_chars))
            available_chars += special_chars

        # Fill remaining length with random characters from pool
        remaining_length = length - len(password_chars)
        for _ in range(remaining_length):
            password_chars.append(secrets.choice(available_chars))

        # Shuffle to avoid predictable patterns
        secrets.SystemRandom().shuffle(password_chars)

        return "".join(password_chars)

    def generate_reset_token(self) -> str:
        """
        Generate a secure password reset token.

        Returns:
            64-character hex string
        """
        return secrets.token_hex(32)

    def validate_password_strength(self, password: str) -> Tuple[bool, str]:
        """
        Validate password against configured requirements.

        Args:
            password: Password to validate

        Returns:
            Tuple of (is_valid, error_message)
            error_message is empty string if valid
        """
        errors = []

        # Check length
        if len(password) < self.min_length:
            errors.append(f"at least {self.min_length} characters")

        # Check uppercase
        if self.require_uppercase and not any(c.isupper() for c in password):
            errors.append("an uppercase letter")

        # Check lowercase
        if self.require_lowercase and not any(c.islower() for c in password):
            errors.append("a lowercase letter")

        # Check digit
        if self.require_digit and not any(c.isdigit() for c in password):
            errors.append("a digit")

        # Check special character
        if self.require_special:
            special_chars = set("!@#$%^&*()_+-=[]{}|;:,.<>?")
            if not any(c in special_chars for c in password):
                errors.append("a special character (!@#$%^&*()_+-=[]{}|;:,.<>?)")

        if errors:
            error_msg = "Password must contain " + ", ".join(errors)
            return False, error_msg

        return True, ""


# Singleton instance
_password_service = None


def get_password_service() -> PasswordService:
    """Get or create password service singleton."""
    global _password_service
    if _password_service is None:
        from app.config import get_base_app_config

        _password_service = PasswordService(get_base_app_config())
    return _password_service
