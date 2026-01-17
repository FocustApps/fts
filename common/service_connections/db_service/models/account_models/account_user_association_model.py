"""
Account-user association model for managing many-to-many user-account relationships.
"""

import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel, Field
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from common.service_connections.db_service.database.tables.account_tables.auth_user_account_association import (
    AuthUserAccountAssociation,
)
from common.service_connections.db_service.database.enums import AccountRoleEnum
from common.service_connections.db_service.database.engine import (
    get_database_session as session,
)


class AccountUserAssociationModel(BaseModel):
    """
    Schema for representing user-account association with role.
    """

    association_id: Optional[str] = None
    auth_user_id: str
    account_id: str
    role: str = AccountRoleEnum.MEMBER.value
    is_primary: bool = False  # New field for primary account designation
    is_active: bool = True
    invited_by_user_id: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: Optional[datetime] = None


class AccountUserWithDetailsModel(BaseModel):
    """
    Association with user details for display purposes.
    """

    association_id: str
    auth_user_id: str
    account_id: str
    role: str
    is_primary: bool
    is_active: bool
    user_email: Optional[str] = None
    user_username: Optional[str] = None
    invited_by_user_id: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


class BulkOperationResult(BaseModel):
    """
    Result summary for bulk operations.
    """

    total: int
    successful: int
    failed: int
    errors: list[str] = []


def add_user_to_account(
    auth_user_id: str,
    account_id: str,
    role: str = AccountRoleEnum.MEMBER.value,
    is_primary: bool = False,
    invited_by_user_id: Optional[str] = None,
    engine: Engine = None,
) -> str:
    """
    Add a user to an account with a specific role.

    Args:
        auth_user_id: User ID to add
        account_id: Account ID
        role: User's role in the account (owner/admin/member/viewer)
        is_primary: Whether this is the user's primary account
        invited_by_user_id: ID of the user who invited this user
        engine: Database engine

    Returns:
        str: The association_id

    Raises:
        ValueError: If association already exists or if attempting to set multiple primary accounts
    """
    with session(engine) as db_session:
        # Check if association already exists
        existing = (
            db_session.query(AuthUserAccountAssociation)
            .filter(
                AuthUserAccountAssociation.auth_user_id == auth_user_id,
                AuthUserAccountAssociation.account_id == account_id,
            )
            .first()
        )

        if existing:
            raise ValueError(
                f"User {auth_user_id} is already associated with account {account_id}"
            )

        # If setting as primary, unset any existing primary for this user
        if is_primary:
            _unset_primary_accounts(auth_user_id, db_session)

        # Create association
        association_id = str(uuid4())
        association = AuthUserAccountAssociation(
            association_id=association_id,
            auth_user_id=auth_user_id,
            account_id=account_id,
            role=role,
            is_primary=is_primary,  # Set the is_primary field
            is_active=True,
            invited_by_user_id=invited_by_user_id,
            created_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )

        db_session.add(association)
        db_session.commit()

    return association_id


def bulk_add_users_to_account(
    user_ids: list[str],
    account_id: str,
    role: str = AccountRoleEnum.MEMBER.value,
    invited_by_user_id: Optional[str] = None,
    engine: Engine = None,
) -> BulkOperationResult:
    """
    Add multiple users to an account in bulk.

    Args:
        user_ids: List of user IDs to add
        account_id: Account ID
        role: Role to assign to all users
        invited_by_user_id: ID of the user who invited these users
        engine: Database engine

    Returns:
        BulkOperationResult: Summary of the operation
    """
    result = BulkOperationResult(total=len(user_ids), successful=0, failed=0, errors=[])

    for user_id in user_ids:
        try:
            add_user_to_account(
                auth_user_id=user_id,
                account_id=account_id,
                role=role,
                is_primary=False,  # Bulk operations don't set primary
                invited_by_user_id=invited_by_user_id,
                engine=engine,
            )
            result.successful += 1
        except Exception as e:
            result.failed += 1
            result.errors.append(f"User {user_id}: {str(e)}")
            logging.error(f"Failed to add user {user_id} to account {account_id}: {e}")

    return result


def update_user_role(
    auth_user_id: str, account_id: str, new_role: str, engine: Engine
) -> bool:
    """
    Update a user's role in an account.

    Args:
        auth_user_id: User ID
        account_id: Account ID
        new_role: New role to assign
        engine: Database engine

    Returns:
        bool: True if successful

    Raises:
        ValueError: If association not found
    """
    with session(engine) as db_session:
        association = (
            db_session.query(AuthUserAccountAssociation)
            .filter(
                AuthUserAccountAssociation.auth_user_id == auth_user_id,
                AuthUserAccountAssociation.account_id == account_id,
            )
            .first()
        )

        if not association:
            raise ValueError(
                f"User {auth_user_id} is not associated with account {account_id}"
            )

        association.role = new_role
        association.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
        db_session.commit()

    return True


def bulk_update_roles(
    updates: list[tuple[str, str, str]], engine: Engine
) -> BulkOperationResult:
    """
    Update roles for multiple users in bulk.

    Args:
        updates: List of tuples (auth_user_id, account_id, new_role)
        engine: Database engine

    Returns:
        BulkOperationResult: Summary of the operation
    """
    result = BulkOperationResult(total=len(updates), successful=0, failed=0, errors=[])

    for auth_user_id, account_id, new_role in updates:
        try:
            update_user_role(auth_user_id, account_id, new_role, engine)
            result.successful += 1
        except Exception as e:
            result.failed += 1
            result.errors.append(f"User {auth_user_id} in account {account_id}: {str(e)}")
            logging.error(
                f"Failed to update role for user {auth_user_id} in account {account_id}: {e}"
            )

    return result


def set_primary_account(auth_user_id: str, account_id: str, engine: Engine) -> bool:
    """
    Set an account as the user's primary account.
    Unsets any other primary account for the user.

    Args:
        auth_user_id: User ID
        account_id: Account ID to set as primary
        engine: Database engine

    Returns:
        bool: True if successful

    Raises:
        ValueError: If association not found
    """
    with session(engine) as db_session:
        # Check if association exists
        target_association = (
            db_session.query(AuthUserAccountAssociation)
            .filter(
                AuthUserAccountAssociation.auth_user_id == auth_user_id,
                AuthUserAccountAssociation.account_id == account_id,
            )
            .first()
        )

        if not target_association:
            raise ValueError(
                f"User {auth_user_id} is not associated with account {account_id}"
            )

        # Unset all other primary accounts for this user
        _unset_primary_accounts(auth_user_id, db_session)

        # Set this as primary (need to update within same session)
        target_association_updated = (
            db_session.query(AuthUserAccountAssociation)
            .filter(
                AuthUserAccountAssociation.auth_user_id == auth_user_id,
                AuthUserAccountAssociation.account_id == account_id,
            )
            .first()
        )
        target_association_updated.is_primary = True
        target_association_updated.updated_at = datetime.now(timezone.utc).replace(
            tzinfo=None
        )
        db_session.commit()

    return True


def remove_user_from_account(auth_user_id: str, account_id: str, engine: Engine) -> bool:
    """
    Remove a user from an account (hard delete).

    Args:
        auth_user_id: User ID
        account_id: Account ID
        engine: Database engine

    Returns:
        bool: True if successful

    Raises:
        ValueError: If association not found
    """
    with session(engine) as db_session:
        association = (
            db_session.query(AuthUserAccountAssociation)
            .filter(
                AuthUserAccountAssociation.auth_user_id == auth_user_id,
                AuthUserAccountAssociation.account_id == account_id,
            )
            .first()
        )

        if not association:
            raise ValueError(
                f"User {auth_user_id} is not associated with account {account_id}"
            )

        db_session.delete(association)
        db_session.commit()

    return True


def bulk_remove_users(
    removals: list[tuple[str, str]], engine: Engine
) -> BulkOperationResult:
    """
    Remove multiple users from accounts in bulk.

    Args:
        removals: List of tuples (auth_user_id, account_id)
        engine: Database engine

    Returns:
        BulkOperationResult: Summary of the operation
    """
    result = BulkOperationResult(total=len(removals), successful=0, failed=0, errors=[])

    for auth_user_id, account_id in removals:
        try:
            remove_user_from_account(auth_user_id, account_id, engine)
            result.successful += 1
        except Exception as e:
            result.failed += 1
            result.errors.append(
                f"User {auth_user_id} from account {account_id}: {str(e)}"
            )
            logging.error(
                f"Failed to remove user {auth_user_id} from account {account_id}: {e}"
            )

    return result


def query_users_by_account(
    account_id: str, db_session: Session, engine: Engine, active_only: bool = True
) -> list[AccountUserWithDetailsModel]:
    """
    Query all users associated with an account.

    Args:
        account_id: Account ID
        db_session: Active database session
        engine: Database engine
        active_only: If True, only return active associations

    Returns:
        List[AccountUserWithDetailsModel]: List of users with details
    """
    from common.service_connections.db_service.database.tables.account_tables.auth_user import (
        AuthUserTable,
    )

    query = (
        db_session.query(
            AuthUserAccountAssociation,
            AuthUserTable.email,
            AuthUserTable.username,
        )
        .join(
            AuthUserTable,
            AuthUserAccountAssociation.auth_user_id == AuthUserTable.auth_user_id,
        )
        .filter(AuthUserAccountAssociation.account_id == account_id)
    )

    if active_only:
        query = query.filter(AuthUserAccountAssociation.is_active == True)

    results = query.all()

    return [
        AccountUserWithDetailsModel(
            association_id=assoc.association_id,
            auth_user_id=assoc.auth_user_id,
            account_id=assoc.account_id,
            role=assoc.role,
            is_primary=getattr(assoc, "is_primary", False),
            is_active=assoc.is_active,
            user_email=email,
            user_username=username,
            invited_by_user_id=assoc.invited_by_user_id,
            created_at=assoc.created_at,
            updated_at=assoc.updated_at,
        )
        for assoc, email, username in results
    ]


def query_accounts_by_user(
    auth_user_id: str, db_session: Session, engine: Engine, active_only: bool = True
) -> list[AccountUserAssociationModel]:
    """
    Query all accounts a user belongs to.

    Args:
        auth_user_id: User ID
        db_session: Active database session
        engine: Database engine
        active_only: If True, only return active associations

    Returns:
        List[AccountUserAssociationModel]: List of account associations
    """
    query = db_session.query(AuthUserAccountAssociation).filter(
        AuthUserAccountAssociation.auth_user_id == auth_user_id
    )

    if active_only:
        query = query.filter(AuthUserAccountAssociation.is_active == True)

    associations = query.all()

    return [
        AccountUserAssociationModel(
            association_id=assoc.association_id,
            auth_user_id=assoc.auth_user_id,
            account_id=assoc.account_id,
            role=assoc.role,
            is_primary=getattr(assoc, "is_primary", False),
            is_active=assoc.is_active,
            invited_by_user_id=assoc.invited_by_user_id,
            created_at=assoc.created_at,
            updated_at=assoc.updated_at,
        )
        for assoc in associations
    ]


def query_user_primary_account(
    auth_user_id: str, db_session: Session, engine: Engine
) -> Optional[AccountUserAssociationModel]:
    """
    Query a user's primary account.

    Args:
        auth_user_id: User ID
        db_session: Active database session
        engine: Database engine

    Returns:
        Optional[AccountUserAssociationModel]: Primary account association or None
    """
    association = (
        db_session.query(AuthUserAccountAssociation)
        .filter(
            AuthUserAccountAssociation.auth_user_id == auth_user_id,
            AuthUserAccountAssociation.is_primary == True,
            AuthUserAccountAssociation.is_active == True,
        )
        .first()
    )

    if not association:
        return None

    return AccountUserAssociationModel(
        association_id=association.association_id,
        auth_user_id=association.auth_user_id,
        account_id=association.account_id,
        role=association.role,
        is_primary=getattr(association, "is_primary", False),
        is_active=association.is_active,
        invited_by_user_id=association.invited_by_user_id,
        created_at=association.created_at,
        updated_at=association.updated_at,
    )


def query_user_role_in_account(
    auth_user_id: str, account_id: str, db_session: Session, engine: Engine
) -> Optional[str]:
    """
    Query a user's role in a specific account.

    Args:
        auth_user_id: User ID
        account_id: Account ID
        db_session: Active database session
        engine: Database engine

    Returns:
        Optional[str]: Role string or None if not found
    """
    association = (
        db_session.query(AuthUserAccountAssociation)
        .filter(
            AuthUserAccountAssociation.auth_user_id == auth_user_id,
            AuthUserAccountAssociation.account_id == account_id,
            AuthUserAccountAssociation.is_active == True,
        )
        .first()
    )

    return association.role if association else None


def _unset_primary_accounts(auth_user_id: str, db_session: Session) -> None:
    """
    Helper to unset all primary accounts for a user.
    Must be called within an active session.

    Args:
        auth_user_id: User ID
        db_session: Active database session
    """
    # Note: is_primary column may not exist yet in database
    # This is a forward-compatible implementation
    try:
        db_session.query(AuthUserAccountAssociation).filter(
            AuthUserAccountAssociation.auth_user_id == auth_user_id
        ).update(
            {
                "is_primary": False,
                "updated_at": datetime.now(timezone.utc).replace(tzinfo=None),
            }
        )
    except Exception as e:
        logging.warning(f"Could not unset primary accounts (column may not exist): {e}")


__all__ = [
    "AccountUserAssociationModel",
    "AccountUserWithDetailsModel",
    "BulkOperationResult",
    "add_user_to_account",
    "bulk_add_users_to_account",
    "update_user_role",
    "bulk_update_roles",
    "set_primary_account",
    "remove_user_from_account",
    "bulk_remove_users",
    "query_users_by_account",
    "query_accounts_by_user",
    "query_user_primary_account",
    "query_user_role_in_account",
]
