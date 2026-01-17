"""
Tests for Plan model with legacy suites_ids migration support.

Tests cover:
- @model_validator for legacy string list migration
- Plan creation with automatic suite association
- Migration flag behavior (migrate_suites=True/False)
- Legacy data format parsing
"""

from sqlalchemy.engine import Engine

from common.service_connections.db_service.database.engine import (
    get_database_session as session,
)
from common.service_connections.db_service.models.plan_model import (
    PlanModel,
    insert_plan,
    query_plan_by_id,
    query_plans_by_account,
    update_plan,
    deactivate_plan,
)
from common.service_connections.db_service.models.plan_suite_helpers import (
    query_suites_for_plan,
)


class TestPlanLegacyMigration:
    """Test Plan model @model_validator for legacy suites_ids migration."""

    def test_insert_plan_without_legacy_data(
        self, plan_factory, account_factory, engine: Engine
    ):
        """Test normal plan creation without legacy suites_ids."""
        # Arrange
        account_id = account_factory()

        # Act - Create plan without legacy field
        plan_id = plan_factory(
            plan_name="Modern Plan",
            account_id=account_id,
            # suites_ids not provided (modern pattern)
        )

        # Assert
        with session(engine) as db_session:
            plan = query_plan_by_id(plan_id, db_session, engine)

        assert plan.plan_name == "Modern Plan"
        assert plan.suites_ids == ""  # Empty string for new plans

    def test_insert_plan_with_legacy_string_list(
        self, suite_factory, account_factory, engine: Engine
    ):
        """Test plan creation with legacy suites_ids as comma-separated string."""
        # Arrange
        account_id = account_factory()

        # Create suites for legacy association
        suite1 = suite_factory(name="Suite 1")
        suite2 = suite_factory(name="Suite 2")
        suite3 = suite_factory(name="Suite 3")

        # Legacy format: comma-separated UUID string
        legacy_suites = f"{suite1},{suite2},{suite3}"

        # Act - Insert with migrate_suites=True
        plan_model = PlanModel(
            plan_name="Legacy Migration Plan",
            account_id=account_id,
            suites_ids=legacy_suites,  # String format
        )
        plan_id = insert_plan(
            model=plan_model,
            engine=engine,
            migrate_suites=True,  # Enable migration
        )

        # Assert - Legacy field should be empty after migration
        with session(engine) as db_session:
            plan = query_plan_by_id(plan_id, db_session, engine)

            # Check that associations were created
            plan_suites = query_suites_for_plan(
                plan_id=plan_id, db_session=db_session, engine=engine
            )

        assert plan.suites_ids == ""  # Should be cleared after migration
        assert len(plan_suites) == 3

        # plan_suites is a list of suite_id strings
        suite_ids_set = set(plan_suites)
        assert suite_ids_set == {suite1, suite2, suite3}

    def test_insert_plan_with_legacy_list_of_uuids(
        self, suite_factory, account_factory, auth_user_factory, engine: Engine
    ):
        """Test plan creation with legacy suites_ids as comma-separated string."""
        # Arrange
        user_id = auth_user_factory()
        account_id = account_factory(owner_user_id=user_id)

        suite1 = suite_factory(account_id=account_id, owner_user_id=user_id)
        suite2 = suite_factory(account_id=account_id, owner_user_id=user_id)

        # Legacy format: comma-separated UUID string
        legacy_suites = f"{suite1},{suite2}"

        # Act - Insert with migration enabled
        plan_model = PlanModel(
            plan_name="Legacy List Plan",
            account_id=account_id,
            suites_ids=legacy_suites,
            owner_user_id=user_id,
        )
        plan_id = insert_plan(
            model=plan_model,
            engine=engine,
            migrate_suites=True,
        )

        # Assert
        with session(engine) as db_session:
            plan = query_plan_by_id(plan_id, db_session, engine)
            plan_suites = query_suites_for_plan(
                plan_id=plan_id, db_session=db_session, engine=engine
            )

        assert plan.suites_ids == ""  # Should be cleared after migration
        assert len(plan_suites) == 2

        # plan_suites is a list of suite_id strings
        suite_ids_set = set(plan_suites)
        assert suite_ids_set == {suite1, suite2}

    def test_migration_disabled_preserves_legacy_field(
        self, suite_factory, account_factory, auth_user_factory, engine: Engine
    ):
        """Test that migrate_suites=False preserves suites_ids without creating associations."""
        # Arrange
        user_id = auth_user_factory()
        account_id = account_factory(owner_user_id=user_id)
        suite1 = suite_factory(account_id=account_id, owner_user_id=user_id)
        suite2 = suite_factory(account_id=account_id, owner_user_id=user_id)

        legacy_suites = f"{suite1},{suite2}"

        # Act - Insert WITHOUT migration
        plan_model = PlanModel(
            plan_name="No Migration Plan",
            account_id=account_id,
            suites_ids=legacy_suites,
            owner_user_id=user_id,
        )
        plan_id = insert_plan(
            model=plan_model,
            engine=engine,
            migrate_suites=False,  # Migration disabled
        )

        # Assert - Legacy field preserved, no associations created
        with session(engine) as db_session:
            plan = query_plan_by_id(plan_id, db_session, engine)
            plan_suites = query_suites_for_plan(
                plan_id=plan_id, db_session=db_session, engine=engine
            )

        # Legacy field should still be set
        assert plan.suites_ids == legacy_suites
        # No associations should exist
        assert len(plan_suites) == 0


class TestPlanCRUD:
    """Test basic CRUD operations for Plan model."""

    def test_insert_and_query_plan(self, plan_factory, account_factory, engine: Engine):
        """Test inserting and querying a plan."""
        # Arrange
        account_id = account_factory()

        # Act
        plan_id = plan_factory(
            name="Integration Test Plan",
            account_id=account_id,
        )

        # Assert
        with session(engine) as db_session:
            plan = query_plan_by_id(plan_id, db_session, engine)

        assert plan.plan_name == "Integration Test Plan"
        assert plan.is_active is True

    def test_query_plans_by_account(self, plan_factory, account_factory, engine: Engine):
        """Test querying all plans for an account."""
        # Arrange
        account1 = account_factory()
        account2 = account_factory()

        plan1 = plan_factory(account_id=account1, name="Account 1 Plan A")
        plan2 = plan_factory(account_id=account1, name="Account 1 Plan B")
        plan3 = plan_factory(account_id=account2, name="Account 2 Plan")

        # Act
        with session(engine) as db_session:
            account1_plans = query_plans_by_account(
                account_id=account1, db_session=db_session, engine=engine
            )

            account2_plans = query_plans_by_account(
                account_id=account2, db_session=db_session, engine=engine
            )

        # Assert - Multi-tenant isolation
        account1_ids = {plan.plan_id for plan in account1_plans}
        account2_ids = {plan.plan_id for plan in account2_plans}

        assert plan1 in account1_ids
        assert plan2 in account1_ids
        assert plan3 not in account1_ids

        assert plan3 in account2_ids
        assert plan1 not in account2_ids

    def test_update_plan(self, plan_factory, account_factory, engine: Engine):
        """Test updating plan fields."""
        # Arrange
        account_id = account_factory()
        plan_id = plan_factory(account_id=account_id, plan_name="Original Name")

        # Get existing plan to update
        with session(engine) as db_session:
            existing_plan = query_plan_by_id(plan_id, db_session, engine)

        # Update the plan_name
        existing_plan.plan_name = "Updated Name"

        # Act
        result = update_plan(
            plan_id=plan_id,
            updates=existing_plan,
            engine=engine,
        )

        # Assert
        assert result is True

        with session(engine) as db_session:
            plan = query_plan_by_id(plan_id, db_session, engine)

        assert plan.plan_name == "Updated Name"

    def test_deactivate_plan(
        self, plan_factory, account_factory, auth_user_factory, engine: Engine
    ):
        """Test soft-deleting a plan."""
        # Arrange
        account_id = account_factory()
        user_id = auth_user_factory()
        plan_id = plan_factory(account_id=account_id)

        # Act
        result = deactivate_plan(
            plan_id=plan_id, deactivated_by_user_id=user_id, engine=engine
        )

        # Assert
        assert result is True

        with session(engine) as db_session:
            plan = query_plan_by_id(plan_id, db_session, engine)

        assert plan.is_active is False
        assert plan.deactivated_by_user_id == user_id
        assert plan.deactivated_at is not None


class TestPlanModelValidator:
    """Test the @model_validator logic for suites_ids migration."""

    def test_validator_converts_comma_separated_string(self):
        """Test model validator extracts suites_ids into _migrated_suite_ids."""
        # Arrange
        legacy_string = "abc-123,def-456,ghi-789"

        # Act - Model validator should extract IDs on instantiation
        plan_data = {
            "plan_id": "test-plan-id",
            "plan_name": "Test Plan",
            "account_id": "account-123",
            "suites_ids": legacy_string,
            "owner_user_id": "user-1",
        }

        plan = PlanModel(**plan_data)

        # Assert - IDs should be extracted into _migrated_suite_ids
        assert plan._migration_required == True
        assert plan._migrated_suite_ids == ["abc-123", "def-456", "ghi-789"]
        # Original field remains unchanged (deprecated)
        assert plan.suites_ids == legacy_string

    def test_validator_handles_list_input(self):
        """Test model validator with no legacy suites_ids."""
        # Act - Model with no suites_ids
        plan = PlanModel(
            plan_id="test-plan",
            plan_name="Test",
            account_id="account",
            suites_ids=None,
            owner_user_id="user",
        )

        # Assert - No migration should be required
        assert plan._migration_required == False
        assert plan._migrated_suite_ids == []

    def test_validator_handles_none(self):
        """Test model validator handles None suites_ids."""
        # Arrange & Act
        plan = PlanModel(
            plan_id="test-plan",
            plan_name="Test",
            account_id="account",
            suites_ids=None,
            owner_user_id="user",
        )

        # Assert
        assert plan.suites_ids is None
        assert plan._migration_required == False

    def test_validator_strips_whitespace(self):
        """Test validator strips whitespace from comma-separated values."""
        # Arrange
        legacy_with_spaces = "uuid-1 , uuid-2 ,uuid-3"

        # Act
        plan = PlanModel(
            plan_id="test-plan",
            plan_name="Test",
            account_id="account",
            suites_ids=legacy_with_spaces,
            owner_user_id="user",
        )

        # Assert - Whitespace should be stripped in _migrated_suite_ids
        assert plan._migrated_suite_ids == ["uuid-1", "uuid-2", "uuid-3"]
