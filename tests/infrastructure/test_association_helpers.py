"""
Tests for association helpers (Suite-TestCase and Plan-Suite relationships).

Tests cover:
- Adding/removing associations
- Execution order management
- Bulk operations
- Composite queries (suite with test cases, plan with suites)
"""

from sqlalchemy.engine import Engine

from common.service_connections.db_service.database.engine import (
    get_database_session as session,
)
from common.service_connections.db_service.models.suite_test_case_helpers import (
    add_test_case_to_suite,
    reorder_suite_test_cases,
    query_suite_with_test_cases,
    query_test_cases_for_suite,
    get_suite_test_count,
    bulk_add_test_cases_to_suite,
    replace_suite_test_cases,
)
from common.service_connections.db_service.models.plan_suite_helpers import (
    add_suite_to_plan,
    reorder_plan_suites,
    query_plan_with_suites,
    query_suites_for_plan,
    bulk_add_suites_to_plan,
)


class TestSuiteTestCaseAssociations:
    """Test suite-test case relationship management."""

    def test_add_test_case_to_suite(
        self,
        suite_factory,
        test_case_factory,
        system_under_test_factory,
        account_factory,
        engine: Engine,
    ):
        """Test adding a test case to a suite with execution order."""
        # Arrange
        account_id = account_factory()
        sut_id = system_under_test_factory(account_id=account_id)
        suite_id = suite_factory(account_id=account_id, name="Login Suite")
        test_case_id = test_case_factory(
            account_id=account_id, sut_id=sut_id, name="Test Login Form"
        )

        # Act
        assoc_id = add_test_case_to_suite(
            suite_id=suite_id, test_case_id=test_case_id, execution_order=0, engine=engine
        )

        # Assert
        assert assoc_id is not None

        with session() as db_session:
            suite_with_tests = query_suite_with_test_cases(suite_id, db_session, engine)

        assert suite_with_tests is not None
        assert len(suite_with_tests.test_cases) == 1
        assert suite_with_tests.test_cases[0]["test_case_name"] == "Test Login Form"
        assert suite_with_tests.test_cases[0]["execution_order"] == 0

    def test_reorder_suite_test_cases(
        self,
        suite_factory,
        test_case_factory,
        system_under_test_factory,
        account_factory,
        engine: Engine,
    ):
        """Test reordering test cases within a suite."""
        # Arrange
        account_id = account_factory()
        sut_id = system_under_test_factory(account_id=account_id)
        suite_id = suite_factory(account_id=account_id)

        # Create three test cases
        tc1 = test_case_factory(account_id=account_id, sut_id=sut_id, name="Test A")
        tc2 = test_case_factory(account_id=account_id, sut_id=sut_id, name="Test B")
        tc3 = test_case_factory(account_id=account_id, sut_id=sut_id, name="Test C")

        # Add to suite in order A, B, C
        add_test_case_to_suite(suite_id, tc1, execution_order=0, engine=engine)
        add_test_case_to_suite(suite_id, tc2, execution_order=1, engine=engine)
        add_test_case_to_suite(suite_id, tc3, execution_order=2, engine=engine)

        # Act - Reorder to C, A, B
        new_order = [tc3, tc1, tc2]
        update_count = reorder_suite_test_cases(suite_id, new_order, engine)

        # Assert
        assert update_count > 0

        with session() as db_session:
            ordered_ids = query_test_cases_for_suite(suite_id, db_session, engine)

        assert ordered_ids == new_order

    def test_bulk_add_test_cases(
        self,
        suite_factory,
        test_case_factory,
        system_under_test_factory,
        account_factory,
        engine: Engine,
    ):
        """Test bulk adding multiple test cases to a suite."""
        # Arrange
        account_id = account_factory()
        sut_id = system_under_test_factory(account_id=account_id)
        suite_id = suite_factory(account_id=account_id, name="Bulk Suite")

        test_case_ids = [
            test_case_factory(account_id=account_id, sut_id=sut_id, name=f"Test {i}")
            for i in range(5)
        ]

        # Act
        assoc_ids = bulk_add_test_cases_to_suite(
            suite_id=suite_id,
            test_case_ids=test_case_ids,
            engine=engine,
            starting_order=0,
        )

        # Assert
        assert len(assoc_ids) == 5

        with session() as db_session:
            count = get_suite_test_count(suite_id, db_session, engine)
        assert count == 5

    def test_replace_suite_test_cases(
        self,
        suite_factory,
        test_case_factory,
        system_under_test_factory,
        account_factory,
        engine: Engine,
    ):
        """Test replacing all test cases in a suite (soft delete old, add new)."""
        # Arrange
        account_id = account_factory()
        sut_id = system_under_test_factory(account_id=account_id)
        suite_id = suite_factory(account_id=account_id)

        # Add initial test cases
        old_tc1 = test_case_factory(account_id=account_id, sut_id=sut_id, name="Old 1")
        old_tc2 = test_case_factory(account_id=account_id, sut_id=sut_id, name="Old 2")
        add_test_case_to_suite(suite_id, old_tc1, 0, engine)
        add_test_case_to_suite(suite_id, old_tc2, 1, engine)

        # Create new test cases
        new_tc1 = test_case_factory(account_id=account_id, sut_id=sut_id, name="New 1")
        new_tc2 = test_case_factory(account_id=account_id, sut_id=sut_id, name="New 2")
        new_tc3 = test_case_factory(account_id=account_id, sut_id=sut_id, name="New 3")

        # Act
        result = replace_suite_test_cases(
            suite_id=suite_id,
            new_test_case_ids=[new_tc1, new_tc2, new_tc3],
            engine=engine,
            soft_delete_old=True,
        )

        # Assert
        assert len(result["removed"]) == 2
        assert len(result["added"]) == 3

        with session() as db_session:
            active_tests = query_test_cases_for_suite(
                suite_id, db_session, engine, active_only=True
            )

        assert len(active_tests) == 3
        assert new_tc1 in active_tests


class TestPlanSuiteAssociations:
    """Test plan-suite relationship management."""

    def test_add_suite_to_plan(
        self, plan_factory, suite_factory, account_factory, engine: Engine
    ):
        """Test adding a suite to a plan."""
        # Arrange
        account_id = account_factory()
        plan_id = plan_factory(account_id=account_id, name="Q1 Test Plan")
        suite_id = suite_factory(account_id=account_id, name="Regression Suite")

        # Act
        assoc_id = add_suite_to_plan(
            plan_id=plan_id, suite_id=suite_id, execution_order=0, engine=engine
        )

        # Assert
        assert assoc_id is not None

        with session() as db_session:
            plan_with_suites = query_plan_with_suites(plan_id, db_session, engine)

        assert plan_with_suites is not None
        assert len(plan_with_suites.suites) == 1
        assert plan_with_suites.suites[0]["suite_name"] == "Regression Suite"

    def test_reorder_plan_suites(
        self, plan_factory, suite_factory, account_factory, engine: Engine
    ):
        """Test reordering suites within a plan."""
        # Arrange
        account_id = account_factory()
        plan_id = plan_factory(account_id=account_id)

        suite1 = suite_factory(account_id=account_id, name="Suite 1")
        suite2 = suite_factory(account_id=account_id, name="Suite 2")
        suite3 = suite_factory(account_id=account_id, name="Suite 3")

        add_suite_to_plan(plan_id, suite1, 0, engine)
        add_suite_to_plan(plan_id, suite2, 1, engine)
        add_suite_to_plan(plan_id, suite3, 2, engine)

        # Act - Reverse order
        new_order = [suite3, suite2, suite1]
        update_count = reorder_plan_suites(plan_id, new_order, engine)

        # Assert
        assert update_count > 0

        with session() as db_session:
            ordered_ids = query_suites_for_plan(plan_id, db_session, engine)

        assert ordered_ids == new_order

    def test_bulk_add_suites_to_plan(
        self, plan_factory, suite_factory, account_factory, engine: Engine
    ):
        """Test bulk adding multiple suites to a plan."""
        # Arrange
        account_id = account_factory()
        plan_id = plan_factory(account_id=account_id, name="Master Plan")

        suite_ids = [
            suite_factory(account_id=account_id, name=f"Suite {i}") for i in range(4)
        ]

        # Act
        assoc_ids = bulk_add_suites_to_plan(
            plan_id=plan_id, suite_ids=suite_ids, engine=engine, starting_order=0
        )

        # Assert
        assert len(assoc_ids) == 4

        with session() as db_session:
            plan_with_suites = query_plan_with_suites(plan_id, db_session, engine)

        assert len(plan_with_suites.suites) == 4


class TestCompositeQueries:
    """Test composite queries that join across associations."""

    def test_query_suite_with_test_cases_includes_metadata(
        self,
        suite_factory,
        test_case_factory,
        system_under_test_factory,
        account_factory,
        engine: Engine,
    ):
        """Test that composite query includes test case metadata."""
        # Arrange
        account_id = account_factory()
        sut_id = system_under_test_factory(account_id=account_id)
        suite_id = suite_factory(account_id=account_id, name="Metadata Suite")

        tc1 = test_case_factory(
            account_id=account_id,
            sut_id=sut_id,
            name="Functional Test",
            test_type="functional",
        )
        tc2 = test_case_factory(
            account_id=account_id,
            sut_id=sut_id,
            name="Performance Test",
            test_type="performance",
        )

        add_test_case_to_suite(suite_id, tc1, 0, engine)
        add_test_case_to_suite(suite_id, tc2, 1, engine)

        # Act
        with session() as db_session:
            suite_with_tests = query_suite_with_test_cases(suite_id, db_session, engine)

        # Assert - Check metadata is included
        assert suite_with_tests.test_cases[0]["test_type"] == "functional"
        assert suite_with_tests.test_cases[1]["test_type"] == "performance"
        assert suite_with_tests.test_cases[0]["execution_order"] == 0
        assert suite_with_tests.test_cases[1]["execution_order"] == 1
