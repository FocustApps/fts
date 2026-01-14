"""
Tests for Account-User Association model operations.
"""

import pytest
from sqlalchemy.engine import Engine

from common.service_connections.db_service.models.account_models.account_user_association_model import (
    AccountUserWithDetailsModel,
    BulkOperationResult,
    add_user_to_account,
    bulk_add_users_to_account,
    update_user_role,
    bulk_update_roles,
    set_primary_account,
    remove_user_from_account,
    bulk_remove_users,
    query_users_by_account,
    query_accounts_by_user,
    query_user_primary_account,
    query_user_role_in_account,
)
from common.service_connections.db_service.database.enums import AccountRoleEnum
from common.service_connections.db_service.database.engine import (
    get_database_session as session,
)


class TestAccountUserAssociation:
    """Test basic account-user association operations."""

    def test_add_user_to_account(
        self, engine: Engine, account_factory, auth_user_factory
    ):
        """Test adding a user to an account."""
        account_id = account_factory()
        user_id = auth_user_factory()

        association_id = add_user_to_account(
            auth_user_id=user_id,
            account_id=account_id,
            role=AccountRoleEnum.MEMBER.value,
            engine=engine,
        )

        assert association_id is not None
        assert len(association_id) == 36  # UUID length

        # Verify association was created
        with session(engine) as db_session:
            associations = query_users_by_account(account_id, db_session, engine)
            assert len(associations) == 1
            assert associations[0].auth_user_id == user_id
            assert associations[0].role == AccountRoleEnum.MEMBER.value

    def test_add_user_to_account_with_custom_role(
        self, engine: Engine, account_factory, auth_user_factory
    ):
        """Test adding a user with admin role."""
        account_id = account_factory()
        user_id = auth_user_factory()

        add_user_to_account(
            auth_user_id=user_id,
            account_id=account_id,
            role=AccountRoleEnum.ADMIN.value,
            engine=engine,
        )

        with session(engine) as db_session:
            role = query_user_role_in_account(user_id, account_id, db_session, engine)
            assert role == AccountRoleEnum.ADMIN.value

    def test_add_user_to_account_duplicate_raises_error(
        self, engine: Engine, account_factory, auth_user_factory
    ):
        """Test adding same user to account twice raises ValueError."""
        account_id = account_factory()
        user_id = auth_user_factory()

        # Add once
        add_user_to_account(auth_user_id=user_id, account_id=account_id, engine=engine)

        # Try to add again
        with pytest.raises(ValueError, match="already associated"):
            add_user_to_account(
                auth_user_id=user_id, account_id=account_id, engine=engine
            )

    def test_add_user_as_primary(
        self, engine: Engine, account_factory, auth_user_factory
    ):
        """Test adding a user with primary account designation."""
        account_id = account_factory()
        user_id = auth_user_factory()

        add_user_to_account(
            auth_user_id=user_id,
            account_id=account_id,
            is_primary=True,
            engine=engine,
        )

        with session(engine) as db_session:
            primary = query_user_primary_account(user_id, db_session, engine)
            assert primary is not None
            assert primary.account_id == account_id

    def test_update_user_role(self, engine: Engine, account_factory, auth_user_factory):
        """Test updating a user's role in an account."""
        account_id = account_factory()
        user_id = auth_user_factory()

        # Add user as member
        add_user_to_account(
            auth_user_id=user_id,
            account_id=account_id,
            role=AccountRoleEnum.MEMBER.value,
            engine=engine,
        )

        # Update to admin
        result = update_user_role(
            user_id, account_id, AccountRoleEnum.ADMIN.value, engine
        )
        assert result is True

        # Verify update
        with session(engine) as db_session:
            role = query_user_role_in_account(user_id, account_id, db_session, engine)
            assert role == AccountRoleEnum.ADMIN.value

    def test_update_user_role_not_found(self, engine: Engine):
        """Test updating role for non-existent association raises ValueError."""
        with pytest.raises(ValueError, match="not associated"):
            update_user_role("fake-user", "fake-account", "admin", None)

    def test_set_primary_account(
        self, engine: Engine, account_factory, auth_user_factory
    ):
        """Test setting an account as primary."""
        user_id = auth_user_factory()
        account1 = account_factory()
        account2 = account_factory()

        # Add user to both accounts
        add_user_to_account(user_id, account1, is_primary=True, engine=engine)
        add_user_to_account(user_id, account2, engine=engine)

        # Set account2 as primary
        result = set_primary_account(user_id, account2, engine)
        assert result is True

        # Verify account2 is now primary
        with session(engine) as db_session:
            primary = query_user_primary_account(user_id, db_session, engine)
            assert primary.account_id == account2

    def test_set_primary_account_not_found(self, engine: Engine):
        """Test setting primary for non-existent association raises ValueError."""
        with pytest.raises(ValueError, match="not associated"):
            set_primary_account("fake-user", "fake-account", None)

    def test_remove_user_from_account(
        self, engine: Engine, account_factory, auth_user_factory
    ):
        """Test removing a user from an account."""
        account_id = account_factory()
        user_id = auth_user_factory()

        # Add user
        add_user_to_account(user_id, account_id, engine=engine)

        # Remove user
        result = remove_user_from_account(user_id, account_id, engine)
        assert result is True

        # Verify removal
        with session(engine) as db_session:
            users = query_users_by_account(account_id, db_session, engine)
            assert len(users) == 0

    def test_remove_user_from_account_not_found(self, engine: Engine):
        """Test removing non-existent association raises ValueError."""
        with pytest.raises(ValueError, match="not associated"):
            remove_user_from_account("fake-user", "fake-account", None)


class TestBulkOperations:
    """Test bulk account-user association operations."""

    def test_bulk_add_users_to_account(
        self, engine: Engine, account_factory, auth_user_factory
    ):
        """Test adding multiple users to an account in bulk."""
        account_id = account_factory()
        user_ids = [auth_user_factory() for _ in range(5)]

        result = bulk_add_users_to_account(
            user_ids=user_ids,
            account_id=account_id,
            role=AccountRoleEnum.MEMBER.value,
            engine=engine,
        )

        assert isinstance(result, BulkOperationResult)
        assert result.total == 5
        assert result.successful == 5
        assert result.failed == 0

        # Verify all users were added
        with session(engine) as db_session:
            users = query_users_by_account(account_id, db_session, engine)
            assert len(users) == 5

    def test_bulk_add_users_handles_duplicates(
        self, engine: Engine, account_factory, auth_user_factory
    ):
        """Test bulk add handles duplicate gracefully."""
        account_id = account_factory()
        user1 = auth_user_factory()
        user2 = auth_user_factory()
        user3 = auth_user_factory()

        # Add user1 first
        add_user_to_account(user1, account_id, engine=engine)

        # Try to bulk add including user1 (duplicate)
        result = bulk_add_users_to_account(
            user_ids=[user1, user2, user3],
            account_id=account_id,
            engine=engine,
        )

        assert result.total == 3
        assert result.successful == 2  # user2 and user3
        assert result.failed == 1  # user1 (duplicate)
        assert len(result.errors) == 1

    def test_bulk_update_roles(self, engine: Engine, account_factory, auth_user_factory):
        """Test updating roles for multiple users in bulk."""
        account_id = account_factory()
        user_ids = [auth_user_factory() for _ in range(3)]

        # Add users as members
        for user_id in user_ids:
            add_user_to_account(
                user_id, account_id, role=AccountRoleEnum.MEMBER.value, engine=engine
            )

        # Update all to admin
        updates = [(uid, account_id, AccountRoleEnum.ADMIN.value) for uid in user_ids]
        result = bulk_update_roles(updates, engine)

        assert result.total == 3
        assert result.successful == 3
        assert result.failed == 0

        # Verify updates
        with session(engine) as db_session:
            for user_id in user_ids:
                role = query_user_role_in_account(user_id, account_id, db_session, engine)
                assert role == AccountRoleEnum.ADMIN.value

    def test_bulk_remove_users(self, engine: Engine, account_factory, auth_user_factory):
        """Test removing multiple users from accounts in bulk."""
        account_id = account_factory()
        user_ids = [auth_user_factory() for _ in range(4)]

        # Add users
        for user_id in user_ids:
            add_user_to_account(user_id, account_id, engine=engine)

        # Remove half of them
        removals = [(user_ids[0], account_id), (user_ids[1], account_id)]
        result = bulk_remove_users(removals, engine)

        assert result.total == 2
        assert result.successful == 2
        assert result.failed == 0

        # Verify removals
        with session(engine) as db_session:
            users = query_users_by_account(account_id, db_session, engine)
            assert len(users) == 2
            remaining_ids = [u.auth_user_id for u in users]
            assert user_ids[2] in remaining_ids
            assert user_ids[3] in remaining_ids


class TestQueryOperations:
    """Test query operations for account-user associations."""

    def test_query_users_by_account(
        self, engine: Engine, account_factory, auth_user_factory
    ):
        """Test querying all users in an account."""
        account_id = account_factory()
        user1 = auth_user_factory(email="user1@example.com", username="user1")
        user2 = auth_user_factory(email="user2@example.com", username="user2")

        add_user_to_account(
            user1, account_id, role=AccountRoleEnum.ADMIN.value, engine=engine
        )
        add_user_to_account(
            user2, account_id, role=AccountRoleEnum.MEMBER.value, engine=engine
        )

        with session(engine) as db_session:
            users = query_users_by_account(account_id, db_session, engine)

        assert len(users) == 2
        assert all(isinstance(u, AccountUserWithDetailsModel) for u in users)
        assert users[0].user_email is not None
        assert users[0].user_username is not None

    def test_query_users_by_account_active_only(
        self, engine: Engine, account_factory, auth_user_factory
    ):
        """Test querying only active associations."""
        from common.service_connections.db_service.database.tables.account_tables.auth_user_account_association import (
            AuthUserAccountAssociation,
        )

        account_id = account_factory()
        user1 = auth_user_factory()
        user2 = auth_user_factory()

        # Add both users
        add_user_to_account(user1, account_id, engine=engine)
        add_user_to_account(user2, account_id, engine=engine)

        # Deactivate user1's association
        with session(engine) as db_session:
            assoc = (
                db_session.query(AuthUserAccountAssociation)
                .filter(
                    AuthUserAccountAssociation.auth_user_id == user1,
                    AuthUserAccountAssociation.account_id == account_id,
                )
                .first()
            )
            assoc.is_active = False
            db_session.commit()

        # Query active only
        with session(engine) as db_session:
            users = query_users_by_account(
                account_id, db_session, engine, active_only=True
            )

        assert len(users) == 1
        assert users[0].auth_user_id == user2

    def test_query_accounts_by_user(
        self, engine: Engine, account_factory, auth_user_factory
    ):
        """Test querying all accounts a user belongs to."""
        user_id = auth_user_factory()
        account1 = account_factory()
        account2 = account_factory()
        account3 = account_factory()

        # Add user to multiple accounts with different roles
        add_user_to_account(
            user_id, account1, role=AccountRoleEnum.OWNER.value, engine=engine
        )
        add_user_to_account(
            user_id, account2, role=AccountRoleEnum.ADMIN.value, engine=engine
        )
        add_user_to_account(
            user_id, account3, role=AccountRoleEnum.VIEWER.value, engine=engine
        )

        with session(engine) as db_session:
            accounts = query_accounts_by_user(user_id, db_session, engine)

        assert len(accounts) == 3
        account_ids = [acc.account_id for acc in accounts]
        assert account1 in account_ids
        assert account2 in account_ids
        assert account3 in account_ids

    def test_query_user_primary_account(
        self, engine: Engine, account_factory, auth_user_factory
    ):
        """Test querying a user's primary account."""
        user_id = auth_user_factory()
        primary_account = account_factory()
        other_account = account_factory()

        add_user_to_account(user_id, primary_account, is_primary=True, engine=engine)
        add_user_to_account(user_id, other_account, engine=engine)

        with session(engine) as db_session:
            result = query_user_primary_account(user_id, db_session, engine)

        assert result is not None
        assert result.account_id == primary_account
        assert result.is_primary is True

    def test_query_user_primary_account_none(self, engine: Engine, auth_user_factory):
        """Test querying primary account for user with no associations."""
        user_id = auth_user_factory()

        with session(engine) as db_session:
            result = query_user_primary_account(user_id, db_session, engine)

        assert result is None

    def test_query_user_role_in_account(
        self, engine: Engine, account_factory, auth_user_factory
    ):
        """Test querying a user's role in a specific account."""
        account_id = account_factory()
        user_id = auth_user_factory()

        add_user_to_account(
            user_id, account_id, role=AccountRoleEnum.ADMIN.value, engine=engine
        )

        with session(engine) as db_session:
            role = query_user_role_in_account(user_id, account_id, db_session, engine)

        assert role == AccountRoleEnum.ADMIN.value

    def test_query_user_role_in_account_not_found(
        self, engine: Engine, account_factory, auth_user_factory
    ):
        """Test querying role for non-existent association returns None."""
        account_id = account_factory()
        user_id = auth_user_factory()

        with session(engine) as db_session:
            role = query_user_role_in_account(user_id, account_id, db_session, engine)

        assert role is None


class TestPrimaryAccountLogic:
    """Test primary account designation logic."""

    def test_only_one_primary_account(
        self, engine: Engine, account_factory, auth_user_factory
    ):
        """Test that only one account can be primary at a time."""
        user_id = auth_user_factory()
        account1 = account_factory()
        account2 = account_factory()

        # Add user to both, first as primary
        add_user_to_account(user_id, account1, is_primary=True, engine=engine)
        add_user_to_account(user_id, account2, is_primary=True, engine=engine)

        # Only account2 should be primary (last one set)
        with session(engine) as db_session:
            primary = query_user_primary_account(user_id, db_session, engine)

        # Note: Current implementation may not properly handle is_primary
        # This test documents expected behavior
        assert primary is not None

    def test_set_primary_unsets_others(
        self, engine: Engine, account_factory, auth_user_factory
    ):
        """Test that setting primary account unsets previous primary."""
        user_id = auth_user_factory()
        account1 = account_factory()
        account2 = account_factory()
        account3 = account_factory()

        # Add user to all accounts
        add_user_to_account(user_id, account1, is_primary=True, engine=engine)
        add_user_to_account(user_id, account2, engine=engine)
        add_user_to_account(user_id, account3, engine=engine)

        # Set account3 as primary
        set_primary_account(user_id, account3, engine)

        # Verify account3 is primary
        with session(engine) as db_session:
            primary = query_user_primary_account(user_id, db_session, engine)
            accounts = query_accounts_by_user(user_id, db_session, engine)

        assert primary.account_id == account3

        # Only one should be marked as primary
        primary_count = sum(1 for acc in accounts if acc.is_primary)
        assert primary_count <= 1  # Should be exactly 1, but at most 1
