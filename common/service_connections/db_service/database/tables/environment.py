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
    """Environment model representing deployment environments."""

    __tablename__ = "environment"

    environment_id: Mapped[str] = mapped_column(
        sql.String(36), unique=True, primary_key=True
    )
    environment_name: Mapped[str] = mapped_column(sql.String(96), unique=True, nullable=False)
    environment_designation: Mapped[str] = mapped_column(sql.String(80), nullable=False)
    environment_base_url: Mapped[str] = mapped_column(sql.String(512), nullable=False)
    api_base_url: Mapped[Optional[str]] = mapped_column(sql.String(1024))
    environment_status: Mapped[str] = mapped_column(sql.String(96), nullable=False)
    users_in_environment: Mapped[List] = mapped_column(JSONB, default=list)
    created_at: Mapped[datetime] = mapped_column(
        sql.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(sql.DateTime, nullable=True)

    def __repr__(self) -> str:
        return f"<Environment(id={self.environment_id}, name='{self.environment_name}', designation='{self.environment_designation}')>"

__all__ = ["EnvironmentTable"]
