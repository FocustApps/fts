"""
Database model fixtures for pytest testing with synthetic data.

Provides factory fixtures for all database models with:
- Threading-safe counter for unique synthetic data
- Function scope for test isolation
- Explicit fixture dependencies
- Automatic cleanup with rollback
- Configurable validation bypass for bulk operations
"""

import threading
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

import pytest
from sqlalchemy.engine import Engine

from common.service_connections.db_service.database import session
from common.service_connections.db_service.database.tables.account import AccountTable
from common.service_connections.db_service.database.tables.action_chain import (
    ActionChainTable,
)
from common.service_connections.db_service.database.tables.audit_log import (
    AuditLogTable,
)
from common.service_connections.db_service.database.tables.entity_tag import (
    EntityTagTable,
)
from common.service_connections.db_service.database.tables.plan import PlanTable
from common.service_connections.db_service.database.tables.plan_suite_association import (
    PlanSuiteAssociation,
)
from common.service_connections.db_service.database.tables.purge_table import (
    PurgeTable,
)
from common.service_connections.db_service.database.tables.suite import SuiteTable
from common.service_connections.db_service.database.tables.suite_test_case_association import (
    SuiteTestCaseAssociation,
)
from common.service_connections.db_service.database.tables.system_under_test import (
    SystemUnderTestTable,
)
from common.service_connections.db_service.database.tables.test_case import (
    TestCaseTable,
)


# Thread-safe counter for unique fixture data
_fixture_counter = 0
_fixture_lock = threading.Lock()


def _get_fixture_counter() -> int:
    """Get next fixture counter value in thread-safe manner."""
    global _fixture_counter
    with _fixture_lock:
        _fixture_counter += 1
        return _fixture_counter


# ============================================================================
# Core Entity Fixtures
# ============================================================================


@pytest.fixture(scope="function")
def account_factory(engine: Engine):
    """Factory fixture for creating account records with synthetic data.

    Usage:
        def test_something(account_factory):
            account_id = account_factory()
            account_id2 = account_factory(name="Custom Account Name")

    Args:
        engine: Database engine from test configuration

    Yields:
        Factory function(name: Optional[str] = None) -> str (account_id)

    Cleanup:
        Rolls back all account creations after test
    """
    created_account_ids = []

    def _create_account(name: Optional[str] = None) -> str:
        """Create account with synthetic data."""
        counter = _get_fixture_counter()

        with session(engine) as db_session:
            account = AccountTable(
                account_id=str(uuid4()),
                account_name=name or f"Test Account {counter:03d}",
                is_active=True,
                created_at=datetime.now(timezone.utc),
            )
            db_session.add(account)
            db_session.commit()
            created_account_ids.append(account.account_id)
            return account.account_id

    yield _create_account

    # Cleanup: Delete all created accounts
    with session(engine) as db_session:
        for account_id in created_account_ids:
            account = db_session.get(AccountTable, account_id)
            if account:
                db_session.delete(account)
        db_session.commit()


@pytest.fixture(scope="function")
def system_under_test_factory(engine: Engine, account_factory):
    """Factory fixture for creating SystemUnderTest records.

    Usage:
        def test_something(system_under_test_factory, account_factory):
            account_id = account_factory()
            sut_id = system_under_test_factory(account_id=account_id)

    Dependencies:
        account_factory: Creates account for multi-tenant association

    Yields:
        Factory function(account_id: str, name: Optional[str] = None, ...) -> str (sut_id)
    """
    created_sut_ids = []

    def _create_sut(
        account_id: str,
        name: Optional[str] = None,
        system_type: str = "web_application",
        owner_user_id: Optional[str] = None,
    ) -> str:
        """Create SystemUnderTest with synthetic data."""
        counter = _get_fixture_counter()

        with session(engine) as db_session:
            sut = SystemUnderTestTable(
                sut_id=str(uuid4()),
                system_name=name or f"Test System {counter:03d}",
                system_type=system_type,
                account_id=account_id,
                owner_user_id=owner_user_id,
                is_active=True,
                created_at=datetime.now(timezone.utc),
            )
            db_session.add(sut)
            db_session.commit()
            created_sut_ids.append(sut.sut_id)
            return sut.sut_id

    yield _create_sut

    # Cleanup: Cascade delete handles most cleanup, but ensure explicit delete
    with session(engine) as db_session:
        for sut_id in created_sut_ids:
            sut = db_session.get(SystemUnderTestTable, sut_id)
            if sut:
                db_session.delete(sut)
        db_session.commit()


@pytest.fixture(scope="function")
def test_case_factory(engine: Engine, system_under_test_factory, account_factory):
    """Factory fixture for creating TestCase records.

    Usage:
        def test_something(test_case_factory, system_under_test_factory, account_factory):
            account_id = account_factory()
            sut_id = system_under_test_factory(account_id=account_id)
            test_case_id = test_case_factory(account_id=account_id, sut_id=sut_id)

    Dependencies:
        account_factory, system_under_test_factory

    Yields:
        Factory function(...) -> str (test_case_id)
    """
    created_test_case_ids = []

    def _create_test_case(
        account_id: str,
        sut_id: str,
        name: Optional[str] = None,
        test_type: str = "functional",
        created_by_user_id: Optional[str] = None,
    ) -> str:
        """Create TestCase with synthetic data."""
        counter = _get_fixture_counter()

        with session(engine) as db_session:
            test_case = TestCaseTable(
                test_case_id=str(uuid4()),
                test_case_name=name or f"Test Case {counter:03d}",
                test_type=test_type,
                account_id=account_id,
                sut_id=sut_id,
                created_by_user_id=created_by_user_id or str(uuid4()),
                is_active=True,
                created_at=datetime.now(timezone.utc),
            )
            db_session.add(test_case)
            db_session.commit()
            created_test_case_ids.append(test_case.test_case_id)
            return test_case.test_case_id

    yield _create_test_case

    # Cleanup
    with session(engine) as db_session:
        for test_case_id in created_test_case_ids:
            test_case = db_session.get(TestCaseTable, test_case_id)
            if test_case:
                db_session.delete(test_case)
        db_session.commit()


@pytest.fixture(scope="function")
def suite_factory(engine: Engine, account_factory):
    """Factory fixture for creating Suite records.

    Yields:
        Factory function(...) -> str (suite_id)
    """
    created_suite_ids = []

    def _create_suite(
        account_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        created_by_user_id: Optional[str] = None,
    ) -> str:
        """Create Suite with synthetic data."""
        counter = _get_fixture_counter()

        with session(engine) as db_session:
            suite = SuiteTable(
                suite_id=str(uuid4()),
                suite_name=name or f"Test Suite {counter:03d}",
                suite_description=description or f"Description for suite {counter:03d}",
                account_id=account_id,
                created_by_user_id=created_by_user_id or str(uuid4()),
                is_active=True,
                created_at=datetime.now(timezone.utc),
            )
            db_session.add(suite)
            db_session.commit()
            created_suite_ids.append(suite.suite_id)
            return suite.suite_id

    yield _create_suite

    # Cleanup
    with session(engine) as db_session:
        for suite_id in created_suite_ids:
            suite = db_session.get(SuiteTable, suite_id)
            if suite:
                db_session.delete(suite)
        db_session.commit()


@pytest.fixture(scope="function")
def plan_factory(engine: Engine, account_factory):
    """Factory fixture for creating Plan records.

    Yields:
        Factory function(...) -> str (plan_id)
    """
    created_plan_ids = []

    def _create_plan(
        account_id: str,
        name: Optional[str] = None,
        owner_user_id: Optional[str] = None,
        status: str = "active",
    ) -> str:
        """Create Plan with synthetic data."""
        counter = _get_fixture_counter()

        with session(engine) as db_session:
            plan = PlanTable(
                plan_id=str(uuid4()),
                plan_name=name or f"Test Plan {counter:03d}",
                suites_ids="",  # Legacy field - empty for new plans
                account_id=account_id,
                owner_user_id=owner_user_id,
                status=status,
                is_active=True,
                created_at=datetime.now(timezone.utc),
            )
            db_session.add(plan)
            db_session.commit()
            created_plan_ids.append(plan.plan_id)
            return plan.plan_id

    yield _create_plan

    # Cleanup
    with session(engine) as db_session:
        for plan_id in created_plan_ids:
            plan = db_session.get(PlanTable, plan_id)
            if plan:
                db_session.delete(plan)
        db_session.commit()


# ============================================================================
# Association Fixtures
# ============================================================================


@pytest.fixture(scope="function")
def suite_test_case_association_factory(engine: Engine):
    """Factory fixture for creating SuiteTestCaseAssociation records.

    Yields:
        Factory function(suite_id: str, test_case_id: str, ...) -> str (association_id)
    """
    created_association_ids = []

    def _create_association(
        suite_id: str, test_case_id: str, execution_order: int = 0
    ) -> str:
        """Create SuiteTestCaseAssociation."""
        with session(engine) as db_session:
            assoc = SuiteTestCaseAssociation(
                association_id=str(uuid4()),
                suite_id=suite_id,
                test_case_id=test_case_id,
                execution_order=execution_order,
                is_active=True,
                created_at=datetime.now(timezone.utc),
            )
            db_session.add(assoc)
            db_session.commit()
            created_association_ids.append(assoc.association_id)
            return assoc.association_id

    yield _create_association

    # Cleanup
    with session(engine) as db_session:
        for assoc_id in created_association_ids:
            assoc = db_session.get(SuiteTestCaseAssociation, assoc_id)
            if assoc:
                db_session.delete(assoc)
        db_session.commit()


@pytest.fixture(scope="function")
def plan_suite_association_factory(engine: Engine):
    """Factory fixture for creating PlanSuiteAssociation records.

    Yields:
        Factory function(plan_id: str, suite_id: str, ...) -> str (association_id)
    """
    created_association_ids = []

    def _create_association(plan_id: str, suite_id: str, execution_order: int = 0) -> str:
        """Create PlanSuiteAssociation."""
        with session(engine) as db_session:
            assoc = PlanSuiteAssociation(
                association_id=str(uuid4()),
                plan_id=plan_id,
                suite_id=suite_id,
                execution_order=execution_order,
                is_active=True,
                created_at=datetime.now(timezone.utc),
            )
            db_session.add(assoc)
            db_session.commit()
            created_association_ids.append(assoc.association_id)
            return assoc.association_id

    yield _create_association

    # Cleanup
    with session(engine) as db_session:
        for assoc_id in created_association_ids:
            assoc = db_session.get(PlanSuiteAssociation, assoc_id)
            if assoc:
                db_session.delete(assoc)
        db_session.commit()


# ============================================================================
# Advanced Entity Fixtures
# ============================================================================


@pytest.fixture(scope="function")
def action_chain_factory(engine: Engine, account_factory, system_under_test_factory):
    """Factory fixture for creating ActionChain records with JSONB steps.

    Yields:
        Factory function(...) -> str (action_chain_id)
    """
    created_chain_ids = []

    def _create_action_chain(
        account_id: str,
        sut_id: str,
        name: Optional[str] = None,
        action_steps: Optional[list] = None,
        created_by_user_id: Optional[str] = None,
    ) -> str:
        """Create ActionChain with synthetic data."""
        counter = _get_fixture_counter()

        with session(engine) as db_session:
            chain = ActionChainTable(
                action_chain_id=str(uuid4()),
                action_chain_name=name or f"Test Action Chain {counter:03d}",
                action_steps=action_steps or [],
                account_id=account_id,
                sut_id=sut_id,
                created_by_user_id=created_by_user_id or str(uuid4()),
                is_active=True,
                created_at=datetime.now(timezone.utc),
            )
            db_session.add(chain)
            db_session.commit()
            created_chain_ids.append(chain.action_chain_id)
            return chain.action_chain_id

    yield _create_action_chain

    # Cleanup
    with session(engine) as db_session:
        for chain_id in created_chain_ids:
            chain = db_session.get(ActionChainTable, chain_id)
            if chain:
                db_session.delete(chain)
        db_session.commit()


@pytest.fixture(scope="function")
def entity_tag_factory(engine: Engine, account_factory):
    """Factory fixture for creating EntityTag records (polymorphic).

    Yields:
        Factory function(...) -> str (tag_id)
    """
    created_tag_ids = []

    def _create_tag(
        entity_type: str,
        entity_id: str,
        tag_name: str,
        tag_category: str,
        account_id: str,
        created_by_user_id: Optional[str] = None,
        tag_value: Optional[str] = None,
    ) -> str:
        """Create EntityTag."""
        with session(engine) as db_session:
            tag = EntityTagTable(
                tag_id=str(uuid4()),
                entity_type=entity_type,
                entity_id=entity_id,
                tag_name=tag_name,
                tag_category=tag_category,
                tag_value=tag_value,
                account_id=account_id,
                created_by_user_id=created_by_user_id or str(uuid4()),
                is_active=True,
                created_at=datetime.now(timezone.utc),
            )
            db_session.add(tag)
            db_session.commit()
            created_tag_ids.append(tag.tag_id)
            return tag.tag_id

    yield _create_tag

    # Cleanup
    with session(engine) as db_session:
        for tag_id in created_tag_ids:
            tag = db_session.get(EntityTagTable, tag_id)
            if tag:
                db_session.delete(tag)
        db_session.commit()


# ============================================================================
# Admin/System Fixtures
# ============================================================================


@pytest.fixture(scope="function")
def audit_log_factory(engine: Engine):
    """Factory fixture for creating AuditLog records (INSERT-ONLY).

    NOTE: No cleanup - audit logs are immutable. Use test database isolation.

    Yields:
        Factory function(...) -> str (audit_id)
    """
    created_audit_ids = []

    def _create_audit_log(
        entity_type: str,
        entity_id: str,
        action: str,
        performed_by_user_id: Optional[str] = None,
        account_id: Optional[str] = None,
        is_sensitive: bool = False,
        details: Optional[dict] = None,
    ) -> str:
        """Create AuditLog (immutable)."""
        with session(engine) as db_session:
            audit = AuditLogTable(
                audit_id=str(uuid4()),
                entity_type=entity_type,
                entity_id=entity_id,
                action=action,
                performed_by_user_id=performed_by_user_id,
                account_id=account_id,
                timestamp=datetime.now(timezone.utc),
                details=details,
                is_sensitive=is_sensitive,
            )
            db_session.add(audit)
            db_session.commit()
            created_audit_ids.append(audit.audit_id)
            return audit.audit_id

    yield _create_audit_log

    # Audit logs are immutable - cleanup only in test database teardown


@pytest.fixture(scope="function")
def purge_schedule_factory(engine: Engine):
    """Factory fixture for creating PurgeTable records (admin-only).

    Yields:
        Factory function(...) -> str (purge_id)
    """
    created_purge_ids = []

    def _create_purge_schedule(table_name: str, purge_interval_days: int = 30) -> str:
        """Create PurgeTable schedule."""
        with session(engine) as db_session:
            purge = PurgeTable(
                purge_id=str(uuid4()),
                table_name=table_name,
                last_purged_at=datetime.now(timezone.utc),
                purge_interval_days=purge_interval_days,
                created_at=datetime.now(timezone.utc),
            )
            db_session.add(purge)
            db_session.commit()
            created_purge_ids.append(purge.purge_id)
            return purge.purge_id

    yield _create_purge_schedule

    # Cleanup
    with session(engine) as db_session:
        for purge_id in created_purge_ids:
            purge = db_session.get(PurgeTable, purge_id)
            if purge:
                db_session.delete(purge)
        db_session.commit()
