"""
Composite fixtures that represent realistic domain scenarios.

These fixtures create complete entity hierarchies for testing real-world use cases.
"""

import pytest
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from common.service_connections.db_service.models.plan_suite_helpers import (
    add_suite_to_plan,
)
from common.service_connections.db_service.models.suite_test_case_helpers import (
    add_test_case_to_suite,
)


@pytest.fixture(scope="function")
def complete_test_hierarchy(
    engine: Engine,
    session: Session,
    auth_user_factory,
    account_factory,
    system_under_test_factory,
    plan_factory,
    suite_factory,
    test_case_factory,
    plan_suite_association_factory,
    suite_test_case_association_factory,
):
    """Create a complete test management hierarchy.

    Creates: user → account → SUT → plan → suite → test_case (all linked)

    Returns:
        dict with keys: user_id, account_id, sut_id, plan_id, suite_id, test_case_id
    """
    # Build hierarchy
    user_id = auth_user_factory()
    account_id = account_factory(owner_user_id=user_id)
    sut_id = system_under_test_factory(account_id=account_id, owner_user_id=user_id)
    plan_id = plan_factory(name="Integration Test Plan", owner_user_id=user_id)
    suite_id = suite_factory(
        name="API Tests",
        account_id=account_id,
        sut_id=sut_id,
        owner_user_id=user_id,
    )
    test_case_id = test_case_factory(
        name="Test User Login",
        account_id=account_id,
        sut_id=sut_id,
        owner_user_id=user_id,
    )

    # Link relationships
    add_suite_to_plan(
        plan_id=plan_id,
        suite_id=suite_id,
        execution_order=1,
        engine=engine,
    )
    add_test_case_to_suite(
        suite_id=suite_id,
        test_case_id=test_case_id,
        execution_order=1,
        engine=engine,
    )

    return {
        "user_id": user_id,
        "account_id": account_id,
        "sut_id": sut_id,
        "plan_id": plan_id,
        "suite_id": suite_id,
        "test_case_id": test_case_id,
    }


@pytest.fixture(scope="function")
def multi_tenant_setup(
    engine: Engine,
    session: Session,
    auth_user_factory,
    account_factory,
    system_under_test_factory,
):
    """Create two separate tenant accounts for isolation testing.

    Returns:
        dict with keys:
            - tenant1: {user_id, account_id, sut_id}
            - tenant2: {user_id, account_id, sut_id}
    """
    # Tenant 1
    user1_id = auth_user_factory()
    account1_id = account_factory(owner_user_id=user1_id)
    sut1_id = system_under_test_factory(account_id=account1_id, owner_user_id=user1_id)

    # Tenant 2
    user2_id = auth_user_factory()
    account2_id = account_factory(owner_user_id=user2_id)
    sut2_id = system_under_test_factory(account_id=account2_id, owner_user_id=user2_id)

    return {
        "tenant1": {
            "user_id": user1_id,
            "account_id": account1_id,
            "sut_id": sut1_id,
        },
        "tenant2": {
            "user_id": user2_id,
            "account_id": account2_id,
            "sut_id": sut2_id,
        },
    }


@pytest.fixture(scope="function")
def test_suite_with_cases(
    engine: Engine,
    session: Session,
    auth_user_factory,
    account_factory,
    system_under_test_factory,
    suite_factory,
    test_case_factory,
    suite_test_case_association_factory,
):
    """Create a suite with multiple test cases.

    Returns:
        dict with keys:
            - user_id, account_id, sut_id, suite_id
            - test_case_ids: list of test case IDs
    """
    # Setup context
    user_id = auth_user_factory()
    account_id = account_factory(owner_user_id=user_id)
    sut_id = system_under_test_factory(account_id=account_id, owner_user_id=user_id)
    suite_id = suite_factory(
        name="Regression Suite",
        account_id=account_id,
        sut_id=sut_id,
        owner_user_id=user_id,
    )

    # Create test cases
    test_case_ids = []
    test_names = ["Login Test", "Logout Test", "Profile Update Test"]

    for idx, name in enumerate(test_names):
        tc_id = test_case_factory(
            name=name,
            account_id=account_id,
            sut_id=sut_id,
            owner_user_id=user_id,
        )
        test_case_ids.append(tc_id)

        # Link to suite
        add_test_case_to_suite(
            suite_id=suite_id,
            test_case_id=tc_id,
            execution_order=idx + 1,
            engine=engine,
        )

    return {
        "user_id": user_id,
        "account_id": account_id,
        "sut_id": sut_id,
        "suite_id": suite_id,
        "test_case_ids": test_case_ids,
    }


@pytest.fixture(scope="function")
def plan_with_suites(
    engine: Engine,
    session: Session,
    auth_user_factory,
    account_factory,
    system_under_test_factory,
    plan_factory,
    suite_factory,
    plan_suite_association_factory,
):
    """Create a plan with multiple suites.

    Returns:
        dict with keys:
            - user_id, account_id, sut_id, plan_id
            - suite_ids: list of suite IDs
    """
    # Setup context
    user_id = auth_user_factory()
    account_id = account_factory(owner_user_id=user_id)
    sut_id = system_under_test_factory(account_id=account_id, owner_user_id=user_id)
    plan_id = plan_factory(name="Sprint 1 Test Plan", owner_user_id=user_id)

    # Create suites
    suite_ids = []
    suite_names = ["Smoke Tests", "Regression Tests", "Performance Tests"]

    for idx, name in enumerate(suite_names):
        suite_id = suite_factory(
            name=name,
            account_id=account_id,
            sut_id=sut_id,
            owner_user_id=user_id,
        )
        suite_ids.append(suite_id)

        # Link to plan
        add_suite_to_plan(
            plan_id=plan_id,
            suite_id=suite_id,
            execution_order=idx + 1,
            engine=engine,
        )

    return {
        "user_id": user_id,
        "account_id": account_id,
        "sut_id": sut_id,
        "plan_id": plan_id,
        "suite_ids": suite_ids,
    }


@pytest.fixture(scope="function")
def tagged_entities(
    engine: Engine,
    session: Session,
    auth_user_factory,
    account_factory,
    system_under_test_factory,
    suite_factory,
    test_case_factory,
    entity_tag_factory,
):
    """Create entities with tags for testing tag-based queries.

    Returns:
        dict with keys:
            - user_id, account_id, sut_id
            - smoke_suite_id (tagged: "smoke", "critical")
            - regression_suite_id (tagged: "regression")
            - api_test_id (tagged: "api", "smoke")
            - ui_test_id (tagged: "ui")
    """
    # Setup context
    user_id = auth_user_factory()
    account_id = account_factory(owner_user_id=user_id)
    sut_id = system_under_test_factory(account_id=account_id, owner_user_id=user_id)

    # Create and tag smoke suite
    smoke_suite_id = suite_factory(
        name="Smoke Tests",
        account_id=account_id,
        sut_id=sut_id,
        owner_user_id=user_id,
    )
    entity_tag_factory(
        entity_type="suite",
        entity_id=smoke_suite_id,
        tag_name="smoke",
        tag_category="test-type",
        account_id=account_id,
        created_by_user_id=user_id,
    )
    entity_tag_factory(
        entity_type="suite",
        entity_id=smoke_suite_id,
        tag_name="critical",
        tag_category="priority",
        account_id=account_id,
        created_by_user_id=user_id,
    )

    # Create and tag regression suite
    regression_suite_id = suite_factory(
        name="Regression Tests",
        account_id=account_id,
        sut_id=sut_id,
        owner_user_id=user_id,
    )
    entity_tag_factory(
        entity_type="suite",
        entity_id=regression_suite_id,
        tag_name="regression",
        tag_category="test-type",
        account_id=account_id,
        created_by_user_id=user_id,
    )

    # Create and tag test cases
    api_test_id = test_case_factory(
        name="API Login Test",
        account_id=account_id,
        sut_id=sut_id,
        owner_user_id=user_id,
    )
    entity_tag_factory(
        entity_type="test_case",
        entity_id=api_test_id,
        tag_name="api",
        tag_category="layer",
        account_id=account_id,
        created_by_user_id=user_id,
    )
    entity_tag_factory(
        entity_type="test_case",
        entity_id=api_test_id,
        tag_name="smoke",
        tag_category="test-type",
        account_id=account_id,
        created_by_user_id=user_id,
    )

    ui_test_id = test_case_factory(
        name="UI Profile Test",
        account_id=account_id,
        sut_id=sut_id,
        owner_user_id=user_id,
    )
    entity_tag_factory(
        entity_type="test_case",
        entity_id=ui_test_id,
        tag_name="ui",
        tag_category="layer",
        account_id=account_id,
        created_by_user_id=user_id,
    )

    return {
        "user_id": user_id,
        "account_id": account_id,
        "sut_id": sut_id,
        "smoke_suite_id": smoke_suite_id,
        "regression_suite_id": regression_suite_id,
        "api_test_id": api_test_id,
        "ui_test_id": ui_test_id,
    }
