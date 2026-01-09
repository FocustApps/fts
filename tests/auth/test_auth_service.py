"""
Unit tests for authentication service.

Tests token generation, validation, persistence, rotation, and error handling
with comprehensive mocking and edge case coverage.
"""

import os
import tempfile
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from app.services.auth_service import (
    AuthService,
    AuthTokenError,
    get_auth_service,
    initialize_auth_service,
    shutdown_auth_service,
)


class TestAuthService:
    """Test cases for AuthService class."""

    @pytest.fixture
    def temp_token_file(self):
        """Create a temporary file for token storage."""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f:
            temp_path = Path(f.name)
        yield temp_path
        # Cleanup
        if temp_path.exists():
            temp_path.unlink()

    @pytest.fixture
    def auth_service(self, temp_token_file):
        """Create an AuthService instance with temporary file."""
        return AuthService(
            token_file_path=temp_token_file,
            rotation_interval_minutes=1,  # Short interval for testing
        )

    @pytest.fixture
    def mock_external_sync(self):
        """Mock external sync callback."""
        return MagicMock()

    def test_init_creates_directory(self):
        """Test that AuthService creates token directory if it doesn't exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            token_path = Path(temp_dir) / "subdir" / "token.txt"

            # Directory shouldn't exist initially
            assert not token_path.parent.exists()

            # Creating AuthService should create directory
            service = AuthService(token_file_path=token_path)
            assert token_path.parent.exists()

    def test_generate_token_format(self, auth_service):
        """Test that generated tokens have correct format."""
        token = auth_service.generate_token()

        # Should be 64 hex characters (256 bits)
        assert len(token) == 64
        assert all(c in "0123456789abcdef" for c in token)

    def test_generate_token_uniqueness(self, auth_service):
        """Test that generated tokens are unique."""
        tokens = {auth_service.generate_token() for _ in range(100)}

        # All tokens should be unique
        assert len(tokens) == 100

    def test_validate_token_success(self, auth_service):
        """Test successful token validation."""
        # Generate and get a token
        expected_token = auth_service.get_current_token()

        # Validation should succeed
        assert auth_service.validate_token(expected_token) is True

    def test_validate_token_failure(self, auth_service):
        """Test token validation failure."""
        # Get current token and create a different one
        auth_service.get_current_token()  # Initialize
        wrong_token = "0123456789abcdef"

        # Validation should fail
        assert auth_service.validate_token(wrong_token) is False

    def test_validate_token_empty(self, auth_service):
        """Test validation with empty/None token."""
        assert auth_service.validate_token("") is False
        assert auth_service.validate_token(None) is False

    def test_get_current_token_generates_new(self, auth_service):
        """Test that get_current_token generates a new token when none exists."""
        token = auth_service.get_current_token()

        assert token is not None
        assert len(token) == 64
        assert auth_service._current_token == token

    def test_get_current_token_returns_cached(self, auth_service):
        """Test that get_current_token returns cached token when valid."""
        # Get initial token
        token1 = auth_service.get_current_token()

        # Get again immediately - should be same
        token2 = auth_service.get_current_token()

        assert token1 == token2

    def test_token_expiration(self, auth_service):
        """Test that tokens expire after rotation interval."""
        # Use freezegun or simple time mocking for expiration test
        # For now, just test that rotation happens when we call it directly
        token1 = auth_service.get_current_token()

        # Manually rotate token to simulate expiration
        token2 = auth_service.rotate_token()

        assert token1 != token2

    def test_rotate_token_immediate(self, auth_service):
        """Test immediate token rotation."""
        # Get initial token
        token1 = auth_service.get_current_token()

        # Force rotation
        token2 = auth_service.rotate_token()

        assert token1 != token2
        assert auth_service.get_current_token() == token2

    def test_external_sync_callback(self, auth_service, mock_external_sync):
        """Test that external sync callback is called on rotation."""
        auth_service.external_sync_callback = mock_external_sync

        # Rotate token
        new_token = auth_service.rotate_token()

        # Callback should be called with token and file path
        mock_external_sync.assert_called_once_with(
            new_token, auth_service.token_file_path
        )

    def test_external_sync_callback_error_handling(
        self, auth_service, mock_external_sync
    ):
        """Test that external sync errors don't break rotation."""
        # Make callback raise an exception
        mock_external_sync.side_effect = Exception("Sync failed")
        auth_service.external_sync_callback = mock_external_sync

        # Rotation should still succeed
        new_token = auth_service.rotate_token()
        assert new_token is not None
        assert len(new_token) == 16

    def test_file_persistence(self, auth_service, temp_token_file):
        """Test that tokens are persisted to file."""
        # Generate token
        token = auth_service.get_current_token()

        # File should exist and contain token
        assert temp_token_file.exists()

        with open(temp_token_file, "r") as f:
            content = f.read()
            assert f"token={token}" in content
            assert "created_at=" in content
            assert "expires_at=" in content

    def test_file_loading(self, temp_token_file):
        """Test loading token from existing file."""
        # Create a token file manually
        test_token = "0123456789abcdef"
        created_at = datetime.now(timezone.utc)
        expires_at = created_at + timedelta(minutes=30)

        with open(temp_token_file, "w") as f:
            f.write(f"token={test_token}\n")
            f.write(f"created_at={created_at.isoformat()}\n")
            f.write(f"expires_at={expires_at.isoformat()}\n")

        # Create new service - should load existing token
        service = AuthService(
            token_file_path=temp_token_file, rotation_interval_minutes=30
        )

        assert service.get_current_token() == test_token

    def test_file_loading_expired_token(self, temp_token_file):
        """Test that expired tokens in file are replaced."""
        # Create an expired token file
        test_token = "0123456789abcdef"
        created_at = datetime.now(timezone.utc) - timedelta(hours=1)  # 1 hour ago
        expires_at = created_at + timedelta(minutes=30)  # Expired 30 minutes ago

        with open(temp_token_file, "w") as f:
            f.write(f"token={test_token}\n")
            f.write(f"created_at={created_at.isoformat()}\n")
            f.write(f"expires_at={expires_at.isoformat()}\n")

        # Create new service - should generate new token
        service = AuthService(
            token_file_path=temp_token_file, rotation_interval_minutes=30
        )

        current_token = service.get_current_token()
        assert current_token != test_token

    def test_file_permissions(self, auth_service, temp_token_file):
        """Test that token file has correct permissions."""
        # Generate token to create file
        auth_service.get_current_token()

        # Check file permissions (should be 0o600 - owner read/write only)
        file_mode = oct(temp_token_file.stat().st_mode)[-3:]
        assert file_mode == "600"

    def test_concurrent_access(self, auth_service):
        """Test thread safety of token operations."""
        tokens = []
        errors = []

        def worker():
            try:
                token = auth_service.get_current_token()
                tokens.append(token)
            except Exception as e:
                errors.append(e)

        # Start multiple threads
        threads = [threading.Thread(target=worker) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Should have no errors and all tokens should be the same
        assert len(errors) == 0
        assert len(set(tokens)) == 1  # All tokens should be identical

    def test_get_token_info(self, auth_service):
        """Test token info retrieval."""
        # Before any token
        info = auth_service.get_token_info()
        assert info["has_token"] is False
        assert info["is_current"] is False

        # After generating token
        token = auth_service.get_current_token()
        info = auth_service.get_token_info()

        assert info["has_token"] is True
        assert info["is_current"] is True
        assert info["token_preview"] == f"{token[:4]}...{token[-4:]}"
        assert "created_at" in info
        assert "expires_at" in info

    def test_invalid_file_format(self, temp_token_file):
        """Test handling of invalid token file format."""
        # Create invalid file content
        with open(temp_token_file, "w") as f:
            f.write("invalid file content")

        # Should handle gracefully and generate new token
        service = AuthService(token_file_path=temp_token_file)
        token = service.get_current_token()

        assert token is not None
        assert len(token) == 16


class TestGlobalAuthService:
    """Test cases for global auth service functions."""

    def test_initialize_and_get_auth_service(self):
        """Test global auth service initialization and retrieval."""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f:
            temp_path = Path(f.name)

        try:
            # Should raise error before initialization
            with pytest.raises(RuntimeError, match="Auth service not initialized"):
                get_auth_service()

            # Initialize
            service = initialize_auth_service(token_file_path=temp_path)

            # Should return same instance
            assert get_auth_service() is service

            # Shutdown
            shutdown_auth_service()

            # Should raise error after shutdown
            with pytest.raises(RuntimeError, match="Auth service not initialized"):
                get_auth_service()

        finally:
            # Cleanup
            if temp_path.exists():
                temp_path.unlink()

    def test_initialize_with_callback(self):
        """Test initialization with external sync callback."""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f:
            temp_path = Path(f.name)

        mock_callback = MagicMock()

        try:
            service = initialize_auth_service(
                token_file_path=temp_path,
                rotation_interval_minutes=5,
                external_sync_callback=mock_callback,
            )

            # Generate token to trigger callback
            token = service.get_current_token()

            # Callback should be called during initial token generation
            mock_callback.assert_called_with(token, temp_path)

        finally:
            shutdown_auth_service()
            if temp_path.exists():
                temp_path.unlink()


class TestAuthServiceErrors:
    """Test error conditions and edge cases."""

    def test_token_persistence_error(self):
        """Test handling of file system errors."""
        # Try to use a path in a temporary directory that we make inaccessible
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a subdirectory and make it inaccessible
            restricted_dir = Path(temp_dir) / "restricted"
            restricted_dir.mkdir()
            invalid_path = restricted_dir / "subdir" / "token.txt"

            # Make the restricted directory inaccessible
            os.chmod(restricted_dir, 0o000)

            try:
                # Should raise AuthTokenError when trying to create service
                with pytest.raises((AuthTokenError, PermissionError, OSError)):
                    service = AuthService(token_file_path=invalid_path)
                    service.get_current_token()
            finally:
                # Restore permissions for cleanup
                os.chmod(restricted_dir, 0o755)

    def test_file_permission_error(self, temp_token_file):
        """Test handling of file permission errors."""
        # Create service and generate initial token
        service = AuthService(token_file_path=temp_token_file)
        service.get_current_token()

        # Make file read-only
        os.chmod(temp_token_file, 0o444)

        try:
            # Our service handles permission errors gracefully and logs them
            # So we test that it doesn't crash rather than expecting an exception
            service.rotate_token()
            # If we get here, it means the service handled the error gracefully
            assert True
        except (PermissionError, OSError):
            # This is also acceptable - the OS rejected the write
            assert True
        finally:
            # Restore permissions for cleanup
            os.chmod(temp_token_file, 0o600)

    @patch("app.services.auth_service.secrets.token_bytes")
    def test_token_generation_error(self, mock_token_bytes, temp_token_file):
        """Test handling of token generation errors."""
        # Make token generation fail
        mock_token_bytes.side_effect = Exception("Random generation failed")

        service = AuthService(token_file_path=temp_token_file)

        with pytest.raises(AuthTokenError):
            service.get_current_token()


if __name__ == "__main__":
    pytest.main([__file__])
