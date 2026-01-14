"""
In-app notification model for managing user notifications.
"""

from datetime import datetime, timezone, timedelta
from typing import Optional
from uuid import uuid4
import logging

from pydantic import BaseModel
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from common.service_connections.db_service.database.tables.in_app_notification import (
    InAppNotificationTable,
)
from common.service_connections.db_service.database.engine import (
    get_database_session as session,
)


class InAppNotificationModel(BaseModel):
    """Pydantic model for in-app notifications."""

    notification_id: Optional[str] = None
    auth_user_id: str
    notification_type: str
    title: str
    message: str
    related_account_id: Optional[str] = None
    related_user_id: Optional[str] = None
    metadata_json: Optional[dict] = None
    is_read: bool = False
    read_at: Optional[datetime] = None
    priority: str = "normal"  # low, normal, high, urgent
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class NotificationSummary(BaseModel):
    """Summary of user notifications."""

    total: int
    unread: int
    notifications: list[InAppNotificationModel]


# CRUD Operations


def create_notification(
    auth_user_id: str,
    notification_type: str,
    title: str,
    message: str,
    related_account_id: Optional[str] = None,
    related_user_id: Optional[str] = None,
    metadata_json: Optional[dict] = None,
    priority: str = "normal",
    engine: Engine = None,
) -> str:
    """
    Create a new in-app notification for a user.

    Args:
        auth_user_id: User ID to receive notification
        notification_type: Type of notification (account_added, role_changed, etc.)
        title: Notification title
        message: Notification message
        related_account_id: Related account ID (optional)
        related_user_id: Related user ID (optional)
        metadata_json: Additional metadata (optional)
        priority: Priority level (low, normal, high, urgent)
        engine: Database engine

    Returns:
        str: Notification ID
    """
    with session(engine) as db_session:
        notification_id = str(uuid4())
        notification = InAppNotificationTable(
            notification_id=notification_id,
            auth_user_id=auth_user_id,
            notification_type=notification_type,
            title=title,
            message=message,
            related_account_id=related_account_id,
            related_user_id=related_user_id,
            metadata_json=metadata_json,
            priority=priority,
            created_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )
        db_session.add(notification)
        db_session.commit()

    return notification_id


def bulk_create_notifications(
    notifications: list[dict],
    engine: Engine,
) -> int:
    """
    Create multiple notifications in bulk.

    Args:
        notifications: List of notification dicts with keys matching create_notification params
        engine: Database engine

    Returns:
        int: Number of notifications created
    """
    with session(engine) as db_session:
        notification_objects = []
        for notif in notifications:
            notification_objects.append(
                InAppNotificationTable(
                    notification_id=str(uuid4()),
                    auth_user_id=notif["auth_user_id"],
                    notification_type=notif["notification_type"],
                    title=notif["title"],
                    message=notif["message"],
                    related_account_id=notif.get("related_account_id"),
                    related_user_id=notif.get("related_user_id"),
                    metadata_json=notif.get("metadata_json"),
                    priority=notif.get("priority", "normal"),
                    created_at=datetime.now(timezone.utc).replace(tzinfo=None),
                )
            )

        db_session.bulk_save_objects(notification_objects)
        db_session.commit()

    return len(notification_objects)


def query_user_notifications(
    auth_user_id: str,
    db_session: Session,
    engine: Engine,
    unread_only: bool = False,
    limit: int = 50,
    offset: int = 0,
) -> NotificationSummary:
    """
    Query a user's notifications with pagination.

    Args:
        auth_user_id: User ID
        db_session: Active database session
        engine: Database engine
        unread_only: If True, only return unread notifications
        limit: Maximum number of notifications to return
        offset: Number of notifications to skip (for pagination)

    Returns:
        NotificationSummary: Summary with total, unread count, and notifications
    """
    # Build query
    query = db_session.query(InAppNotificationTable).filter(
        InAppNotificationTable.auth_user_id == auth_user_id
    )

    if unread_only:
        query = query.filter(InAppNotificationTable.is_read == False)

    # Get total count
    total = query.count()

    # Get unread count (separate query to avoid interference with filters)
    unread_query = db_session.query(InAppNotificationTable).filter(
        InAppNotificationTable.auth_user_id == auth_user_id,
        InAppNotificationTable.is_read == False,
    )
    unread = unread_query.count()

    # Get paginated results ordered by priority and creation date
    priority_order = {
        "urgent": 0,
        "high": 1,
        "normal": 2,
        "low": 3,
    }

    notifications = (
        query.order_by(
            InAppNotificationTable.is_read.asc(),  # Unread first
            InAppNotificationTable.created_at.desc(),  # Newest first
        )
        .limit(limit)
        .offset(offset)
        .all()
    )

    notification_models = [
        InAppNotificationModel(**notif.__dict__) for notif in notifications
    ]

    return NotificationSummary(
        total=total,
        unread=unread,
        notifications=notification_models,
    )


def mark_notification_as_read(notification_id: str, engine: Engine) -> bool:
    """
    Mark a notification as read.

    Args:
        notification_id: Notification ID
        engine: Database engine

    Returns:
        bool: True if successful

    Raises:
        ValueError: If notification not found
    """
    with session(engine) as db_session:
        notification = (
            db_session.query(InAppNotificationTable)
            .filter(InAppNotificationTable.notification_id == notification_id)
            .first()
        )

        if not notification:
            raise ValueError(f"Notification {notification_id} not found")

        notification.is_read = True
        notification.read_at = datetime.now(timezone.utc).replace(tzinfo=None)
        db_session.commit()

    return True


def mark_all_as_read(auth_user_id: str, engine: Engine) -> int:
    """
    Mark all notifications as read for a user.

    Args:
        auth_user_id: User ID
        engine: Database engine

    Returns:
        int: Number of notifications marked as read
    """
    with session(engine) as db_session:
        updated_count = (
            db_session.query(InAppNotificationTable)
            .filter(
                InAppNotificationTable.auth_user_id == auth_user_id,
                InAppNotificationTable.is_read == False,
            )
            .update(
                {
                    "is_read": True,
                    "read_at": datetime.now(timezone.utc).replace(tzinfo=None),
                }
            )
        )
        db_session.commit()

    return updated_count


def delete_notification(notification_id: str, engine: Engine) -> bool:
    """
    Delete a specific notification.

    Args:
        notification_id: Notification ID
        engine: Database engine

    Returns:
        bool: True if successful

    Raises:
        ValueError: If notification not found
    """
    with session(engine) as db_session:
        notification = (
            db_session.query(InAppNotificationTable)
            .filter(InAppNotificationTable.notification_id == notification_id)
            .first()
        )

        if not notification:
            raise ValueError(f"Notification {notification_id} not found")

        db_session.delete(notification)
        db_session.commit()

    return True


def purge_old_notifications(days: int = 30, engine: Engine = None) -> int:
    """
    Purge notifications older than specified days (default 30).
    Should be called by automated purge task.

    Args:
        days: Number of days to retain notifications
        engine: Database engine

    Returns:
        int: Number of notifications deleted
    """
    with session(engine) as db_session:
        cutoff_date = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(
            days=days
        )

        deleted_count = (
            db_session.query(InAppNotificationTable)
            .filter(InAppNotificationTable.created_at < cutoff_date)
            .delete()
        )
        db_session.commit()

    logging.info(f"Purged {deleted_count} notifications older than {days} days")
    return deleted_count


def get_unread_count(auth_user_id: str, db_session: Session, engine: Engine) -> int:
    """
    Get count of unread notifications for a user.
    Lightweight query for polling/badge display.

    Args:
        auth_user_id: User ID
        db_session: Active database session
        engine: Database engine

    Returns:
        int: Number of unread notifications
    """
    count = (
        db_session.query(InAppNotificationTable)
        .filter(
            InAppNotificationTable.auth_user_id == auth_user_id,
            InAppNotificationTable.is_read == False,
        )
        .count()
    )

    return count


__all__ = [
    "InAppNotificationModel",
    "NotificationSummary",
    "create_notification",
    "bulk_create_notifications",
    "query_user_notifications",
    "mark_notification_as_read",
    "mark_all_as_read",
    "delete_notification",
    "purge_old_notifications",
    "get_unread_count",
]
