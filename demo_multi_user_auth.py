#!/usr/bin/env python3
"""
Demo script for multi-user authentication system.

This script demonstrates how to use the new multi-user authentication features:
- Adding users through the API
- Managing authentication tokens
- Email notifications
"""

import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.multi_user_auth_service import get_multi_user_auth_service


def demo_basic_usage():
    """Demonstrate basic multi-user authentication usage."""
    print("🎯 Multi-User Authentication Demo\n")

    # Get the service
    auth_service = get_multi_user_auth_service()

    print("📝 Step 1: Adding a new user")
    print("Code example:")
    print("  auth_service = get_multi_user_auth_service()")
    print("  new_user = auth_service.add_user(")
    print("      email='alice@company.com',")
    print("      username='Alice Smith',")
    print("      is_admin=False,")
    print("      send_welcome_email=True  # Sends token via email")
    print("  )")

    print("\n🔑 Step 2: Generating tokens for users")
    print("Code example:")
    print("  # Generate new token and email it to user")
    print("  token = auth_service.generate_user_token(")
    print("      email='alice@company.com',")
    print("      send_email=True")
    print("  )")

    print("\n✅ Step 3: Validating user tokens")
    print("Code example:")
    print("  # Validate a token for a specific user")
    print("  is_valid = auth_service.validate_user_token(")
    print("      email='alice@company.com',")
    print("      provided_token=token")
    print("  )")

    print("\n📋 Step 4: Managing users")
    print("Code examples:")
    print("  # List all active users")
    print("  users = auth_service.list_users()")
    print("  ")
    print("  # Get user by email")
    print("  user = auth_service.get_user_by_email('alice@company.com')")
    print("  ")
    print("  # Deactivate a user")
    print("  auth_service.deactivate_user('alice@company.com')")

    print("\n🌐 Step 5: Using the web interface")
    print("Admin routes available at:")
    print("  • /auth-users/           - List all users")
    print("  • /auth-users/new/       - Add new user form")
    print("  • /auth-users/{user_id}  - View user details")
    print("  • POST /auth-users/{user_id}/generate-token")
    print("  • POST /auth-users/{user_id}/deactivate")

    print("\n🔗 Step 6: API endpoints")
    print("API routes available at:")
    print("  • GET  /api/auth-users/users          - List users")
    print("  • POST /api/auth-users/users          - Create user")
    print("  • GET  /api/auth-users/users/{id}     - Get user")
    print("  • POST /api/auth-users/users/{id}/generate-token")
    print("  • DELETE /api/auth-users/users/{id}   - Deactivate user")

    print("\n🔐 Step 7: Authentication in your code")
    print("Code example for routes:")
    print("  from app.dependencies.multi_user_auth_dependency import (")
    print("      verify_multi_user_auth_token, verify_admin_auth_token")
    print("  ")
    print("  @app.get('/api/protected')")
    print("  async def protected_endpoint(")
    print("      auth_context: AuthContext = Depends(verify_multi_user_auth_token)")
    print("  ):")
    print("      # auth_context contains:")
    print("      # - token: str")
    print("      # - user_email: str")
    print("      # - user_id: int")
    print("      # - username: str")
    print("      # - is_admin: bool")
    print("      # - is_legacy_token: bool")
    print("      return {'message': f'Hello {auth_context.user_email}!'}")

    print("\n📧 Step 8: Email notifications")
    print("Email features:")
    print("  • Welcome emails sent automatically to new users")
    print("  • Token generation emails with instructions")
    print("  • Secure token delivery via email")
    print("  • Admin notifications for user management actions")

    print("\n🔄 Step 9: Backward compatibility")
    print("The system maintains backward compatibility:")
    print("  • Legacy single-user tokens still work")
    print("  • Existing auth_dependency functions remain functional")
    print("  • Legacy tokens have admin privileges")
    print("  • Gradual migration supported")


def show_current_users():
    """Show current users in the system."""
    print("\n👥 Current Users in System")
    print("-" * 50)

    try:
        auth_service = get_multi_user_auth_service()
        users = auth_service.list_users(include_inactive=True)

        if not users:
            print("No users found in the system.")
        else:
            for user in users:
                status = "Active" if user.is_active else "Inactive"
                admin = "Admin" if user.is_admin else "User"
                has_token = "Yes" if user.current_token else "No"

                print(f"📧 {user.email}")
                print(f"   Name: {user.username or 'Not set'}")
                print(f"   Role: {admin}")
                print(f"   Status: {status}")
                print(f"   Has Token: {has_token}")
                print(f"   Created: {user.created_at}")
                if user.last_login_at:
                    print(f"   Last Login: {user.last_login_at}")
                print()

    except Exception as e:
        print(f"Error retrieving users: {e}")


def main():
    """Run the demo."""
    try:
        demo_basic_usage()
        show_current_users()

        print("\n🎉 Demo completed successfully!")
        print("\nNext steps:")
        print("1. Start the application: bash run-fenrir-app.sh")
        print("2. Visit http://localhost:8080/auth-users/ for user management")
        print("3. Use the API endpoints for programmatic access")
        print("4. Configure email settings in your environment for notifications")

    except Exception as e:
        print(f"❌ Demo failed: {e}")
        import traceback

        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
