"""
Audit log model with insert-only operations and JSONB change tracking.

This module provides:
1. AuditChangeModel: Nested Pydantic model for validating 'details' JSONB field
2. AuditLogModel: Insert-only model (no update/delete to preserve audit trail)
3. Query helpers for forensic analysis (by entity, account, date range, sensitivity)
4. Built-in IP address and user agent tracking
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, field_validator
from sqlalchemy import and_, func
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from common.config import should_validate_write
from common.service_connections.db_service.database.engine import (
    get_database_session as session,
)

from common.service_connections.db_service.database.tables.audit_log import (
    AuditLogTable,
)

logger = logging.getLogger(__name__)


class AuditChangeModel(BaseModel):
    """Nested model for validating audit log details JSONB structure.

    Common fields for change tracking:
    - old_value: Previous value before change
    - new_value: New value after change
    - field_name: Name of field changed
    - change_reason: Optional reason for change
    """

    old_value: Optional[Any] = None
    new_value: Optional[Any] = None
    field_name: Optional[str] = None
    change_reason: Optional[str] = None
    additional_context: Optional[Dict[str, Any]] = None

    @field_validator("field_name")
    def validate_field_name(cls, v: Optional[str]) -> Optional[str]:
        """Validate field_name length if provided."""
        if not should_validate_write():
            return v

        if v is not None and len(v) > 255:
            raise ValueError(f"field_name exceeds 255 characters: {len(v)}")

        return v


class AuditLogModel(BaseModel):
    """Pydantic model for audit log validation.

    INSERT-ONLY: This model does not support update or delete operations to preserve
    audit trail integrity. Use query functions for forensic analysis only.
    """

    audit_id: Optional[str] = None
    entity_type: str
    entity_id: str
    action: str
    performed_by_user_id: Optional[str] = None
    account_id: Optional[str] = None
    timestamp: Optional[datetime] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    details: Optional[Dict[str, Any]] = (
        None  # Validated against AuditChangeModel structure
    )
    is_sensitive: bool = False

    @field_validator("entity_type")
    def validate_entity_type(cls, v: str) -> str:
        """Validate entity_type length."""
        if not should_validate_write():
            return v

        if len(v) > 128:
            raise ValueError(f"entity_type exceeds 128 characters: {len(v)}")

        return v

    @field_validator("action")
    def validate_action(cls, v: str) -> str:
        """Validate action against common audit actions."""
        if not should_validate_write():
            return v

        if len(v) > 64:
            raise ValueError(f"action exceeds 64 characters: {len(v)}")

        # Common audit actions (not exhaustive - can be extended)
        common_actions = {
            "create",
            "read",
            "update",
            "delete",
            "deactivate",
            "reactivate",
            "login",
            "logout",
            "login_failed",
            "password_change",
            "password_reset",
            "execute",
            "run",
            "cancel",
            "approve",
            "reject",
            "export",
            "import",
            "upload",
            "download",
        }

        # Log warning if action not in common set (not an error, just informational)
        if v not in common_actions:
            logger.debug(f"Audit action '{v}' not in common action set")

        return v

    @field_validator("ip_address")
    def validate_ip_address(cls, v: Optional[str]) -> Optional[str]:
        """Validate IP address length (supports IPv4 and IPv6)."""
        if not should_validate_write():
            return v

        if v is not None and len(v) > 45:
            raise ValueError(f"ip_address exceeds 45 characters: {len(v)}")

        return v

    @field_validator("user_agent")
    def validate_user_agent(cls, v: Optional[str]) -> Optional[str]:
        """Validate user_agent length."""
        if not should_validate_write():
            return v

        if v is not None and len(v) > 512:
            # Truncate instead of error to prevent audit logging failures
            logger.warning(f"user_agent exceeds 512 characters, truncating: {len(v)}")
            return v[:512]

        return v

    @field_validator("details")
    def validate_details_structure(
        cls, v: Optional[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """Validate details JSONB structure against AuditChangeModel."""
        if not should_validate_write():
            return v

        if v is None:
            return v

        # If details contains change tracking fields, validate with AuditChangeModel
        change_fields = {"old_value", "new_value", "field_name", "change_reason"}
        if any(field in v for field in change_fields):
            try:
                # Validate structure (allows additional fields beyond AuditChangeModel)
                AuditChangeModel(**v)
            except Exception as e:
                logger.warning(f"Audit details structure validation warning: {e}")
                # Don't fail audit logging on validation issues - just warn

        return v


# ============================================================================
# INSERT-ONLY Operations (No Update/Delete)
# ============================================================================


def insert_audit_log(model: AuditLogModel, engine: Engine) -> str:
    """Insert new audit log record.

    This is the ONLY write operation for audit logs. No update or delete allowed.

    Args:
        model: AuditLogModel with audit data
        engine: Database engine
    Returns:
        audit_id of inserted record

    Raises:
        ValueError: If validation fails
        SQLAlchemyError: If database operation fails
    """
    # Set timestamp if not provided
    if model.timestamp is None:
        model.timestamp = datetime.now(timezone.utc)

    audit_dict = model.model_dump(exclude_unset=True)

    with session(engine) as db_session:
        new_audit = AuditLogTable(**audit_dict)
        db_session.add(new_audit)
        db_session.commit()
        return new_audit.audit_id


def bulk_insert_audit_logs(models: List[AuditLogModel], engine: Engine) -> List[str]:
    """Bulk insert multiple audit log records in a single transaction.

    Args:
        models: List of AuditLogModel instances
        engine: Database engine
    Returns:
        List of audit_ids for inserted records

    Raises:
        ValueError: If validation fails
        SQLAlchemyError: If database operation fails
    """
    audit_ids = []
    current_time = datetime.now(timezone.utc)

    with session(engine) as db_session:
        for model in models:
            # Set timestamp if not provided
            if model.timestamp is None:
                model.timestamp = current_time

            audit_dict = model.model_dump(exclude_unset=True)
            new_audit = AuditLogTable(**audit_dict)
            db_session.add(new_audit)
            audit_ids.append(new_audit.audit_id)

        db_session.commit()
        return audit_ids


# ============================================================================
# READ-ONLY Query Operations
# ============================================================================


def query_audit_log_by_id(
    audit_id: str, session: Session, engine: Engine
) -> Optional[AuditLogModel]:
    """Query audit log by audit_id.

    Args:
        audit_id: Audit log ID to query
        session: Active database session
        engine: Database engine

    Returns:
        AuditLogModel if found, None otherwise
    """
    audit = session.get(AuditLogTable, audit_id)
    if audit:
        return AuditLogModel(**audit.__dict__)
    return None


def query_audit_logs_by_entity(
    entity_type: str, entity_id: str, session: Session, engine: Engine, limit: int = 100
) -> List[AuditLogModel]:
    """Query all audit logs for a specific entity (most recent first).

    Args:
        entity_type: Type of entity
        entity_id: Entity's primary key
        session: Active database session
        engine: Database engine
        limit: Maximum number of records to return

    Returns:
        List of AuditLogModel instances ordered by timestamp desc
    """
    audits = (
        session.query(AuditLogTable)
        .filter(
            and_(
                AuditLogTable.entity_type == entity_type,
                AuditLogTable.entity_id == entity_id,
            )
        )
        .order_by(AuditLogTable.timestamp.desc())
        .limit(limit)
        .all()
    )
    return [AuditLogModel(**audit.__dict__) for audit in audits]


def query_audit_logs_by_account(
    account_id: str,
    session: Session,
    engine: Engine,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = 1000,
) -> List[AuditLogModel]:
    """Query audit logs for an account with optional date range.

    Args:
        account_id: Account ID to filter by
        session: Active database session
        engine: Database engine
        start_date: Optional start timestamp (inclusive)
        end_date: Optional end timestamp (inclusive)
        limit: Maximum number of records to return

    Returns:
        List of AuditLogModel instances ordered by timestamp desc
    """
    filters = [AuditLogTable.account_id == account_id]

    if start_date:
        filters.append(AuditLogTable.timestamp >= start_date)

    if end_date:
        filters.append(AuditLogTable.timestamp <= end_date)

    audits = (
        session.query(AuditLogTable)
        .filter(and_(*filters))
        .order_by(AuditLogTable.timestamp.desc())
        .limit(limit)
        .all()
    )
    return [AuditLogModel(**audit.__dict__) for audit in audits]


def query_audit_logs_by_user(
    user_id: str,
    session: Session,
    engine: Engine,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = 500,
) -> List[AuditLogModel]:
    """Query audit logs for actions performed by a user.

    Args:
        user_id: User ID to filter by
        session: Active database session
        engine: Database engine
        start_date: Optional start timestamp (inclusive)
        end_date: Optional end timestamp (inclusive)
        limit: Maximum number of records to return

    Returns:
        List of AuditLogModel instances ordered by timestamp desc
    """
    filters = [AuditLogTable.performed_by_user_id == user_id]

    if start_date:
        filters.append(AuditLogTable.timestamp >= start_date)

    if end_date:
        filters.append(AuditLogTable.timestamp <= end_date)

    audits = (
        session.query(AuditLogTable)
        .filter(and_(*filters))
        .order_by(AuditLogTable.timestamp.desc())
        .limit(limit)
        .all()
    )
    return [AuditLogModel(**audit.__dict__) for audit in audits]


def query_sensitive_audit_logs(
    session: Session,
    engine: Engine,
    account_id: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = 1000,
) -> List[AuditLogModel]:
    """Query sensitive audit logs (e.g., password changes, permission changes).

    Args:
        session: Active database session
        engine: Database engine
        account_id: Optional account filter
        start_date: Optional start timestamp (inclusive)
        end_date: Optional end timestamp (inclusive)
        limit: Maximum number of records to return

    Returns:
        List of AuditLogModel instances ordered by timestamp desc
    """
    filters = [AuditLogTable.is_sensitive == True]

    if account_id:
        filters.append(AuditLogTable.account_id == account_id)

    if start_date:
        filters.append(AuditLogTable.timestamp >= start_date)

    if end_date:
        filters.append(AuditLogTable.timestamp <= end_date)

    audits = (
        session.query(AuditLogTable)
        .filter(and_(*filters))
        .order_by(AuditLogTable.timestamp.desc())
        .limit(limit)
        .all()
    )
    return [AuditLogModel(**audit.__dict__) for audit in audits]


def query_audit_logs_by_action(
    action: str,
    session: Session,
    engine: Engine,
    entity_type: Optional[str] = None,
    account_id: Optional[str] = None,
    limit: int = 500,
) -> List[AuditLogModel]:
    """Query audit logs by action type.

    Args:
        action: Action to filter by (create, update, delete, etc.)
        session: Active database session
        engine: Database engine
        entity_type: Optional entity type filter
        account_id: Optional account filter
        limit: Maximum number of records to return

    Returns:
        List of AuditLogModel instances ordered by timestamp desc
    """
    filters = [AuditLogTable.action == action]

    if entity_type:
        filters.append(AuditLogTable.entity_type == entity_type)

    if account_id:
        filters.append(AuditLogTable.account_id == account_id)

    audits = (
        session.query(AuditLogTable)
        .filter(and_(*filters))
        .order_by(AuditLogTable.timestamp.desc())
        .limit(limit)
        .all()
    )
    return [AuditLogModel(**audit.__dict__) for audit in audits]


def get_audit_log_count(
    session: Session,
    engine: Engine,
    account_id: Optional[str] = None,
    entity_type: Optional[str] = None,
    is_sensitive: Optional[bool] = None,
) -> int:
    """Get count of audit logs matching filters.

    Args:
        session: Active database session
        engine: Database engine
        account_id: Optional account filter
        entity_type: Optional entity type filter
        is_sensitive: Optional sensitivity filter

    Returns:
        Count of matching audit log records
    """
    with session(engine) as db_session:
        filters = []

        if account_id:
            filters.append(AuditLogTable.account_id == account_id)

        if entity_type:
            filters.append(AuditLogTable.entity_type == entity_type)

        if is_sensitive is not None:
            filters.append(AuditLogTable.is_sensitive == is_sensitive)

        query = db_session.query(func.count(AuditLogTable.audit_id))

        if filters:
            query = query.filter(and_(*filters))

        return query.scalar() or 0
