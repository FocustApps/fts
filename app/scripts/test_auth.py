#!/usr/bin/env python3
"""
Simple script to test JWT authentication with the current token.
"""
import requests
import sys


def get_token_from_file():
    """Get JWT token from the auth token file."""
    # Try new JWT token file first
    token_files = [
        "/tmp/fenrir_jwt_token.txt",
        "/tmp/fenrir_auth_token.txt",  # Legacy fallback
    ]

    for token_file in token_files:
        try:
            with open(token_file, "r") as f:
                content = f.read().strip()
                for line in content.split("\n"):
                    if line.startswith("token="):
                        token = line.split("token=", 1)[1].strip()
                        print(f"📁 Found token in: {token_file}")
                        return token
        except FileNotFoundError:
            continue
        except Exception as e:
            print(f"Error reading {token_file}: {e}")

    return None


def test_auth():
    """Test JWT authentication with current token."""
    print("🔍 Testing JWT authentication...")

    # Get token
    token = get_token_from_file()
    if not token:
        print("❌ Could not get token from file")
        print("💡 Run 'python app/scripts/get_jwt_token.py' first")
        return False

    print(f"🔑 Using JWT token: {token[:20]}...{token[-20:]}")

    # Test authentication with JWT Bearer token
    headers = {"Authorization": f"Bearer {token}"}

    try:
        response = requests.get(
            "http://localhost:8080/v1/env/api/", headers=headers, timeout=10
        )
        print(f"📡 Response status: {response.status_code}")

        if response.status_code == 200:
            print("✅ Authentication successful!")
            return True
        elif response.status_code == 401:
            print("❌ Authentication failed - token invalid")
            print(f"Response: {response.text}")
            return False
        else:
            print(f"❓ Unexpected response: {response.status_code}")
            print(f"Response: {response.text}")
            return False

    except Exception as e:
        print(f"❌ Request failed: {e}")
        return False


if __name__ == "__main__":
    success = test_auth()
    sys.exit(0 if success else 1)
