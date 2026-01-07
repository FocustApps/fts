"""
Action chain table model for sequential action execution.
"""

from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

import sqlalchemy as sql
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import JSONB

from common.service_connections.db_service.database.base import Base


class ActionChainTable(Base):
    """Action chain table for sequential action execution workflows.

    Business Logic Documentation:

    1. Define at a high level what this table is suppose to represent in terms of a goal
       or goals that need to be accomplished by a user?
       - Defines sequences of actions (API, UI, database, infrastructure) to be executed
         in order for complex test workflows. Enables reusable action sequences that can
         be composed into larger test scenarios, supporting modular test design and
         maintenance efficiency.

       JSON structure for action_steps:
       [
           {
               "step_name": "Step 1",
               "action_type": "api_action",
               "action_id": "action_uuid_1",
               "depends_on": [],
               "parallel": false
           },
           {
               "step_name": "Step 2a",
               "action_type": "repository_action",
               "action_id": "action_uuid_2",
               "depends_on": ["Step 1"],
               "parallel": true
           }
       ]

    2. What level of user should be interacting with this table?
       - Test Automation Engineers: Primary users - create and manage action chains
       - Test Lead/Admin: Full CRUD access
       - Test Automation Framework: Read access during test execution
       - Regular Users: Read access to view workflow definitions

    3. What are the names of the tables that are either above or below this table in the
       data structure? This is to understand where to put in in a architecture diagram.
       - Above: SystemUnderTestTable (via sut_id), AccountTable (via account_id)
       - Below: Action tables (api_action, ui_action, database_action) referenced in
                action_steps JSONB

    4. Should a record in this table be deleted based on the deletion of a record in a
       different table? If so, what table?
       - Soft delete when SystemUnderTestTable or AccountTable is deactivated
         (application logic cascade). Hard CASCADE delete not recommended - preserve
         for historical test execution records.

    5. Will this table be require a connection a secure cloud provider service?
       - No direct cloud connection required. Action execution may trigger cloud
         operations via referenced infrastructure actions.
    """

    __tablename__ = "action_chain"

    action_chain_id: Mapped[str] = mapped_column(
        sql.String(36), primary_key=True, default=lambda: str(uuid4())
    )
    chain_name: Mapped[str] = mapped_column(sql.String(255), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(sql.Text, nullable=True)
    action_steps: Mapped[dict] = mapped_column(JSONB, nullable=False, default=list)
    sut_id: Mapped[str] = mapped_column(
        sql.String(36),
        sql.ForeignKey("system_under_test.sut_id", ondelete="CASCADE"),
        nullable=False,
    )
    account_id: Mapped[str] = mapped_column(
        sql.String(36),
        sql.ForeignKey("account.account_id", ondelete="CASCADE"),
        nullable=False,
    )
    owner_user_id: Mapped[str] = mapped_column(
        sql.String(36),
        sql.ForeignKey("auth_users.auth_user_id", ondelete="RESTRICT"),
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

    __table_args__ = (
        sql.Index("idx_actionchain_pk", "action_chain_id", postgresql_using="btree"),
        sql.Index("idx_actionchain_sut", "sut_id"),
        sql.Index("idx_actionchain_account", "account_id"),
        sql.Index(
            "idx_actionchain_active",
            "is_active",
            postgresql_where=sql.text("is_active = true"),
        ),
    )

    def __repr__(self) -> str:
        return f"<ActionChain(id={self.action_chain_id}, name='{self.chain_name}', sut_id='{self.sut_id}')>"


__all__ = ["ActionChainTable"]
