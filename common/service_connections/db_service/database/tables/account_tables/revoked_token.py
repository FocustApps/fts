"""
Revoked tokens table for JWT token blacklisting.
"""

from datetime import datetime, timezone
from sqlalchemy import String as sqlString, DateTime as sqlDateTime, Index
from sqlalchemy.orm import Mapped, mapped_column

from common.service_connections.db_service.database.base import Base


class RevokedTokenTable(Base):
    """
    Revoked JWT tokens table for token blacklisting.

    Business Logic Documentation:

    1. What this table represents:
       - Stores JTI (JWT ID) values of tokens that have been explicitly revoked
       - Prevents revoked tokens from being used until natural expiry
       - Enables immediate logout/revocation functionality

    2. User interaction level:
       - System-level table (no direct user interaction)
       - Automated cleanup via background job

    3. Data structure position:
       - Above: None (leaf table)
       - Below: None
       - Related: Checked during JWT verification in auth dependency

    4. Deletion cascade:
       - Records are deleted by background job when expires_at < now()
       - No FK dependencies

    5. Cloud services:
       - No direct cloud connection required
    """

    __tablename__ = "revoked_tokens"

    jti: Mapped[str] = mapped_column(sqlString(36), primary_key=True)
    revoked_at: Mapped[datetime] = mapped_column(
        sqlDateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    expires_at: Mapped[datetime] = mapped_column(sqlDateTime, nullable=False)

    __table_args__ = (Index("idx_revoked_tokens_expires", "expires_at"),)

    def __repr__(self) -> str:
        return f"<RevokedTokenTable(jti='{self.jti}', expires_at={self.expires_at})>"
