"""
Audit log table model for tracking all system actions and changes.
"""

from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

import sqlalchemy as sql
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import JSONB

from common.service_connections.db_service.database.base import Base


class AuditLogTable(Base):
    """Audit log table for comprehensive system action tracking.

    Business Logic Documentation:

    1. Define at a high level what this table is suppose to represent in terms of a goal
       or goals that need to be accomplished by a user?
       - Provides complete audit trail of all user and system actions for compliance,
         security monitoring, and troubleshooting. Tracks who did what, when, and from
         where across all entities in the system. Supports forensic analysis and
         regulatory compliance requirements (SOC 2, GDPR, etc.).

    2. What level of user should be interacting with this table?
       - Super Admin: Full read access to all audit logs
       - Account Admin: Read access to account-specific audit logs
       - Compliance Officers: Read access for audit reporting
       - System: Write access (automated logging)
       - Regular Users: No direct access (logs their actions automatically)

    3. What are the names of the tables that are either above or below this table in the
       data structure? This is to understand where to put in in a architecture diagram.
       - Above: AuthUserTable (via performed_by_user_id), AccountTable (via account_id)
       - Below: None (leaf node - stores references but no children)

    4. Should a record in this table be deleted based on the deletion of a record in a
       different table? If so, what table?
       - No CASCADE deletes. Audit logs must be preserved even when referenced entities
         are deleted. Uses nullable FKs or no FKs to preserve audit trail integrity.
         Pruning handled by PurgeTable retention policy (90 days non-sensitive, 365 days
         sensitive).

    5. Will this table be require a connection a secure cloud provider service?
       - Optional. For high-compliance environments, logs may be replicated to immutable
         cloud storage (AWS S3 with object lock, Azure immutable blob storage) for
         tamper-proof audit trails.
    """

    __tablename__ = "audit_log"

    audit_id: Mapped[str] = mapped_column(
        sql.String(36), primary_key=True, default=lambda: str(uuid4())
    )
    entity_type: Mapped[str] = mapped_column(sql.String(128), nullable=False)
    entity_id: Mapped[str] = mapped_column(sql.String(36), nullable=False)
    action: Mapped[str] = mapped_column(sql.String(64), nullable=False)
    performed_by_user_id: Mapped[Optional[str]] = mapped_column(
        sql.String(36),
        sql.ForeignKey("auth_users.id", ondelete="SET NULL"),
        nullable=True,
    )
    account_id: Mapped[Optional[str]] = mapped_column(
        sql.String(36),
        sql.ForeignKey("account.account_id", ondelete="SET NULL"),
        nullable=True,
    )
    timestamp: Mapped[datetime] = mapped_column(
        sql.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    ip_address: Mapped[Optional[str]] = mapped_column(sql.String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(sql.String(512), nullable=True)
    details: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    is_sensitive: Mapped[bool] = mapped_column(sql.Boolean, nullable=False, default=False)

    __table_args__ = (
        sql.Index("idx_audit_pk", "audit_id", postgresql_using="btree"),
        sql.Index("idx_audit_entity", "entity_type", "entity_id"),
        sql.Index("idx_audit_user", "performed_by_user_id"),
        sql.Index("idx_audit_timestamp", "timestamp"),
        sql.Index("idx_audit_account", "account_id"),
        sql.Index("idx_audit_sensitive", "is_sensitive", "timestamp"),
    )

    def __repr__(self) -> str:
        return f"<AuditLog(id={self.audit_id}, entity_type='{self.entity_type}', action='{self.action}', timestamp='{self.timestamp}')>"


__all__ = ["AuditLogTable"]
