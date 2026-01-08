#!/usr/bin/env python3
"""
Generate a multi-user authentication token for the admin user.

This script creates a valid multi-user token that can be used for API authentication
when accessing environment, pages, and identifier endpoints.
"""

import sys
import asyncio
import os
from pathlib import Path

# Add the project root to the path (works both inside container and locally)
if os.path.exists("/fenrir"):
    # Inside container
    project_root = Path("/fenrir")
else:
    # Local development
    project_root = Path(__file__).parent.parent

sys.path.insert(0, str(project_root))

from app.config import get_config
from app.services.multi_user_auth_service import get_multi_user_auth_service


async def generate_admin_token():
    """Generate a multi-user authentication token for the admin user."""
    try:
        print("🔑 Multi-User Token Generator")
        print("=" * 40)

        # Get configuration
        config = get_config()
        admin_email = config.email_recipient

        if not admin_email:
            print("❌ Error: EMAIL_RECIPIENT not found in .env file")
            return None

        print(f"📧 Admin email: {admin_email}")

        # Get auth service
        auth_service = get_multi_user_auth_service()

        # Check if user exists
        try:
            user = auth_service.get_user_by_email(admin_email)
            if not user:
                print(f"❌ Error: Admin user {admin_email} not found in database")
                print("💡 Make sure the seeding process completed successfully")
                return None

            print(
                f"✅ Found user: {user.username} (ID: {user.auth_user_id}, Admin: {user.is_admin})"
            )

        except Exception as e:
            print(f"❌ Error checking user: {e}")
            return None

        # Generate new token for the user
        try:
            print("🔄 Generating fresh multi-user authentication token...")
            token = await auth_service.generate_user_token(
                admin_email, send_email=False  # Don't send email, just return token
            )

            if token:
                print(f"🎯 WORKING TOKEN: {token}")
                print()

                # Test the token immediately to verify it works
                import requests

                try:
                    print("🧪 Testing token validity...")
                    response = requests.get(
                        "http://localhost:8080/v1/env/api/",
                        headers={"X-Auth-Token": token},
                        timeout=5,
                    )
                    if response.status_code == 200:
                        print("✅ TOKEN VERIFIED - This token works!")
                        print(f"📊 Found {len(response.json())} environments")
                    else:
                        print(f"❌ Token test failed: {response.status_code}")
                        print(f"Response: {response.text[:100]}")

                except Exception as e:
                    print(f"❌ Token test error: {e}")

                print()
                print("=" * 60)
                print("� SUCCESS: Use this token for all API calls and web login:")
                print("=" * 60)
                print(f"X-Auth-Token: {token}")
                print("=" * 60)
                print()
                print("💡 Usage examples:")
                print(
                    f"  curl -H 'X-Auth-Token: {token}' http://localhost:8080/v1/env/api/"
                )
                print()
                print("📝 This token works with endpoints like:")
                print("  - /v1/env/api/ (environments)")
                print("  - /v1/api/pages/ (pages)")
                print("  - /v1/api/identifiers/ (identifiers)")
                print("  - /v1/user/api/ (users)")
                print()
                print("🌐 For web login:")
                print(f"  Email: {admin_email}")
                print(f"  Token: {token}")

                return token
            else:
                print("❌ Failed to generate token")
                return None

        except Exception as e:
            print(f"❌ Error generating token: {e}")
            return None

    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return None


async def main():
    """Main entry point."""
    token = await generate_admin_token()

    if token:
        print("\n🎉 Token generation successful!")
        sys.exit(0)
    else:
        print("\n❌ Token generation failed!")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
