"""
System under test table model for managing tested systems.
"""

from datetime import datetime, timezone
from typing import Optional, List, TYPE_CHECKING
from uuid import uuid4

import sqlalchemy as sql
from sqlalchemy.orm import Mapped, mapped_column, relationship

from common.service_connections.db_service.database.base import Base

if TYPE_CHECKING:
    from common.service_connections.db_service.database.tables.environment import (
        EnvironmentTable,
    )
    from common.service_connections.db_service.database.tables.environment_user import (
        TestEnvUserAccountsTable,
    )
    from common.service_connections.db_service.database.tables.action_tables.user_interface_action.page import (
        PageTable,
    )


class SystemUnderTestTable(Base):
    """System Under Test table representing systems being tested.

    Business Logic Documentation:

    1. Define at a high level what this table is suppose to represent in terms of a goal
       or goals that need to be accomplished by a user?
       - Represents complete application systems under test, encompassing multiple code
         repositories (frontend, backend, mobile) and environments (QA, Staging, Production).
         Enables centralized management of test resources, documentation, and relationships
         to pages, users, and environments for comprehensive test coverage.

    2. What level of user should be interacting with this table?
       - System Owner: Full CRUD access to their owned systems
       - Account Owner: Full access to all systems in their account
       - Super Admin: Full access to all systems
       - Regular Users: Read access to assigned systems

    3. What are the names of the tables that are either above or below this table in the
       data structure? This is to understand where to put in in a architecture diagram.
       - Above: AccountTable (via account_id for multi-tenant isolation)
       - Below: EnvironmentTable (via many-to-many), SystemUnderTestUserTable (one-to-many),
                PageTable (one-to-many), SuiteTable, TestCaseTable, ActionTables

    4. Should a record in this table be deleted based on the deletion of a record in a
       different table? If so, what table?
       - Soft delete when AccountTable is deactivated (application logic cascade).
         Hard CASCADE delete from AccountTable not recommended - preserve for audit.
         Child entities (environments, pages, users) should CASCADE when system deleted.

    5. Will this table be require a connection a secure cloud provider service?
       - Optional. wiki_url may reference cloud-hosted documentation. Future: repository
         integration with GitHub/GitLab/Azure DevOps for automated context gathering.
    """

    __tablename__ = "system_under_test"

    sut_id: Mapped[str] = mapped_column(
        sql.String(36), primary_key=True, default=lambda: str(uuid4())
    )
    system_name: Mapped[str] = mapped_column(sql.String(96), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(sql.Text, nullable=True)
    wiki_url: Mapped[Optional[str]] = mapped_column(sql.String(1024), nullable=True)
    account_id: Mapped[str] = mapped_column(
        sql.String(36),
        sql.ForeignKey("account.account_id", ondelete="CASCADE"),
        nullable=False,
    )
    owner_user_id: Mapped[str] = mapped_column(
        sql.String(36),
        sql.ForeignKey("auth_users.auth_user_id", ondelete="CASCADE"),
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
    environments: Mapped[List["EnvironmentTable"]] = relationship(
        "EnvironmentTable",
        secondary="system_environment_association",
        back_populates="systems",
    )
    users: Mapped[List["TestEnvUserAccountsTable"]] = relationship(
        "TestEnvUserAccountsTable",
        back_populates="system",
        cascade="all, delete-orphan",
    )
    # TODO: Re-enable after page table migration is fixed
    # pages: Mapped[List["PageTable"]] = relationship(
    #     "PageTable",
    #     back_populates="system",
    #     cascade="all, delete-orphan",
    # )

    __table_args__ = (
        sql.Index("idx_sut_pk", "sut_id", postgresql_using="btree"),
        sql.Index("idx_sut_account", "account_id"),
        sql.Index(
            "idx_sut_active", "is_active", postgresql_where=sql.text("is_active = true")
        ),
    )

    def __repr__(self) -> str:
        return f"<SystemUnderTest(id={self.sut_id}, name='{self.system_name}', account_id='{self.account_id}')>"


__all__ = ["SystemUnderTestTable"]
