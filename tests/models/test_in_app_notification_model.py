"""
Tests for in-app notification model operations.
"""

import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy.engine import Engine

from common.service_connections.db_service.models.notification_models.in_app_notification_model import (
    create_notification,
    bulk_create_notifications,
    query_user_notifications,
    mark_notification_as_read,
    mark_all_as_read,
    delete_notification,
    purge_old_notifications,
    get_unread_count,
)
from common.service_connections.db_service.database.engine import (
    get_database_session as session,
)


class TestInAppNotificationCRUD:
    """Test CRUD operations for in-app notifications."""

    def test_create_notification(
        self, engine: Engine, auth_user_factory, account_factory
    ):
        """Test creating a notification."""
        user_id = auth_user_factory()
        account_id = account_factory()

        notification_id = create_notification(
            auth_user_id=user_id,
            notification_type="account_added",
            title="Added to Account",
            message="You have been added to Test Account",
            related_account_id=account_id,
            priority="normal",
            engine=engine,
        )

        assert notification_id is not None
        assert len(notification_id) == 36  # UUID length

        # Verify notification was created
        with session(engine) as db_session:
            summary = query_user_notifications(user_id, db_session, engine)

        assert summary.total == 1
        assert summary.unread == 1
        assert len(summary.notifications) == 1
        assert summary.notifications[0].notification_type == "account_added"
        assert summary.notifications[0].is_read is False

    def test_create_notification_with_metadata(self, engine: Engine, auth_user_factory):
        """Test creating notification with metadata."""
        user_id = auth_user_factory()

        metadata = {"old_role": "member", "new_role": "admin"}
        notification_id = create_notification(
            auth_user_id=user_id,
            notification_type="role_changed",
            title="Role Updated",
            message="Your role has been changed",
            metadata_json=metadata,
            engine=engine,
        )

        assert notification_id is not None

        # Verify metadata
        with session(engine) as db_session:
            summary = query_user_notifications(user_id, db_session, engine)

        assert summary.notifications[0].metadata_json == metadata

    def test_bulk_create_notifications(self, engine: Engine, auth_user_factory):
        """Test bulk creating notifications."""
        user1 = auth_user_factory()
        user2 = auth_user_factory()
        user3 = auth_user_factory()

        notifications = [
            {
                "auth_user_id": user1,
                "notification_type": "account_added",
                "title": "Welcome",
                "message": "You were added",
            },
            {
                "auth_user_id": user2,
                "notification_type": "account_added",
                "title": "Welcome",
                "message": "You were added",
            },
            {
                "auth_user_id": user3,
                "notification_type": "role_changed",
                "title": "Role Updated",
                "message": "Your role changed",
                "priority": "high",
            },
        ]

        count = bulk_create_notifications(notifications, engine)
        assert count == 3

        # Verify each user got their notification
        with session(engine) as db_session:
            summary1 = query_user_notifications(user1, db_session, engine)
            summary2 = query_user_notifications(user2, db_session, engine)
            summary3 = query_user_notifications(user3, db_session, engine)

        assert summary1.total == 1
        assert summary2.total == 1
        assert summary3.total == 1
        assert summary3.notifications[0].priority == "high"

    def test_mark_notification_as_read(self, engine: Engine, auth_user_factory):
        """Test marking a notification as read."""
        user_id = auth_user_factory()

        notification_id = create_notification(
            auth_user_id=user_id,
            notification_type="account_added",
            title="Test",
            message="Test message",
            engine=engine,
        )

        result = mark_notification_as_read(notification_id, engine)
        assert result is True

        # Verify it's marked as read
        with session(engine) as db_session:
            summary = query_user_notifications(user_id, db_session, engine)

        assert summary.unread == 0
        assert summary.notifications[0].is_read is True
        assert summary.notifications[0].read_at is not None

    def test_mark_notification_as_read_not_found(self, engine: Engine):
        """Test marking non-existent notification raises error."""
        with pytest.raises(ValueError, match="not found"):
            mark_notification_as_read("fake-id", engine)

    def test_mark_all_as_read(self, engine: Engine, auth_user_factory):
        """Test marking all notifications as read."""
        user_id = auth_user_factory()

        # Create multiple notifications
        for i in range(5):
            create_notification(
                auth_user_id=user_id,
                notification_type="account_added",
                title=f"Test {i}",
                message=f"Message {i}",
                engine=engine,
            )

        # Mark all as read
        count = mark_all_as_read(user_id, engine)
        assert count == 5

        # Verify all are read
        with session(engine) as db_session:
            summary = query_user_notifications(user_id, db_session, engine)

        assert summary.unread == 0
        assert all(notif.is_read for notif in summary.notifications)

    def test_delete_notification(self, engine: Engine, auth_user_factory):
        """Test deleting a notification."""
        user_id = auth_user_factory()

        notification_id = create_notification(
            auth_user_id=user_id,
            notification_type="account_added",
            title="Test",
            message="Test message",
            engine=engine,
        )

        result = delete_notification(notification_id, engine)
        assert result is True

        # Verify deletion
        with session(engine) as db_session:
            summary = query_user_notifications(user_id, db_session, engine)

        assert summary.total == 0

    def test_delete_notification_not_found(self, engine: Engine):
        """Test deleting non-existent notification raises error."""
        with pytest.raises(ValueError, match="not found"):
            delete_notification("fake-id", engine)


class TestInAppNotificationQueries:
    """Test query operations for in-app notifications."""

    def test_query_user_notifications_pagination(self, engine: Engine, auth_user_factory):
        """Test pagination of user notifications."""
        user_id = auth_user_factory()

        # Create 10 notifications
        for i in range(10):
            create_notification(
                auth_user_id=user_id,
                notification_type="account_added",
                title=f"Test {i}",
                message=f"Message {i}",
                engine=engine,
            )

        # Query first page (5 items)
        with session(engine) as db_session:
            page1 = query_user_notifications(
                user_id, db_session, engine, limit=5, offset=0
            )

        assert page1.total == 10
        assert len(page1.notifications) == 5

        # Query second page (5 items)
        with session(engine) as db_session:
            page2 = query_user_notifications(
                user_id, db_session, engine, limit=5, offset=5
            )

        assert page2.total == 10
        assert len(page2.notifications) == 5

        # Verify no overlap
        page1_ids = [n.notification_id for n in page1.notifications]
        page2_ids = [n.notification_id for n in page2.notifications]
        assert len(set(page1_ids) & set(page2_ids)) == 0

    def test_query_user_notifications_unread_only(
        self, engine: Engine, auth_user_factory
    ):
        """Test querying only unread notifications."""
        user_id = auth_user_factory()

        # Create 5 notifications
        notification_ids = []
        for i in range(5):
            notif_id = create_notification(
                auth_user_id=user_id,
                notification_type="account_added",
                title=f"Test {i}",
                message=f"Message {i}",
                engine=engine,
            )
            notification_ids.append(notif_id)

        # Mark 2 as read
        mark_notification_as_read(notification_ids[0], engine)
        mark_notification_as_read(notification_ids[1], engine)

        # Query unread only
        with session(engine) as db_session:
            summary = query_user_notifications(
                user_id, db_session, engine, unread_only=True
            )

        assert summary.total == 3  # Only unread in filtered query
        assert summary.unread == 3
        assert all(not notif.is_read for notif in summary.notifications)

    def test_query_user_notifications_ordering(self, engine: Engine, auth_user_factory):
        """Test notifications are ordered correctly (unread first, newest first)."""
        user_id = auth_user_factory()

        # Create notifications with different read states
        notif1 = create_notification(
            auth_user_id=user_id,
            notification_type="account_added",
            title="Old Read",
            message="Message",
            engine=engine,
        )
        mark_notification_as_read(notif1, engine)

        notif2 = create_notification(
            auth_user_id=user_id,
            notification_type="account_added",
            title="New Unread",
            message="Message",
            engine=engine,
        )

        notif3 = create_notification(
            auth_user_id=user_id,
            notification_type="account_added",
            title="Newer Unread",
            message="Message",
            engine=engine,
        )

        # Query all
        with session(engine) as db_session:
            summary = query_user_notifications(user_id, db_session, engine)

        # Unread should come first, then ordered by created_at desc
        assert summary.notifications[0].is_read is False
        assert summary.notifications[1].is_read is False
        assert summary.notifications[2].is_read is True

    def test_get_unread_count(self, engine: Engine, auth_user_factory):
        """Test getting unread notification count."""
        user_id = auth_user_factory()

        # Create 3 notifications
        notification_ids = []
        for i in range(3):
            notif_id = create_notification(
                auth_user_id=user_id,
                notification_type="account_added",
                title=f"Test {i}",
                message=f"Message {i}",
                engine=engine,
            )
            notification_ids.append(notif_id)

        # All should be unread
        with session(engine) as db_session:
            count = get_unread_count(user_id, db_session, engine)
        assert count == 3

        # Mark one as read
        mark_notification_as_read(notification_ids[0], engine)

        # Count should be 2
        with session(engine) as db_session:
            count = get_unread_count(user_id, db_session, engine)
        assert count == 2


class TestInAppNotificationPurge:
    """Test purging old notifications."""

    def test_purge_old_notifications(self, engine: Engine, auth_user_factory):
        """Test purging notifications older than specified days."""
        from common.service_connections.db_service.database.tables.in_app_notification import (
            InAppNotificationTable,
        )

        user_id = auth_user_factory()

        # Create old notification (manually set created_at)
        with session(engine) as db_session:
            old_notif = InAppNotificationTable(
                notification_id="old-notif-id",
                auth_user_id=user_id,
                notification_type="account_added",
                title="Old Notification",
                message="This is old",
                created_at=datetime.now(timezone.utc).replace(tzinfo=None)
                - timedelta(days=35),
            )
            db_session.add(old_notif)
            db_session.commit()

        # Create recent notification
        create_notification(
            auth_user_id=user_id,
            notification_type="account_added",
            title="Recent",
            message="This is recent",
            engine=engine,
        )

        # Purge notifications older than 30 days
        deleted_count = purge_old_notifications(days=30, engine=engine)
        assert deleted_count == 1

        # Verify only recent notification remains
        with session(engine) as db_session:
            summary = query_user_notifications(user_id, db_session, engine)

        assert summary.total == 1
        assert summary.notifications[0].title == "Recent"


class TestInAppNotificationCascade:
    """Test CASCADE deletion behavior."""

    def test_notifications_deleted_with_user(self, engine: Engine, auth_user_factory):
        """Test notifications CASCADE deleted when user is deleted."""
        from common.service_connections.db_service.database.tables.account_tables.auth_user import (
            AuthUserTable,
        )

        user_id = auth_user_factory()

        # Create notifications
        create_notification(
            auth_user_id=user_id,
            notification_type="account_added",
            title="Test",
            message="Test",
            engine=engine,
        )

        # Verify notification exists
        with session(engine) as db_session:
            summary_before = query_user_notifications(user_id, db_session, engine)
        assert summary_before.total == 1

        # Delete user
        with session(engine) as db_session:
            user = (
                db_session.query(AuthUserTable)
                .filter(AuthUserTable.auth_user_id == user_id)
                .first()
            )
            db_session.delete(user)
            db_session.commit()

        # Verify notifications are deleted (CASCADE)
        with session(engine) as db_session:
            summary_after = query_user_notifications(user_id, db_session, engine)
        assert summary_after.total == 0

    def test_related_account_set_null(
        self, engine: Engine, auth_user_factory, account_factory
    ):
        """Test related_account_id SET NULL when account is deleted."""
        from common.service_connections.db_service.database.tables.account_tables.account import (
            AccountTable,
        )

        user_id = auth_user_factory()
        account_id = account_factory()

        # Create notification with related account
        notification_id = create_notification(
            auth_user_id=user_id,
            notification_type="account_added",
            title="Test",
            message="Test",
            related_account_id=account_id,
            engine=engine,
        )

        # Delete account
        with session(engine) as db_session:
            account = (
                db_session.query(AccountTable)
                .filter(AccountTable.account_id == account_id)
                .first()
            )
            db_session.delete(account)
            db_session.commit()

        # Verify notification still exists with related_account_id set to NULL
        with session(engine) as db_session:
            summary = query_user_notifications(user_id, db_session, engine)

        assert summary.total == 1
        assert summary.notifications[0].related_account_id is None
