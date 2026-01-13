"""
Purge Schedule routes for admin data retention management.

Note: These are admin-only operations for managing automated data purging.
"""

from fastapi import APIRouter, Depends
from typing import List

from common.service_connections.db_service.db_manager import DB_ENGINE
from common.service_connections.db_service.database.engine import (
    get_database_session as get_session,
)
from app.dependencies.jwt_auth_dependency import get_current_user
from app.models.auth_models import TokenPayload

from common.service_connections.db_service.models.purge_model import (
    PurgeModel,
    insert_purge_schedule,
    query_purge_schedule_by_id,
    query_all_purge_schedules,
    query_purge_schedule_by_table,
    query_tables_due_for_purge,
    update_purge_schedule,
    update_last_purged_at,
    update_purge_interval,
    drop_purge_schedule,
)


purge_api_router = APIRouter(prefix="/v1/api/purge", tags=["purge-api"])


@purge_api_router.get("/", response_model=List[PurgeModel])
async def get_all_purge_schedules(
    current_user: TokenPayload = Depends(get_current_user),
):
    """Get all purge schedules (admin only)."""
    # Note: Add admin role check in production
    with get_session(DB_ENGINE) as db_session:
        return query_all_purge_schedules(db_session=db_session, engine=DB_ENGINE)


@purge_api_router.get("/due", response_model=List[PurgeModel])
async def get_tables_due_for_purge(
    current_user: TokenPayload = Depends(get_current_user),
):
    """Get all tables that are due for purging."""
    with get_session(DB_ENGINE) as db_session:
        return query_tables_due_for_purge(db_session=db_session, engine=DB_ENGINE)


@purge_api_router.get("/table/{table_name}", response_model=PurgeModel)
async def get_purge_schedule_by_table(
    table_name: str,
    current_user: TokenPayload = Depends(get_current_user),
):
    """Get purge schedule for a specific table."""
    with get_session(DB_ENGINE) as db_session:
        return query_purge_schedule_by_table(
            table_name=table_name, db_session=db_session, engine=DB_ENGINE
        )


@purge_api_router.get("/{purge_id}", response_model=PurgeModel)
async def get_purge_schedule_by_id(
    purge_id: str,
    current_user: TokenPayload = Depends(get_current_user),
):
    """Get a specific purge schedule by ID."""
    with get_session(DB_ENGINE) as db_session:
        return query_purge_schedule_by_id(
            purge_id=purge_id, db_session=db_session, engine=DB_ENGINE
        )


@purge_api_router.post("/", response_model=PurgeModel)
async def create_purge_schedule(
    purge: PurgeModel,
    current_user: TokenPayload = Depends(get_current_user),
):
    """Create a new purge schedule (admin only)."""
    purge_id = insert_purge_schedule(model=purge, engine=DB_ENGINE)
    with get_session(DB_ENGINE) as db_session:
        return query_purge_schedule_by_id(
            purge_id=purge_id, db_session=db_session, engine=DB_ENGINE
        )


@purge_api_router.put("/{purge_id}", response_model=PurgeModel)
async def update_purge_schedule_endpoint(
    purge_id: str,
    purge: PurgeModel,
    current_user: TokenPayload = Depends(get_current_user),
):
    """Update a purge schedule."""
    update_purge_schedule(purge_id=purge_id, updates=purge, engine=DB_ENGINE)
    with get_session(DB_ENGINE) as db_session:
        return query_purge_schedule_by_id(
            purge_id=purge_id, db_session=db_session, engine=DB_ENGINE
        )


@purge_api_router.patch("/{purge_id}/last-purged")
async def update_last_purged_timestamp(
    purge_id: str,
    current_user: TokenPayload = Depends(get_current_user),
):
    """Update the last_purged_at timestamp (called after purge execution)."""
    update_last_purged_at(purge_id=purge_id, engine=DB_ENGINE)
    return {
        "status": "success",
        "message": f"Last purged timestamp updated for {purge_id}",
    }


@purge_api_router.patch("/{purge_id}/interval")
async def update_purge_interval_endpoint(
    purge_id: str,
    new_interval_days: int,
    current_user: TokenPayload = Depends(get_current_user),
):
    """Update the purge interval for a schedule."""
    update_purge_interval(
        purge_id=purge_id, new_interval_days=new_interval_days, engine=DB_ENGINE
    )
    return {
        "status": "success",
        "message": f"Purge interval updated to {new_interval_days} days",
    }


@purge_api_router.delete("/{purge_id}")
async def delete_purge_schedule(
    purge_id: str,
    current_user: TokenPayload = Depends(get_current_user),
):
    """Delete a purge schedule (admin only)."""
    drop_purge_schedule(purge_id=purge_id, engine=DB_ENGINE)
    return {"status": "success", "message": f"Purge schedule {purge_id} deleted"}
