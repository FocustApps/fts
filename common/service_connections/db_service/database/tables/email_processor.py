"""
Email processor table model for email automation tasks.
"""

from datetime import datetime, timezone
from typing import List, Optional

import sqlalchemy as sql
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import JSONB

from common.service_connections.db_service.database.base import Base


class EmailProcessorTable(Base):
    """Email processor model for handling email automation tasks."""

    __tablename__ = "emailProcessorTable"

    email_processor_id: Mapped[int] = mapped_column(sql.Integer, primary_key=True)
    email_item_id: Mapped[int] = mapped_column(sql.Integer, unique=True, nullable=False)
    multi_item_email_ids: Mapped[Optional[List]] = mapped_column(JSONB)
    multi_email_flag: Mapped[bool] = mapped_column(sql.Boolean, default=False)
    multi_attachment_flag: Mapped[bool] = mapped_column(sql.Boolean, default=False)
    system: Mapped[Optional[str]] = mapped_column(sql.String(96))
    test_name: Mapped[Optional[str]] = mapped_column(sql.String(255))
    requires_processing: Mapped[bool] = mapped_column(sql.Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        sql.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(sql.DateTime, nullable=True)
    last_processed_at: Mapped[Optional[datetime]] = mapped_column(
        sql.DateTime, nullable=True
    )

    def __repr__(self) -> str:
        return f"<EmailProcessor(id={self.email_processor_id}, \
        email_item_id={self.email_item_id}, system='{self.system}')>"


__all__ = ["EmailProcessorTable"]
