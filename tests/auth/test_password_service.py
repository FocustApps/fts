"""
Tests for password service (hashing, validation, generation).
"""

from app.services.password_service import get_password_service


class TestPasswordService:
    """Test password service functionality."""

    def test_hash_password(self):
        """Test password hashing."""
        password_service = get_password_service()

        password = "TestPassword123!"
        hashed = password_service.hash_password(password)

        # Should be bcrypt hash
        assert isinstance(hashed, str)
        assert hashed.startswith("$2b$")
        assert len(hashed) > 50

    def test_hash_different_passwords_produce_different_hashes(self):
        """Test different passwords produce different hashes."""
        password_service = get_password_service()

        hash1 = password_service.hash_password("password1")
        hash2 = password_service.hash_password("password2")

        assert hash1 != hash2

    def test_same_password_produces_different_hashes(self):
        """Test same password produces different hashes (salt)."""
        password_service = get_password_service()

        password = "TestPassword123!"
        hash1 = password_service.hash_password(password)
        hash2 = password_service.hash_password(password)

        # Hashes should differ due to random salt
        assert hash1 != hash2

    def test_verify_password_correct(self):
        """Test password verification with correct password."""
        password_service = get_password_service()

        password = "TestPassword123!"
        hashed = password_service.hash_password(password)

        assert password_service.verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        """Test password verification with incorrect password."""
        password_service = get_password_service()

        password = "TestPassword123!"
        hashed = password_service.hash_password(password)

        assert password_service.verify_password("WrongPassword", hashed) is False

    def test_validate_password_strength_valid(self):
        """Test password validation with valid password."""
        password_service = get_password_service()

        password = "StrongPass123!"
        is_valid, error_msg = password_service.validate_password_strength(password)

        assert is_valid is True
        assert error_msg == ""

    def test_validate_password_too_short(self):
        """Test password validation rejects short password."""
        password_service = get_password_service()

        password = "Sh0rt!"  # Only 6 characters
        is_valid, error_msg = password_service.validate_password_strength(password)

        assert is_valid is False
        assert "8 characters" in error_msg

    def test_validate_password_no_uppercase(self):
        """Test password validation rejects password without uppercase."""
        password_service = get_password_service()

        password = "lowercase123!"
        is_valid, error_msg = password_service.validate_password_strength(password)

        assert is_valid is False
        assert "uppercase" in error_msg.lower()

    def test_validate_password_no_lowercase(self):
        """Test password validation rejects password without lowercase."""
        password_service = get_password_service()

        password = "UPPERCASE123!"
        is_valid, error_msg = password_service.validate_password_strength(password)

        assert is_valid is False
        assert "lowercase" in error_msg.lower()

    def test_validate_password_no_digit(self):
        """Test password validation rejects password without digit."""
        password_service = get_password_service()

        password = "NoDigitsHere!"
        is_valid, error_msg = password_service.validate_password_strength(password)

        assert is_valid is False
        assert "digit" in error_msg.lower()

    def test_validate_password_no_special_char(self):
        """Test password validation rejects password without special char."""
        password_service = get_password_service()

        password = "NoSpecialChar123"
        is_valid, error_msg = password_service.validate_password_strength(password)

        assert is_valid is False
        assert "special character" in error_msg.lower()

    def test_generate_secure_password(self):
        """Test secure password generation."""
        password_service = get_password_service()

        password = password_service.generate_secure_password()

        # Should meet all requirements
        is_valid, error_msg = password_service.validate_password_strength(password)
        assert is_valid is True

        # Default length should be 16
        assert len(password) == 16

    def test_generate_secure_password_custom_length(self):
        """Test secure password generation with custom length."""
        password_service = get_password_service()

        password = password_service.generate_secure_password(length=24)

        # Should meet all requirements
        is_valid, error_msg = password_service.validate_password_strength(password)
        assert is_valid is True

        # Length should match
        assert len(password) == 24

    def test_generate_secure_password_unique(self):
        """Test generated passwords are unique."""
        password_service = get_password_service()

        password1 = password_service.generate_secure_password()
        password2 = password_service.generate_secure_password()

        assert password1 != password2

    def test_generate_reset_token(self):
        """Test reset token generation."""
        password_service = get_password_service()

        token = password_service.generate_reset_token()

        # Should be 64-char hex string
        assert isinstance(token, str)
        assert len(token) == 64

        # Should be valid hex
        int(token, 16)  # Raises ValueError if not hex

    def test_generate_reset_token_unique(self):
        """Test reset tokens are unique."""
        password_service = get_password_service()

        token1 = password_service.generate_reset_token()
        token2 = password_service.generate_reset_token()

        assert token1 != token2
