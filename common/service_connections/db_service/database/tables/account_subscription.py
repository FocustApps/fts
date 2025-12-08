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
    """AccountSubscription model representing subscriptions for accounts."""

    __tablename__ = "account_subscription"

    account_subscription_id: Mapped[str] = mapped_column(sql.String(36), primary_key=True)
    subscription_plan_type: Mapped[str] = mapped_column(
        ENUM("small", "medium", "large", "big_af", name="plan_type_enum"), nullable=False
    )
    payment_term: Mapped[str] = mapped_column(
        ENUM("monthly", "yearly", "perpetual", name="payment_term_enum"), nullable=False
    )
    payment_type: Mapped[str] = mapped_column(
        ENUM("credit_card", "paypal", "bank_transfer", name="payment_type_enum"),
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
