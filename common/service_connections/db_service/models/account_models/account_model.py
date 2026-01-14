"""
Account model for managing organization accounts.
"""

import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel, Field
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from common.service_connections.db_service.database.tables.account_tables.account import (
    AccountTable,
)
from common.service_connections.db_service.database.engine import (
    get_database_session as session,
)


class AccountModel(BaseModel):
    """
    Schema for representing an organization account.

    Fields match AccountTable database schema.
    """

    account_id: Optional[str] = None
    account_name: str
    owner_user_id: str
    is_active: bool = True
    logo_url: Optional[str] = None
    primary_contact: Optional[str] = None
    subscription_id: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: Optional[datetime] = None


class AccountWithOwnerModel(BaseModel):
    """
    Account model with owner user information for detailed views.
    """

    account_id: str
    account_name: str
    owner_user_id: str
    owner_email: Optional[str] = None
    owner_username: Optional[str] = None
    is_active: bool
    logo_url: Optional[str] = None
    primary_contact: Optional[str] = None
    subscription_id: Optional[str] = None
    user_count: int = 0
    created_at: datetime
    updated_at: Optional[datetime] = None


def insert_account(account: AccountModel, engine: Engine) -> str:
    """
    Insert a new account into the database.

    Args:
        account: Account data to insert
        engine: Database engine

    Returns:
        str: The account_id of the created account
    """
    if account.account_id:
        account.account_id = None
        logging.warning("Account ID will only be set by the system")

    with session(engine) as db_session:
        # Generate account ID
        account_id = str(uuid4())
        account.account_id = account_id
        account.created_at = datetime.now(timezone.utc).replace(tzinfo=None)

        # Create database record
        account_data = account.model_dump(exclude_none=True)
        db_account = AccountTable(**account_data)
        db_session.add(db_account)
        db_session.commit()

    return account_id


def query_account_by_id(
    account_id: str, db_session: Session, engine: Engine
) -> AccountModel:
    """
    Query an account by ID.

    Args:
        account_id: Account ID to search for
        db_session: Active database session
        engine: Database engine

    Returns:
        AccountModel: The account data

    Raises:
        ValueError: If account not found
    """
    db_account = db_session.get(AccountTable, account_id)
    if not db_account:
        raise ValueError(f"Account with ID {account_id} not found.")

    return AccountModel(**db_account.__dict__)


def query_all_accounts(
    db_session: Session, engine: Engine, active_only: bool = False
) -> list[AccountModel]:
    """
    Query all accounts.

    Args:
        db_session: Active database session
        engine: Database engine
        active_only: If True, only return active accounts

    Returns:
        List[AccountModel]: List of all accounts
    """
    query = db_session.query(AccountTable)

    if active_only:
        query = query.filter(AccountTable.is_active == True)

    accounts = query.all()
    return [AccountModel(**account.__dict__) for account in accounts]


def query_account_with_owner(
    account_id: str, db_session: Session, engine: Engine
) -> AccountWithOwnerModel:
    """
    Query an account with owner information.

    Args:
        account_id: Account ID to search for
        db_session: Active database session
        engine: Database engine

    Returns:
        AccountWithOwnerModel: Account data with owner info

    Raises:
        ValueError: If account not found
    """
    from common.service_connections.db_service.database.tables.account_tables.auth_user import (
        AuthUserTable,
    )
    from common.service_connections.db_service.database.tables.account_tables.auth_user_account_association import (
        AuthUserAccountAssociation,
    )

    # Query account with owner join
    result = (
        db_session.query(AccountTable, AuthUserTable.email, AuthUserTable.username)
        .join(
            AuthUserTable,
            AccountTable.owner_user_id == AuthUserTable.auth_user_id,
        )
        .filter(AccountTable.account_id == account_id)
        .first()
    )

    if not result:
        raise ValueError(f"Account with ID {account_id} not found.")

    account, owner_email, owner_username = result

    # Count users in account
    user_count = (
        db_session.query(AuthUserAccountAssociation)
        .filter(
            AuthUserAccountAssociation.account_id == account_id,
            AuthUserAccountAssociation.is_active == True,
        )
        .count()
    )

    return AccountWithOwnerModel(
        account_id=account.account_id,
        account_name=account.account_name,
        owner_user_id=account.owner_user_id,
        owner_email=owner_email,
        owner_username=owner_username,
        is_active=account.is_active,
        logo_url=account.logo_url,
        primary_contact=account.primary_contact,
        subscription_id=account.subscription_id,
        user_count=user_count,
        created_at=account.created_at,
        updated_at=account.updated_at,
    )


def update_account(account_id: str, account: AccountModel, engine: Engine) -> bool:
    """
    Update an existing account.

    Args:
        account_id: Account ID to update
        account: Updated account data
        engine: Database engine

    Returns:
        bool: True if successful

    Raises:
        ValueError: If account not found
    """
    with session(engine) as db_session:
        db_account = db_session.get(AccountTable, account_id)
        if not db_account:
            raise ValueError(f"Account with ID {account_id} not found.")

        # Update fields
        update_data = account.model_dump(
            exclude_unset=True, exclude={"account_id", "created_at"}
        )
        for key, value in update_data.items():
            setattr(db_account, key, value)

        db_account.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
        db_session.commit()

    return True


def deactivate_account(account_id: str, engine: Engine) -> bool:
    """
    Deactivate an account (soft delete).

    Args:
        account_id: Account ID to deactivate
        engine: Database engine

    Returns:
        bool: True if successful

    Raises:
        ValueError: If account not found
    """
    with session(engine) as db_session:
        db_account = db_session.get(AccountTable, account_id)
        if not db_account:
            raise ValueError(f"Account with ID {account_id} not found.")

        db_account.is_active = False
        db_account.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
        db_session.commit()

    return True


def activate_account(account_id: str, engine: Engine) -> bool:
    """
    Activate a deactivated account.

    Args:
        account_id: Account ID to activate
        engine: Database engine

    Returns:
        bool: True if successful

    Raises:
        ValueError: If account not found
    """
    with session(engine) as db_session:
        db_account = db_session.get(AccountTable, account_id)
        if not db_account:
            raise ValueError(f"Account with ID {account_id} not found.")

        db_account.is_active = True
        db_account.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
        db_session.commit()

    return True


__all__ = [
    "AccountModel",
    "AccountWithOwnerModel",
    "insert_account",
    "query_account_by_id",
    "query_all_accounts",
    "query_account_with_owner",
    "update_account",
    "deactivate_account",
    "activate_account",
]
