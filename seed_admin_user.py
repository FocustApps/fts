#!/usr/bin/env python3
"""
Seed admin user script for Fenrir FTS.

This script creates an admin user in the database for the email specified
in the .env file. This is needed after removing the legacy authentication
system to ensure the primary user can access the system.

Usage:
    python seed_admin_user.py
"""

import sys
import asyncio
from pathlib import Path

# Add the project root to the path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.config import get_config
from app.services.multi_user_auth_service import get_multi_user_auth_service


async def seed_admin_user():
    """Create admin user from .env configuration."""
    try:
        # Get configuration
        config = get_config()
        admin_email = config.email_recipient

        if not admin_email:
            print("❌ Error: EMAIL_RECIPIENT not found in .env file")
            return False

        print(f"🌱 Seeding admin user: {admin_email}")

        # Get auth service
        auth_service = get_multi_user_auth_service()

        # Extract username from email
        username = admin_email.split("@")[0]

        try:
            # Add admin user
            user = await auth_service.add_user(
                email=admin_email,
                username=username,
                is_admin=True,
                send_welcome_email=True,
            )

            print(f"✅ Admin user created successfully!")
            print(f"   Email: {user.email}")
            print(f"   Username: {user.username}")
            print(f"   Admin: {user.is_admin}")
            print(f"   ID: {user.id}")
            print(f"📧 Welcome email with authentication token sent to {admin_email}")

            return True

        except Exception as e:
            if "already exists" in str(e):
                print(f"ℹ️  User {admin_email} already exists in database")

                # Generate a new token for existing user
                try:
                    token = await auth_service.generate_user_token(
                        admin_email, send_email=True
                    )
                    print(f"📧 New authentication token sent to {admin_email}")
                    return True
                except Exception as token_error:
                    print(f"❌ Error generating new token: {token_error}")
                    return False
            else:
                print(f"❌ Error creating admin user: {e}")
                return False

    except Exception as e:
        print(f"❌ Error: {e}")
        return False


async def main():
    """Main entry point."""
    print("🔑 Fenrir Admin User Seeder")
    print("=" * 50)

    success = await seed_admin_user()

    if success:
        print(
            "\n🎉 Setup complete! You should receive an email with your authentication token."
        )
        print("💡 Use the token to log into the FTS application.")
    else:
        print("\n❌ Setup failed. Please check the errors above.")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
