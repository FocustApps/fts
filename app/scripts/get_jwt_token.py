#!/usr/bin/env python3
"""
Generate a JWT access token for admin user authentication.

This script logs in with admin credentials and returns a JWT access token
that can be used for API authentication.
"""

import sys
import os
from pathlib import Path
import requests

# Add the project root to the path (works both inside container and locally)
if os.path.exists("/fenrir"):
    # Inside container
    project_root = Path("/fenrir")
else:
    # Local development
    project_root = Path(__file__).parent.parent.parent

sys.path.insert(0, str(project_root))

from app.config import get_config


def get_jwt_token(base_url: str = "http://localhost:8080") -> str:
    """
    Generate a JWT access token by logging in with admin credentials.

    Args:
        base_url: Base URL of the application

    Returns:
        JWT access token string
    """
    try:
        print("🔑 JWT Token Generator")
        print("=" * 40)

        # Get configuration
        config = get_config()
        admin_email = config.email_recipient

        if not admin_email:
            print("❌ Error: EMAIL_RECIPIENT not found in .env file")
            return None

        print(f"📧 Admin email: {admin_email}")

        # For local development, use a known admin password
        # In production, this should prompt for password or use env variable
        # Default matches the password used in seed_admin_user.py
        admin_password = os.getenv("ADMIN_PASSWORD", "Admin123!")

        print("🔄 Logging in to get JWT token...")

        # Call JWT login endpoint
        login_response = requests.post(
            f"{base_url}/v1/api/auth/login",
            json={
                "email": admin_email,
                "password": admin_password,
            },
            timeout=10,
        )

        if login_response.status_code == 200:
            token_data = login_response.json()
            access_token = token_data.get("access_token")

            if access_token:
                print(f"✅ Successfully obtained JWT token")
                print()

                # Test the token immediately to verify it works
                try:
                    print("🧪 Testing token validity...")
                    response = requests.get(
                        f"{base_url}/v1/env/api/",
                        headers={"Authorization": f"Bearer {access_token}"},
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
                print("=" * 80)
                print("🎉 SUCCESS: Use this token for all API calls:")
                print("=" * 80)
                print(f"Authorization: Bearer {access_token}")
                print("=" * 80)
                print()
                print("Token details:")
                print(
                    f"  - Expires in: {token_data.get('expires_in', 'unknown')} seconds"
                )
                print(f"  - Token type: {token_data.get('token_type', 'Bearer')}")
                print()

                return access_token
            else:
                print("❌ No access_token in response")
                return None

        elif login_response.status_code == 401:
            print(f"❌ Login failed: Invalid credentials")
            print(f"   Make sure admin user exists with email: {admin_email}")
            print(f"   Default password: {admin_password}")
            print(f"   Response: {login_response.text}")
            return None
        else:
            print(f"❌ Login failed with status: {login_response.status_code}")
            print(f"Response: {login_response.text}")
            return None

    except requests.exceptions.ConnectionError:
        print("❌ Error: Could not connect to application")
        print("   Make sure the application is running at:", base_url)
        return None
    except Exception as e:
        print(f"❌ Error generating JWT token: {e}")
        import traceback

        traceback.print_exc()
        return None


if __name__ == "__main__":
    token = get_jwt_token()
    if token:
        # Save token to file for use by other scripts
        token_file = "/tmp/fenrir_jwt_token.txt"
        try:
            with open(token_file, "w") as f:
                f.write(f"token={token}\n")
            print(f"💾 Token saved to: {token_file}")
        except Exception as e:
            print(f"⚠️  Could not save token to file: {e}")

        sys.exit(0)
    else:
        print("\n❌ Failed to generate JWT token")
        sys.exit(1)
