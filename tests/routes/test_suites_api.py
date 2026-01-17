"""
Tests for suites API routes with role-based authorization.
"""

import pytest
from uuid import uuid4
from fastapi.testclient import TestClient

from app.fenrir_app import app
from app.services.user_auth_service import get_user_auth_service
from common.service_connections.db_service.database.engine import (
    get_database_session as session,
)
from common.service_connections.db_service.database.enums import AccountRoleEnum
from common.service_connections.db_service.db_manager import DB_ENGINE
from common.service_connections.db_service.models.account_models import (
    add_user_to_account,
)
from common.service_connections.db_service.models.suite_model import insert_suite

client = TestClient(app)


@pytest.fixture
def engine():
    return DB_ENGINE


@pytest.fixture
def auth_service(engine):
    return get_user_auth_service(engine)


@pytest.fixture
def create_test_user(auth_user_factory, auth_service):
    from app.models.auth_models import RegisterRequest, LoginRequest

    def _create_user(email: str = None, is_super_admin: bool = False):
        test_email = email or f"test_{uuid4().hex[:8]}@example.com"
        register_req = RegisterRequest(
            email=test_email,
            password="TestPass123!",
            username=f"testuser_{uuid4().hex[:8]}",
        )
        user = auth_service.register_user(register_req)

        if is_super_admin:
            with session(DB_ENGINE) as db_session:
                from common.service_connections.db_service.database.tables.account_tables.auth_user import (
                    AuthUserTable,
                )

                db_user = db_session.get(AuthUserTable, user.auth_user_id)
                db_user.is_super_admin = True
                db_session.commit()

        login_req = LoginRequest(
            email=test_email, password="TestPass123!", remember_me=False
        )
        tokens = auth_service.authenticate(login_req)
        return user.auth_user_id, tokens.access_token

    return _create_user


@pytest.fixture
def create_user_with_role(create_test_user, account_factory):
    def _create(role: AccountRoleEnum = AccountRoleEnum.MEMBER):
        user_id, _ = create_test_user()
        account_id = account_factory(owner_user_id=user_id)

        if role != AccountRoleEnum.OWNER:
            add_user_to_account(
                auth_user_id=user_id,
                account_id=account_id,
                role=role.value,
                is_primary=True,
                invited_by_user_id=user_id,
                engine=DB_ENGINE,
            )

        from common.service_connections.db_service.database.tables.account_tables.auth_user import (
            AuthUserTable,
        )

        with session(DB_ENGINE) as db_session:
            user = db_session.get(AuthUserTable, user_id)

        from app.services.jwt_service import get_jwt_service

        jwt_service = get_jwt_service()
        token = jwt_service.create_access_token(
            user_id=user_id,
            email=user.email,
            is_admin=user.is_admin,
            account_id=account_id,
            account_role=role.value,
        )
        return user_id, account_id, token

    return _create


class TestSuiteAuthorizationGET:
    def test_get_all_suites_requires_member(self, create_test_user):
        _, token = create_test_user()
        response = client.get(
            "/v1/api/suites", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 403

    def test_get_all_suites_with_member_succeeds(self, create_user_with_role):
        _, _, token = create_user_with_role(AccountRoleEnum.MEMBER)
        response = client.get(
            "/v1/api/suites", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200

    def test_get_suites_by_account_validates_access(
        self, create_user_with_role, account_factory
    ):
        user_id, account_id, token = create_user_with_role(AccountRoleEnum.MEMBER)

        other_account_id = account_factory(owner_user_id=user_id)
        response = client.get(
            f"/v1/api/suites/account/{other_account_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403

        response = client.get(
            f"/v1/api/suites/account/{account_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200


class TestSuiteAuthorizationPOST:
    def test_create_suite_requires_admin(self, create_user_with_role, suite_factory):
        user_id, account_id, token = create_user_with_role(AccountRoleEnum.MEMBER)
        suite = suite_factory(account_id=account_id, owner_user_id=user_id)

        response = client.post(
            "/v1/api/suites",
            json=suite.model_dump(),
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403

    def test_create_suite_admin_succeeds(self, create_user_with_role, suite_factory):
        user_id, account_id, token = create_user_with_role(AccountRoleEnum.ADMIN)
        suite = suite_factory(account_id=account_id, owner_user_id=user_id)

        response = client.post(
            "/v1/api/suites",
            json=suite.model_dump(),
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200


class TestSuiteAuthorizationUPDATE:
    def test_update_suite_requires_admin(
        self, create_user_with_role, suite_factory, engine
    ):
        user_id, account_id, member_token = create_user_with_role(AccountRoleEnum.MEMBER)
        suite = suite_factory(account_id=account_id, owner_user_id=user_id)
        suite_id = insert_suite(suite=suite, engine=engine)

        suite.description = "Updated"
        response = client.put(
            f"/v1/api/suites/{suite_id}",
            json=suite.model_dump(),
            headers={"Authorization": f"Bearer {member_token}"},
        )
        assert response.status_code == 403

    def test_update_suite_admin_succeeds(
        self, create_user_with_role, suite_factory, engine
    ):
        user_id, account_id, token = create_user_with_role(AccountRoleEnum.ADMIN)
        suite = suite_factory(account_id=account_id, owner_user_id=user_id)
        suite_id = insert_suite(suite=suite, engine=engine)

        suite.description = "Updated"
        response = client.put(
            f"/v1/api/suites/{suite_id}",
            json=suite.model_dump(),
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200


class TestSuiteAuthorizationDELETE:
    def test_delete_suite_requires_admin(
        self, create_user_with_role, suite_factory, engine
    ):
        user_id, account_id, member_token = create_user_with_role(AccountRoleEnum.MEMBER)
        suite = suite_factory(account_id=account_id, owner_user_id=user_id)
        suite_id = insert_suite(suite=suite, engine=engine)

        response = client.delete(
            f"/v1/api/suites/{suite_id}",
            headers={"Authorization": f"Bearer {member_token}"},
        )
        assert response.status_code == 403

    def test_delete_suite_admin_succeeds(
        self, create_user_with_role, suite_factory, engine
    ):
        user_id, account_id, token = create_user_with_role(AccountRoleEnum.ADMIN)
        suite = suite_factory(account_id=account_id, owner_user_id=user_id)
        suite_id = insert_suite(suite=suite, engine=engine)

        response = client.delete(
            f"/v1/api/suites/{suite_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
