"""
Fenrir Actions table model for SeleniumController method documentation.
"""

from datetime import datetime, timezone
from typing import TYPE_CHECKING

import sqlalchemy as sql
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import JSONB

from common.service_connections.db_service.database.base import Base

if TYPE_CHECKING:
    from common.service_connections.db_service.database.tables.action_tables.user_interface_action.page import (
        PageTable,
    )


class FenrirActionsTable(Base):
    """Fenrir Actions model representing SeleniumController method documentation.

    After I deploy my application this table will be used to dynamically load available
    SeleniumController methods along with their docstrings, parameters, and return types.

    Business Logic Documentation:

    1. Define at a high level what this table is suppose to represent in terms of a goal
       or goals that need to be accomplished by a user?
       - Stores comprehensive documentation for SeleniumController methods including
         method names, docstrings, parameters, type hints, and return types. Enables
         dynamic discovery of available Selenium automation capabilities and provides
         a centralized registry of frontend automation actions.

    2. What level of user should be interacting with this table?
       - Test Automation Engineers: Read access to discover available methods
       - Admin: Full CRUD access for maintaining method documentation
       - Test Automation Framework: Read access for dynamic method invocation

    3. What are the names of the tables that are either above or below this table in the
       data structure? This is to understand where to put in in a architecture diagram.
       - Above: None (root-level reference table)
       - Below: None (leaf node - no child relationships)
       - Peer: PageTable, IdentifierTable (used together in UI automation workflows)

    4. Should a record in this table be deleted based on the deletion of a record in a
       different table? If so, what table?
       - No. This is a reference table that maintains SeleniumController method
         documentation independently of other tables.

    5. Will this table be require a connection a secure cloud provider service?
       - No direct cloud connection required.
    """

    __tablename__ = "fenrir_actions"

    fenrir_action_id: Mapped[int] = mapped_column(sql.Integer, primary_key=True)
    method_name: Mapped[str] = mapped_column(sql.String(128), unique=True, nullable=False)
    docstring: Mapped[str] = mapped_column(sql.Text, nullable=False)
    parameters: Mapped[dict] = mapped_column(JSONB, nullable=True)
    return_type: Mapped[str] = mapped_column(sql.String(256), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        sql.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        sql.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # TODO: Re-enable after page_fenrir_action_association table is created
    # Many-to-many relationship with pages
    # pages: Mapped[List["PageTable"]] = relationship(
    #     "PageTable",
    #     secondary="page_fenrir_action_association",
    #     back_populates="fenrir_actions",
    # )

    def __repr__(self) -> str:
        return f"<FenrirAction(id={self.fenrir_action_id}, method='{self.method_name}', return_type='{self.return_type}')>"


__all__ = ["FenrirActionsTable"]
