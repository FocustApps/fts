"""Test database schema is properly created."""

import pytest
from uuid import uuid4
from datetime import datetime, timezone
from common.service_connections.db_service.db_manager import DB_ENGINE
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text


@pytest.fixture(scope="class")
def session():
    """Create a database session factory."""
    Session = sessionmaker(bind=DB_ENGINE)
    return Session


@pytest.mark.usefixtures("session")
class TestDatabaseSchema:
    """Test database schema creation."""

    def test_system_under_test_insertion(
        self, session, auth_user_factory, account_factory
    ):
        """Test inserting a record into system_under_test table."""
        # Use factories to create prerequisite records
        user_id = auth_user_factory()
        account_id = account_factory(owner_user_id=user_id)

        # Create system_under_test using raw SQL to test schema directly
        with session() as db_session:
            sut_id = str(uuid4())
            db_session.execute(
                text(
                    """
                INSERT INTO system_under_test 
                (sut_id, system_name, description, account_id, owner_user_id, is_active, created_at, updated_at)
                VALUES (:sut_id, :system_name, :description, :account_id, :owner_user_id, :is_active, :created_at, :updated_at)
                """
                ),
                {
                    "sut_id": sut_id,
                    "system_name": f"Test System {sut_id[:8]}",
                    "description": "Test system under test",
                    "account_id": account_id,
                    "owner_user_id": user_id,
                    "is_active": True,
                    "created_at": datetime.now(timezone.utc),
                    "updated_at": datetime.now(timezone.utc),
                },
            )
            db_session.commit()

            # Verify the record was created
            result = db_session.execute(
                text(
                    "SELECT sut_id, system_name FROM system_under_test WHERE sut_id = :sut_id"
                ),
                {"sut_id": sut_id},
            ).fetchone()

            assert result is not None
            assert result[0] == sut_id
            assert result[1] == f"Test System {sut_id[:8]}"

            # Cleanup
            db_session.execute(
                text("DELETE FROM system_under_test WHERE sut_id = :sut_id"),
                {"sut_id": sut_id},
            )
            db_session.execute(
                text("DELETE FROM account WHERE account_id = :account_id"),
                {"account_id": account_id},
            )
            db_session.execute(
                text("DELETE FROM auth_users WHERE auth_user_id = :auth_user_id"),
                {"auth_user_id": user_id},
            )
            db_session.commit()
