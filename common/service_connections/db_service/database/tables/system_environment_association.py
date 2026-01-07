"""
System environment association table for linking systems to environments.
"""

from datetime import datetime, timezone
from uuid import uuid4

import sqlalchemy as sql
from sqlalchemy.orm import Mapped, mapped_column

from common.service_connections.db_service.database.base import Base


class SystemEnvironmentAssociation(Base):
    """Association table linking systems under test to environments.

    Business Logic Documentation:

    1. Define at a high level what this table is suppose to represent in terms of a goal
       or goals that need to be accomplished by a user?
       - Links systems under test to multiple environments (QA, Staging, Production).
         Enables testing the same system across different environments with environment-
         specific configurations, users, and test data.

    2. What level of user should be interacting with this table?
       - System Owner: Create and manage system-environment relationships
       - Admin: Full CRUD access
       - Test Automation Framework: Read access to determine test targets

    3. What are the names of the tables that are either above or below this table in the
       data structure? This is to understand where to put in in a architecture diagram.
       - Above: SystemUnderTestTable (via sut_id), EnvironmentTable (via environment_id)
       - Below: None (association table - no children)

    4. Should a record in this table be deleted based on the deletion of a record in a
       different table? If so, what table?
       - Yes. CASCADE delete when either SystemUnderTestTable or EnvironmentTable is
         deleted (enforced by foreign key constraints ondelete='CASCADE').

    5. Will this table be require a connection a secure cloud provider service?
       - No direct cloud connection required.
    """

    __tablename__ = "system_environment_association"

    association_id: Mapped[str] = mapped_column(
        sql.String(36), primary_key=True, default=lambda: str(uuid4())
    )
    sut_id: Mapped[str] = mapped_column(
        sql.String(36),
        sql.ForeignKey("system_under_test.sut_id", ondelete="CASCADE"),
        nullable=False,
    )
    environment_id: Mapped[str] = mapped_column(
        sql.String(36),
        sql.ForeignKey("environment.environment_id", ondelete="CASCADE"),
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(sql.Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        sql.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    __table_args__ = (
        sql.UniqueConstraint("sut_id", "environment_id", name="uq_system_environment"),
        sql.Index("idx_system_env_system", "sut_id"),
        sql.Index("idx_system_env_environment", "environment_id"),
    )

    def __repr__(self) -> str:
        return f"<SystemEnvironmentAssociation(sut_id='{self.sut_id}', environment_id='{self.environment_id}')>"


__all__ = ["SystemEnvironmentAssociation"]
