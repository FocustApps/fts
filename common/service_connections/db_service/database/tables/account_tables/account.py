"""
Account table model for managing accounts.
"""

from datetime import datetime, timezone
from typing import Optional, List, TYPE_CHECKING
import sqlalchemy as sql
from sqlalchemy.orm import Mapped, mapped_column, relationship

from common.service_connections.db_service.database.base import Base

if TYPE_CHECKING:
    from common.service_connections.db_service.database.tables.account_tables.auth_user import (
        AuthUserTable,
    )


class AccountTable(Base):
    """Account model representing user accounts.
    Accounts are going to be associated with companies that we will service. I

    Business Logic Documentation:

    1. Define at a high level what this table is suppose to represent in terms of a goal
       or goals that need to be accomplished by a user?
       - Represents top-level organization accounts that own and manage access to the Fenrir
         testing platform. Enables multi-tenant architecture where each account can have
         multiple users, subscriptions, and testing resources.

    2. What level of user should be interacting with this table?
       - Super Admin: Full CRUD access for all accounts
       - Account Owner: Read/Update access for their own account
       - Admin Users: Read-only access to account details

    3. What are the names of the tables that are either above or below this table in the
       data structure? This is to understand where to put in in a architecture diagram.
       - Above: None (top-level entity)
       - Below: AccountSubscriptionTable, AuthUserTable (via account_ids field)

    4. Should a record in this table be deleted based on the deletion of a record in a
       different table? If so, what table?
       - No. Account is a root entity and should only be soft-deleted (is_active=False)
         or hard-deleted by Super Admin action. Child records should be deleted when
         account is deleted.

    5. Will this table be require a connection a secure cloud provider service?
       - Yes, if logo_url references cloud storage (AWS S3, Azure Blob) for account logos.
    """

    __tablename__ = "account"

    account_id: Mapped[str] = mapped_column(sql.String(36), primary_key=True)
    account_name: Mapped[str] = mapped_column(
        sql.String(255), unique=True, nullable=False
    )
    owner_user_id: Mapped[str] = mapped_column(sql.String(36), unique=True)
    is_active: Mapped[bool] = mapped_column(sql.Boolean, default=True, nullable=False)
    logo_url: Mapped[Optional[str]] = mapped_column(sql.String(512))
    primary_contact: Mapped[Optional[str]] = mapped_column(sql.String(36))
    subscription_id: Mapped[Optional[str]] = mapped_column(sql.String(36))
    created_at: Mapped[datetime] = mapped_column(
        sql.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(sql.DateTime, nullable=True)

    # Relationships
    users: Mapped[List["AuthUserTable"]] = relationship(
        "AuthUserTable",
        secondary="auth_user_account_association",
        back_populates="accounts",
    )

    def __repr__(self) -> str:
        return f"<Account(id={self.account_id}, name='{self.account_name}', \
        owner_user_id='{self.owner_user_id}')>"
