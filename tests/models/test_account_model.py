"""
Tests for Account model CRUD operations.
"""

import pytest
from sqlalchemy.engine import Engine

from common.service_connections.db_service.models.account_models.account_model import (
    AccountModel,
    AccountWithOwnerModel,
    insert_account,
    query_account_by_id,
    query_all_accounts,
    query_account_with_owner,
    update_account,
    deactivate_account,
    activate_account,
)
from common.service_connections.db_service.database.engine import (
    get_database_session as session,
)


class TestAccountCRUD:
    """Test Account model CRUD operations."""

    def test_insert_account(self, engine: Engine, auth_user_factory):
        """Test creating a new account."""
        # Create owner user
        owner_id = auth_user_factory()

        # Create account
        account = AccountModel(
            account_name="Test Account",
            owner_user_id=owner_id,
        )

        account_id = insert_account(account, engine)

        assert account_id is not None
        assert len(account_id) == 36  # UUID length

        # Verify it was created
        with session(engine) as db_session:
            result = query_account_by_id(account_id, db_session, engine)
            assert result.account_name == "Test Account"
            assert result.owner_user_id == owner_id
            assert result.is_active is True

    def test_insert_account_ignores_provided_id(self, engine: Engine, auth_user_factory):
        """Test that insert_account ignores user-provided account_id."""
        owner_id = auth_user_factory()

        account = AccountModel(
            account_id="should-be-ignored",
            account_name="Test Account",
            owner_user_id=owner_id,
        )

        account_id = insert_account(account, engine)

        # Should generate new ID, not use provided one
        assert account_id != "should-be-ignored"

    def test_query_account_by_id(self, engine: Engine, account_factory):
        """Test querying an account by ID."""
        account_id = account_factory(name="Query Test Account")

        with session(engine) as db_session:
            result = query_account_by_id(account_id, db_session, engine)

        assert result.account_id == account_id
        assert result.account_name == "Query Test Account"
        assert result.is_active is True

    def test_query_account_by_id_not_found(self, engine: Engine):
        """Test querying a non-existent account raises ValueError."""
        with session(engine) as db_session:
            with pytest.raises(ValueError, match="Account with ID .* not found"):
                query_account_by_id("non-existent-id", db_session, engine)

    def test_query_all_accounts(self, engine: Engine, account_factory):
        """Test querying all accounts."""
        # Create multiple accounts
        account_id1 = account_factory(name="Account 1")
        account_id2 = account_factory(name="Account 2")
        account_id3 = account_factory(name="Account 3")

        with session(engine) as db_session:
            accounts = query_all_accounts(db_session, engine)

        account_ids = [acc.account_id for acc in accounts]
        assert account_id1 in account_ids
        assert account_id2 in account_ids
        assert account_id3 in account_ids

    def test_query_all_accounts_active_only(
        self, engine: Engine, account_factory, auth_user_factory
    ):
        """Test querying only active accounts."""
        # Create active and inactive accounts
        active_id = account_factory(name="Active Account")
        inactive_id = account_factory(name="Inactive Account")

        # Deactivate one
        deactivate_account(inactive_id, engine)

        with session(engine) as db_session:
            active_accounts = query_all_accounts(db_session, engine, active_only=True)

        account_ids = [acc.account_id for acc in active_accounts]
        assert active_id in account_ids
        assert inactive_id not in account_ids

    def test_query_account_with_owner(
        self, engine: Engine, account_factory, auth_user_factory
    ):
        """Test querying account with owner information."""
        # Create owner with specific details
        owner_id = auth_user_factory(email="owner@example.com", username="accountowner")
        account_id = account_factory(owner_user_id=owner_id, name="Owner Test Account")

        with session(engine) as db_session:
            result = query_account_with_owner(account_id, db_session, engine)

        assert isinstance(result, AccountWithOwnerModel)
        assert result.account_id == account_id
        assert result.account_name == "Owner Test Account"
        assert result.owner_email == "owner@example.com"
        assert result.owner_username == "accountowner"
        assert result.user_count == 0  # No associations yet

    def test_update_account(self, engine: Engine, account_factory, auth_user_factory):
        """Test updating an account."""
        account_id = account_factory(name="Original Name")
        new_owner_id = auth_user_factory()  # Create valid user for owner update

        # Update account
        updated_account = AccountModel(
            account_name="Updated Name",
            owner_user_id=new_owner_id,  # Use valid user ID
            logo_url="https://example.com/logo.png",
            primary_contact="contact@example.com",
        )

        result = update_account(account_id, updated_account, engine)
        assert result is True

        # Verify update
        with session(engine) as db_session:
            account = query_account_by_id(account_id, db_session, engine)
            assert account.account_name == "Updated Name"
            assert account.logo_url == "https://example.com/logo.png"
            assert account.primary_contact == "contact@example.com"
            assert account.updated_at is not None

    def test_update_account_not_found(self, engine: Engine, auth_user_factory):
        """Test updating a non-existent account raises ValueError."""
        owner_id = auth_user_factory()
        account = AccountModel(account_name="Test", owner_user_id=owner_id)

        with pytest.raises(ValueError, match="Account with ID .* not found"):
            update_account("non-existent-id", account, engine)

    def test_deactivate_account(self, engine: Engine, account_factory):
        """Test deactivating an account."""
        account_id = account_factory()

        # Deactivate
        result = deactivate_account(account_id, engine)
        assert result is True

        # Verify deactivation
        with session(engine) as db_session:
            account = query_account_by_id(account_id, db_session, engine)
            assert account.is_active is False
            assert account.updated_at is not None

    def test_activate_account(self, engine: Engine, account_factory):
        """Test activating a deactivated account."""
        account_id = account_factory()

        # Deactivate then reactivate
        deactivate_account(account_id, engine)
        result = activate_account(account_id, engine)
        assert result is True

        # Verify activation
        with session(engine) as db_session:
            account = query_account_by_id(account_id, db_session, engine)
            assert account.is_active is True

    def test_deactivate_account_not_found(self, engine: Engine):
        """Test deactivating a non-existent account raises ValueError."""
        with pytest.raises(ValueError, match="Account with ID .* not found"):
            deactivate_account("non-existent-id", engine)

    def test_activate_account_not_found(self, engine: Engine):
        """Test activating a non-existent account raises ValueError."""
        with pytest.raises(ValueError, match="Account with ID .* not found"):
            activate_account("non-existent-id", engine)


class TestAccountWithOwner:
    """Test querying accounts with owner details."""

    def test_query_account_with_owner_includes_user_count(
        self, engine: Engine, account_factory, auth_user_factory
    ):
        """Test that query_account_with_owner includes accurate user count."""
        from common.service_connections.db_service.database.tables.account_tables.auth_user_account_association import (
            AuthUserAccountAssociation,
        )

        owner_id = auth_user_factory()
        account_id = account_factory(owner_user_id=owner_id)

        # Add some user associations manually
        with session(engine) as db_session:
            user1 = auth_user_factory()
            user2 = auth_user_factory()

            assoc1 = AuthUserAccountAssociation(
                auth_user_id=user1,
                account_id=account_id,
                role="member",
            )
            assoc2 = AuthUserAccountAssociation(
                auth_user_id=user2,
                account_id=account_id,
                role="admin",
            )
            db_session.add(assoc1)
            db_session.add(assoc2)
            db_session.commit()

        # Query with owner
        with session(engine) as db_session:
            result = query_account_with_owner(account_id, db_session, engine)

        assert result.user_count == 2

    def test_query_account_with_owner_not_found(self, engine: Engine):
        """Test querying non-existent account with owner raises ValueError."""
        with session(engine) as db_session:
            with pytest.raises(ValueError, match="Account with ID .* not found"):
                query_account_with_owner("non-existent-id", db_session, engine)
