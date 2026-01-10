"""
Tests for SystemUnderTest, TestCase, and Suite models with multi-tenant isolation.

Tests cover:
- CRUD operations
- Multi-tenant queries
- Soft delete operations
- Validation with environment variable controls
"""

import os

from sqlalchemy.engine import Engine

from common.service_connections.db_service.database.engine import (
    get_database_session as session,
)
from common.service_connections.db_service.models.system_under_test_model import (
    deactivate_system_under_test_by_id as deactivate_system_under_test,
    insert_system_under_test,
    query_system_under_test_by_id,
    query_systems_under_test_by_account,
    reactivate_system_under_test_by_id as reactivate_system_under_test,
    SystemUnderTestModel,
    update_system_under_test_by_id as update_system_under_test,
)
from common.service_connections.db_service.models.test_case_model import (
    insert_test_case,
    query_test_case_by_id,
    query_test_cases_by_sut,
    query_test_cases_by_type,
    TestCaseModel,
)
from common.service_connections.db_service.models.suite_model import (
    insert_suite,
    query_suite_by_id,
    query_suites_by_account,
    SuiteModel,
)


class TestSystemUnderTestCRUD:
    """Test SystemUnderTest CRUD operations."""

    def test_insert_and_query_system(
        self, account_factory, auth_user_factory, engine: Engine
    ):
        """Test inserting and querying a system under test."""
        # Arrange
        user_id = auth_user_factory()
        account_id = account_factory(owner_user_id=user_id, name="Test Account for SUT")

        sut_model = SystemUnderTestModel(
            system_name="Production Web App",
            account_id=account_id,
            owner_user_id=user_id,
        )

        # Act
        result = insert_system_under_test(sut_model, session, engine)

        # Assert
        assert result is not None
        assert result.sut_id is not None

        # Query back
        with session(engine) as db_session:
            retrieved = query_system_under_test_by_id(result.sut_id, db_session, engine)

        assert retrieved is not None
        assert retrieved.system_name == "Production Web App"
        assert retrieved.account_id == account_id
        assert retrieved.is_active is True

    def test_query_systems_by_account(
        self,
        system_under_test_factory,
        account_factory,
        auth_user_factory,
        engine: Engine,
    ):
        """Test querying systems by account ID."""
        # Arrange
        owner_id = auth_user_factory()
        account1 = account_factory(owner_user_id=owner_id, name="Account 1")
        account2 = account_factory(owner_user_id=owner_id, name="Account 2")

        sut1 = system_under_test_factory(
            account_id=account1, owner_user_id=owner_id, name="SUT 1"
        )
        sut2 = system_under_test_factory(
            account_id=account1, owner_user_id=owner_id, name="SUT 2"
        )
        sut3 = system_under_test_factory(
            account_id=account2, owner_user_id=owner_id, name="SUT 3"
        )

        # Act
        with session(engine) as db_session:
            account1_systems = query_systems_under_test_by_account(
                account1, db_session, engine
            )

        # Assert
        assert len(account1_systems) == 2
        system_names = {s.system_name for s in account1_systems}
        assert "SUT 1" in system_names
        assert "SUT 2" in system_names
        assert "SUT 3" not in system_names  # Different account

    def test_deactivate_and_reactivate_system(
        self,
        system_under_test_factory,
        account_factory,
        auth_user_factory,
        engine: Engine,
    ):
        """Test soft delete and reactivation."""
        # Arrange
        owner_id = auth_user_factory()
        account_id = account_factory(owner_user_id=owner_id)
        sut_id = system_under_test_factory(account_id=account_id, owner_user_id=owner_id)
        deactivated_by = auth_user_factory()

        # Act - Deactivate
        result = deactivate_system_under_test(sut_id, deactivated_by, engine)

        # Assert deactivated
        assert result is True
        with session(engine) as db_session:
            sut = query_system_under_test_by_id(sut_id, db_session, engine)
        assert sut.is_active is False
        assert sut.deactivated_by_user_id == deactivated_by
        assert sut.deactivated_at is not None

        # Act - Reactivate
        result = reactivate_system_under_test(sut_id, engine)

        # Assert reactivated
        assert result is True
        with session(engine) as db_session:
            sut = query_system_under_test_by_id(sut_id, db_session, engine)
        assert sut.is_active is True
        assert sut.deactivated_at is None
        assert sut.deactivated_by_user_id is None

    def test_update_system(
        self,
        system_under_test_factory,
        account_factory,
        auth_user_factory,
        engine: Engine,
    ):
        """Test updating system fields."""
        # Arrange
        owner_id = auth_user_factory()
        account_id = account_factory(owner_user_id=owner_id)
        sut_id = system_under_test_factory(
            account_id=account_id, owner_user_id=owner_id, name="Original Name"
        )

        # Act
        updates = SystemUnderTestModel(
            system_name="Updated Name",
            account_id=account_id,
            owner_user_id=owner_id,
        )
        result = update_system_under_test(sut_id, updates, engine)

        # Assert
        assert result is True
        with session(engine) as db_session:
            sut = query_system_under_test_by_id(sut_id, db_session, engine)
        assert sut.system_name == "Updated Name"


class TestTestCaseCRUD:
    """Test TestCase CRUD operations with enum validation."""

    def test_insert_test_case_with_valid_type(
        self,
        test_case_factory,
        system_under_test_factory,
        account_factory,
        auth_user_factory,
        engine: Engine,
    ):
        """Test inserting test case with valid test_type enum."""
        # Arrange
        owner_id = auth_user_factory()
        account_id = account_factory(owner_user_id=owner_id)
        sut_id = system_under_test_factory(account_id=account_id, owner_user_id=owner_id)

        test_case_model = TestCaseModel(
            test_name="Login Test",
            test_type="functional",
            account_id=account_id,
            sut_id=sut_id,
            owner_user_id=owner_id,
        )

        # Act
        test_case_id = insert_test_case(test_case_model, engine)

        # Assert
        with session(engine) as db_session:
            retrieved = query_test_case_by_id(test_case_id, db_session, engine)
        assert retrieved.test_type == "functional"

    def test_query_test_cases_by_type(
        self,
        test_case_factory,
        system_under_test_factory,
        account_factory,
        auth_user_factory,
        engine: Engine,
    ):
        """Test filtering test cases by type."""
        # Arrange
        owner_id = auth_user_factory()
        account_id = account_factory(owner_user_id=owner_id)
        sut_id = system_under_test_factory(account_id=account_id, owner_user_id=owner_id)

        tc1 = test_case_factory(
            account_id=account_id,
            sut_id=sut_id,
            owner_user_id=owner_id,
            name="Func Test",
            test_type="functional",
        )
        tc2 = test_case_factory(
            account_id=account_id,
            sut_id=sut_id,
            owner_user_id=owner_id,
            name="Perf Test",
            test_type="performance",
        )
        tc3 = test_case_factory(
            account_id=account_id,
            sut_id=sut_id,
            owner_user_id=owner_id,
            name="Smoke Test",
            test_type="smoke",
        )

        # Act
        with session(engine) as db_session:
            functional_tests = query_test_cases_by_type(
                "functional", account_id, db_session, engine
            )

        # Assert
        assert len(functional_tests) == 1
        assert functional_tests[0].test_name == "Func Test"

    def test_query_test_cases_by_sut(
        self,
        test_case_factory,
        system_under_test_factory,
        account_factory,
        auth_user_factory,
        engine: Engine,
    ):
        """Test querying test cases for a specific system."""
        # Arrange
        owner_id = auth_user_factory()
        account_id = account_factory(owner_user_id=owner_id)
        sut1 = system_under_test_factory(
            account_id=account_id, owner_user_id=owner_id, name="Web App"
        )
        sut2 = system_under_test_factory(
            account_id=account_id, owner_user_id=owner_id, name="Mobile App"
        )

        tc1 = test_case_factory(
            account_id=account_id, sut_id=sut1, owner_user_id=owner_id, name="Web Test 1"
        )
        tc2 = test_case_factory(
            account_id=account_id, sut_id=sut1, owner_user_id=owner_id, name="Web Test 2"
        )
        tc3 = test_case_factory(
            account_id=account_id, sut_id=sut2, owner_user_id=owner_id, name="Mobile Test"
        )

        # Act
        with session(engine) as db_session:
            web_tests = query_test_cases_by_sut(sut1, db_session, engine)

        # Assert
        assert len(web_tests) == 2
        test_names = {t.test_name for t in web_tests}
        assert "Web Test 1" in test_names
        assert "Mobile Test" not in test_names


class TestSuiteCRUD:
    """Test Suite CRUD operations."""

    def test_insert_and_query_suite(
        self,
        suite_factory,
        system_under_test_factory,
        account_factory,
        auth_user_factory,
        engine: Engine,
    ):
        """Test creating and retrieving a suite."""
        # Arrange
        owner_id = auth_user_factory()
        account_id = account_factory(owner_user_id=owner_id)
        sut_id = system_under_test_factory(account_id=account_id, owner_user_id=owner_id)

        suite_model = SuiteModel(
            suite_name="Regression Suite",
            description="Full regression test suite",
            sut_id=sut_id,
            account_id=account_id,
            owner_user_id=owner_id,
        )

        # Act
        suite_id = insert_suite(suite_model, engine)

        # Assert
        with session(engine) as db_session:
            retrieved = query_suite_by_id(suite_id, db_session, engine)
        assert retrieved.suite_name == "Regression Suite"
        assert retrieved.description == "Full regression test suite"

    def test_query_suites_by_account_multi_tenant(
        self,
        suite_factory,
        system_under_test_factory,
        account_factory,
        auth_user_factory,
        engine: Engine,
    ):
        """Test multi-tenant isolation for suites."""
        # Arrange
        owner_id = auth_user_factory()
        account1 = account_factory(owner_user_id=owner_id, name="Company A")
        account2 = account_factory(owner_user_id=owner_id, name="Company B")
        sut1 = system_under_test_factory(account_id=account1, owner_user_id=owner_id)
        sut2 = system_under_test_factory(account_id=account2, owner_user_id=owner_id)

        suite1 = suite_factory(
            account_id=account1,
            sut_id=sut1,
            owner_user_id=owner_id,
            name="Company A Suite 1",
        )
        suite2 = suite_factory(
            account_id=account1,
            sut_id=sut1,
            owner_user_id=owner_id,
            name="Company A Suite 2",
        )
        suite3 = suite_factory(
            account_id=account2,
            sut_id=sut2,
            owner_user_id=owner_id,
            name="Company B Suite",
        )

        # Act
        with session(engine) as db_session:
            account1_suites = query_suites_by_account(account1, db_session, engine)

        # Assert
        assert len(account1_suites) == 2
        suite_names = {s.suite_name for s in account1_suites}
        assert "Company B Suite" not in suite_names


class TestValidationConfiguration:
    """Test validation environment variable controls."""

    def test_validation_config_reads_environment(self):
        """Test that validation config respects environment variables."""
        # Arrange - Set environment variable
        original_write = os.environ.get("FTS_VALIDATE_WRITES")
        os.environ["FTS_VALIDATE_WRITES"] = "0"

        try:
            # Act
            from common.config import should_validate_write

            result = should_validate_write()

            # Assert
            assert result is False  # Validation disabled
        finally:
            # Cleanup
            if original_write is not None:
                os.environ["FTS_VALIDATE_WRITES"] = original_write
            else:
                os.environ.pop("FTS_VALIDATE_WRITES", None)

    def test_bulk_insert_with_validation_disabled(
        self,
        account_factory,
        auth_user_factory,
        system_under_test_factory,
        engine: Engine,
    ):
        """Test bulk insert performance with validation disabled."""
        # Arrange
        owner_id = auth_user_factory()
        account_id = account_factory(owner_user_id=owner_id)
        sut_id = system_under_test_factory(account_id=account_id, owner_user_id=owner_id)

        # Set environment to disable write validation
        original_write = os.environ.get("FTS_VALIDATE_WRITES")
        os.environ["FTS_VALIDATE_WRITES"] = "0"

        try:
            # Act - Bulk insert test cases
            test_cases = []
            for i in range(10):
                tc_model = TestCaseModel(
                    test_name=f"Bulk Test {i}",
                    test_type="functional",
                    account_id=account_id,
                    sut_id=sut_id,
                    owner_user_id=owner_id,
                )
                tc_id = insert_test_case(tc_model, engine)
                test_cases.append(tc_id)

            # Assert
            assert len(test_cases) == 10

        finally:
            # Cleanup
            if original_write is not None:
                os.environ["FTS_VALIDATE_WRITES"] = original_write
            else:
                os.environ.pop("FTS_VALIDATE_WRITES", None)
