"""
Test case table model for individual test definitions.
"""

from datetime import datetime, timezone
from typing import Optional, List, TYPE_CHECKING
from uuid import uuid4

import sqlalchemy as sql
from sqlalchemy.orm import Mapped, mapped_column, relationship

from common.service_connections.db_service.database.base import Base

if TYPE_CHECKING:
    from common.service_connections.db_service.database.tables.suite import (
        SuiteTable,
    )


class TestCaseTable(Base):
    """Test case table for defining individual test cases.

    Business Logic Documentation:

    1. Define at a high level what this table is suppose to represent in terms of a goal
       or goals that need to be accomplished by a user?
       - Defines individual test cases with specific test types (functional, integration,
         regression, smoke, performance, security). Enables granular test management and
         reusability across multiple test suites, supporting comprehensive test coverage
         and flexible test organization.

    2. What level of user should be interacting with this table?
       - Test Engineers: Primary users - create and manage test cases
       - Test Lead/Admin: Full CRUD access
       - Test Automation Framework: Read access during test execution
       - Regular Users: Read access to view test definitions

    3. What are the names of the tables that are either above or below this table in the
       data structure? This is to understand where to put in in a architecture diagram.
       - Above: SystemUnderTestTable (via sut_id), AccountTable (via account_id)
       - Below: SuiteTable (via many-to-many), action tables (future - test steps)

    4. Should a record in this table be deleted based on the deletion of a record in a
       different table? If so, what table?
       - Soft delete when SystemUnderTestTable or AccountTable is deactivated
         (application logic cascade). Hard CASCADE delete not recommended - preserve
         for historical test execution records.

    5. Will this table be require a connection a secure cloud provider service?
       - No direct cloud connection required. Future: could integrate with test
         management tools (Azure Test Plans, TestRail) for synchronization.
    """

    __tablename__ = "test_case"

    test_case_id: Mapped[str] = mapped_column(
        sql.String(36), primary_key=True, default=lambda: str(uuid4())
    )
    test_name: Mapped[str] = mapped_column(sql.String(255), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(sql.Text, nullable=True)
    test_type: Mapped[str] = mapped_column(
        sql.String(64), nullable=False, default="functional"
    )
    sut_id: Mapped[str] = mapped_column(
        sql.String(36),
        sql.ForeignKey("system_under_test.sut_id", ondelete="CASCADE"),
        nullable=False,
    )
    owner_user_id: Mapped[str] = mapped_column(
        sql.String(36),
        sql.ForeignKey("auth_users.auth_user_id", ondelete="RESTRICT"),
        nullable=False,
    )
    account_id: Mapped[str] = mapped_column(
        sql.String(36),
        sql.ForeignKey("account.account_id", ondelete="CASCADE"),
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(sql.Boolean, nullable=False, default=True)
    deactivated_at: Mapped[Optional[datetime]] = mapped_column(
        sql.DateTime, nullable=True
    )
    deactivated_by_user_id: Mapped[Optional[str]] = mapped_column(
        sql.String(36),
        sql.ForeignKey("auth_users.auth_user_id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        sql.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        sql.DateTime,
        nullable=True,
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    suites: Mapped[List["SuiteTable"]] = relationship(
        "SuiteTable",
        secondary="suite_test_case_association",
        back_populates="test_cases",
    )

    __table_args__ = (
        sql.Index("idx_testcase_pk", "test_case_id", postgresql_using="btree"),
        sql.Index("idx_testcase_sut", "sut_id"),
        sql.Index("idx_testcase_account", "account_id"),
        sql.Index("idx_testcase_type", "test_type"),
        sql.Index(
            "idx_testcase_active",
            "is_active",
            postgresql_where=sql.text("is_active = true"),
        ),
    )

    def __repr__(self) -> str:
        return f"<TestCase(id={self.test_case_id}, name='{self.test_name}', type='{self.test_type}')>"


__all__ = ["TestCaseTable"]
