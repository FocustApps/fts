"""
User table model for test users.
"""

from datetime import datetime, timezone
from typing import Optional

import sqlalchemy as sql
from sqlalchemy.orm import Mapped, mapped_column

from common.service_connections.db_service.database.base import Base


class SystemUnderTestUserTable(Base):
    """SystemUnderTestUser model representing test users for different environments."""

    __tablename__ = "user"

    id: Mapped[int] = mapped_column(sql.Integer, primary_key=True)
    username: Mapped[str] = mapped_column(sql.String(96), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(sql.String(96), nullable=False)
    password: Mapped[Optional[str]] = mapped_column(sql.String(96))
    secret_provider: Mapped[Optional[str]] = mapped_column(sql.String(96))
    secret_url: Mapped[Optional[str]] = mapped_column(sql.String(1024))
    secret_name: Mapped[Optional[str]] = mapped_column(sql.String(1024))
    environment_id: Mapped[int] = mapped_column(
        sql.Integer, sql.ForeignKey("environment.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        sql.DateTime, nullable=False, default=datetime.now(timezone.utc)
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(sql.DateTime)

    def __repr__(self) -> str:
        return f"<User(id={self.id}, username='{self.username}', email='{self.email}')>"


__all__ = ["SystemUnderTestUserTable"]
