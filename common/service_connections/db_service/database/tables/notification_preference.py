"""
Notification preference table for storing user notification preferences.
"""

from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

import sqlalchemy as sql
from sqlalchemy.orm import Mapped, mapped_column

from common.service_connections.db_service.database.base import Base


class NotificationPreferenceTable(Base):
    """Notification preference table for user-specific notification settings.

    Business Logic Documentation:

    1. Define at a high level what this table is suppose to represent in terms of a goal
       or goals that need to be accomplished by a user?
       - Allows users to customize which types of notifications they receive and through
         which channels (email, in-app). Reduces notification fatigue by letting users
         opt-in/opt-out of specific notification types. Supports granular control over
         communication preferences while maintaining critical notifications.

    2. What level of user should be interacting with this table?
       - All authenticated users: Read and update their own preferences
       - Super Admin: Read all preferences for troubleshooting notification issues
       - System: Create default preferences on user creation, query for notification delivery

    3. What are the names of the tables that are either above or below this table in the
       data structure? This is to understand where to put in in a architecture diagram.
       - Above: AuthUserTable (via auth_user_id)
       - Below: None (stores user preferences, no children)

    4. Should a record in this table be deleted based on the deletion of a record in a
       different table? If so, what table?
       - Yes. CASCADE delete when AuthUserTable record is deleted (user account removal
         should delete their preferences). Enforced by foreign key ondelete='CASCADE'.

    5. Will this table be require a connection a secure cloud provider service?
       - No direct cloud connection required. Works with local database only.
    """

    __tablename__ = "notification_preference"

    preference_id: Mapped[str] = mapped_column(
        sql.String(36), primary_key=True, default=lambda: str(uuid4())
    )
    auth_user_id: Mapped[str] = mapped_column(
        sql.String(36),
        sql.ForeignKey("auth_users.auth_user_id", ondelete="CASCADE"),
        nullable=False,
        unique=True,  # One preference record per user
    )

    # Account membership notifications
    account_added_email: Mapped[bool] = mapped_column(
        sql.Boolean, nullable=False, default=True
    )
    account_added_in_app: Mapped[bool] = mapped_column(
        sql.Boolean, nullable=False, default=True
    )
    account_removed_email: Mapped[bool] = mapped_column(
        sql.Boolean, nullable=False, default=True
    )
    account_removed_in_app: Mapped[bool] = mapped_column(
        sql.Boolean, nullable=False, default=True
    )

    # Role change notifications
    role_changed_email: Mapped[bool] = mapped_column(
        sql.Boolean, nullable=False, default=True
    )
    role_changed_in_app: Mapped[bool] = mapped_column(
        sql.Boolean, nullable=False, default=True
    )

    # Primary account notifications
    primary_account_changed_email: Mapped[bool] = mapped_column(
        sql.Boolean, nullable=False, default=True
    )
    primary_account_changed_in_app: Mapped[bool] = mapped_column(
        sql.Boolean, nullable=False, default=True
    )

    # Bulk operation summary notifications
    bulk_operation_email: Mapped[bool] = mapped_column(
        sql.Boolean, nullable=False, default=True
    )
    bulk_operation_in_app: Mapped[bool] = mapped_column(
        sql.Boolean, nullable=False, default=False
    )

    # Account-level change notifications (account name, settings, etc.)
    account_updated_email: Mapped[bool] = mapped_column(
        sql.Boolean, nullable=False, default=False
    )
    account_updated_in_app: Mapped[bool] = mapped_column(
        sql.Boolean, nullable=False, default=True
    )

    # Metadata
    created_at: Mapped[datetime] = mapped_column(
        sql.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        sql.DateTime,
        nullable=True,
        onupdate=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (sql.Index("idx_notification_pref_user", "auth_user_id"),)

    def __repr__(self) -> str:
        return f"<NotificationPreferenceTable(user_id='{self.auth_user_id}')>"


__all__ = ["NotificationPreferenceTable"]
