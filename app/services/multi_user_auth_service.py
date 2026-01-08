"""
Multi-user authentication service for email-based authentication.

Extends the existing AuthService to support multiple users with database-backed
token management and email-specific authentication flows.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional, List
from sqlalchemy.exc import SQLAlchemyError

from app.services.auth_service import AuthService, AuthTokenError, logger
from app.services.email_service import (
    send_multiuser_token_notification,
    EmailServiceError,
)
from app.services.storage import StorageService, create_storage_service, StorageError
from app.config import get_base_app_config, get_storage_config
from common.service_connections.db_service.database import (
    get_database_session,
)
from common.service_connections.db_service.models.auth_user_model import (
    AuthUserModel,
    insert_auth_user,
    query_auth_user_by_email,
    query_auth_user_by_id,
    query_all_auth_users,
    query_active_auth_users,
    deactivate_auth_user,
    update_auth_user_by_id,
    check_email_exists,
)


class MultiUserAuthError(AuthTokenError):
    """Raised when multi-user authentication operations fail."""

    pass


class MultiUserAuthService:
    """
    Manages authentication for multiple users with email-based tokens.

    Features:
    - Email-based user identification
    - Per-user token management with database persistence
    - Admin user management capabilities
    - Token expiration and rotation
    """

    def __init__(self, token_expiry_hours: int = 24):
        """
        Initialize the multi-user authentication service.

        Args:
            token_expiry_hours: Hours until tokens expire (default 24)
        """
        self.token_expiry_hours = token_expiry_hours
        self._base_auth_service = AuthService("/tmp/multiuser_auth_token.txt")

        # Initialize storage service if enabled
        self._storage_service: Optional[StorageService] = None
        try:
            app_config = get_base_app_config()
            if app_config.storage_enabled:
                storage_config = get_storage_config(app_config)
                self._storage_service = create_storage_service(storage_config)
                logger.info(
                    f"Storage service initialized with provider: {storage_config['provider_type']}"
                )
            else:
                logger.info("Storage service disabled in configuration")
        except Exception as e:
            logger.warning(f"Failed to initialize storage service: {e}")
            # Continue without storage - not critical for auth functionality

        logger.info("MultiUserAuthService initialized")

    def _execute_auth_model_function(self, func, *args, **kwargs):
        """
        Adapter to execute auth_user_model functions with current session management.

        Converts get_database_session() context manager pattern to
        session factory + engine pattern expected by auth_user_model functions.

        Args:
            func: The auth_user_model function to execute
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function

        Returns:
            Result from the auth_user_model function

        Raises:
            SQLAlchemyError: If database operation fails
        """
        try:
            with get_database_session() as session:
                # Get the session class and engine from the active session
                session_class = session.__class__
                engine = session.bind

                # Call the auth_user_model function with session class and engine
                return func(*args, session=session_class, engine=engine, **kwargs)

        except Exception as e:
            logger.error(f"Error executing auth_user_model function {func.__name__}: {e}")
            raise

    async def add_user(
        self,
        email: str,
        username: Optional[str] = None,
        is_admin: bool = False,
        send_welcome_email: bool = True,
    ) -> AuthUserModel:
        """
        Add a new authenticated user to the system.

        Args:
            email: User's email address (must be unique)
            username: Optional display name
            is_admin: Whether user has admin privileges
            send_welcome_email: Whether to send welcome email with initial token

        Returns:
            Created AuthUserModel instance

        Raises:
            MultiUserAuthError: If user already exists or creation fails
        """
        try:
            # Check if user already exists
            if self._execute_auth_model_function(check_email_exists, email=email):
                raise MultiUserAuthError(f"User with email {email} already exists")

            # Create new AuthUserModel
            new_auth_user = AuthUserModel(
                email=email,
                username=username,
                is_admin=is_admin,
                is_active=True,
                created_at=datetime.now(timezone.utc),
            )

            # Insert user using auth_user_model function
            created_user = self._execute_auth_model_function(
                insert_auth_user, auth_user=new_auth_user
            )

            logger.info(f"Added new user: {email} (ID: {created_user.auth_user_id})")

            # Send welcome email with initial token if requested
            if send_welcome_email:
                try:
                    initial_token = await self.generate_user_token(
                        email, send_email=False
                    )
                    send_multiuser_token_notification(
                        user_email=email,
                        token=initial_token,
                        username=username,
                        is_new_user=True,
                    )
                    logger.info(f"Welcome email sent to new user: {email}")
                except EmailServiceError as e:
                    logger.warning(f"Failed to send welcome email to {email}: {e}")
                    # Don't fail user creation if email fails

            return created_user

        except SQLAlchemyError as e:
            logger.error(f"Database error adding user {email}: {e}")
            raise MultiUserAuthError(f"Failed to add user: {e}")

    async def generate_user_token(self, email: str, send_email: bool = True) -> str:
        """
        Generate and store a new token for a specific user.

        Args:
            email: User's email address
            send_email: Whether to send email notification with the new token

        Returns:
            Generated token

        Raises:
            MultiUserAuthError: If user not found or token generation fails
        """
        try:
            # Get user by email
            user = self._execute_auth_model_function(
                query_auth_user_by_email, email=email
            )
            if not user or not user.is_active:
                raise MultiUserAuthError(f"Active user not found: {email}")

            # Generate new token
            new_token = self._base_auth_service.generate_token()
            expires_at = datetime.now(timezone.utc) + timedelta(
                hours=self.token_expiry_hours
            )

            # Update user with new token using auth_user_model
            user.current_token = new_token
            user.token_expires_at = expires_at
            user.updated_at = datetime.now(timezone.utc)

            self._execute_auth_model_function(
                update_auth_user_by_id, user_id=user.auth_user_id, auth_user=user
            )

            logger.info(f"Generated new token for user: {email}")

            # Store token in configured storage if available
            if self._storage_service:
                try:
                    await self._store_token_to_storage(email, new_token, expires_at)
                except Exception as e:
                    logger.warning(f"Failed to store token to storage for {email}: {e}")
                    # Don't fail token generation if storage fails

            # Send email notification if requested
            if send_email:
                try:
                    send_multiuser_token_notification(
                        user_email=email,
                        token=new_token,
                        username=user.username,
                        is_new_user=False,
                    )
                    logger.info(f"Token notification email sent to: {email}")
                except EmailServiceError as e:
                    logger.warning(f"Failed to send token notification to {email}: {e}")
                    # Don't fail token generation if email fails

            return new_token

        except SQLAlchemyError as e:
            logger.error(f"Database error generating token for {email}: {e}")
            raise MultiUserAuthError(f"Failed to generate token: {e}")

    async def _store_token_to_storage(
        self, email: str, token: str, expires_at: datetime
    ) -> None:
        """
        Store token to configured storage service.

        Args:
            email: User's email address
            token: Generated token
            expires_at: Token expiration datetime
        """
        if not self._storage_service:
            return

        try:
            await self._storage_service.store_user_token(
                user_email=email,
                token=token,
                token_expires_at=expires_at.isoformat(),
                additional_metadata={
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "expiry_hours": str(self.token_expiry_hours),
                },
            )
            logger.debug(f"Token stored to storage for user: {email}")
        except StorageError as e:
            logger.error(f"Storage error for user {email}: {e}")
            raise

    def validate_user_token(self, email: str, provided_token: str) -> bool:
        """
        Validate a token for a specific user.

        Args:
            email: User's email address
            provided_token: Token to validate

        Returns:
            True if token is valid and not expired
        """
        if not email or not provided_token:
            return False

        try:
            user = self._execute_auth_model_function(
                query_auth_user_by_email, email=email
            )
            if not user or not user.is_active:
                logger.debug(f"User not found or inactive: {email}")
                return False

            # Check if token matches and is not expired
            if (
                user.current_token == provided_token
                and user.token_expires_at
                and datetime.now(timezone.utc)
                < user.token_expires_at.replace(tzinfo=timezone.utc)
            ):
                # Update last login time
                user.last_login_at = datetime.now(timezone.utc)
                user.updated_at = datetime.now(timezone.utc)
                self._execute_auth_model_function(
                    update_auth_user_by_id, user_id=user.auth_user_id, auth_user=user
                )

                logger.debug(f"Token validated successfully for user: {email}")
                return True

            logger.debug(f"Token validation failed for user: {email}")
            return False

        except SQLAlchemyError as e:
            logger.error(f"Database error validating token for {email}: {e}")
            return False

    def get_user_by_email(self, email: str) -> Optional[AuthUserModel]:
        """
        Get user information by email address.

        Args:
            email: User's email address

        Returns:
            AuthUserModel instance or None if not found
        """
        try:
            return self._execute_auth_model_function(
                query_auth_user_by_email, email=email
            )
        except SQLAlchemyError as e:
            logger.error(f"Database error getting user {email}: {e}")
            return None

    def get_user_by_id(self, user_id: int) -> Optional[AuthUserModel]:
        """
        Get user information by user ID.

        Args:
            user_id: User's unique ID

        Returns:
            AuthUserModel instance or None if not found
        """
        try:
            return self._execute_auth_model_function(
                query_auth_user_by_id, user_id=user_id
            )
        except (SQLAlchemyError, ValueError) as e:
            logger.error(f"Database error getting user ID {user_id}: {e}")
            return None

    def list_users(self, include_inactive: bool = False) -> List[AuthUserModel]:
        """
        List all users in the system.

        Args:
            include_inactive: Whether to include inactive users

        Returns:
            List of AuthUserModel instances
        """
        try:
            if include_inactive:
                return self._execute_auth_model_function(query_all_auth_users)
            else:
                return self._execute_auth_model_function(query_active_auth_users)
        except SQLAlchemyError as e:
            logger.error(f"Database error listing users: {e}")
            return []

    def deactivate_user(self, email: str) -> bool:
        """
        Deactivate a user (soft delete).

        Args:
            email: User's email address

        Returns:
            True if user was deactivated, False if not found
        """
        try:
            # Get user by email first
            user = self._execute_auth_model_function(
                query_auth_user_by_email, email=email
            )
            if not user:
                return False

            # Deactivate user using auth_user_model function
            self._execute_auth_model_function(
                deactivate_auth_user, user_id=user.auth_user_id
            )

            logger.info(f"Deactivated user: {email}")
            return True

        except (SQLAlchemyError, ValueError) as e:
            logger.error(f"Database error deactivating user {email}: {e}")
            return False

    async def rotate_user_token(self, email: str) -> Optional[str]:
        """
        Force rotation of a user's token.

        Args:
            email: User's email address

        Returns:
            New token or None if user not found
        """
        try:
            user = self.get_user_by_email(email)
            if not user or not user.is_active:
                return None

            return await self.generate_user_token(email)

        except MultiUserAuthError:
            return None

    def clean_expired_tokens(self) -> int:
        """
        Remove expired tokens from all users.

        Returns:
            Number of tokens cleaned
        """
        try:
            # Get all users
            all_users = self._execute_auth_model_function(query_all_auth_users)

            count = 0
            current_time = datetime.now(timezone.utc)

            for user in all_users:
                # Check if user has expired token
                if (
                    user.current_token
                    and user.token_expires_at
                    and current_time > user.token_expires_at.replace(tzinfo=timezone.utc)
                ):

                    # Clear expired token
                    user.current_token = None
                    user.token_expires_at = None
                    user.updated_at = current_time

                    self._execute_auth_model_function(
                        update_auth_user_by_id, user_id=user.auth_user_id, auth_user=user
                    )
                    count += 1

            if count > 0:
                logger.info(f"Cleaned {count} expired tokens")

            return count

        except SQLAlchemyError as e:
            logger.error(f"Database error cleaning expired tokens: {e}")
            return 0

    def invalidate_user_token(self, email: str, token: str) -> bool:
        """
        Invalidate a specific token for a user.

        Args:
            email: User's email address
            token: Token to invalidate

        Returns:
            True if token was invalidated, False if not found or error

        Raises:
            MultiUserAuthError: If database operation fails
        """
        try:
            user = self._execute_auth_model_function(
                query_auth_user_by_email, email=email.lower()
            )

            if not user:
                logger.warning(f"Cannot invalidate token: User {email} not found")
                return False

            if not user.current_token:
                logger.debug(f"No active token to invalidate for user {email}")
                return False

            # Check if the provided token matches the current token
            if user.current_token != token:
                logger.warning(f"Token mismatch during invalidation for user {email}")
                return False

            # Invalidate the token
            user.current_token = None
            user.token_expires_at = None
            user.updated_at = datetime.now(timezone.utc)

            self._execute_auth_model_function(
                update_auth_user_by_id, user_id=user.auth_user_id, auth_user=user
            )

            logger.info(f"Token invalidated for user {email}")
            return True

        except SQLAlchemyError as e:
            logger.error(f"Database error invalidating token for {email}: {e}")
            raise MultiUserAuthError(f"Failed to invalidate token: {e}")

    def invalidate_all_user_tokens(self, email: str) -> bool:
        """
        Invalidate all tokens for a specific user.

        Args:
            email: User's email address

        Returns:
            True if successful, False if user not found

        Raises:
            MultiUserAuthError: If database operation fails
        """
        try:
            user = self._execute_auth_model_function(
                query_auth_user_by_email, email=email.lower()
            )

            if not user:
                logger.warning(f"Cannot invalidate tokens: User {email} not found")
                return False

            # Clear all token information
            user.current_token = None
            user.token_expires_at = None
            user.updated_at = datetime.now(timezone.utc)

            self._execute_auth_model_function(
                update_auth_user_by_id, user_id=user.auth_user_id, auth_user=user
            )

            logger.info(f"All tokens invalidated for user {email}")
            return True

        except SQLAlchemyError as e:
            logger.error(f"Database error invalidating all tokens for {email}: {e}")
            raise MultiUserAuthError(f"Failed to invalidate tokens: {e}")


# Global instance for application use
_multi_user_auth_service: Optional[MultiUserAuthService] = None


def get_multi_user_auth_service() -> MultiUserAuthService:
    """Get the global multi-user authentication service instance."""
    global _multi_user_auth_service

    if _multi_user_auth_service is None:
        _multi_user_auth_service = MultiUserAuthService()

    return _multi_user_auth_service


def initialize_multi_user_auth_service(
    token_expiry_hours: int = 24,
) -> MultiUserAuthService:
    """
    Initialize and configure the global multi-user authentication service.

    Args:
        token_expiry_hours: Hours until tokens expire

    Returns:
        Configured MultiUserAuthService instance
    """
    global _multi_user_auth_service

    _multi_user_auth_service = MultiUserAuthService(token_expiry_hours)
    return _multi_user_auth_service
