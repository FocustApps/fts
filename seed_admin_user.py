#!/usr/bin/env python3
"""
Seed admin user script for FTS.

This script creates a super admin user in the database with:
- is_super_admin=True flag
- Default "Super Admin Account"
- Account association with owner role and is_primary=True
- Default notification preferences
- Purge schedule entries for audit logs and in-app notifications

Usage:
    python seed_admin_user.py
"""

import sys
from pathlib import Path
from datetime import timezone, datetime

# Add the project root to the path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.config import get_config
from app.services.user_auth_service import get_user_auth_service
from app.models.auth_models import RegisterRequest
from common.service_connections.db_service.db_manager import DB_ENGINE
from common.service_connections.db_service.database.engine import (
    get_database_session as get_session,
)
from common.service_connections.db_service.database.tables.account_tables.auth_user import (
    AuthUserTable,
)
from common.service_connections.db_service.database.tables.account_tables.account import (
    AccountTable,
)
from common.service_connections.db_service.database.tables.account_tables.auth_user_account_association import (
    AuthUserAccountAssociation,
)
from common.service_connections.db_service.database.tables.notification_preference import (
    NotificationPreferenceTable,
)
from common.service_connections.db_service.database.tables.purge_table import (
    PurgeTable,
)
from common.service_connections.db_service.database.enums import AccountRoleEnum


def ensure_super_admin_account(db_session, user_id: str) -> str:
    """
    Ensure the Super Admin Account exists and return its ID.

    Args:
        db_session: Active database session
        user_id: Super admin user ID

    Returns:
        Account ID of the Super Admin Account
    """
    # Check if Super Admin Account already exists
    super_admin_account = (
        db_session.query(AccountTable)
        .filter(AccountTable.account_name == "Super Admin Account")
        .first()
    )

    if super_admin_account:
        print(
            f"ℹ️  Super Admin Account already exists (ID: {super_admin_account.account_id})"
        )
        return super_admin_account.account_id

    # Create Super Admin Account
    new_account = AccountTable(
        account_name="Super Admin Account",
        owner_user_id=user_id,
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(new_account)
    db_session.flush()  # Get the account_id

    print(f"✅ Created Super Admin Account (ID: {new_account.account_id})")
    return new_account.account_id


def create_account_association(db_session, user_id: str, account_id: str):
    """
    Create account association with owner role and set as primary account.

    Args:
        db_session: Active database session
        user_id: User ID
        account_id: Account ID
    """
    # Check if association already exists
    existing_assoc = (
        db_session.query(AuthUserAccountAssociation)
        .filter(
            AuthUserAccountAssociation.auth_user_id == user_id,
            AuthUserAccountAssociation.account_id == account_id,
        )
        .first()
    )

    if existing_assoc:
        # Ensure it's owner role and primary
        if existing_assoc.role != AccountRoleEnum.OWNER.value:
            existing_assoc.role = AccountRoleEnum.OWNER.value
        if not existing_assoc.is_primary:
            # Clear any other primary associations
            db_session.query(AuthUserAccountAssociation).filter(
                AuthUserAccountAssociation.auth_user_id == user_id
            ).update({"is_primary": False}, synchronize_session=False)
            existing_assoc.is_primary = True
        print(f"ℹ️  Account association already exists, updated to owner/primary")
        return

    # Clear any existing primary associations
    db_session.query(AuthUserAccountAssociation).filter(
        AuthUserAccountAssociation.auth_user_id == user_id
    ).update({"is_primary": False}, synchronize_session=False)

    # Create new association
    association = AuthUserAccountAssociation(
        auth_user_id=user_id,
        account_id=account_id,
        role=AccountRoleEnum.OWNER.value,
        is_primary=True,
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(association)
    print(f"✅ Created account association (role=owner, is_primary=True)")


def create_notification_preferences(db_session, user_id: str):
    """
    Create default notification preferences for the user.

    Args:
        db_session: Active database session
        user_id: User ID
    """
    # Check if preferences already exist
    existing_prefs = (
        db_session.query(NotificationPreferenceTable)
        .filter(NotificationPreferenceTable.auth_user_id == user_id)
        .first()
    )

    if existing_prefs:
        print(f"ℹ️  Notification preferences already exist")
        return

    # Create default preferences (all enabled)
    preferences = NotificationPreferenceTable(
        auth_user_id=user_id,
        account_added_email=True,
        account_added_in_app=True,
        account_removed_email=True,
        account_removed_in_app=True,
        role_changed_email=True,
        role_changed_in_app=True,
        primary_account_changed_email=True,
        primary_account_changed_in_app=True,
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(preferences)
    print(f"✅ Created default notification preferences (all enabled)")


def create_purge_schedule_entries(db_session):
    """
    Create purge schedule entries for audit logs and in-app notifications.

    Args:
        db_session: Active database session
    """
    from uuid import uuid4

    # Check for existing audit_logs entry
    audit_logs_entry = (
        db_session.query(PurgeTable).filter(PurgeTable.table_name == "audit_logs").first()
    )

    if not audit_logs_entry:
        audit_entry = PurgeTable(
            purge_id=str(uuid4()),
            table_name="audit_logs",
            purge_interval_days=90,
            last_purged_at=datetime.now(timezone.utc),
            created_at=datetime.now(timezone.utc),
        )
        db_session.add(audit_entry)
        print(f"✅ Created purge schedule for audit_logs (90-day retention)")
    else:
        print(f"ℹ️  Purge schedule for audit_logs already exists")

    # Check for existing in_app_notifications entry
    notifications_entry = (
        db_session.query(PurgeTable)
        .filter(PurgeTable.table_name == "in_app_notifications")
        .first()
    )

    if not notifications_entry:
        notification_entry = PurgeTable(
            purge_id=str(uuid4()),
            table_name="in_app_notifications",
            purge_interval_days=30,
            last_purged_at=datetime.now(timezone.utc),
            created_at=datetime.now(timezone.utc),
        )
        db_session.add(notification_entry)
        print(f"✅ Created purge schedule for in_app_notifications (30-day retention)")
    else:
        print(f"ℹ️  Purge schedule for in_app_notifications already exists")


def seed_admin_user():
    """Create super admin user from .env configuration with full setup."""
    try:
        # Get configuration
        config = get_config()
        admin_email = config.email_recipient or "admin@fenrir.local"

        # Default admin password for local development (meets all requirements)
        admin_password = "Admin123!"

        print(f"🌱 Seeding super admin user: {admin_email}")

        # Extract username from email
        username = admin_email.split("@")[0]

        try:
            # Check if user already exists
            with get_session(DB_ENGINE) as db_session:
                existing_user = (
                    db_session.query(AuthUserTable)
                    .filter(AuthUserTable.email == admin_email)
                    .first()
                )

                if existing_user:
                    print(f"ℹ️  User {admin_email} already exists in database")
                    print(f"   ID: {existing_user.auth_user_id}")
                    print(f"   Admin: {existing_user.is_admin}")
                    print(f"   Super Admin: {existing_user.is_super_admin}")

                    # Ensure user is admin and super admin
                    updated = False
                    if not existing_user.is_admin:
                        existing_user.is_admin = True
                        updated = True
                    if not existing_user.is_super_admin:
                        existing_user.is_super_admin = True
                        updated = True

                    if updated:
                        db_session.commit()
                        print(f"✅ Updated user to admin/super admin status")

                    user_id = existing_user.auth_user_id
                else:
                    # Create new super admin user
                    auth_service = get_user_auth_service(DB_ENGINE)
                    register_request = RegisterRequest(
                        email=admin_email,
                        password=admin_password,
                        username=username,
                    )

                    user = auth_service.register_user(register_request)

                    # Set as admin and super admin
                    db_user = db_session.get(AuthUserTable, user.auth_user_id)
                    db_user.is_admin = True
                    db_user.is_super_admin = True
                    db_session.commit()

                    print(f"✅ Super admin user created successfully!")
                    print(f"   Email: {admin_email}")
                    print(f"   Username: {username}")
                    print(f"   Password: {admin_password}")
                    print(f"   Admin: True")
                    print(f"   Super Admin: True")
                    print(f"   ID: {user.auth_user_id}")

                    user_id = user.auth_user_id

                # Ensure Super Admin Account exists
                account_id = ensure_super_admin_account(db_session, user_id)

                # Create account association
                create_account_association(db_session, user_id, account_id)

                # Create notification preferences
                create_notification_preferences(db_session, user_id)

                # Create purge schedule entries
                create_purge_schedule_entries(db_session)

                db_session.commit()

            print(f"\n💡 Use these credentials to login:")
            print(f"   Email: {admin_email}")
            print(f"   Password: {admin_password}")

            return True

        except Exception as e:
            print(f"❌ Error creating super admin user: {e}")
            import traceback

            traceback.print_exc()
            return False

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    """Main entry point."""
    print("🔑 Fenrir Super Admin User Seeder")
    print("=" * 50)

    success = seed_admin_user()

    if success:
        print("\n🎉 Setup complete! Super admin user is ready.")
        print("💡 Super Admin Account created with:")
        print("   - is_super_admin=True flag")
        print("   - Default 'Super Admin Account'")
        print("   - Owner role association (primary account)")
        print("   - Default notification preferences")
        print("   - Purge schedules (audit logs: 90d, notifications: 30d)")
        print("\n💡 Login at: http://localhost:8080/auth/login")
        print("💡 Or get JWT token: python app/scripts/get_jwt_token.py")
    else:
        print("\n❌ Setup failed. Please check the errors above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
