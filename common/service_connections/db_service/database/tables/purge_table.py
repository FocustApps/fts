"""
Docstring for common.service_connections.db_service.database.tables.purge_table
"""

from common.service_connections.db_service.database.base import Base
from sqlalchemy import String as sqlString, DateTime as sqlDateTime
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime, timezone
import sqlalchemy as sql


class PurgeTable(Base):
    """Purge table model for tracking purge operations."""

    __tablename__ = "purgeTable"

    purge_id: Mapped[str] = mapped_column(sqlString(36), primary_key=True)
    table_name: Mapped[str] = mapped_column(sqlString(255), nullable=False)
    last_purged_at: Mapped[datetime] = mapped_column(
        sqlDateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    created_at: Mapped[datetime] = mapped_column(
        sqlDateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(sqlDateTime, nullable=True)
    purge_interval_days: Mapped[int] = mapped_column(
        sql.Integer, nullable=False, default=30
    )

    def __repr__(self) -> str:
        return f"<PurgeTable(id={self.id}, table_name='{self.table_name}', last_purged_at={self.last_purged_at})>"
