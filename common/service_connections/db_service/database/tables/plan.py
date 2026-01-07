"""
Docstring for common.service_connections.db_service.database.tables.plan_table
"""

from typing import Optional, List, TYPE_CHECKING
from common.service_connections.db_service.database.base import Base
from sqlalchemy import String as sqlString, DateTime as sqlDateTime, Enum as sqlEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime, timezone
import sqlalchemy as sql

if TYPE_CHECKING:
    from common.service_connections.db_service.database.tables.suite import (
        SuiteTable,
    )


class PlanTable(Base):
    """Test plan table for organizing and executing test suites.

    Business Logic Documentation:

    1. Define at a high level what this table is suppose to represent in terms of a goal
       or goals that need to be accomplished by a user?
       - Represents test execution plans that group multiple test suites together. Enables
         users to define test campaigns, tag suites for batch execution, and track test
         plan status (active/inactive).

    2. What level of user should be interacting with this table?
       - Admin/Test Lead: Primary users - create and manage test plans
       - Regular Users: Read access to view and execute assigned test plans
       - Test Automation: Read access to execute plans programmatically

    3. What are the names of the tables that are either above or below this table in the
       data structure? This is to understand where to put in in a architecture diagram.
       - Above: AccountTable (via owner_user_id, though not formally linked)
       - Below: Test suite tables (via test_suite_ids, if test suite table exists)

    4. Should a record in this table be deleted based on the deletion of a record in a
       different table? If so, what table?
       - Optional: Could be deleted or set inactive when owner_user_id user is deleted,
         but typically should be preserved for historical test execution records.

    5. Will this table be require a connection a secure cloud provider service?
       - No direct cloud connection required for the table itself.
    """

    __tablename__ = "plan"

    plan_id: Mapped[str] = mapped_column(sqlString(36), primary_key=True)
    plan_name: Mapped[str] = mapped_column(sqlString(255), nullable=False)
    suites_ids: Mapped[str] = mapped_column(
        sqlString(1024), nullable=False
    )  # DEPRECATED: Use suites relationship instead
    suite_tags: Mapped[Optional[str]] = mapped_column(sql.JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        sqlDateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(sqlDateTime, nullable=True)
    status: Mapped[str] = mapped_column(
        sqlEnum("active", "inactive", name="plan_status_enum"),
        nullable=False,
        default="active",
    )
    owner_user_id: Mapped[Optional[str]] = mapped_column(sql.Integer, nullable=True)
    account_id: Mapped[Optional[str]] = mapped_column(sql.String(36), nullable=True)
    is_active: Mapped[bool] = mapped_column(sql.Boolean, nullable=False, default=True)
    deactivated_at: Mapped[Optional[datetime]] = mapped_column(
        sql.DateTime, nullable=True
    )
    deactivated_by_user_id: Mapped[Optional[str]] = mapped_column(
        sql.String(36),
        sql.ForeignKey("auth_users.auth_user_id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    suites: Mapped[List["SuiteTable"]] = relationship(
        "SuiteTable",
        secondary="plan_suite_association",
        back_populates="plans",
    )

    __table_args__ = (
        sql.Index("idx_plan_pk", "plan_id"),
        sql.Index("idx_plan_account", "account_id"),
        sql.Index(
            "idx_plan_active", "is_active", postgresql_where=sql.text("is_active = true")
        ),
    )

    def __repr__(self) -> str:
        return f"<Plan(id={self.plan_id}, name='{self.plan_name}', status='{self.status}', active={self.is_active})>"


__all__ = ["PlanTable"]
