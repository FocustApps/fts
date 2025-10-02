#!/usr/bin/env python3
"""
Seed admin user script fo            p            print(f"                # Generate a new    if success:
        print(
            "\n🎉 Setup complete! Admin user is ready."
        )
        print("💡 Use the token generator script to get authentication tokens:")
        print("    docker exec fts-fenrir-1 python /fenrir/app/scripts/get_multiuser_token.py")for existing user (but don't send email)
                try:
                    token = await auth_service.generate_user_token(
                        admin_email, send_email=False  # Don't send email - use token generator script instead
                    )
                    print(f"💡 User exists. Use the token generator script to get authentication tokens")
                    return True user created successfully!")
            print(f"   Email: {user.email}")
            print(f"   Username: {user.username}")
            print(f"   Admin: {user.is_admin}")
            print(f"   ID: {user.id}")
            print(f"💡 Use the token generator script to get authentication tokens")

            return True               # Generate a new token for existing user and send email
                try:
                    token = await auth_service.generate_user_token(
                        admin_email, send_email=True  # Send email with new token
                    )
                    print(f"📧 New authentication token sent to {admin_email}")
                    return True user created successfully!")
            print(f"   Email: {user.email}")
            print(f"   Username: {user.username}")
            print(f"   Admin: {user.is_admin}")
            print(f"   ID: {user.id}")
            print(f"📧 Welcome email with authentication token sent to {user.email}")

            return True FTS.

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
                send_welcome_email=False,  # Don't send welcome email - use token generator script instead
            )

            print(f"✅ Admin user created successfully!")
            print(f"   Email: {user.email}")
            print(f"   Username: {user.username}")
            print(f"   Admin: {user.is_admin}")
            print(f"   ID: {user.id}")
            print(f"� Use the token generator script to get authentication tokens")

            return True

        except Exception as e:
            if "already exists" in str(e):
                print(f"ℹ️  User {admin_email} already exists in database")

                # Generate a new token for existing user (but don't send email)
                try:
                    token = await auth_service.generate_user_token(
                        admin_email, send_email=False  # Don't send email - use token generator script instead
                    )
                    print(f"� User exists. Use the token generator script to get authentication tokens")
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
            "\n🎉 Setup complete! Admin user is ready."
        )
        print("� Check your email for the authentication token.")
        print("�💡 You can also use the token generator script if needed:")
        print("    docker exec fts-fenrir-1 python /fenrir/app/scripts/get_multiuser_token.py")
    else:
        print("\n❌ Setup failed. Please check the errors above.")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
