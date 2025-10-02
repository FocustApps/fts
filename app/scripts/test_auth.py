#!/usr/bin/env python3
"""
Simple script to test authentication with the current token.
"""
import requests
import sys


def get_token_from_file():
    """Get token from the auth token file."""
    token_file = "/tmp/fenrir_auth_token.txt"
    try:
        with open(token_file, "r") as f:
            content = f.read().strip()
            for line in content.split("\n"):
                if line.startswith("token="):
                    return line.split("token=", 1)[1].strip()
    except Exception as e:
        print(f"Error reading token file: {e}")
    return None


def test_auth():
    """Test authentication with current token."""
    print("🔍 Testing authentication...")

    # Get token
    token = get_token_from_file()
    if not token:
        print("❌ Could not get token from file")
        return False

    print(f"🔑 Using token: {token[:8]}...{token[-8:]}")

    # Test authentication
    headers = {"X-Auth-Token": token}

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
