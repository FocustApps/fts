"""
API routes for in-app notifications and notification preferences.

Endpoints:
Notification Preferences:
- GET    /users/me/notification-preferences - Get user's notification preferences
- PUT    /users/me/notification-preferences - Update user's notification preferences

In-App Notifications:
- GET    /users/me/notifications            - List user's notifications
- GET    /users/me/notifications/unread-count - Get unread notification count
- PUT    /users/me/notifications/{id}/read  - Mark notification as read
- PUT    /users/me/notifications/read-all   - Mark all notifications as read
- DELETE /users/me/notifications/{id}       - Delete a notification

Admin Endpoints:
- POST   /notifications                     - Create notification (admin/system only)
- POST   /notifications/bulk                - Bulk create notifications (admin/system only)
"""

import logging
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from starlette.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_204_NO_CONTENT,
    HTTP_400_BAD_REQUEST,
    HTTP_404_NOT_FOUND,
)

from app.dependencies.authorization_dependency import (
    get_current_user,
    require_admin,
)
from app.config import get_config
from common.service_connections.db_service.database.engine import (
    get_database_session as get_session,
)
from common.service_connections.db_service.db_manager import DB_ENGINE
from common.service_connections.db_service.models.notification_models.notification_preference_model import (
    query_user_preferences,
    update_user_preferences,
    create_default_preferences,
)
from common.service_connections.db_service.models.notification_models.in_app_notification_model import (
    create_notification,
    bulk_create_notifications,
    query_user_notifications,
    mark_notification_as_read,
    mark_all_as_read,
    delete_notification,
    get_unread_count,
)
from app.models.auth_models import TokenPayload

logger = logging.getLogger(__name__)
BASE_CONFIG = get_config()

# Create routers
notification_preferences_api_router = APIRouter(
    prefix="/api/users/me/notification-preferences",
    tags=["api"],
)

notifications_api_router = APIRouter(
    prefix="/api/users/me/notifications",
    tags=["api"],
)

admin_notifications_api_router = APIRouter(
    prefix="/api/notifications",
    tags=["api"],
)


# ============================================================================
# Request/Response Models
# ============================================================================


class NotificationPreferencesResponse(BaseModel):
    """Response model for notification preferences."""

    preference_id: str
    auth_user_id: str

    # Account membership notifications
    account_added_email: bool
    account_added_in_app: bool
    account_removed_email: bool
    account_removed_in_app: bool

    # Role change notifications
    role_changed_email: bool
    role_changed_in_app: bool

    # Primary account notifications
    primary_account_changed_email: bool
    primary_account_changed_in_app: bool

    # Bulk operation notifications
    bulk_operation_email: bool
    bulk_operation_in_app: bool

    # Account-level change notifications
    account_updated_email: bool
    account_updated_in_app: bool

    created_at: str
    updated_at: Optional[str] = None


class UpdatePreferencesRequest(BaseModel):
    """Request model for updating notification preferences (all optional for partial updates)."""

    # Account membership notifications
    account_added_email: Optional[bool] = None
    account_added_in_app: Optional[bool] = None
    account_removed_email: Optional[bool] = None
    account_removed_in_app: Optional[bool] = None

    # Role change notifications
    role_changed_email: Optional[bool] = None
    role_changed_in_app: Optional[bool] = None

    # Primary account notifications
    primary_account_changed_email: Optional[bool] = None
    primary_account_changed_in_app: Optional[bool] = None

    # Bulk operation notifications
    bulk_operation_email: Optional[bool] = None
    bulk_operation_in_app: Optional[bool] = None

    # Account-level change notifications
    account_updated_email: Optional[bool] = None
    account_updated_in_app: Optional[bool] = None


class NotificationResponse(BaseModel):
    """Response model for in-app notification."""

    notification_id: str
    auth_user_id: str
    notification_type: str
    title: str
    message: str
    action_url: Optional[str] = None
    is_read: bool
    read_at: Optional[str] = None
    created_at: str
    expires_at: Optional[str] = None


class CreateNotificationRequest(BaseModel):
    """Request model for creating a notification."""

    auth_user_id: str
    notification_type: str
    title: str
    message: str
    action_url: Optional[str] = None
    expires_at: Optional[datetime] = None


class BulkCreateNotificationsRequest(BaseModel):
    """Request model for bulk creating notifications."""

    user_ids: List[str]
    notification_type: str
    title: str
    message: str
    action_url: Optional[str] = None
    expires_at: Optional[datetime] = None


class UnreadCountResponse(BaseModel):
    """Response model for unread notification count."""

    unread_count: int


# ============================================================================
# Notification Preferences Endpoints
# ============================================================================


@notification_preferences_api_router.get(
    "",
    response_model=NotificationPreferencesResponse,
)
async def get_notification_preferences(
    current_user: TokenPayload = Depends(get_current_user),
):
    """
    Get the current user's notification preferences.

    Returns:
        NotificationPreferencesResponse: User's notification preferences
    """
    try:
        with get_session(DB_ENGINE) as db_session:
            prefs = query_user_preferences(
                auth_user_id=current_user.user_id,
                db_session=db_session,
                engine=DB_ENGINE,
            )

        # If no preferences exist, create defaults
        if not prefs:
            pref_id = create_default_preferences(
                auth_user_id=current_user.user_id,
                engine=DB_ENGINE,
            )
            with get_session(DB_ENGINE) as db_session:
                prefs = query_user_preferences(
                    auth_user_id=current_user.user_id,
                    db_session=db_session,
                    engine=DB_ENGINE,
                )

        return NotificationPreferencesResponse(
            preference_id=prefs.preference_id,
            auth_user_id=prefs.auth_user_id,
            account_added_email=prefs.account_added_email,
            account_added_in_app=prefs.account_added_in_app,
            account_removed_email=prefs.account_removed_email,
            account_removed_in_app=prefs.account_removed_in_app,
            role_changed_email=prefs.role_changed_email,
            role_changed_in_app=prefs.role_changed_in_app,
            primary_account_changed_email=prefs.primary_account_changed_email,
            primary_account_changed_in_app=prefs.primary_account_changed_in_app,
            bulk_operation_email=prefs.bulk_operation_email,
            bulk_operation_in_app=prefs.bulk_operation_in_app,
            account_updated_email=prefs.account_updated_email,
            account_updated_in_app=prefs.account_updated_in_app,
            created_at=prefs.created_at.isoformat(),
            updated_at=prefs.updated_at.isoformat() if prefs.updated_at else None,
        )

    except Exception as e:
        logger.error(f"Error retrieving notification preferences: {e}")
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=str(e))


@notification_preferences_api_router.put(
    "",
    response_model=NotificationPreferencesResponse,
)
async def update_notification_preferences(
    body: UpdatePreferencesRequest,
    current_user: TokenPayload = Depends(get_current_user),
):
    """
    Update the current user's notification preferences.

    Args:
        body: Updated preference settings
        current_user: JWT token payload

    Returns:
        NotificationPreferencesResponse: Updated notification preferences
    """
    try:
        # Get existing preferences
        with get_session(DB_ENGINE) as db_session:
            existing = query_user_preferences(
                auth_user_id=current_user.user_id,
                db_session=db_session,
                engine=DB_ENGINE,
            )

        # If no preferences exist, create defaults first
        if not existing:
            create_default_preferences(
                auth_user_id=current_user.user_id,
                engine=DB_ENGINE,
            )
            with get_session(DB_ENGINE) as db_session:
                existing = query_user_preferences(
                    auth_user_id=current_user.user_id,
                    db_session=db_session,
                    engine=DB_ENGINE,
                )

        # Update preferences
        from common.service_connections.db_service.models.notification_models.notification_preference_model import (
            NotificationPreferenceModel,
        )

        updated_prefs = NotificationPreferenceModel(
            preference_id=existing.preference_id,
            auth_user_id=current_user.user_id,
            account_added_email=(
                body.account_added_email
                if body.account_added_email is not None
                else existing.account_added_email
            ),
            account_added_in_app=(
                body.account_added_in_app
                if body.account_added_in_app is not None
                else existing.account_added_in_app
            ),
            account_removed_email=(
                body.account_removed_email
                if body.account_removed_email is not None
                else existing.account_removed_email
            ),
            account_removed_in_app=(
                body.account_removed_in_app
                if body.account_removed_in_app is not None
                else existing.account_removed_in_app
            ),
            role_changed_email=(
                body.role_changed_email
                if body.role_changed_email is not None
                else existing.role_changed_email
            ),
            role_changed_in_app=(
                body.role_changed_in_app
                if body.role_changed_in_app is not None
                else existing.role_changed_in_app
            ),
            primary_account_changed_email=(
                body.primary_account_changed_email
                if body.primary_account_changed_email is not None
                else existing.primary_account_changed_email
            ),
            primary_account_changed_in_app=(
                body.primary_account_changed_in_app
                if body.primary_account_changed_in_app is not None
                else existing.primary_account_changed_in_app
            ),
            bulk_operation_email=(
                body.bulk_operation_email
                if body.bulk_operation_email is not None
                else existing.bulk_operation_email
            ),
            bulk_operation_in_app=(
                body.bulk_operation_in_app
                if body.bulk_operation_in_app is not None
                else existing.bulk_operation_in_app
            ),
            account_updated_email=(
                body.account_updated_email
                if body.account_updated_email is not None
                else existing.account_updated_email
            ),
            account_updated_in_app=(
                body.account_updated_in_app
                if body.account_updated_in_app is not None
                else existing.account_updated_in_app
            ),
            created_at=existing.created_at,
        )

        update_user_preferences(current_user.user_id, updated_prefs, DB_ENGINE)

        # Query back updated preferences
        with get_session(DB_ENGINE) as db_session:
            updated = query_user_preferences(
                auth_user_id=current_user.user_id,
                db_session=db_session,
                engine=DB_ENGINE,
            )

        return NotificationPreferencesResponse(
            preference_id=updated.preference_id,
            auth_user_id=updated.auth_user_id,
            account_added_email=updated.account_added_email,
            account_added_in_app=updated.account_added_in_app,
            account_removed_email=updated.account_removed_email,
            account_removed_in_app=updated.account_removed_in_app,
            role_changed_email=updated.role_changed_email,
            role_changed_in_app=updated.role_changed_in_app,
            primary_account_changed_email=updated.primary_account_changed_email,
            primary_account_changed_in_app=updated.primary_account_changed_in_app,
            bulk_operation_email=updated.bulk_operation_email,
            bulk_operation_in_app=updated.bulk_operation_in_app,
            account_updated_email=updated.account_updated_email,
            account_updated_in_app=updated.account_updated_in_app,
            created_at=updated.created_at.isoformat(),
            updated_at=updated.updated_at.isoformat() if updated.updated_at else None,
        )

    except ValueError as e:
        logger.error(f"Validation error updating preferences: {e}")
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating notification preferences: {e}")
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=str(e))


# ============================================================================
# In-App Notifications Endpoints
# ============================================================================


@notifications_api_router.get(
    "",
    response_model=List[NotificationResponse],
)
async def list_notifications(
    include_read: bool = Query(False, description="Include read notifications"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of notifications"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    current_user: TokenPayload = Depends(get_current_user),
):
    """
    List the current user's notifications.

    Args:
        include_read: Whether to include read notifications
        limit: Maximum number of notifications to return
        offset: Offset for pagination
        current_user: JWT token payload

    Returns:
        List[NotificationResponse]: List of notifications
    """
    try:
        with get_session(DB_ENGINE) as db_session:
            notifications = query_user_notifications(
                auth_user_id=current_user.user_id,
                db_session=db_session,
                engine=DB_ENGINE,
                include_read=include_read,
                limit=limit,
                offset=offset,
            )

        return [
            NotificationResponse(
                notification_id=notif.notification_id,
                auth_user_id=notif.auth_user_id,
                notification_type=notif.notification_type,
                title=notif.title,
                message=notif.message,
                action_url=notif.action_url,
                is_read=notif.is_read,
                read_at=notif.read_at.isoformat() if notif.read_at else None,
                created_at=notif.created_at.isoformat(),
                expires_at=notif.expires_at.isoformat() if notif.expires_at else None,
            )
            for notif in notifications
        ]

    except Exception as e:
        logger.error(f"Error listing notifications: {e}")
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=str(e))


@notifications_api_router.get(
    "/unread-count",
    response_model=UnreadCountResponse,
)
async def get_unread_notification_count(
    current_user: TokenPayload = Depends(get_current_user),
):
    """
    Get the count of unread notifications for the current user.

    Returns:
        UnreadCountResponse: Unread notification count
    """
    try:
        with get_session(DB_ENGINE) as db_session:
            count = get_unread_count(
                auth_user_id=current_user.user_id,
                db_session=db_session,
                engine=DB_ENGINE,
            )

        return UnreadCountResponse(unread_count=count)

    except Exception as e:
        logger.error(f"Error getting unread count: {e}")
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=str(e))


@notifications_api_router.put(
    "/{notification_id}/read",
    status_code=HTTP_200_OK,
)
async def mark_notification_read(
    notification_id: str,
    current_user: TokenPayload = Depends(get_current_user),
):
    """
    Mark a notification as read.

    Args:
        notification_id: Notification ID to mark as read
        current_user: JWT token payload

    Returns:
        dict: Success message
    """
    try:
        # Verify notification belongs to user
        with get_session(DB_ENGINE) as db_session:
            notifications = query_user_notifications(
                auth_user_id=current_user.user_id,
                db_session=db_session,
                engine=DB_ENGINE,
                include_read=True,
            )
            notif = next(
                (n for n in notifications if n.notification_id == notification_id), None
            )

        if not notif:
            raise HTTPException(
                status_code=HTTP_404_NOT_FOUND,
                detail="Notification not found",
            )

        mark_notification_as_read(notification_id, DB_ENGINE)

        return {"message": "Notification marked as read"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error marking notification as read: {e}")
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=str(e))


@notifications_api_router.put(
    "/read-all",
    status_code=HTTP_200_OK,
)
async def mark_all_notifications_read(
    current_user: TokenPayload = Depends(get_current_user),
):
    """
    Mark all notifications as read for the current user.

    Returns:
        dict: Number of notifications marked as read
    """
    try:
        count = mark_all_as_read(
            auth_user_id=current_user.user_id,
            engine=DB_ENGINE,
        )

        return {"message": f"Marked {count} notifications as read", "count": count}

    except Exception as e:
        logger.error(f"Error marking all notifications as read: {e}")
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=str(e))


@notifications_api_router.delete(
    "/{notification_id}",
    status_code=HTTP_204_NO_CONTENT,
)
async def delete_notification_endpoint(
    notification_id: str,
    current_user: TokenPayload = Depends(get_current_user),
):
    """
    Delete a notification.

    Args:
        notification_id: Notification ID to delete
        current_user: JWT token payload
    """
    try:
        # Verify notification belongs to user
        with get_session(DB_ENGINE) as db_session:
            notifications = query_user_notifications(
                auth_user_id=current_user.user_id,
                db_session=db_session,
                engine=DB_ENGINE,
                include_read=True,
            )
            notif = next(
                (n for n in notifications if n.notification_id == notification_id), None
            )

        if not notif:
            raise HTTPException(
                status_code=HTTP_404_NOT_FOUND,
                detail="Notification not found",
            )

        delete_notification(notification_id, DB_ENGINE)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting notification: {e}")
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=str(e))


# ============================================================================
# Admin Notification Creation Endpoints
# ============================================================================


@admin_notifications_api_router.post(
    "",
    response_model=NotificationResponse,
    status_code=HTTP_201_CREATED,
)
async def create_notification_endpoint(
    body: CreateNotificationRequest,
    current_user: TokenPayload = Depends(require_admin),
):
    """
    Create a notification for a specific user.

    Requires: Admin or system permissions

    Args:
        body: Notification creation data
        current_user: JWT token payload

    Returns:
        NotificationResponse: Created notification
    """
    try:
        # Validate notification type (basic validation - just check it's not empty)
        if not body.notification_type or len(body.notification_type.strip()) == 0:
            raise ValueError("Notification type is required")

        from common.service_connections.db_service.models.notification_models.in_app_notification_model import (
            InAppNotificationModel,
        )

        notification = InAppNotificationModel(
            auth_user_id=body.auth_user_id,
            notification_type=body.notification_type,
            title=body.title,
            message=body.message,
            action_url=body.action_url,
            expires_at=body.expires_at,
        )

        notification_id = create_notification(notification, DB_ENGINE)

        # Query back created notification
        with get_session(DB_ENGINE) as db_session:
            notifications = query_user_notifications(
                auth_user_id=body.auth_user_id,
                db_session=db_session,
                engine=DB_ENGINE,
                include_read=True,
            )
            created = next(
                (n for n in notifications if n.notification_id == notification_id), None
            )

        if not created:
            raise ValueError("Failed to retrieve created notification")

        return NotificationResponse(
            notification_id=created.notification_id,
            auth_user_id=created.auth_user_id,
            notification_type=created.notification_type,
            title=created.title,
            message=created.message,
            action_url=created.action_url,
            is_read=created.is_read,
            read_at=created.read_at.isoformat() if created.read_at else None,
            created_at=created.created_at.isoformat(),
            expires_at=created.expires_at.isoformat() if created.expires_at else None,
        )

    except ValueError as e:
        logger.error(f"Validation error creating notification: {e}")
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating notification: {e}")
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=str(e))


@admin_notifications_api_router.post(
    "/bulk",
    status_code=HTTP_201_CREATED,
)
async def bulk_create_notifications_endpoint(
    body: BulkCreateNotificationsRequest,
    current_user: TokenPayload = Depends(require_admin),
):
    """
    Create notifications for multiple users.

    Requires: Admin or system permissions

    Args:
        body: Bulk notification creation data
        current_user: JWT token payload

    Returns:
        dict: Success message with count
    """
    try:
        # Validate notification type (basic validation - just check it's not empty)
        if not body.notification_type or len(body.notification_type.strip()) == 0:
            raise ValueError("Notification type is required")

        count = bulk_create_notifications(
            user_ids=body.user_ids,
            notification_type=body.notification_type,
            title=body.title,
            message=body.message,
            action_url=body.action_url,
            expires_at=body.expires_at,
            engine=DB_ENGINE,
        )

        return {
            "message": f"Created {count} notifications",
            "count": count,
            "user_ids": body.user_ids,
        }

    except ValueError as e:
        logger.error(f"Validation error bulk creating notifications: {e}")
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error bulk creating notifications: {e}")
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=str(e))
