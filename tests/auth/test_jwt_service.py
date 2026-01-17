"""
Tests for JWT service (token creation, verification, revocation).
"""

import pytest
from datetime import datetime, timezone, timedelta
from jose import jwt
from fastapi import HTTPException

from app.services.jwt_service import get_jwt_service
from app.config import get_base_app_config
from common.service_connections.db_service.models.account_models.revoked_token_model import (
    insert_revoked_token,
    is_token_revoked,
)
from common.service_connections.db_service.database.engine import (
    get_database_session as session,
)


class TestJWTService:
    """Test JWT service functionality."""

    def test_create_access_token(self, engine):
        """Test access token creation."""
        jwt_service = get_jwt_service()

        token = jwt_service.create_access_token(
            user_id="user123", email="test@example.com", is_admin=True
        )

        # Token should be non-empty string
        assert isinstance(token, str)
        assert len(token) > 0

        # Should have 3 parts (header.payload.signature)
        parts = token.split(".")
        assert len(parts) == 3

        # Decode and verify payload
        payload = jwt_service.decode_token(token)
        assert payload["sub"] == "test@example.com"
        assert payload["user_id"] == "user123"
        assert payload["is_admin"] is True
        assert "exp" in payload
        assert "jti" in payload

    def test_create_refresh_token(self, engine):
        """Test refresh token creation."""
        jwt_service = get_jwt_service()

        plaintext, hashed = jwt_service.create_refresh_token(
            user_id="user123", token_family_id="family456"
        )

        # Plaintext should be 64-char hex
        assert isinstance(plaintext, str)
        assert len(plaintext) == 64

        # Hash should be bcrypt format
        assert isinstance(hashed, str)
        assert hashed.startswith("$2b$")

    def test_decode_token(self, engine):
        """Test token decoding."""
        jwt_service = get_jwt_service()
        config = get_base_app_config()

        # Create token manually
        payload = {
            "sub": "test@example.com",
            "user_id": "user123",
            "is_admin": False,
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
            "jti": "test-jti-123",
        }

        token = jwt.encode(payload, config.jwt_secret_key, algorithm=config.jwt_algorithm)

        # Decode it
        decoded = jwt_service.decode_token(token)
        assert decoded["sub"] == "test@example.com"
        assert decoded["user_id"] == "user123"

    def test_verify_and_decode_valid_token(self, engine):
        """Test verification of valid token."""
        jwt_service = get_jwt_service()

        token = jwt_service.create_access_token(
            user_id="user123", email="test@example.com", is_admin=False
        )

        payload = jwt_service.verify_and_decode(token)
        assert payload.user_id == "user123"
        assert payload.email == "test@example.com"
        assert payload.is_admin is False

    def test_verify_expired_token(self, engine):
        """Test verification rejects expired token."""
        jwt_service = get_jwt_service()
        config = get_base_app_config()

        # Create expired token
        payload = {
            "sub": "test@example.com",
            "user_id": "user123",
            "is_admin": False,
            "exp": datetime.now(timezone.utc) - timedelta(hours=1),  # Expired
            "jti": "expired-jti",
        }

        token = jwt.encode(payload, config.jwt_secret_key, algorithm=config.jwt_algorithm)

        # Should raise 401
        with pytest.raises(HTTPException) as exc_info:
            jwt_service.verify_and_decode(token)
        assert exc_info.value.status_code == 401
        assert "expired" in exc_info.value.detail.lower()

    def test_verify_invalid_signature(self, engine):
        """Test verification rejects token with invalid signature."""
        jwt_service = get_jwt_service()
        config = get_base_app_config()

        # Create token with wrong secret
        payload = {
            "sub": "test@example.com",
            "user_id": "user123",
            "is_admin": False,
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
            "jti": "invalid-sig-jti",
        }

        token = jwt.encode(payload, "wrong-secret-key", algorithm=config.jwt_algorithm)

        # Should raise 401
        with pytest.raises(HTTPException) as exc_info:
            jwt_service.verify_and_decode(token)
        assert exc_info.value.status_code == 401

    def test_verify_revoked_token(self, engine):
        """Test verification rejects revoked token."""
        jwt_service = get_jwt_service()

        # Create token
        token = jwt_service.create_access_token(
            user_id="user123", email="test@example.com", is_admin=False
        )

        payload = jwt_service.decode_token(token)
        jti = payload["jti"]

        # Revoke it
        expires_at = datetime.now(timezone.utc) + timedelta(hours=24)
        insert_revoked_token(jti, expires_at, engine)

        # Should be marked as revoked
        with session(engine) as db_session:
            assert is_token_revoked(jti, db_session, engine) is True

        # Verification should fail
        with pytest.raises(HTTPException) as exc_info:
            jwt_service.verify_and_decode(token, check_revoked=True)
        assert exc_info.value.status_code == 401
        assert "revoked" in exc_info.value.detail.lower()

    def test_revoke_token(self, engine):
        """Test token revocation."""
        from uuid import uuid4

        jwt_service = get_jwt_service()

        jti = str(uuid4())  # Use unique JTI for each test run
        expires_at = datetime.now(timezone.utc) + timedelta(hours=24)

        # Revoke token
        jwt_service.revoke_token(jti, expires_at)

        # Check it's in database
        with session(engine) as db_session:
            assert is_token_revoked(jti, db_session, engine) is True

    def test_get_token_expiry_hours(self, engine):
        """Test token expiry calculation."""
        jwt_service = get_jwt_service()
        config = get_base_app_config()

        # Create token with known expiry
        token = jwt_service.create_access_token(
            user_id="user123", email="test@example.com", is_admin=False
        )

        hours = jwt_service.get_token_expiry_hours(token)

        # Should be approximately the configured hours
        expected_hours = config.jwt_access_token_expire_hours
        assert (
            abs(hours - expected_hours) <= 1
        )  # Within 1 hour (accounts for test execution time)

    def test_get_token_expiry_expired(self, engine):
        """Test expiry calculation for expired token."""
        jwt_service = get_jwt_service()
        config = get_base_app_config()

        # Create expired token
        payload = {
            "sub": "test@example.com",
            "user_id": "user123",
            "is_admin": False,
            "exp": datetime.now(timezone.utc) - timedelta(hours=1),
            "jti": "expired-jti",
        }

        token = jwt.encode(payload, config.jwt_secret_key, algorithm=config.jwt_algorithm)

        hours = jwt_service.get_token_expiry_hours(token)
        assert hours == 0
