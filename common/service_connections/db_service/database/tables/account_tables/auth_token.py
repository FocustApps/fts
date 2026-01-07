"""
Auth token table model for multi-device authentication token management.
"""

from datetime import datetime, timezone
from typing import Optional, TYPE_CHECKING
from uuid import uuid4

import sqlalchemy as sql
from sqlalchemy.orm import Mapped, mapped_column, relationship

from common.service_connections.db_service.database.base import Base

if TYPE_CHECKING:
    from common.service_connections.db_service.database.tables.account_tables.auth_user import (
        AuthUserTable,
    )


class AuthTokenTable(Base):
    """Auth token table for multi-device token authentication and rotation.

    Business Logic Documentation:

    1. Define at a high level what this table is suppose to represent in terms of a goal
       or goals that need to be accomplished by a user?
       - Manages authentication tokens for user sessions across multiple devices. Enables
         token rotation for security, tracks device information for session management,
         and supports simultaneous login from different devices (desktop, mobile, etc.).
         Replaces single-token approach with scalable multi-token architecture.

    2. What level of user should be interacting with this table?
       - System/Authentication Service: Primary writer - creates and validates tokens
       - Users: Indirect interaction through login/logout actions
       - Admin: Read access for security auditing and troubleshooting
       - Background Tasks: Token rotation and cleanup jobs

    3. What are the names of the tables that are either above or below this table in the
       data structure? This is to understand where to put in in a architecture diagram.
       - Above: AuthUserTable (via auth_user_id foreign key with CASCADE delete)
       - Below: None (leaf node in hierarchy)

    4. Should a record in this table be deleted based on the deletion of a record in a
       different table? If so, what table?
       - Yes. CASCADE delete when parent AuthUserTable record is deleted (enforced by
         foreign key constraint ondelete='CASCADE'). When user is deactivated, tokens
         are revoked (is_active=False) but not deleted for audit trail.

    5. Will this table be require a connection a secure cloud provider service?
       - No direct cloud connection required for core functionality. Optional: token
         storage could integrate with Redis/ElastiCache for distributed caching in
         multi-server deployments.
    """

    __tablename__ = "auth_tokens"

    token_id: Mapped[str] = mapped_column(
        sql.String(36), primary_key=True, default=lambda: str(uuid4())
    )
    auth_user_id: Mapped[str] = mapped_column(
        sql.String(36),
        sql.ForeignKey("auth_users.id", ondelete="CASCADE"),
        nullable=False,
    )
    token_value: Mapped[str] = mapped_column(sql.String(64), unique=True, nullable=False)
    token_expires_at: Mapped[datetime] = mapped_column(sql.DateTime, nullable=False)
    device_info: Mapped[Optional[str]] = mapped_column(sql.String(255), nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(sql.String(45), nullable=True)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(sql.DateTime, nullable=True)
    is_active: Mapped[bool] = mapped_column(sql.Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        sql.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    revoked_at: Mapped[Optional[datetime]] = mapped_column(sql.DateTime, nullable=True)

    # Relationship to AuthUserTable
    user: Mapped["AuthUserTable"] = relationship("AuthUserTable", back_populates="tokens")

    __table_args__ = (
        sql.Index("idx_auth_tokens_pk", "token_id", postgresql_using="btree"),
        sql.Index("idx_auth_tokens_value", "token_value", unique=True),
        sql.Index("idx_auth_tokens_user_active", "auth_user_id", "is_active"),
        sql.Index(
            "idx_auth_tokens_expires",
            "token_expires_at",
            postgresql_where=sql.text("is_active = true"),
        ),
        sql.CheckConstraint("token_expires_at > created_at", name="chk_token_expiry"),
    )

    def __repr__(self) -> str:
        return f"<AuthToken(id={self.token_id}, user_id='{self.auth_user_id}', expires='{self.token_expires_at}', active={self.is_active})>"


__all__ = ["AuthTokenTable"]
