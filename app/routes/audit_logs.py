"""
Audit Log routes for read-only access to audit trails.

Note: Audit logs are INSERT-ONLY. No update or delete operations are exposed.
"""

from fastapi import APIRouter, Depends, Query
from typing import List, Optional

from common.service_connections.db_service.db_manager import DB_ENGINE
from common.service_connections.db_service.database.engine import (
    get_database_session as get_session,
)
from app.dependencies.jwt_auth_dependency import get_current_user
from app.models.auth_models import TokenPayload

from common.service_connections.db_service.models.audit_log_model import (
    AuditLogModel,
    query_audit_log_by_id,
    query_audit_logs_by_entity,
    query_audit_logs_by_account,
    query_audit_logs_by_user,
    query_audit_logs_by_action,
    query_sensitive_audit_logs,
    get_audit_log_count,
)


audit_log_api_router = APIRouter(prefix="/v1/api/audit-logs", tags=["audit-logs-api"])


@audit_log_api_router.get("/{audit_log_id}", response_model=AuditLogModel)
async def get_audit_log_by_id(
    audit_log_id: str,
    current_user: TokenPayload = Depends(get_current_user),
):
    """Get a specific audit log entry by ID."""
    with get_session(DB_ENGINE) as db_session:
        return query_audit_log_by_id(
            audit_log_id=audit_log_id, session=db_session, engine=DB_ENGINE
        )


@audit_log_api_router.get(
    "/entity/{entity_type}/{entity_id}", response_model=List[AuditLogModel]
)
async def get_audit_logs_by_entity(
    entity_type: str,
    entity_id: str,
    account_id: str = Query(...),
    limit: Optional[int] = Query(None),
    current_user: TokenPayload = Depends(get_current_user),
):
    """Get audit log history for a specific entity."""
    with get_session(DB_ENGINE) as db_session:
        return query_audit_logs_by_entity(
            entity_type=entity_type,
            entity_id=entity_id,
            account_id=account_id,
            limit=limit,
            session=db_session,
            engine=DB_ENGINE,
        )


@audit_log_api_router.get("/account/{account_id}", response_model=List[AuditLogModel])
async def get_audit_logs_by_account(
    account_id: str,
    limit: Optional[int] = Query(100),
    current_user: TokenPayload = Depends(get_current_user),
):
    """Get audit logs for a specific account."""
    with get_session(DB_ENGINE) as db_session:
        return query_audit_logs_by_account(
            account_id=account_id,
            limit=limit,
            session=db_session,
            engine=DB_ENGINE,
        )


@audit_log_api_router.get("/user/{user_id}", response_model=List[AuditLogModel])
async def get_audit_logs_by_user(
    user_id: str,
    account_id: str = Query(...),
    limit: Optional[int] = Query(100),
    current_user: TokenPayload = Depends(get_current_user),
):
    """Get all audit logs for actions performed by a specific user."""
    with get_session(DB_ENGINE) as db_session:
        return query_audit_logs_by_user(
            user_id=user_id,
            account_id=account_id,
            limit=limit,
            session=db_session,
            engine=DB_ENGINE,
        )


@audit_log_api_router.get("/action/{action}", response_model=List[AuditLogModel])
async def get_audit_logs_by_action(
    action: str,
    account_id: str = Query(...),
    entity_type: Optional[str] = Query(None),
    limit: Optional[int] = Query(100),
    current_user: TokenPayload = Depends(get_current_user),
):
    """Get audit logs filtered by action type."""
    with get_session(DB_ENGINE) as db_session:
        return query_audit_logs_by_action(
            action=action,
            account_id=account_id,
            entity_type=entity_type,
            limit=limit,
            session=db_session,
            engine=DB_ENGINE,
        )


@audit_log_api_router.get("/sensitive/all", response_model=List[AuditLogModel])
async def get_sensitive_audit_logs(
    account_id: str = Query(...),
    limit: Optional[int] = Query(100),
    current_user: TokenPayload = Depends(get_current_user),
):
    """Get all sensitive audit logs (admin only)."""
    # Note: In production, add additional authorization check for admin role
    with get_session(DB_ENGINE) as db_session:
        return query_sensitive_audit_logs(
            account_id=account_id,
            limit=limit,
            session=db_session,
            engine=DB_ENGINE,
        )


@audit_log_api_router.get("/count/total")
async def get_audit_log_count_endpoint(
    account_id: str = Query(...),
    entity_type: Optional[str] = Query(None),
    current_user: TokenPayload = Depends(get_current_user),
):
    """Get the total count of audit logs."""
    with get_session(DB_ENGINE) as db_session:
        count = get_audit_log_count(
            account_id=account_id,
            entity_type=entity_type,
            session=db_session,
            engine=DB_ENGINE,
        )
    return {"account_id": account_id, "count": count, "entity_type": entity_type}
