"""
Tests for entity_tags API routes with role-based authorization.
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
from common.service_connections.db_service.models.entity_tag_model import (
    insert_entity_tag,
)

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


class TestEntityTagAuthorizationGET:
    def test_get_all_tags_requires_member(self, create_test_user):
        _, token = create_test_user()
        response = client.get(
            "/v1/api/tags", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 403

    def test_get_all_tags_with_member_succeeds(self, create_user_with_role):
        _, _, token = create_user_with_role(AccountRoleEnum.MEMBER)
        response = client.get(
            "/v1/api/tags", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200

    def test_get_tags_for_entity_validates_access(
        self, create_user_with_role, account_factory
    ):
        user_id, account_id, token = create_user_with_role(AccountRoleEnum.MEMBER)

        # Try different account - should fail
        other_account_id = account_factory(owner_user_id=user_id)
        response = client.get(
            f"/v1/api/tags/entity/plan/{uuid4()}?account_id={other_account_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403

        # Access own account - should succeed
        response = client.get(
            f"/v1/api/tags/entity/plan/{uuid4()}?account_id={account_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200

    def test_get_unique_tag_names_validates_access(
        self, create_user_with_role, account_factory
    ):
        user_id, account_id, token = create_user_with_role(AccountRoleEnum.MEMBER)

        # Try different account - should fail
        other_account_id = account_factory(owner_user_id=user_id)
        response = client.get(
            f"/v1/api/tags/names/unique?account_id={other_account_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403

        # Access own account - should succeed
        response = client.get(
            f"/v1/api/tags/names/unique?account_id={account_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200


class TestEntityTagAuthorizationPOST:
    def test_create_tag_requires_admin(self, create_user_with_role, entity_tag_factory):
        user_id, account_id, token = create_user_with_role(AccountRoleEnum.MEMBER)
        tag = entity_tag_factory(
            account_id=account_id,
            created_by_user_id=user_id,
            entity_id=str(uuid4()),
            entity_type="plan",
        )

        response = client.post(
            "/v1/api/tags",
            json=tag.model_dump(),
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403

    def test_create_tag_admin_succeeds(self, create_user_with_role, entity_tag_factory):
        user_id, account_id, token = create_user_with_role(AccountRoleEnum.ADMIN)
        tag = entity_tag_factory(
            account_id=account_id,
            created_by_user_id=user_id,
            entity_id=str(uuid4()),
            entity_type="plan",
        )

        response = client.post(
            "/v1/api/tags",
            json=tag.model_dump(),
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200

    def test_bulk_add_tags_validates_access(self, create_user_with_role, account_factory):
        user_id, account_id, token = create_user_with_role(AccountRoleEnum.ADMIN)

        # Try different account - should fail
        other_account_id = account_factory(owner_user_id=user_id)
        response = client.post(
            "/v1/api/tags/bulk/add",
            params={
                "entity_type": "plan",
                "entity_id": str(uuid4()),
                "tag_names": ["tag1", "tag2"],
                "tag_category": "category",
                "account_id": other_account_id,
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403


class TestEntityTagAuthorizationUPDATE:
    def test_update_tag_requires_admin(
        self, create_user_with_role, entity_tag_factory, engine
    ):
        user_id, account_id, member_token = create_user_with_role(AccountRoleEnum.MEMBER)
        tag = entity_tag_factory(
            account_id=account_id,
            created_by_user_id=user_id,
            entity_id=str(uuid4()),
            entity_type="plan",
        )
        tag_id = insert_entity_tag(tag=tag, engine=engine)

        tag.tag_name = "updated_tag"
        response = client.put(
            f"/v1/api/tags/{tag_id}",
            json=tag.model_dump(),
            headers={"Authorization": f"Bearer {member_token}"},
        )
        assert response.status_code == 403

    def test_update_tag_admin_succeeds(
        self, create_user_with_role, entity_tag_factory, engine
    ):
        user_id, account_id, token = create_user_with_role(AccountRoleEnum.ADMIN)
        tag = entity_tag_factory(
            account_id=account_id,
            created_by_user_id=user_id,
            entity_id=str(uuid4()),
            entity_type="plan",
        )
        tag_id = insert_entity_tag(tag=tag, engine=engine)

        tag.tag_name = "updated_tag"
        response = client.put(
            f"/v1/api/tags/{tag_id}",
            json=tag.model_dump(),
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200


class TestEntityTagAuthorizationDELETE:
    def test_delete_tag_requires_admin(
        self, create_user_with_role, entity_tag_factory, engine
    ):
        user_id, account_id, member_token = create_user_with_role(AccountRoleEnum.MEMBER)
        tag = entity_tag_factory(
            account_id=account_id,
            created_by_user_id=user_id,
            entity_id=str(uuid4()),
            entity_type="plan",
        )
        tag_id = insert_entity_tag(tag=tag, engine=engine)

        response = client.delete(
            f"/v1/api/tags/{tag_id}",
            headers={"Authorization": f"Bearer {member_token}"},
        )
        assert response.status_code == 403

    def test_delete_tag_admin_succeeds(
        self, create_user_with_role, entity_tag_factory, engine
    ):
        user_id, account_id, token = create_user_with_role(AccountRoleEnum.ADMIN)
        tag = entity_tag_factory(
            account_id=account_id,
            created_by_user_id=user_id,
            entity_id=str(uuid4()),
            entity_type="plan",
        )
        tag_id = insert_entity_tag(tag=tag, engine=engine)

        response = client.delete(
            f"/v1/api/tags/{tag_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
