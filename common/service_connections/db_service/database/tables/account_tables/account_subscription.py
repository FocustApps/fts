"""
AccountSubscription table model for managing account subscriptions.
"""

from datetime import datetime, timezone
from typing import Optional

import sqlalchemy as sql
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import ENUM

from common.service_connections.db_service.database.base import Base


class AccountSubscriptionTable(Base):
    """AccountSubscription model representing subscriptions for accounts.

    Business Logic Documentation:

    1. Define at a high level what this table is suppose to represent in terms of a goal
       or goals that need to be accomplished by a user?
       - Manages subscription plans and billing information for accounts. Defines service
         tier (small, medium, large, big_af), payment terms, and payment methods. Enables
         feature gating and resource limits based on subscription level.

    2. What level of user should be interacting with this table?
       - Super Admin: Full CRUD access for managing all subscriptions
       - Account Owner: Read access to view their subscription, Update for payment method changes
       - Billing System: Automated updates for subscription renewals and changes

    3. What are the names of the tables that are either above or below this table in the
       data structure? This is to understand where to put in in a architecture diagram.
       - Above: AccountTable (via subscription_id reference in AccountTable)
       - Below: None (leaf node)

    4. Should a record in this table be deleted based on the deletion of a record in a
       different table? If so, what table?
       - No. Subscription records should be preserved for billing history and audit.
         Should be marked inactive or expired rather than deleted.

    5. Will this table be require a connection a secure cloud provider service?
       - Yes, likely requires integration with payment processing services (Stripe, PayPal)
         for payment method validation and subscription management.
    """

    __tablename__ = "account_subscription"

    account_subscription_id: Mapped[str] = mapped_column(sql.String(36), primary_key=True)
    subscription_plan_type: Mapped[str] = mapped_column(
        ENUM("small", "medium", "large", "big_af", name="plan_type_enum"), nullable=False
    )
    payment_term: Mapped[str] = mapped_column(
        ENUM("monthly", "yearly", "perpetual", name="payment_term_enum"), nullable=False
    )
    payment_type: Mapped[str] = mapped_column(
        ENUM(
            "credit_card", "paypal", "bank_transfer", "system", name="payment_type_enum"
        ),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        sql.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(sql.DateTime, nullable=True)

    def __repr__(self) -> str:
        return f"<AccountSubscription(id={self.account_subscription_id}, \
        plan_type='{self.subscription_plan_type}', \
        payment_term='{self.payment_term}', payment_type='{self.payment_type}')>"
