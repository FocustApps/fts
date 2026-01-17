"""
Audit logging service for multi-tenant account operations.

Provides high-level audit logging functions for:
- Account lifecycle (create, update, delete)
- User-account associations (add, remove, role change)
- Account switching and impersonation
- Notification preferences
- Super admin actions

All functions use the existing AuditLogModel infrastructure with standardized
action names and detail structures.
"""

import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from sqlalchemy.engine import Engine

from common.service_connections.db_service.models.audit_log_model import (
    AuditLogModel,
    insert_audit_log,
)
from common.service_connections.db_service.database.enums import AuditActionEnum

logger = logging.getLogger(__name__)


# ============================================================================
# Standard Action Names for Multi-Tenant Operations
# ============================================================================


class AuditAction:
    """Standard audit action names for consistency across the system."""

    # Account lifecycle
    ACCOUNT_CREATE = "account_create"
    ACCOUNT_UPDATE = "account_update"
    ACCOUNT_DELETE = "account_delete"
    ACCOUNT_DEACTIVATE = "account_deactivate"
    ACCOUNT_REACTIVATE = "account_reactivate"

    # User-account associations
    USER_ADDED_TO_ACCOUNT = "user_added_to_account"
    USER_REMOVED_FROM_ACCOUNT = "user_removed_from_account"
    USER_ROLE_CHANGED = "user_role_changed"
    PRIMARY_ACCOUNT_CHANGED = "primary_account_changed"
    BULK_USER_INVITE = "bulk_user_invite"

    # Account switching and authentication
    ACCOUNT_SWITCHED = "account_switched"
    USER_IMPERSONATED = "user_impersonated"
    IMPERSONATION_ENDED = "impersonation_ended"

    # Notification management
    NOTIFICATION_PREFERENCES_UPDATED = "notification_preferences_updated"
    NOTIFICATION_SENT = "notification_sent"
    NOTIFICATION_READ = "notification_read"

    # Super admin actions
    SUPER_ADMIN_ACCESS = "super_admin_access"
    USER_SUSPENDED = "user_suspended"
    USER_REACTIVATED = "user_reactivated"


# ============================================================================
# Account Lifecycle Audit Functions
# ============================================================================


def log_account_created(
    account_id: str,
    account_name: str,
    owner_user_id: str,
    performed_by_user_id: str,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    engine: Engine = None,
) -> str:
    """
    Log account creation event.

    Args:
        account_id: ID of created account
        account_name: Name of the account
        owner_user_id: ID of account owner
        performed_by_user_id: ID of user who created account (usually same as owner)
        ip_address: Client IP address
        user_agent: Client user agent string
        engine: Database engine

    Returns:
        audit_id of created log entry
    """
    audit = AuditLogModel(
        entity_type="account",
        entity_id=account_id,
        action=AuditActionEnum.CREATE,
        performed_by_user_id=performed_by_user_id,
        account_id=account_id,
        ip_address=ip_address,
        user_agent=user_agent,
        details={
            "account_name": account_name,
            "owner_user_id": owner_user_id,
        },
        is_sensitive=False,
    )

    return insert_audit_log(audit, engine)


def log_account_updated(
    account_id: str,
    performed_by_user_id: str,
    changes: Dict[str, Any],
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    engine: Engine = None,
) -> str:
    """
    Log account update event with change details.

    Args:
        account_id: ID of updated account
        performed_by_user_id: ID of user who made changes
        changes: Dictionary of changes (old_value, new_value per field)
        ip_address: Client IP address
        user_agent: Client user agent string
        engine: Database engine

    Returns:
        audit_id of created log entry
    """
    audit = AuditLogModel(
        entity_type="account",
        entity_id=account_id,
        action=AuditActionEnum.UPDATE,
        performed_by_user_id=performed_by_user_id,
        account_id=account_id,
        ip_address=ip_address,
        user_agent=user_agent,
        details={"changes": changes},
        is_sensitive=False,
    )

    return insert_audit_log(audit, engine)


def log_account_deleted(
    account_id: str,
    account_name: str,
    performed_by_user_id: str,
    reason: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    engine: Engine = None,
) -> str:
    """
    Log account deletion event.

    Args:
        account_id: ID of deleted account
        account_name: Name of deleted account
        performed_by_user_id: ID of user who deleted account
        reason: Optional reason for deletion
        ip_address: Client IP address
        user_agent: Client user agent string
        engine: Database engine

    Returns:
        audit_id of created log entry
    """
    audit = AuditLogModel(
        entity_type="account",
        entity_id=account_id,
        action=AuditActionEnum.DELETE,
        performed_by_user_id=performed_by_user_id,
        account_id=account_id,
        ip_address=ip_address,
        user_agent=user_agent,
        details={
            "account_name": account_name,
            "reason": reason,
        },
        is_sensitive=True,  # Deletion is sensitive
    )

    return insert_audit_log(audit, engine)


# ============================================================================
# User-Account Association Audit Functions
# ============================================================================


def log_user_added_to_account(
    association_id: str,
    account_id: str,
    target_user_id: str,
    target_user_email: str,
    role: str,
    performed_by_user_id: str,
    is_primary: bool = False,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    engine: Engine = None,
) -> str:
    """
    Log user being added to an account.

    Args:
        association_id: ID of the association record
        account_id: Account the user was added to
        target_user_id: ID of user added
        target_user_email: Email of user added
        role: Role assigned (owner/admin/member/viewer)
        performed_by_user_id: ID of user who added them
        is_primary: Whether this is the user's primary account
        ip_address: Client IP address
        user_agent: Client user agent string
        engine: Database engine

    Returns:
        audit_id of created log entry
    """
    audit = AuditLogModel(
        entity_type="account_user_association",
        entity_id=association_id,
        action=AuditAction.USER_ADDED_TO_ACCOUNT,
        performed_by_user_id=performed_by_user_id,
        account_id=account_id,
        ip_address=ip_address,
        user_agent=user_agent,
        details={
            "target_user_id": target_user_id,
            "target_user_email": target_user_email,
            "role": role,
            "is_primary": is_primary,
        },
        is_sensitive=False,
    )

    return insert_audit_log(audit, engine)


def log_user_removed_from_account(
    association_id: str,
    account_id: str,
    target_user_id: str,
    target_user_email: str,
    role: str,
    performed_by_user_id: str,
    reason: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    engine: Engine = None,
) -> str:
    """
    Log user being removed from an account.

    Args:
        association_id: ID of the association record
        account_id: Account the user was removed from
        target_user_id: ID of user removed
        target_user_email: Email of user removed
        role: Role they had before removal
        performed_by_user_id: ID of user who removed them
        reason: Optional reason for removal
        ip_address: Client IP address
        user_agent: Client user agent string
        engine: Database engine

    Returns:
        audit_id of created log entry
    """
    audit = AuditLogModel(
        entity_type="account_user_association",
        entity_id=association_id,
        action=AuditAction.USER_REMOVED_FROM_ACCOUNT,
        performed_by_user_id=performed_by_user_id,
        account_id=account_id,
        ip_address=ip_address,
        user_agent=user_agent,
        details={
            "target_user_id": target_user_id,
            "target_user_email": target_user_email,
            "old_role": role,
            "reason": reason,
        },
        is_sensitive=True,  # User removal is sensitive
    )

    return insert_audit_log(audit, engine)


def log_user_role_changed(
    association_id: str,
    account_id: str,
    target_user_id: str,
    target_user_email: str,
    old_role: str,
    new_role: str,
    performed_by_user_id: str,
    reason: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    engine: Engine = None,
) -> str:
    """
    Log user role change within an account.

    Args:
        association_id: ID of the association record
        account_id: Account where role changed
        target_user_id: ID of user whose role changed
        target_user_email: Email of user whose role changed
        old_role: Previous role
        new_role: New role
        performed_by_user_id: ID of user who changed the role
        reason: Optional reason for change
        ip_address: Client IP address
        user_agent: Client user agent string
        engine: Database engine

    Returns:
        audit_id of created log entry
    """
    audit = AuditLogModel(
        entity_type="account_user_association",
        entity_id=association_id,
        action=AuditAction.USER_ROLE_CHANGED,
        performed_by_user_id=performed_by_user_id,
        account_id=account_id,
        ip_address=ip_address,
        user_agent=user_agent,
        details={
            "target_user_id": target_user_id,
            "target_user_email": target_user_email,
            "old_value": old_role,
            "new_value": new_role,
            "field_name": "role",
            "change_reason": reason,
        },
        is_sensitive=False,
    )

    return insert_audit_log(audit, engine)


def log_primary_account_changed(
    account_id: str,
    target_user_id: str,
    old_primary_account_id: Optional[str],
    new_primary_account_id: str,
    performed_by_user_id: str,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    engine: Engine = None,
) -> str:
    """
    Log primary account change for a user.

    Args:
        account_id: New primary account ID
        target_user_id: ID of user whose primary changed
        old_primary_account_id: Previous primary account (or None)
        new_primary_account_id: New primary account
        performed_by_user_id: ID of user who made the change
        ip_address: Client IP address
        user_agent: Client user agent string
        engine: Database engine

    Returns:
        audit_id of created log entry
    """
    audit = AuditLogModel(
        entity_type="account_user_association",
        entity_id=target_user_id,  # Track against user, not specific association
        action=AuditAction.PRIMARY_ACCOUNT_CHANGED,
        performed_by_user_id=performed_by_user_id,
        account_id=new_primary_account_id,
        ip_address=ip_address,
        user_agent=user_agent,
        details={
            "target_user_id": target_user_id,
            "old_value": old_primary_account_id,
            "new_value": new_primary_account_id,
            "field_name": "primary_account_id",
        },
        is_sensitive=False,
    )

    return insert_audit_log(audit, engine)


def log_bulk_user_invite(
    account_id: str,
    performed_by_user_id: str,
    invited_count: int,
    successful_count: int,
    failed_count: int,
    role: str,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    engine: Engine = None,
) -> str:
    """
    Log bulk user invitation operation.

    Args:
        account_id: Account users were invited to
        performed_by_user_id: ID of user who performed bulk invite
        invited_count: Total number of invitations attempted
        successful_count: Number of successful invitations
        failed_count: Number of failed invitations
        role: Role assigned to invited users
        ip_address: Client IP address
        user_agent: Client user agent string
        engine: Database engine

    Returns:
        audit_id of created log entry
    """
    audit = AuditLogModel(
        entity_type="account",
        entity_id=account_id,
        action=AuditAction.BULK_USER_INVITE,
        performed_by_user_id=performed_by_user_id,
        account_id=account_id,
        ip_address=ip_address,
        user_agent=user_agent,
        details={
            "invited_count": invited_count,
            "successful_count": successful_count,
            "failed_count": failed_count,
            "role": role,
        },
        is_sensitive=False,
    )

    return insert_audit_log(audit, engine)


# ============================================================================
# Account Switching and Impersonation Audit Functions
# ============================================================================


def log_account_switched(
    user_id: str,
    old_account_id: Optional[str],
    new_account_id: str,
    new_account_name: str,
    new_role: str,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    engine: Engine = None,
) -> str:
    """
    Log user switching active account.

    Args:
        user_id: ID of user switching accounts
        old_account_id: Previous active account (or None)
        new_account_id: New active account
        new_account_name: Name of new account
        new_role: User's role in new account
        ip_address: Client IP address
        user_agent: Client user agent string
        engine: Database engine

    Returns:
        audit_id of created log entry
    """
    audit = AuditLogModel(
        entity_type="auth_user",
        entity_id=user_id,
        action=AuditAction.ACCOUNT_SWITCHED,
        performed_by_user_id=user_id,
        account_id=new_account_id,
        ip_address=ip_address,
        user_agent=user_agent,
        details={
            "old_account_id": old_account_id,
            "new_account_id": new_account_id,
            "new_account_name": new_account_name,
            "new_role": new_role,
        },
        is_sensitive=False,
    )

    return insert_audit_log(audit, engine)


def log_user_impersonation_started(
    super_admin_user_id: str,
    super_admin_email: str,
    target_user_id: str,
    target_user_email: str,
    target_account_id: Optional[str],
    reason: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    engine: Engine = None,
) -> str:
    """
    Log super admin starting impersonation of another user.

    Args:
        super_admin_user_id: ID of super admin
        super_admin_email: Email of super admin
        target_user_id: ID of user being impersonated
        target_user_email: Email of user being impersonated
        target_account_id: Account context for impersonation
        reason: Reason for impersonation (required for compliance)
        ip_address: Client IP address
        user_agent: Client user agent string
        engine: Database engine

    Returns:
        audit_id of created log entry
    """
    audit = AuditLogModel(
        entity_type="auth_user",
        entity_id=target_user_id,
        action=AuditAction.USER_IMPERSONATED,
        performed_by_user_id=super_admin_user_id,
        account_id=target_account_id,
        ip_address=ip_address,
        user_agent=user_agent,
        details={
            "super_admin_user_id": super_admin_user_id,
            "super_admin_email": super_admin_email,
            "target_user_id": target_user_id,
            "target_user_email": target_user_email,
            "target_account_id": target_account_id,
            "reason": reason,
            "impersonation_started_at": datetime.now(timezone.utc).isoformat(),
        },
        is_sensitive=True,  # Impersonation is highly sensitive
    )

    return insert_audit_log(audit, engine)


def log_user_impersonation_ended(
    super_admin_user_id: str,
    target_user_id: str,
    duration_seconds: int,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    engine: Engine = None,
) -> str:
    """
    Log super admin ending impersonation session.

    Args:
        super_admin_user_id: ID of super admin
        target_user_id: ID of user who was impersonated
        duration_seconds: Duration of impersonation session
        ip_address: Client IP address
        user_agent: Client user agent string
        engine: Database engine

    Returns:
        audit_id of created log entry
    """
    audit = AuditLogModel(
        entity_type="auth_user",
        entity_id=target_user_id,
        action=AuditAction.IMPERSONATION_ENDED,
        performed_by_user_id=super_admin_user_id,
        account_id=None,
        ip_address=ip_address,
        user_agent=user_agent,
        details={
            "super_admin_user_id": super_admin_user_id,
            "target_user_id": target_user_id,
            "duration_seconds": duration_seconds,
            "impersonation_ended_at": datetime.now(timezone.utc).isoformat(),
        },
        is_sensitive=True,  # Impersonation is highly sensitive
    )

    return insert_audit_log(audit, engine)


# ============================================================================
# Super Admin Action Audit Functions
# ============================================================================


def log_super_admin_access(
    super_admin_user_id: str,
    accessed_resource_type: str,
    accessed_resource_id: str,
    accessed_account_id: Optional[str],
    action: str,
    reason: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    engine: Engine = None,
) -> str:
    """
    Log super admin accessing resources outside their account context.

    Args:
        super_admin_user_id: ID of super admin
        accessed_resource_type: Type of resource accessed
        accessed_resource_id: ID of resource accessed
        accessed_account_id: Account the resource belongs to
        action: Action performed (read, update, delete, etc.)
        reason: Reason for access (for compliance)
        ip_address: Client IP address
        user_agent: Client user agent string
        engine: Database engine

    Returns:
        audit_id of created log entry
    """
    audit = AuditLogModel(
        entity_type=accessed_resource_type,
        entity_id=accessed_resource_id,
        action=AuditAction.SUPER_ADMIN_ACCESS,
        performed_by_user_id=super_admin_user_id,
        account_id=accessed_account_id,
        ip_address=ip_address,
        user_agent=user_agent,
        details={
            "super_admin_user_id": super_admin_user_id,
            "accessed_resource_type": accessed_resource_type,
            "accessed_resource_id": accessed_resource_id,
            "accessed_account_id": accessed_account_id,
            "action_performed": action,
            "reason": reason,
        },
        is_sensitive=True,  # Super admin actions are sensitive
    )

    return insert_audit_log(audit, engine)
