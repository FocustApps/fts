"""
Suite test case association table for linking test suites to test cases.
"""

from datetime import datetime, timezone
from uuid import uuid4

import sqlalchemy as sql
from sqlalchemy.orm import Mapped, mapped_column

from common.service_connections.db_service.database.base import Base


class SuiteTestCaseAssociation(Base):
    """Association table linking test suites to test cases with execution order.

    Business Logic Documentation:

    1. Define at a high level what this table is suppose to represent in terms of a goal
       or goals that need to be accomplished by a user?
       - Organizes test cases into logical test suites with execution order. Enables
         grouping related tests together and controlling test execution sequence within
         each suite for comprehensive test coverage and efficient test runs.

    2. What level of user should be interacting with this table?
       - Test Engineers: Create and manage suite compositions
       - Test Automation Framework: Read access to execute suite tests in sequence
       - Admin: Full CRUD access to manage test organization

    3. What are the names of the tables that are either above or below this table in the
       data structure? This is to understand where to put in in a architecture diagram.
       - Above: SuiteTable (via suite_id), TestCaseTable (via test_case_id)
       - Below: None (association table - no children)

    4. Should a record in this table be deleted based on the deletion of a record in a
       different table? If so, what table?
       - Yes. CASCADE delete when either SuiteTable or TestCaseTable is deleted
         (enforced by foreign key constraints ondelete='CASCADE').

    5. Will this table be require a connection a secure cloud provider service?
       - No direct cloud connection required.
    """

    __tablename__ = "suite_test_case_association"

    association_id: Mapped[str] = mapped_column(
        sql.String(36), primary_key=True, default=lambda: str(uuid4())
    )
    suite_id: Mapped[str] = mapped_column(
        sql.String(36),
        sql.ForeignKey("suite.suite_id", ondelete="CASCADE"),
        nullable=False,
    )
    test_case_id: Mapped[str] = mapped_column(
        sql.String(36),
        sql.ForeignKey("test_case.test_case_id", ondelete="CASCADE"),
        nullable=False,
    )
    execution_order: Mapped[int] = mapped_column(sql.Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(sql.Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        sql.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    __table_args__ = (
        sql.Index("idx_suite_testcase_suite", "suite_id"),
        sql.Index("idx_suite_testcase_test", "test_case_id"),
        sql.Index("idx_suite_testcase_order", "suite_id", "execution_order"),
    )

    def __repr__(self) -> str:
        return f"<SuiteTestCaseAssociation(suite_id='{self.suite_id}', test_case_id='{self.test_case_id}', order={self.execution_order})>"


__all__ = ["SuiteTestCaseAssociation"]
