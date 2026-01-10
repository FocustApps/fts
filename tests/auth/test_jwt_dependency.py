"""
Tests for JWT authentication dependencies.

Integration tests using FastAPI TestClient since dependencies
use Depends() and can't be called directly.
"""

import pytest
from datetime import datetime, timedelta
from fastapi import FastAPI, Depends
from fastapi.testclient import TestClient

from app.dependencies.jwt_auth_dependency import (
    verify_jwt_token,
    require_admin,
    get_current_user,
    get_current_user_optional,
)
from app.models.auth_models import TokenPayload
from app.config import get_base_app_config
from common.service_connections.db_service.db_manager import DB_ENGINE


@pytest.fixture(scope="module")
def test_app():
    """Create test FastAPI app with protected routes."""
    app = FastAPI()

    @app.get("/public")
    def public_route():
        return {"message": "public"}

    @app.get("/protected")
    def protected_route(payload: TokenPayload = Depends(verify_jwt_token)):
        return {"user_id": payload.user_id, "email": payload.email}

    @app.get("/admin")
    def admin_route(payload: TokenPayload = Depends(require_admin)):
        return {"user_id": payload.user_id, "is_admin": payload.is_admin}

    @app.get("/current-user")
    def current_user_route(payload: TokenPayload = Depends(get_current_user)):
        return {"user_id": payload.user_id, "email": payload.email}

    @app.get("/optional-user")
    def optional_user_route(
        payload: TokenPayload | None = Depends(get_current_user_optional),
    ):
        if payload:
            return {"user_id": payload.user_id}
        return {"user_id": None}

    return app


@pytest.fixture
def client(test_app):
    """Create test client."""
    return TestClient(test_app)


@pytest.fixture
def auth_service():
    """Create auth service."""
    from app.services.user_auth_service import get_user_auth_service

    return get_user_auth_service(DB_ENGINE)


@pytest.fixture
def test_user(auth_service):
    """Create test user and return tokens."""
    from app.models.auth_models import RegisterRequest, LoginRequest
    from uuid import uuid4

    # Register user with unique email
    email = f"testuser_{uuid4().hex[:8]}@example.com"
    register_req = RegisterRequest(
        email=email, password="TestPass123!", username=f"testuser_{uuid4().hex[:8]}"
    )
    user = auth_service.register_user(register_req)

    # Authenticate to get tokens
    login_req = LoginRequest(email=user.email, password="TestPass123!", remember_me=False)
    tokens = auth_service.authenticate(
        login_req, device_info="Test Device", ip_address="127.0.0.1"
    )

    return {"user": user, "tokens": tokens}


@pytest.fixture
def admin_user(auth_service):
    """Create admin user and return tokens."""
    from app.models.auth_models import RegisterRequest, LoginRequest
    from common.service_connections.db_service.database.engine import (
        get_database_session as session,
    )
    from common.service_connections.db_service.database.tables.account_tables.auth_user import (
        AuthUserTable,
    )
    from uuid import uuid4

    # Register admin user with unique email
    email = f"adminuser_{uuid4().hex[:8]}@example.com"
    register_req = RegisterRequest(
        email=email, password="AdminPass123!", username=f"adminuser_{uuid4().hex[:8]}"
    )
    user = auth_service.register_user(register_req)

    # Update user to be admin
    with session(DB_ENGINE) as db_session:
        db_user = db_session.get(AuthUserTable, user.auth_user_id)
        db_user.is_admin = True
        db_session.commit()

    # Authenticate to get tokens
    login_req = LoginRequest(
        email=user.email, password="AdminPass123!", remember_me=False
    )
    tokens = auth_service.authenticate(
        login_req, device_info="Test Device", ip_address="127.0.0.1"
    )

    # Update user object with admin status
    user.is_admin = True

    return {"user": user, "tokens": tokens}


class TestProtectedRoute:
    """Test JWT token verification via protected route."""

    def test_protected_route_with_valid_token(self, client, test_user):
        """Test accessing protected route with valid token."""
        response = client.get(
            "/protected",
            headers={"Authorization": f"Bearer {test_user['tokens'].access_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == test_user["user"].auth_user_id
        assert data["email"] == test_user["user"].email

    def test_protected_route_without_token(self, client):
        """Test accessing protected route without token fails."""
        response = client.get("/protected")

        assert response.status_code == 401
        assert "detail" in response.json()

    def test_protected_route_with_invalid_token(self, client):
        """Test accessing protected route with invalid token fails."""
        response = client.get(
            "/protected", headers={"Authorization": "Bearer invalid_token"}
        )

        assert response.status_code == 401

    def test_protected_route_with_expired_token(self, client, auth_service):
        """Test accessing protected route with expired token fails."""
        from app.models.auth_models import RegisterRequest
        from uuid import uuid4

        # Register user with unique email
        email = f"expired_{uuid4().hex[:8]}@example.com"
        register_req = RegisterRequest(
            email=email,
            password="ExpiredPass123!",
            username=f"expireduser_{uuid4().hex[:8]}",
        )
        user = auth_service.register_user(register_req)

        # Create expired token
        config = get_base_app_config()
        from jose import jwt

        expired_time = datetime.utcnow() - timedelta(hours=1)
        payload = {
            "sub": user.email,
            "user_id": user.auth_user_id,
            "is_admin": False,
            "exp": expired_time,
            "jti": f"expired_{user.auth_user_id}",
        }
        expired_token = jwt.encode(
            payload, config.jwt_secret_key, algorithm=config.jwt_algorithm
        )

        response = client.get(
            "/protected", headers={"Authorization": f"Bearer {expired_token}"}
        )

        assert response.status_code == 401


class TestAdminRoute:
    """Test admin-only route protection."""

    def test_admin_route_with_admin_user(self, client, admin_user):
        """Test admin route accessible to admin user."""
        response = client.get(
            "/admin",
            headers={"Authorization": f"Bearer {admin_user['tokens'].access_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["is_admin"] is True

    def test_admin_route_with_regular_user(self, client, test_user):
        """Test admin route blocked for regular user."""
        response = client.get(
            "/admin",
            headers={"Authorization": f"Bearer {test_user['tokens'].access_token}"},
        )

        assert response.status_code == 403
        assert "Admin access required" in response.json()["detail"]

    def test_admin_route_without_token(self, client):
        """Test admin route blocked without token."""
        response = client.get("/admin")

        assert response.status_code == 401


class TestCurrentUserRoute:
    """Test get_current_user dependency."""

    def test_current_user_with_valid_token(self, client, test_user):
        """Test getting current user with valid token."""
        response = client.get(
            "/current-user",
            headers={"Authorization": f"Bearer {test_user['tokens'].access_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == test_user["user"].auth_user_id
        assert data["email"] == test_user["user"].email

    def test_current_user_without_token(self, client):
        """Test current user endpoint fails without token."""
        response = client.get("/current-user")

        assert response.status_code == 401


class TestOptionalUserRoute:
    """Test get_current_user_optional dependency."""

    def test_optional_user_with_valid_token(self, client, test_user):
        """Test optional user returns user with valid token."""
        response = client.get(
            "/optional-user",
            headers={"Authorization": f"Bearer {test_user['tokens'].access_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == test_user["user"].auth_user_id

    def test_optional_user_without_token(self, client):
        """Test optional user returns None without token."""
        response = client.get("/optional-user")

        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] is None

    def test_optional_user_with_invalid_token(self, client):
        """Test optional user returns None with invalid token."""
        response = client.get(
            "/optional-user", headers={"Authorization": "Bearer invalid_token"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] is None
