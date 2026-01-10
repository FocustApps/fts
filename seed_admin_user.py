#!/usr/bin/env python3
"""
Seed admin user script for FTS.

This script creates an admin user in the database for the email specified
in the .env file. Uses the new JWT authentication system.

Usage:
    python seed_admin_user.py
"""

import sys
from pathlib import Path

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


def seed_admin_user():
    """Create admin user from .env configuration."""
    try:
        # Get configuration
        config = get_config()
        admin_email = config.email_recipient or "admin@fenrir.local"

        # Default admin password for local development (meets all requirements)
        admin_password = "Admin123!"

        print(f"🌱 Seeding admin user: {admin_email}")

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

                    # Ensure user is admin
                    if not existing_user.is_admin:
                        existing_user.is_admin = True
                        db_session.commit()
                        print(f"✅ Updated user to admin status")

                    return True

            # Create new admin user
            auth_service = get_user_auth_service(DB_ENGINE)
            register_request = RegisterRequest(
                email=admin_email,
                password=admin_password,
                username=username,
            )

            user = auth_service.register_user(register_request)

            # Set as admin
            with get_session(DB_ENGINE) as db_session:
                db_user = db_session.get(AuthUserTable, user.auth_user_id)
                db_user.is_admin = True
                db_session.commit()

            print(f"✅ Admin user created successfully!")
            print(f"   Email: {admin_email}")
            print(f"   Username: {username}")
            print(f"   Password: {admin_password}")
            print(f"   Admin: True")
            print(f"   ID: {user.auth_user_id}")
            print(f"\n💡 Use these credentials to login:")
            print(f"   Email: {admin_email}")
            print(f"   Password: {admin_password}")

            return True

        except Exception as e:
            print(f"❌ Error creating admin user: {e}")
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
    print("🔑 Fenrir Admin User Seeder")
    print("=" * 50)

    success = seed_admin_user()

    if success:
        print("\n🎉 Setup complete! Admin user is ready.")
        print("💡 Login at: http://localhost:8080/auth/login")
        print("💡 Or get JWT token: python app/scripts/get_jwt_token.py")
    else:
        print("\n❌ Setup failed. Please check the errors above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
