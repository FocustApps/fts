"""
Identifier table model for page element locators.
"""

from datetime import datetime, timezone
from typing import List, Optional, TYPE_CHECKING

import sqlalchemy as sql
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB

from common.service_connections.db_service.database.base import Base

if TYPE_CHECKING:
    from common.service_connections.db_service.database.tables.action_tables.user_interface_action.page import (
        PageTable,
    )


class IdentifierTable(Base):
    """Identifier model representing page element locators."""

    __tablename__ = "identifier"

    id: Mapped[int] = mapped_column(sql.Integer, primary_key=True)
    page_id: Mapped[int] = mapped_column(
        sql.Integer, sql.ForeignKey("page.id", ondelete="CASCADE"), nullable=False
    )
    element_name: Mapped[str] = mapped_column(sql.String(96), unique=True, nullable=False)
    locator_strategy: Mapped[str] = mapped_column(sql.String(96), nullable=False)
    locator_query: Mapped[str] = mapped_column(sql.String(96), nullable=False)
    action: Mapped[Optional[str]] = mapped_column(sql.String(96), nullable=True)
    environments: Mapped[List] = mapped_column(JSONB, default=list)
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

    def __repr__(self) -> str:
        return f"<Identifier(id={self.id}, element='{self.element_name}', page_id={self.page_id}, action='{self.action}')>"


__all__ = ["IdentifierTable"]
