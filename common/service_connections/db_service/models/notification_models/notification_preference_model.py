"""
Notification preference model for managing user notification settings.
"""

from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from common.service_connections.db_service.database.tables.notification_preference import (
    NotificationPreferenceTable,
)
from common.service_connections.db_service.database.engine import (
    get_database_session as session,
)


class NotificationPreferenceModel(BaseModel):
    """Pydantic model for notification preferences."""

    preference_id: Optional[str] = None
    auth_user_id: str

    # Account membership notifications
    account_added_email: bool = True
    account_added_in_app: bool = True
    account_removed_email: bool = True
    account_removed_in_app: bool = True

    # Role change notifications
    role_changed_email: bool = True
    role_changed_in_app: bool = True

    # Primary account notifications
    primary_account_changed_email: bool = True
    primary_account_changed_in_app: bool = True

    # Bulk operation summary notifications
    bulk_operation_email: bool = True
    bulk_operation_in_app: bool = False

    # Account-level change notifications
    account_updated_email: bool = False
    account_updated_in_app: bool = True

    # Metadata
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# CRUD Operations


def create_default_preferences(auth_user_id: str, engine: Engine) -> str:
    """
    Create default notification preferences for a new user.

    Args:
        auth_user_id: User ID
        engine: Database engine

    Returns:
        str: Preference ID
    """
    with session(engine) as db_session:
        preference_id = str(uuid4())
        preference = NotificationPreferenceTable(
            preference_id=preference_id,
            auth_user_id=auth_user_id,
            created_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )
        db_session.add(preference)
        db_session.commit()

    return preference_id


def query_user_preferences(
    auth_user_id: str, db_session: Session, engine: Engine
) -> Optional[NotificationPreferenceModel]:
    """
    Query a user's notification preferences.

    Args:
        auth_user_id: User ID
        db_session: Active database session
        engine: Database engine

    Returns:
        Optional[NotificationPreferenceModel]: User's preferences or None if not found
    """
    preference = (
        db_session.query(NotificationPreferenceTable)
        .filter(NotificationPreferenceTable.auth_user_id == auth_user_id)
        .first()
    )

    if not preference:
        return None

    return NotificationPreferenceModel(**preference.__dict__)


def update_user_preferences(
    auth_user_id: str, preferences: NotificationPreferenceModel, engine: Engine
) -> bool:
    """
    Update a user's notification preferences.

    Args:
        auth_user_id: User ID
        preferences: Updated preferences
        engine: Database engine

    Returns:
        bool: True if successful

    Raises:
        ValueError: If preferences not found
    """
    with session(engine) as db_session:
        db_preference = (
            db_session.query(NotificationPreferenceTable)
            .filter(NotificationPreferenceTable.auth_user_id == auth_user_id)
            .first()
        )

        if not db_preference:
            raise ValueError(
                f"Notification preferences not found for user {auth_user_id}"
            )

        # Update all preference fields
        update_data = preferences.model_dump(
            exclude_none=True, exclude={"preference_id", "auth_user_id", "created_at"}
        )
        for key, value in update_data.items():
            if hasattr(db_preference, key):
                setattr(db_preference, key, value)

        db_preference.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
        db_session.commit()

    return True


def delete_user_preferences(auth_user_id: str, engine: Engine) -> bool:
    """
    Delete a user's notification preferences.
    Typically called when user account is deleted (CASCADE handles this).

    Args:
        auth_user_id: User ID
        engine: Database engine

    Returns:
        bool: True if successful

    Raises:
        ValueError: If preferences not found
    """
    with session(engine) as db_session:
        db_preference = (
            db_session.query(NotificationPreferenceTable)
            .filter(NotificationPreferenceTable.auth_user_id == auth_user_id)
            .first()
        )

        if not db_preference:
            raise ValueError(
                f"Notification preferences not found for user {auth_user_id}"
            )

        db_session.delete(db_preference)
        db_session.commit()

    return True


def get_users_with_preference_enabled(
    notification_type: str,
    channel: str,
    db_session: Session,
    engine: Engine,
) -> list[str]:
    """
    Get list of user IDs who have a specific notification type and channel enabled.

    Args:
        notification_type: Type of notification (account_added, role_changed, etc.)
        channel: Channel type (email or in_app)
        db_session: Active database session
        engine: Database engine

    Returns:
        List[str]: List of user IDs with preference enabled
    """
    # Map notification type to preference field
    field_name = f"{notification_type}_{channel}"

    if not hasattr(NotificationPreferenceTable, field_name):
        return []

    field = getattr(NotificationPreferenceTable, field_name)

    preferences = (
        db_session.query(NotificationPreferenceTable).filter(field == True).all()
    )

    return [pref.auth_user_id for pref in preferences]


__all__ = [
    "NotificationPreferenceModel",
    "create_default_preferences",
    "query_user_preferences",
    "update_user_preferences",
    "delete_user_preferences",
    "get_users_with_preference_enabled",
]
