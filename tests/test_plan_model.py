"""
Tests for Plan model with legacy suites_ids migration support.

Tests cover:
- @model_validator for legacy string list migration
- Plan creation with automatic suite association
- Migration flag behavior (migrate_suites=True/False)
- Legacy data format parsing
"""

from sqlalchemy.engine import Engine

from common.service_connections.db_service.models.plan_model import (
    PlanModel,
    insert_plan,
    query_plan_by_id,
    query_plans_by_account,
    update_plan,
    deactivate_plan,
)
from common.service_connections.db_service.models.plan_suite_helpers import (
    query_plan_with_suites,
    query_plans_for_suite,
    query_suites_for_plan
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
        assert plan.suites_ids is None  # Should remain None

    def test_insert_plan_with_legacy_string_list(
        self, suite_factory, account_factory, engine: Engine
    ):
        """Test plan creation with legacy suites_ids as comma-separated string."""
        # Arrange
        account_id = account_factory()

        # Create suites for legacy association
        suite1 = suite_factory(account_id=account_id, suite_name="Suite 1")
        suite2 = suite_factory(account_id=account_id, suite_name="Suite 2")
        suite3 = suite_factory(account_id=account_id, suite_name="Suite 3")

        # Legacy format: comma-separated UUID string
        legacy_suites = f"{suite1},{suite2},{suite3}"

        # Act - Insert with migrate_suites=True
        plan_id = insert_plan(
            plan_name="Legacy Migration Plan",
            account_id=account_id,
            suites_ids=legacy_suites,  # String format
            created_by_user_id="migrator",
            migrate_suites=True,  # Enable migration
            engine=engine,
        )

        # Assert - Legacy field should be None after migration
        with session(engine) as db_session:
            plan = query_plan_by_id(plan_id, db_session, engine)

            # Check that associations were created
            plan_suites = query_plan_suites(
                plan_id=plan_id, session=db_session, engine=engine
            )

        assert plan.suites_ids is None  # Should be cleared after migration
        assert len(plan_suites) == 3

        suite_ids = {assoc.suite_id for assoc in plan_suites}
        assert suite_ids == {suite1, suite2, suite3}

    def test_insert_plan_with_legacy_list_of_uuids(
        self, suite_factory, account_factory, engine: Engine
    ):
        """Test plan creation with legacy suites_ids as list of UUIDs."""
        # Arrange
        account_id = account_factory()

        suite1 = suite_factory(account_id=account_id)
        suite2 = suite_factory(account_id=account_id)

        # Legacy format: list of UUID strings
        legacy_suites = [suite1, suite2]

        # Act - Insert with migration enabled
        plan_id = insert_plan(
            plan_name="Legacy List Plan",
            account_id=account_id,
            suites_ids=legacy_suites,  # List format
            created_by_user_id="migrator",
            migrate_suites=True,
            engine=engine,
        )

        # Assert
        with session(engine) as db_session:
            plan = query_plan_by_id(plan_id, db_session, engine)
            plan_suites = query_plan_suites(
                plan_id=plan_id, session=db_session, engine=engine
            )

        assert plan.suites_ids is None
        assert len(plan_suites) == 2

    def test_migration_disabled_preserves_legacy_field(
        self, suite_factory, account_factory, engine: Engine
    ):
        """Test that migrate_suites=False preserves suites_ids without creating associations."""
        # Arrange
        account_id = account_factory()
        suite1 = suite_factory(account_id=account_id)
        suite2 = suite_factory(account_id=account_id)

        legacy_suites = f"{suite1},{suite2}"

        # Act - Insert WITHOUT migration
        plan_id = insert_plan(
            plan_name="No Migration Plan",
            account_id=account_id,
            suites_ids=legacy_suites,
            created_by_user_id="user",
            migrate_suites=False,  # Migration disabled
            engine=engine,
        )

        # Assert - Legacy field preserved, no associations created
        with session(engine) as db_session:
            plan = query_plan_by_id(plan_id, db_session, engine)
            plan_suites = query_plan_suites(
                plan_id=plan_id, session=db_session, engine=engine
            )

        # Legacy field should still be set
        assert plan.suites_ids is not None
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
            plan_name="Integration Test Plan",
            plan_description="Tests all critical features",
            account_id=account_id,
        )

        # Assert
        with session(engine) as db_session:
            plan = query_plan_by_id(plan_id, db_session, engine)

        assert plan.plan_name == "Integration Test Plan"
        assert plan.plan_description == "Tests all critical features"
        assert plan.is_active is True

    def test_query_plans_by_account(self, plan_factory, account_factory, engine: Engine):
        """Test querying all plans for an account."""
        # Arrange
        account1 = account_factory()
        account2 = account_factory()

        plan1 = plan_factory(account_id=account1, plan_name="Account 1 Plan A")
        plan2 = plan_factory(account_id=account1, plan_name="Account 1 Plan B")
        plan3 = plan_factory(account_id=account2, plan_name="Account 2 Plan")

        # Act
        with session(engine) as db_session:
            account1_plans = query_plans_by_account(
                account_id=account1, session=db_session, engine=engine
            )

            account2_plans = query_plans_by_account(
                account_id=account2, session=db_session, engine=engine
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

        # Act
        result = update_plan(
            plan_id=plan_id,
            updated_by_user_id="admin",
            plan_name="Updated Name",
            plan_description="New description",
            engine=engine,
        )

        # Assert
        assert result is True

        with session(engine) as db_session:
            plan = query_plan_by_id(plan_id, db_session, engine)

        assert plan.plan_name == "Updated Name"
        assert plan.plan_description == "New description"
        assert plan.updated_by_user_id == "admin"

    def test_deactivate_plan(self, plan_factory, account_factory, engine: Engine):
        """Test soft-deleting a plan."""
        # Arrange
        account_id = account_factory()
        plan_id = plan_factory(account_id=account_id)

        # Act
        result = deactivate_plan(
            plan_id=plan_id, deactivated_by_user_id="admin", engine=engine
        )

        # Assert
        assert result is True

        with session(engine) as db_session:
            plan = query_plan_by_id(plan_id, db_session, engine)

        assert plan.is_active is False
        assert plan.deactivated_by_user_id == "admin"
        assert plan.deactivated_at is not None


class TestPlanModelValidator:
    """Test the @model_validator logic for suites_ids migration."""

    def test_validator_converts_comma_separated_string(self):
        """Test model validator converts "uuid1,uuid2" to list."""
        # Arrange
        legacy_string = "abc-123,def-456,ghi-789"

        # Act - Model validator should convert on instantiation
        plan_data = {
            "plan_id": "test-plan-id",
            "plan_name": "Test Plan",
            "account_id": "account-123",
            "suites_ids": legacy_string,
            "created_by_user_id": "user-1",
        }

        plan = PlanModel(**plan_data)

        # Assert - String should be split into list
        assert isinstance(plan.suites_ids, list)
        assert plan.suites_ids == ["abc-123", "def-456", "ghi-789"]

    def test_validator_handles_list_input(self):
        """Test model validator handles list input correctly."""
        # Arrange
        legacy_list = ["uuid-1", "uuid-2"]

        # Act
        plan = PlanModel(
            plan_id="test-plan",
            plan_name="Test",
            account_id="account",
            suites_ids=legacy_list,
            created_by_user_id="user",
        )

        # Assert - List should remain as list
        assert isinstance(plan.suites_ids, list)
        assert plan.suites_ids == ["uuid-1", "uuid-2"]

    def test_validator_handles_none(self):
        """Test model validator handles None suites_ids."""
        # Arrange & Act
        plan = PlanModel(
            plan_id="test-plan",
            plan_name="Test",
            account_id="account",
            suites_ids=None,
            created_by_user_id="user",
        )

        # Assert
        assert plan.suites_ids is None

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
            created_by_user_id="user",
        )

        # Assert - Whitespace should be stripped
        assert plan.suites_ids == ["uuid-1", "uuid-2", "uuid-3"]
