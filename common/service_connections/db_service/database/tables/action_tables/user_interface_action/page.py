"""
Page table model for web pages in Selenium automation.
"""

from datetime import datetime, timezone
from typing import Dict, List, Optional, TYPE_CHECKING

import sqlalchemy as sql
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB

from common.service_connections.db_service.database.base import Base
from common.service_connections.db_service.database.tables.action_tables.user_interface_action.fenrir_actions import (
    FenrirActionsTable,
)

if TYPE_CHECKING:
    from common.service_connections.db_service.database.tables.action_tables.user_interface_action.identifier import (
        IdentifierTable,
    )


class PageTable(Base):
    """Page model representing web pages for Selenium automation.

    Business Logic Documentation:

    1. Define at a high level what this table is suppose to represent in terms of a goal
       or goals that need to be accomplished by a user?
       - Represents web pages within systems under test for Selenium automation. Stores
         page metadata including URLs and environment-specific configurations. Serves as
         parent container for page element identifiers (locators).

    2. What level of user should be interacting with this table?
       - Test Automation Engineers: Primary users - create and manage page definitions
       - Admin: Full CRUD access
       - Test Automation Framework: Read access during test execution

    3. What are the names of the tables that are either above or below this table in the
       data structure? This is to understand where to put in in a architecture diagram.
       - Above: EnvironmentTable (pages are environment-specific via JSONB field)
       - Below: IdentifierTable (page elements via one-to-many relationship)

    4. Should a record in this table be deleted based on the deletion of a record in a
       different table? If so, what table?
       - Optional: Could be deleted when related EnvironmentTable records are all deleted,
         but typically preserved as page definitions may be reused across environments.

    5. Will this table be require a connection a secure cloud provider service?
       - No direct cloud connection required for the table itself. Page URLs may point
         to cloud-hosted applications.
    """

    __tablename__ = "page"

    page_id: Mapped[int] = mapped_column(sql.Integer, primary_key=True)
    page_name: Mapped[str] = mapped_column(sql.String(96), unique=True, nullable=False)
    page_url: Mapped[str] = mapped_column(sql.String(1024), nullable=False)
    environments: Mapped[Dict] = mapped_column(JSONB, nullable=False)
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
    updated_at: Mapped[datetime] = mapped_column(
        sql.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # One-to-many relationship with identifiers
    identifiers: Mapped[List["IdentifierTable"]] = relationship(
        "IdentifierTable", back_populates="page", cascade="all, delete-orphan"
    )
    fenrir_actions: Mapped[List["FenrirActionsTable"]] = relationship(
        "FenrirActionsTable",
        secondary="page_fenrir_action_association",
        back_populates="pages",
    )

    __table_args__ = (
        sql.Index("idx_page_pk", "page_id"),
        sql.Index(
            "idx_page_active", "is_active", postgresql_where=sql.text("is_active = true")
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<Page(id={self.page_id}, name='{self.page_name}', url='{self.page_url}')>"
        )


__all__ = ["PageTable"]
