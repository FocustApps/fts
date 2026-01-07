"""
Identifier table model for page element locators.
"""

from datetime import datetime, timezone
from typing import Optional, TYPE_CHECKING

import sqlalchemy as sql
from sqlalchemy.orm import Mapped, mapped_column, relationship

from common.service_connections.db_service.database.base import Base

if TYPE_CHECKING:
    from common.service_connections.db_service.database.tables.action_tables.user_interface_action.page import (
        PageTable,
    )


class IdentifierTable(Base):
    """Identifier model representing page element locators.

    Business Logic Documentation:

    1. Define at a high level what this table is suppose to represent in terms of a goal
       or goals that need to be accomplished by a user?
       - Stores Selenium locators (XPath, CSS, ID, etc.) for web page elements. Enables
         centralized management of UI element identifiers, reducing test maintenance when
         UI changes occur. Associates elements with specific actions and environments.

    2. What level of user should be interacting with this table?
       - Test Automation Engineers: Primary users - create and update element locators
       - Admin: Full CRUD access
       - Test Automation Framework: Read access to retrieve locators during test execution

    3. What are the names of the tables that are either above or below this table in the
       data structure? This is to understand where to put in in a architecture diagram.
       - Above: PageTable (via page_id foreign key with CASCADE delete)
       - Below: None (leaf node in hierarchy)

    4. Should a record in this table be deleted based on the deletion of a record in a
       different table? If so, what table?
       - Yes. CASCADE delete when parent PageTable record is deleted (enforced by
         foreign key constraint ondelete='CASCADE' and SQLAlchemy cascade='all, delete-orphan').

    5. Will this table be require a connection a secure cloud provider service?
       - No direct cloud connection required.
    """

    __tablename__ = "identifier"

    identifier_id: Mapped[int] = mapped_column(sql.Integer, primary_key=True)
    page_id: Mapped[int] = mapped_column(
        sql.Integer, sql.ForeignKey("page.page_id", ondelete="CASCADE"), nullable=False
    )
    element_name: Mapped[str] = mapped_column(sql.String(96), unique=True, nullable=False)
    locator_strategy: Mapped[str] = mapped_column(sql.String(96), nullable=False)
    locator_query: Mapped[str] = mapped_column(sql.String(96), nullable=False)
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

    # Many-to-one relationship with page
    page: Mapped["PageTable"] = relationship("PageTable", back_populates="identifiers")

    __table_args__ = (
        sql.Index("idx_identifier_pk", "identifier_id"),
        sql.Index("idx_identifier_page", "page_id"),
        sql.Index(
            "idx_identifier_active",
            "is_active",
            postgresql_where=sql.text("is_active = true"),
        ),
    )

    def __repr__(self) -> str:
        return f"<Identifier(id={self.identifier_id}, element='{self.element_name}', page_id={self.page_id})>"


__all__ = ["IdentifierTable"]
