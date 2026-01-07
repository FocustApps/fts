"""
Environment table model for deployment environments.
"""

from datetime import datetime, timezone
from typing import List, Optional

import sqlalchemy as sql
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import JSONB

from common.service_connections.db_service.database.base import Base


class EnvironmentTable(Base):
    """Environment model representing deployment environments.

    Business Logic Documentation:

    1. Define at a high level what this table is suppose to represent in terms of a goal
       or goals that need to be accomplished by a user?
       - Represents test environments (dev, staging, production) for systems under test.
         Stores environment URLs, status, and associated test users. Enables automated
         testing across multiple deployment environments.

    2. What level of user should be interacting with this table?
       - Admin/Super Admin: Full CRUD access to create and manage environments
       - Regular Users: Read access to view available test environments
       - Test Automation: Read access during test execution

    3. What are the names of the tables that are either above or below this table in the
       data structure? This is to understand where to put in in a architecture diagram.
       - Above: SystemUnderTestTable (environments are part of systems)
       - Below: SystemUnderTestUserTable (users belong to environments), PageTable (pages
         tracked per environment), IdentifierTable (elements tracked per environment)

    4. Should a record in this table be deleted based on the deletion of a record in a
       different table? If so, what table?
       - Yes. Should be deleted when parent SystemUnderTestTable record is deleted
         (if that relationship is formalized).

    5. Will this table be require a connection a secure cloud provider service?
       - No direct connection, but environment URLs may point to cloud-hosted applications.
    """

    __tablename__ = "environment"

    environment_id: Mapped[str] = mapped_column(
        sql.String(36), unique=True, primary_key=True
    )
    environment_name: Mapped[str] = mapped_column(
        sql.String(96), unique=True, nullable=False
    )
    environment_designation: Mapped[str] = mapped_column(sql.String(80), nullable=False)
    environment_base_url: Mapped[str] = mapped_column(sql.String(512), nullable=False)
    api_base_url: Mapped[Optional[str]] = mapped_column(sql.String(1024))
    environment_status: Mapped[str] = mapped_column(sql.String(96), nullable=False)
    users_in_environment: Mapped[List] = mapped_column(JSONB, default=list)
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
    updated_at: Mapped[Optional[datetime]] = mapped_column(sql.DateTime, nullable=True)

    __table_args__ = (
        sql.Index("idx_environment_pk", "environment_id", postgresql_using="btree"),
        sql.Index(
            "idx_environment_active",
            "is_active",
            postgresql_where=sql.text("is_active = true"),
        ),
    )

    def __repr__(self) -> str:
        return f"<Environment(id={self.environment_id}, name='{self.environment_name}', designation='{self.environment_designation}')>"


__all__ = ["EnvironmentTable"]
