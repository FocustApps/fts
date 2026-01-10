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
    """Auth token table for JWT refresh token rotation and device session management.

    Business Logic Documentation:

    1. Define at a high level what this table is suppose to represent in terms of a goal
       or goals that need to be accomplished by a user?
       - Manages JWT refresh tokens for user sessions across multiple devices. Implements
         token rotation with family tracking to detect token reuse attacks. Stores device
         information for user-visible session management. Each token has a corresponding
         access token JTI for revocation.

    2. What level of user should be interacting with this table?
       - System/Authentication Service: Primary writer - creates tokens on login/refresh
       - Users: Indirect interaction through login/logout/refresh actions, visible in UI
       - Admin: Read access for security auditing and session monitoring
       - Background Tasks: Cleanup jobs for inactive tokens

    3. What are the names of the tables that are either above or below this table in the
       data structure? This is to understand where to put in in a architecture diagram.
       - Above: AuthUserTable (via auth_user_id foreign key with CASCADE delete)
       - Below: None (leaf node in hierarchy)
       - Related: Self-referential via previous_token_id for rotation chain tracking

    4. Should a record in this table be deleted based on the deletion of a record in a
       different table? If so, what table?
       - Yes. CASCADE delete when parent AuthUserTable record is deleted (enforced by
         foreign key constraint ondelete='CASCADE'). When user logs out, tokens
         are marked inactive (is_active=False) but not deleted for audit trail.

    5. Will this table be require a connection a secure cloud provider service?
       - No direct cloud connection required for core functionality.
    """

    __tablename__ = "auth_tokens"

    token_id: Mapped[str] = mapped_column(
        sql.String(36), primary_key=True, default=lambda: str(uuid4())
    )
    auth_user_id: Mapped[str] = mapped_column(
        sql.String(36),
        sql.ForeignKey("auth_users.auth_user_id", ondelete="CASCADE"),
        nullable=False,
    )
    refresh_token_hash: Mapped[str] = mapped_column(
        sql.String(255), unique=True, nullable=False
    )  # Bcrypt hash of 64-char hex refresh token
    access_token_jti: Mapped[str] = mapped_column(
        sql.String(36), nullable=False, index=True
    )  # JWT ID of corresponding access token for revocation
    token_family_id: Mapped[str] = mapped_column(
        sql.String(36), nullable=False, index=True
    )  # UUID identifying rotation chain - all tokens from same login share family_id
    previous_token_id: Mapped[Optional[str]] = mapped_column(
        sql.String(36), nullable=True
    )  # Self-referential FK to previous token in rotation chain for reuse detection
    token_expires_at: Mapped[datetime] = mapped_column(sql.DateTime, nullable=False)
    device_info: Mapped[Optional[str]] = mapped_column(
        sql.String(255), nullable=True
    )  # User agent for device identification
    ip_address: Mapped[Optional[str]] = mapped_column(
        sql.String(45), nullable=True
    )  # IPv4/IPv6 address
    last_used_at: Mapped[Optional[datetime]] = mapped_column(
        sql.DateTime, nullable=True
    )  # Updated on each token refresh
    is_active: Mapped[bool] = mapped_column(sql.Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        sql.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    revoked_at: Mapped[Optional[datetime]] = mapped_column(
        sql.DateTime, nullable=True
    )  # When token was manually revoked (logout)

    # Relationship to AuthUserTable
    user: Mapped["AuthUserTable"] = relationship("AuthUserTable", back_populates="tokens")

    __table_args__ = (
        sql.Index("idx_auth_tokens_pk", "token_id", postgresql_using="btree"),
        sql.Index("idx_auth_tokens_hash", "refresh_token_hash", unique=True),
        sql.Index("idx_auth_tokens_user_active", "auth_user_id", "is_active"),
        sql.Index(
            "idx_auth_tokens_expires",
            "token_expires_at",
            postgresql_where=sql.text("is_active = true"),
        ),
        sql.Index("idx_auth_tokens_jti", "access_token_jti"),
        sql.Index("idx_auth_tokens_family", "token_family_id"),
        sql.CheckConstraint("token_expires_at > created_at", name="chk_token_expiry"),
    )

    def __repr__(self) -> str:
        return f"<AuthToken(id={self.token_id}, user_id='{self.auth_user_id}', family='{self.token_family_id}', expires='{self.token_expires_at}', active={self.is_active})>"


__all__ = ["AuthTokenTable"]
