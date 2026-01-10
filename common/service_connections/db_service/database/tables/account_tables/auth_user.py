"""
Auth user table model for system access control.
"""

from datetime import datetime, timezone
from typing import Optional, List, TYPE_CHECKING
from uuid import uuid4

import sqlalchemy as sql
from sqlalchemy.orm import Mapped, mapped_column, relationship

from common.service_connections.db_service.database.base import Base

if TYPE_CHECKING:
    from common.service_connections.db_service.database.tables.account_tables.auth_token import (
        AuthTokenTable,
    )
    from common.service_connections.db_service.database.tables.account_tables.account import (
        AccountTable,
    )
    from common.service_connections.db_service.database.tables.account_tables.auth_user_account_association import (
        AuthUserAccountAssociation,
    )


class AuthUserTable(Base):
    """Authentication users table for JWT-based access control.

    Business Logic Documentation:

    1. Define at a high level what this table is suppose to represent in terms of a goal
       or goals that need to be accomplished by a user?
       - Manages authentication and authorization for users accessing the Fenrir platform.
         Handles JWT-based authentication with bcrypt password hashing, role-based access
         control (admin, super_admin), and multi-account user support.

    2. What level of user should be interacting with this table?
       - Super Admin: Full CRUD access
       - Admin: Create/Read/Update for non-admin users within their account
       - Regular Users: Read access to their own record only

    3. What are the names of the tables that are either above or below this table in the
       data structure? This is to understand where to put in in a architecture diagram.
       - Above: AccountTable (via account_ids relationship)
       - Below: AuthUserSubscriptionTable (via user_subscription_id)

    4. Should a record in this table be deleted based on the deletion of a record in a
       different table? If so, what table?
       - No direct cascade delete. Should be soft-deleted (is_active=False) when account
         is deleted, but record preserved for audit trails.

    5. Will this table be require a connection a secure cloud provider service?
       - No direct cloud connection, but authentication may integrate with external
         OAuth providers or SSO services in the future.
    """

    __tablename__ = "auth_users"

    auth_user_id: Mapped[str] = mapped_column(
        sql.String(36), primary_key=True, default=lambda: str(uuid4())
    )
    email: Mapped[str] = mapped_column(sql.String(255), unique=True, nullable=False)
    username: Mapped[Optional[str]] = mapped_column(sql.String(96))
    first_name: Mapped[Optional[str]] = mapped_column(sql.String(255))
    last_name: Mapped[Optional[str]] = mapped_column(sql.String(255))
    password_hash: Mapped[str] = mapped_column(sql.String(255), nullable=False)
    password_reset_token: Mapped[Optional[str]] = mapped_column(
        sql.String(64), unique=True, nullable=True
    )
    password_reset_expires: Mapped[Optional[datetime]] = mapped_column(sql.DateTime)
    is_active: Mapped[bool] = mapped_column(sql.Boolean, default=True, nullable=False)
    is_admin: Mapped[bool] = mapped_column(sql.Boolean, default=False, nullable=False)
    is_super_admin: Mapped[bool] = mapped_column(
        sql.Boolean, default=False, nullable=False
    )
    multi_account_user: Mapped[bool] = mapped_column(
        sql.Boolean, default=False, nullable=False
    )
    account_ids: Mapped[Optional[str]] = mapped_column(
        sql.String(1024)
    )  # DEPRECATED: Use accounts relationship via auth_user_account_association instead
    user_subscription_id: Mapped[Optional[str]] = mapped_column(sql.String(36))
    created_at: Mapped[datetime] = mapped_column(
        sql.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    last_login_at: Mapped[Optional[datetime]] = mapped_column(sql.DateTime)
    updated_at: Mapped[Optional[datetime]] = mapped_column(sql.DateTime, nullable=True)

    # Relationships
    tokens: Mapped[List["AuthTokenTable"]] = relationship(
        "AuthTokenTable",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    # TODO: Re-enable after auth_user_account_association table is created
    # accounts: Mapped[List["AccountTable"]] = relationship(
    #     "AccountTable",
    #     secondary="auth_user_account_association",
    #     back_populates="users",
    #     foreign_keys="[AuthUserAccountAssociation.auth_user_id, AuthUserAccountAssociation.account_id]",
    # )

    def __repr__(self) -> str:
        return f"<AuthUser(auth_user_id={self.auth_user_id}, email='{self.email}', is_active={self.is_active})>"

    def update_last_login(self) -> None:
        """Update the last login timestamp to now."""
        self.last_login_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)


__all__ = ["AuthUserTable"]
