"""
Plan suite association table for linking test plans to test suites.
"""

from datetime import datetime, timezone
from uuid import uuid4

import sqlalchemy as sql
from sqlalchemy.orm import Mapped, mapped_column

from common.service_connections.db_service.database.base import Base


class PlanSuiteAssociation(Base):
    """Association table linking test plans to test suites with execution order.

    Business Logic Documentation:

    1. Define at a high level what this table is suppose to represent in terms of a goal
       or goals that need to be accomplished by a user?
       - Defines test execution plans by linking plans to multiple suites with execution
         order. Replaces the suites_ids string field in PlanTable with proper many-to-many
         relationship enabling ordered test campaign execution.

    2. What level of user should be interacting with this table?
       - Test Lead/Admin: Create and manage test plan compositions
       - Test Automation Framework: Read access to execute plans in sequence
       - Regular Users: Read access to view plan structure

    3. What are the names of the tables that are either above or below this table in the
       data structure? This is to understand where to put in in a architecture diagram.
       - Above: PlanTable (via plan_id), SuiteTable (via suite_id)
       - Below: None (association table - no children)

    4. Should a record in this table be deleted based on the deletion of a record in a
       different table? If so, what table?
       - Yes. CASCADE delete when either PlanTable or SuiteTable is deleted
         (enforced by foreign key constraints ondelete='CASCADE').

    5. Will this table be require a connection a secure cloud provider service?
       - No direct cloud connection required.
    """

    __tablename__ = "plan_suite_association"

    association_id: Mapped[str] = mapped_column(
        sql.String(36), primary_key=True, default=lambda: str(uuid4())
    )
    plan_id: Mapped[str] = mapped_column(
        sql.String(36),
        sql.ForeignKey("plan.plan_id", ondelete="CASCADE"),
        nullable=False,
    )
    suite_id: Mapped[str] = mapped_column(
        sql.String(36),
        sql.ForeignKey("suite.suite_id", ondelete="CASCADE"),
        nullable=False,
    )
    execution_order: Mapped[int] = mapped_column(sql.Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(sql.Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        sql.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    __table_args__ = (
        sql.Index("idx_plan_suite_plan", "plan_id"),
        sql.Index("idx_plan_suite_suite", "suite_id"),
        sql.Index("idx_plan_suite_order", "plan_id", "execution_order"),
    )

    def __repr__(self) -> str:
        return f"<PlanSuiteAssociation(plan_id='{self.plan_id}', suite_id='{self.suite_id}', order={self.execution_order})>"


__all__ = ["PlanSuiteAssociation"]
