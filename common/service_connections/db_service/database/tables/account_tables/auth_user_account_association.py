"""
Auth user account association table for many-to-many user-account relationships.
"""

from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

import sqlalchemy as sql
from sqlalchemy.orm import Mapped, mapped_column

from common.service_connections.db_service.database.base import Base


class AuthUserAccountAssociation(Base):
    """Association table linking users to accounts with role-based access.

    Business Logic Documentation:

    1. Define at a high level what this table is suppose to represent in terms of a goal
       or goals that need to be accomplished by a user?
       - Enables multi-tenant architecture where users can belong to multiple accounts
         with different roles (owner, admin, member, viewer). Replaces the account_ids
         string field in AuthUserTable with proper many-to-many relationship supporting
         role-based access control within each account.

    2. What level of user should be interacting with this table?
       - Account Owner: Can add/remove users and assign roles within their account
       - Super Admin: Full access to manage all user-account associations
       - System: Automated user invitation and role assignment processes

    3. What are the names of the tables that are either above or below this table in the
       data structure? This is to understand where to put in in a architecture diagram.
       - Above: AuthUserTable (via auth_user_id), AccountTable (via account_id)
       - Below: None (association table - no children)

    4. Should a record in this table be deleted based on the deletion of a record in a
       different table? If so, what table?
       - Yes. CASCADE delete when either AuthUserTable or AccountTable is deleted
         (enforced by foreign key constraints ondelete='CASCADE').

    5. Will this table be require a connection a secure cloud provider service?
       - No direct cloud connection required.
    """

    __tablename__ = "auth_user_account_association"

    association_id: Mapped[str] = mapped_column(
        sql.String(36), primary_key=True, default=lambda: str(uuid4())
    )
    auth_user_id: Mapped[str] = mapped_column(
        sql.String(36),
        sql.ForeignKey("auth_users.auth_user_id", ondelete="CASCADE"),
        nullable=False,
    )
    account_id: Mapped[str] = mapped_column(
        sql.String(36),
        sql.ForeignKey("account.account_id", ondelete="CASCADE"),
        nullable=False,
    )
    role: Mapped[str] = mapped_column(sql.String(64), nullable=False, default="member")
    is_primary: Mapped[bool] = mapped_column(sql.Boolean, nullable=False, default=False)
    is_active: Mapped[bool] = mapped_column(sql.Boolean, nullable=False, default=True)
    invited_by_user_id: Mapped[Optional[str]] = mapped_column(
        sql.String(36),
        sql.ForeignKey("auth_users.auth_user_id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        sql.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        sql.DateTime,
        nullable=True,
        onupdate=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        sql.UniqueConstraint("auth_user_id", "account_id", name="uq_user_account"),
        sql.Index("idx_user_account_user", "auth_user_id"),
        sql.Index("idx_user_account_account", "account_id"),
        sql.Index("idx_user_account_active", "is_active"),
    )

    def __repr__(self) -> str:
        return f"<AuthUserAccountAssociation(user_id='{self.auth_user_id}', account_id='{self.account_id}', role='{self.role}')>"


__all__ = ["AuthUserAccountAssociation"]
