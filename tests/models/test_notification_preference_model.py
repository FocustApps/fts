"""
Tests for notification preference model operations.
"""

import pytest
from sqlalchemy.engine import Engine

from common.service_connections.db_service.models.notification_models.notification_preference_model import (
    NotificationPreferenceModel,
    create_default_preferences,
    query_user_preferences,
    update_user_preferences,
    delete_user_preferences,
    get_users_with_preference_enabled,
)
from common.service_connections.db_service.database.engine import (
    get_database_session as session,
)


class TestNotificationPreferenceCRUD:
    """Test CRUD operations for notification preferences."""

    def test_create_default_preferences(self, engine: Engine, auth_user_factory):
        """Test creating default preferences for a user."""
        user_id = auth_user_factory()

        preference_id = create_default_preferences(user_id, engine)

        assert preference_id is not None
        assert len(preference_id) == 36  # UUID length

        # Verify defaults were created
        with session(engine) as db_session:
            prefs = query_user_preferences(user_id, db_session, engine)

        assert prefs is not None
        assert prefs.auth_user_id == user_id
        # Verify default values
        assert prefs.account_added_email is True
        assert prefs.account_added_in_app is True
        assert prefs.role_changed_email is True
        assert prefs.bulk_operation_in_app is False

    def test_query_user_preferences(self, engine: Engine, auth_user_factory):
        """Test querying user preferences."""
        user_id = auth_user_factory()
        create_default_preferences(user_id, engine)

        with session(engine) as db_session:
            prefs = query_user_preferences(user_id, db_session, engine)

        assert prefs is not None
        assert prefs.auth_user_id == user_id
        assert prefs.preference_id is not None

    def test_query_user_preferences_not_found(self, engine: Engine, auth_user_factory):
        """Test querying preferences for user without preferences."""
        user_id = auth_user_factory()

        with session(engine) as db_session:
            prefs = query_user_preferences(user_id, db_session, engine)

        assert prefs is None

    def test_update_user_preferences(self, engine: Engine, auth_user_factory):
        """Test updating user preferences."""
        user_id = auth_user_factory()
        create_default_preferences(user_id, engine)

        # Update preferences
        updated_prefs = NotificationPreferenceModel(
            auth_user_id=user_id,
            account_added_email=False,  # Disable email
            role_changed_in_app=False,  # Disable in-app
            bulk_operation_email=False,
        )

        result = update_user_preferences(user_id, updated_prefs, engine)
        assert result is True

        # Verify updates
        with session(engine) as db_session:
            prefs = query_user_preferences(user_id, db_session, engine)

        assert prefs.account_added_email is False
        assert prefs.role_changed_in_app is False
        assert prefs.bulk_operation_email is False
        # Unchanged fields should remain default
        assert prefs.account_added_in_app is True

    def test_update_user_preferences_not_found(self, engine: Engine, auth_user_factory):
        """Test updating preferences for user without preferences raises error."""
        user_id = auth_user_factory()

        updated_prefs = NotificationPreferenceModel(
            auth_user_id=user_id,
            account_added_email=False,
        )

        with pytest.raises(ValueError, match="not found"):
            update_user_preferences(user_id, updated_prefs, engine)

    def test_delete_user_preferences(self, engine: Engine, auth_user_factory):
        """Test deleting user preferences."""
        user_id = auth_user_factory()
        create_default_preferences(user_id, engine)

        result = delete_user_preferences(user_id, engine)
        assert result is True

        # Verify deletion
        with session(engine) as db_session:
            prefs = query_user_preferences(user_id, db_session, engine)

        assert prefs is None

    def test_delete_user_preferences_not_found(self, engine: Engine, auth_user_factory):
        """Test deleting non-existent preferences raises error."""
        user_id = auth_user_factory()

        with pytest.raises(ValueError, match="not found"):
            delete_user_preferences(user_id, engine)


class TestNotificationPreferenceQueries:
    """Test query operations for notification preferences."""

    def test_get_users_with_preference_enabled(self, engine: Engine, auth_user_factory):
        """Test getting users with specific preference enabled."""
        user1 = auth_user_factory()
        user2 = auth_user_factory()
        user3 = auth_user_factory()

        # Create preferences for all users
        create_default_preferences(user1, engine)
        create_default_preferences(user2, engine)
        create_default_preferences(user3, engine)

        # Disable email for user2
        updated_prefs = NotificationPreferenceModel(
            auth_user_id=user2,
            account_added_email=False,
        )
        update_user_preferences(user2, updated_prefs, engine)

        # Query users with account_added_email enabled
        with session(engine) as db_session:
            users = get_users_with_preference_enabled(
                "account_added", "email", db_session, engine
            )

        # Should return user1 and user3, but not user2
        assert len(users) >= 2
        assert user1 in users
        assert user3 in users
        assert user2 not in users

    def test_get_users_with_in_app_preference(self, engine: Engine, auth_user_factory):
        """Test getting users with in-app preference enabled."""
        user1 = auth_user_factory()
        user2 = auth_user_factory()

        create_default_preferences(user1, engine)
        create_default_preferences(user2, engine)

        # Disable in-app for user1
        updated_prefs = NotificationPreferenceModel(
            auth_user_id=user1,
            role_changed_in_app=False,
        )
        update_user_preferences(user1, updated_prefs, engine)

        # Query users with role_changed_in_app enabled
        with session(engine) as db_session:
            users = get_users_with_preference_enabled(
                "role_changed", "in_app", db_session, engine
            )

        # Should return user2 but not user1
        assert user2 in users
        assert user1 not in users

    def test_get_users_invalid_preference_type(self, engine: Engine, auth_user_factory):
        """Test getting users with invalid preference type returns empty list."""
        user1 = auth_user_factory()
        create_default_preferences(user1, engine)

        with session(engine) as db_session:
            users = get_users_with_preference_enabled(
                "invalid_type", "email", db_session, engine
            )

        assert users == []


class TestNotificationPreferenceCascade:
    """Test CASCADE deletion when user is deleted."""

    def test_preferences_deleted_with_user(self, engine: Engine, auth_user_factory):
        """Test that preferences are CASCADE deleted when user is deleted."""
        from common.service_connections.db_service.database.tables.account_tables.auth_user import (
            AuthUserTable,
        )

        user_id = auth_user_factory()
        create_default_preferences(user_id, engine)

        # Verify preferences exist
        with session(engine) as db_session:
            prefs_before = query_user_preferences(user_id, db_session, engine)
        assert prefs_before is not None

        # Delete user
        with session(engine) as db_session:
            user = (
                db_session.query(AuthUserTable)
                .filter(AuthUserTable.auth_user_id == user_id)
                .first()
            )
            db_session.delete(user)
            db_session.commit()

        # Verify preferences are also deleted (CASCADE)
        with session(engine) as db_session:
            prefs_after = query_user_preferences(user_id, db_session, engine)
        assert prefs_after is None
