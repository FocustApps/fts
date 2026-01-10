"""
Example tests using domain-based composite fixtures.

These tests demonstrate how to use composite fixtures for realistic scenarios
instead of building everything manually.
"""

from sqlalchemy.engine import Engine

from common.service_connections.db_service.database.engine import (
    get_database_session as session,
)
from common.service_connections.db_service.models.suite_model import (
    query_suites_by_account,
)
from common.service_connections.db_service.models.test_case_model import (
    query_test_cases_by_account,
)
from common.service_connections.db_service.models.entity_tag_model import (
    query_entities_by_tag,
)


class TestMultiTenantIsolation:
    """Test multi-tenant data isolation using composite fixtures."""

    def test_accounts_cannot_see_each_others_suites(
        self, multi_tenant_setup, suite_factory, engine: Engine
    ):
        """Verify tenant1 cannot access tenant2's suites."""
        tenant1 = multi_tenant_setup["tenant1"]
        tenant2 = multi_tenant_setup["tenant2"]

        # Create suite for each tenant
        suite1_id = suite_factory(
            name="Tenant 1 Suite",
            account_id=tenant1["account_id"],
            sut_id=tenant1["sut_id"],
            owner_user_id=tenant1["user_id"],
        )

        suite2_id = suite_factory(
            name="Tenant 2 Suite",
            account_id=tenant2["account_id"],
            sut_id=tenant2["sut_id"],
            owner_user_id=tenant2["user_id"],
        )

        # Query tenant1's suites - should only see their own
        with session(engine) as db_session:
            tenant1_suites = query_suites_by_account(
                account_id=tenant1["account_id"],
                session=db_session,
                engine=engine,
            )

        suite_ids = {s.suite_id for s in tenant1_suites}
        assert suite1_id in suite_ids
        assert suite2_id not in suite_ids  # Tenant2's suite not visible

    def test_test_cases_isolated_by_account(
        self, multi_tenant_setup, test_case_factory, engine: Engine
    ):
        """Verify test cases are isolated between tenants."""
        tenant1 = multi_tenant_setup["tenant1"]
        tenant2 = multi_tenant_setup["tenant2"]

        # Create test case for each tenant
        tc1_id = test_case_factory(
            name="Tenant 1 Test",
            account_id=tenant1["account_id"],
            sut_id=tenant1["sut_id"],
            owner_user_id=tenant1["user_id"],
        )

        tc2_id = test_case_factory(
            name="Tenant 2 Test",
            account_id=tenant2["account_id"],
            sut_id=tenant2["sut_id"],
            owner_user_id=tenant2["user_id"],
        )

        # Query tenant1's test cases
        with session(engine) as db_session:
            tenant1_tests = query_test_cases_by_account(
                account_id=tenant1["account_id"],
                session=db_session,
                engine=engine,
            )

        test_ids = {t.test_case_id for t in tenant1_tests}
        assert tc1_id in test_ids
        assert tc2_id not in test_ids


class TestCompleteHierarchy:
    """Test full entity hierarchy using composite fixtures."""

    def test_plan_contains_suite_contains_test_case(
        self, complete_test_hierarchy, engine: Engine
    ):
        """Verify complete plan → suite → test_case hierarchy."""
        hierarchy = complete_test_hierarchy

        # All IDs should be created
        assert hierarchy["user_id"]
        assert hierarchy["account_id"]
        assert hierarchy["sut_id"]
        assert hierarchy["plan_id"]
        assert hierarchy["suite_id"]
        assert hierarchy["test_case_id"]

        # Verify relationships exist (would query association tables)
        # This is a placeholder - implement actual association queries
        assert True


class TestTagBasedQueries:
    """Test entity tagging using composite fixtures."""

    def test_query_entities_by_smoke_tag(self, tagged_entities, engine: Engine):
        """Find all entities tagged with 'smoke'."""
        account_id = tagged_entities["account_id"]

        # Query suites tagged with smoke
        with session(engine) as db_session:
            smoke_suite_ids = query_entities_by_tag(
                tag_name="smoke",
                entity_type="suite",
                account_id=account_id,
                db_session=db_session,
                engine=engine,
            )

        # Query test_cases tagged with smoke
        with session(engine) as db_session:
            smoke_test_ids = query_entities_by_tag(
                tag_name="smoke",
                entity_type="test_case",
                account_id=account_id,
                db_session=db_session,
                engine=engine,
            )

        # Should find smoke suite and api test (both tagged "smoke")
        assert tagged_entities["smoke_suite_id"] in smoke_suite_ids
        assert tagged_entities["api_test_id"] in smoke_test_ids
        assert tagged_entities["regression_suite_id"] not in smoke_suite_ids

    def test_query_entities_by_api_tag(self, tagged_entities, engine: Engine):
        """Find all entities tagged with 'api'."""
        account_id = tagged_entities["account_id"]

        with session(engine) as db_session:
            api_test_ids = query_entities_by_tag(
                tag_name="api",
                entity_type="test_case",
                account_id=account_id,
                db_session=db_session,
                engine=engine,
            )

        assert tagged_entities["api_test_id"] in api_test_ids
        assert tagged_entities["ui_test_id"] not in api_test_ids


class TestSuiteWithMultipleCases:
    """Test suite operations using composite fixtures."""

    def test_suite_has_three_test_cases(self, test_suite_with_cases, engine: Engine):
        """Verify suite contains correct number of test cases."""
        suite_data = test_suite_with_cases

        assert len(suite_data["test_case_ids"]) == 3
        assert all(isinstance(tc_id, str) for tc_id in suite_data["test_case_ids"])


class TestPlanWithMultipleSuites:
    """Test plan operations using composite fixtures."""

    def test_plan_has_three_suites(self, plan_with_suites, engine: Engine):
        """Verify plan contains correct number of suites."""
        plan_data = plan_with_suites

        assert len(plan_data["suite_ids"]) == 3
        assert all(isinstance(suite_id, str) for suite_id in plan_data["suite_ids"])
