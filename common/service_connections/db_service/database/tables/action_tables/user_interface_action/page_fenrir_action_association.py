"""
Page Fenrir action association table for linking pages to SeleniumController actions.
"""

from datetime import datetime, timezone
from uuid import uuid4

import sqlalchemy as sql
from sqlalchemy.orm import Mapped, mapped_column

from common.service_connections.db_service.database.base import Base


class PageFenrirActionAssociation(Base):
    """Association table linking pages to Fenrir actions with execution order.

    Business Logic Documentation:

    1. Define at a high level what this table is suppose to represent in terms of a goal
       or goals that need to be accomplished by a user?
       - Links web pages to SeleniumController automation methods (fenrir_actions) with
         ordered sequences. Enables pages to define which Selenium actions are available
         and in what order they should be executed for test workflows.

    2. What level of user should be interacting with this table?
       - Test Automation Engineers: Create and manage page-action relationships
       - Admin: Full CRUD access
       - Test Automation Framework: Read access during test execution

    3. What are the names of the tables that are either above or below this table in the
       data structure? This is to understand where to put in in a architecture diagram.
       - Above: PageTable (via page_id), FenrirActionsTable (via fenrir_action_id)
       - Below: None (association table - no children)

    4. Should a record in this table be deleted based on the deletion of a record in a
       different table? If so, what table?
       - Yes. CASCADE delete when either PageTable or FenrirActionsTable is deleted
         (enforced by foreign key constraints ondelete='CASCADE').

    5. Will this table be require a connection a secure cloud provider service?
       - No direct cloud connection required.
    """

    __tablename__ = "page_fenrir_action_association"

    association_id: Mapped[str] = mapped_column(
        sql.String(36), primary_key=True, default=lambda: str(uuid4())
    )
    page_id: Mapped[int] = mapped_column(
        sql.Integer,
        sql.ForeignKey("page.page_id", ondelete="CASCADE"),
        nullable=False,
    )
    fenrir_action_id: Mapped[int] = mapped_column(
        sql.Integer,
        sql.ForeignKey("fenrir_actions.fenrir_action_id", ondelete="CASCADE"),
        nullable=False,
    )
    action_order: Mapped[int] = mapped_column(sql.Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(sql.Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        sql.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    __table_args__ = (
        sql.Index("idx_page_action_page", "page_id"),
        sql.Index("idx_page_action_action", "fenrir_action_id"),
        sql.Index("idx_page_action_order", "page_id", "action_order"),
    )

    def __repr__(self) -> str:
        return f"<PageFenrirActionAssociation(page_id='{self.page_id}', action_id='{self.fenrir_action_id}', order={self.action_order})>"


__all__ = ["PageFenrirActionAssociation"]
