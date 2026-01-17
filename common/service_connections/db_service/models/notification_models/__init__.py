"""
Notification models package for notification preferences and in-app notifications.
"""

from common.service_connections.db_service.models.notification_models.notification_preference_model import (
    NotificationPreferenceModel,
    create_default_preferences,
    query_user_preferences,
    update_user_preferences,
    delete_user_preferences,
    get_users_with_preference_enabled,
)

from common.service_connections.db_service.models.notification_models.in_app_notification_model import (
    InAppNotificationModel,
    NotificationSummary,
    create_notification,
    bulk_create_notifications,
    query_user_notifications,
    mark_notification_as_read,
    mark_all_as_read,
    delete_notification,
    purge_old_notifications,
    get_unread_count,
)


__all__ = [
    # Notification Preference
    "NotificationPreferenceModel",
    "create_default_preferences",
    "query_user_preferences",
    "update_user_preferences",
    "delete_user_preferences",
    "get_users_with_preference_enabled",
    # In-App Notification
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
