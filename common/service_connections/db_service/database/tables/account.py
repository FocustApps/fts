"""
Account table model for managing accounts.
"""


from datetime import datetime, timezone
from typing import Optional
import sqlalchemy as sql
from sqlalchemy.orm import Mapped, mapped_column

from common.service_connections.db_service.database.base import Base

class AccountTable(Base):
    """Account model representing user accounts."""

    __tablename__ = "account"

    account_id: Mapped[str] = mapped_column(sql.String(36), primary_key=True)
    account_name: Mapped[str] = mapped_column(sql.String(255), unique=True, nullable=False)
    owner_email: Mapped[str] = mapped_column(sql.String(255), nullable=False)
    owner_user_id: Mapped[str] = mapped_column(sql.String(36), unique=True)
    is_active: Mapped[bool] = mapped_column(sql.Boolean, default=True, nullable=False)
    logo_url: Mapped[Optional[str]] = mapped_column(sql.String(512))
    primary_contact: Mapped[Optional[str]] = mapped_column(sql.String(36))
    subscription_id: Mapped[Optional[str]] = mapped_column(sql.String(36))
    created_at: Mapped[datetime] = mapped_column(
        sql.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(sql.DateTime, nullable=True)

    def __repr__(self) -> str:
        return f"<Account(id={self.account_id}, name='{self.account_name}', \
        owner_email='{self.owner_email}')>"