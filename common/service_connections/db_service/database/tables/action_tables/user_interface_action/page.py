"""
Page table model for web pages in Selenium automation.
"""

from datetime import datetime, timezone
from typing import Dict, List, TYPE_CHECKING

import sqlalchemy as sql
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB

from common.service_connections.db_service.database.base import Base

if TYPE_CHECKING:
    from common.service_connections.db_service.database.tables.action_tables.user_interface_action.identifier import (
        IdentifierTable,
    )


class PageTable(Base):
    """Page model representing web pages for Selenium automation."""

    __tablename__ = "page"

    id: Mapped[int] = mapped_column(sql.Integer, primary_key=True)
    page_name: Mapped[str] = mapped_column(sql.String(96), unique=True, nullable=False)
    page_url: Mapped[str] = mapped_column(sql.String(1024), nullable=False)
    environments: Mapped[Dict] = mapped_column(JSONB, nullable=False)
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

    def __repr__(self) -> str:
        return f"<Page(id={self.id}, name='{self.page_name}', url='{self.page_url}')>"


__all__ = ["PageTable"]
