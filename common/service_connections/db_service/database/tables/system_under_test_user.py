"""
User table model for test users.
"""

from datetime import datetime, timezone
from typing import Optional, TYPE_CHECKING

import sqlalchemy as sql
from sqlalchemy.orm import Mapped, mapped_column, relationship

from common.service_connections.db_service.database.base import Base

if TYPE_CHECKING:
    from common.service_connections.db_service.database.tables.system_under_test import (
        SystemUnderTestTable,
    )


class SystemUnderTestUserTable(Base):
    """SystemUnderTestUser model representing test users for different environments.

    Business Logic Documentation:

    1. Define at a high level what this table is suppose to represent in terms of a goal
       or goals that need to be accomplished by a user?
       - Stores test user credentials for automated testing across different environments.
         Supports both direct password storage and secure secret provider integration
         (AWS Secrets Manager, Azure Key Vault) for sensitive credential management.

    2. What level of user should be interacting with this table?
       - Admin/Super Admin: Full CRUD access to manage test users
       - Test Automation Framework: Read access to retrieve credentials during test execution
       - Regular Users: No direct access (credentials managed by admins)

    3. What are the names of the tables that are either above or below this table in the
       data structure? This is to understand where to put in in a architecture diagram.
       - Above: EnvironmentTable (via environment_id foreign key)
       - Below: None (leaf node in hierarchy)

    4. Should a record in this table be deleted based on the deletion of a record in a
       different table? If so, what table?
       - Yes. CASCADE delete when parent EnvironmentTable record is deleted
         (enforced by foreign key constraint ondelete='CASCADE').

    5. Will this table be require a connection a secure cloud provider service?
       - Yes, when secret_provider is configured (AWS Secrets Manager, Azure Key Vault).
         The secret_url and secret_name fields reference cloud-stored credentials.
    """

    __tablename__ = "user"

    sut_user_id: Mapped[int] = mapped_column(sql.Integer, primary_key=True)
    account_id: Mapped[Optional[str]] = mapped_column(
        sql.String(36), sql.ForeignKey("account.account_id"), nullable=True
    )
    sut_id: Mapped[str] = mapped_column(
        sql.String(36),
        sql.ForeignKey("system_under_test.sut_id", ondelete="CASCADE"),
        nullable=False,
    )
    username: Mapped[str] = mapped_column(sql.String(96), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(sql.String(96), nullable=False)
    password: Mapped[Optional[str]] = mapped_column(sql.String(96), nullable=True)
    secret_provider: Mapped[Optional[str]] = mapped_column(sql.String(96), nullable=True)
    secret_url: Mapped[Optional[str]] = mapped_column(sql.String(1024), nullable=True)
    secret_name: Mapped[Optional[str]] = mapped_column(sql.String(1024), nullable=True)
    environment_id: Mapped[int] = mapped_column(
        sql.Integer,
        sql.ForeignKey("environment.environment_id", ondelete="CASCADE"),
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
        sql.DateTime, nullable=False, default=datetime.now(timezone.utc)
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(sql.DateTime)

    # Relationships
    system: Mapped["SystemUnderTestTable"] = relationship(
        "SystemUnderTestTable",
        back_populates="users",
    )

    __table_args__ = (
        sql.Index("idx_sut_user_pk", "sut_user_id"),
        sql.Index("idx_sut_user_account", "account_id"),
        sql.Index("idx_sut_user_sut", "sut_id"),
        sql.Index("idx_sut_user_environment", "environment_id"),
        sql.Index(
            "idx_sut_user_active",
            "is_active",
            postgresql_where=sql.text("is_active = true"),
        ),
    )

    def __repr__(self) -> str:
        return f"<User(id={self.sut_user_id}, username='{self.username}', email='{self.email}')>"


__all__ = ["SystemUnderTestUserTable"]
