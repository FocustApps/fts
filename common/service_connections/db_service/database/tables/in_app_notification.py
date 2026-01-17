"""
In-app notification table for storing user notifications.
"""

from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

import sqlalchemy as sql
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import JSONB

from common.service_connections.db_service.database.base import Base


class InAppNotificationTable(Base):
    """In-app notification table for user notifications displayed in the application.

    Business Logic Documentation:

    1. Define at a high level what this table is suppose to represent in terms of a goal
       or goals that need to be accomplished by a user?
       - Stores notifications that appear in the user's notification center within the
         application. Provides real-time (polling-based) awareness of account changes,
         role updates, and system events. Auto-purges after 30 days to maintain database
         performance. Supports read/unread tracking for better UX.

    2. What level of user should be interacting with this table?
       - All authenticated users: Read their own notifications, mark as read
       - Super Admin: Read all notifications for troubleshooting
       - System: Create notifications for user actions, auto-purge old notifications
       - No write access for regular users (notifications created by system only)

    3. What are the names of the tables that are either above or below this table in the
       data structure? This is to understand where to put in in a architecture diagram.
       - Above: AuthUserTable (via auth_user_id), AccountTable (via related_account_id)
       - Below: None (leaf node - stores notifications, no children)

    4. Should a record in this table be deleted based on the deletion of a record in a
       different table? If so, what table?
       - Yes. CASCADE delete when AuthUserTable record is deleted (user's notifications
         deleted with their account). Uses SET NULL for related_account_id and
         related_user_id to preserve notifications even when referenced entities are
         deleted (helps maintain context). Auto-purge via PurgeTable after 30 days.

    5. Will this table be require a connection a secure cloud provider service?
       - No direct cloud connection required. Works with local database only.
    """

    __tablename__ = "in_app_notification"

    notification_id: Mapped[str] = mapped_column(
        sql.String(36), primary_key=True, default=lambda: str(uuid4())
    )
    auth_user_id: Mapped[str] = mapped_column(
        sql.String(36),
        sql.ForeignKey("auth_users.auth_user_id", ondelete="CASCADE"),
        nullable=False,
    )

    # Notification content
    notification_type: Mapped[str] = mapped_column(
        sql.String(64), nullable=False
    )  # account_added, role_changed, account_removed, etc.
    title: Mapped[str] = mapped_column(sql.String(256), nullable=False)
    message: Mapped[str] = mapped_column(sql.Text, nullable=False)

    # Related entities (nullable to preserve notification context if entities deleted)
    related_account_id: Mapped[Optional[str]] = mapped_column(
        sql.String(36),
        sql.ForeignKey("account.account_id", ondelete="SET NULL"),
        nullable=True,
    )
    related_user_id: Mapped[Optional[str]] = mapped_column(
        sql.String(36),
        sql.ForeignKey("auth_users.auth_user_id", ondelete="SET NULL"),
        nullable=True,
    )

    # Additional context (JSONB for flexibility)
    metadata_json: Mapped[Optional[dict]] = mapped_column(
        JSONB, nullable=True
    )  # Store additional context like old_role, new_role, etc.

    # Status tracking
    is_read: Mapped[bool] = mapped_column(sql.Boolean, nullable=False, default=False)
    read_at: Mapped[Optional[datetime]] = mapped_column(sql.DateTime, nullable=True)

    # Priority for sorting/display
    priority: Mapped[str] = mapped_column(
        sql.String(16), nullable=False, default="normal"
    )  # low, normal, high, urgent

    # Metadata
    created_at: Mapped[datetime] = mapped_column(
        sql.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    __table_args__ = (
        sql.Index("idx_notification_user", "auth_user_id"),
        sql.Index("idx_notification_user_unread", "auth_user_id", "is_read"),
        sql.Index("idx_notification_type", "notification_type"),
        sql.Index("idx_notification_created", "created_at"),  # For purge queries
        sql.Index("idx_notification_account", "related_account_id"),
    )

    def __repr__(self) -> str:
        return f"<InAppNotificationTable(id='{self.notification_id}', user='{self.auth_user_id}', type='{self.notification_type}')>"


__all__ = ["InAppNotificationTable"]
