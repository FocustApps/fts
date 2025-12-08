"""
Auth user table model for system access control.
"""

from datetime import datetime, timezone
from typing import Optional

import sqlalchemy as sql
from sqlalchemy.orm import Mapped, mapped_column

from common.service_connections.db_service.database.base import Base


class AuthUserTable(Base):
    """Authentication users table for system access control."""

    __tablename__ = "auth_users"

    auth_user_id: Mapped[int] = mapped_column(sql.Integer, primary_key=True)
    auth_user_email: Mapped[str] = mapped_column(sql.String(255), unique=True, nullable=False)
    auth_username: Mapped[Optional[str]] = mapped_column(sql.String(96))
    not_your_actual_name: Mapped[Optional[str]] = mapped_column(sql.String(255))
    current_auth_token: Mapped[Optional[str]] = mapped_column(sql.String(64))
    token_expires_at: Mapped[Optional[datetime]] = mapped_column(sql.DateTime)
    is_active: Mapped[bool] = mapped_column(sql.Boolean, default=True, nullable=False)
    is_admin: Mapped[bool] = mapped_column(sql.Boolean, default=False, nullable=False)
    is_super_admin: Mapped[bool] = mapped_column(
        sql.Boolean, default=False, nullable=False
    )
    multi_account_user: Mapped[bool] = mapped_column(sql.Boolean, default=False, nullable=False)
    account_ids: Mapped[Optional[str]] = mapped_column(sql.String(1024))
    user_subscription_id: Mapped[Optional[str]] = mapped_column(sql.String(36))
    created_at: Mapped[datetime] = mapped_column(
        sql.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    last_login_at: Mapped[Optional[datetime]] = mapped_column(sql.DateTime)
    updated_at: Mapped[Optional[datetime]] = mapped_column(sql.DateTime, nullable=True)

    def __repr__(self) -> str:
        return (
            f"<AuthUser(id={self.auth_user_id}, email='{self.auth_user_email}', is_active={self.is_active})>"
        )

    def is_token_valid(self) -> bool:
        """Check if the current token is valid and not expired."""
        if not self.current_auth_token or not self.token_expires_at:
            return False
        return datetime.now(timezone.utc) < self.token_expires_at

    def update_last_login(self) -> None:
        """Update the last login timestamp to now."""
        self.last_login_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)


__all__ = ["AuthUserTable"]

