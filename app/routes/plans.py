"""
Plan routes for managing test execution plans.
"""

from fastapi import APIRouter, Depends
from typing import List

from common.service_connections.db_service.db_manager import DB_ENGINE
from common.service_connections.db_service.database.engine import (
    get_database_session as get_session,
)
from app.dependencies.jwt_auth_dependency import get_current_user
from app.models.auth_models import TokenPayload

from common.service_connections.db_service.models.plan_model import (
    PlanModel,
    insert_plan,
    query_plan_by_id,
    query_all_plans,
    query_plans_by_account,
    query_plans_by_owner,
    query_plans_by_status,
    update_plan,
    update_plan_status,
    deactivate_plan,
    reactivate_plan,
    drop_plan,
)


plan_api_router = APIRouter(prefix="/v1/api/plans", tags=["plans-api"])


@plan_api_router.get("/", response_model=List[PlanModel])
async def get_all_plans(
    current_user: TokenPayload = Depends(get_current_user),
):
    """Get all test plans."""
    with get_session(DB_ENGINE) as db_session:
        return query_all_plans(db_session=db_session, engine=DB_ENGINE)


@plan_api_router.get("/account/{account_id}", response_model=List[PlanModel])
async def get_plans_by_account(
    account_id: str,
    current_user: TokenPayload = Depends(get_current_user),
):
    """Get all test plans for a specific account."""
    with get_session(DB_ENGINE) as db_session:
        return query_plans_by_account(
            account_id=account_id, db_session=db_session, engine=DB_ENGINE
        )


@plan_api_router.get("/owner/{owner_user_id}", response_model=List[PlanModel])
async def get_plans_by_owner(
    owner_user_id: str,
    current_user: TokenPayload = Depends(get_current_user),
):
    """Get all test plans owned by a specific user."""
    with get_session(DB_ENGINE) as db_session:
        return query_plans_by_owner(
            owner_user_id=owner_user_id, db_session=db_session, engine=DB_ENGINE
        )


@plan_api_router.get("/status/{status}", response_model=List[PlanModel])
async def get_plans_by_status(
    status: str,
    current_user: TokenPayload = Depends(get_current_user),
):
    """Get all test plans with a specific status."""
    with get_session(DB_ENGINE) as db_session:
        return query_plans_by_status(
            status=status, db_session=db_session, engine=DB_ENGINE
        )


@plan_api_router.get("/{plan_id}", response_model=PlanModel)
async def get_plan_by_id(
    plan_id: str,
    current_user: TokenPayload = Depends(get_current_user),
):
    """Get a specific test plan by ID."""
    with get_session(DB_ENGINE) as db_session:
        return query_plan_by_id(plan_id=plan_id, db_session=db_session, engine=DB_ENGINE)


@plan_api_router.post("/", response_model=PlanModel)
async def create_plan(
    plan: PlanModel,
    current_user: TokenPayload = Depends(get_current_user),
):
    """Create a new test plan."""
    plan_id = insert_plan(model=plan, engine=DB_ENGINE)
    with get_session(DB_ENGINE) as db_session:
        return query_plan_by_id(plan_id=plan_id, db_session=db_session, engine=DB_ENGINE)


@plan_api_router.put("/{plan_id}", response_model=PlanModel)
async def update_plan_endpoint(
    plan_id: str,
    plan: PlanModel,
    current_user: TokenPayload = Depends(get_current_user),
):
    """Update a test plan."""
    update_plan(plan_id=plan_id, updates=plan, engine=DB_ENGINE)
    with get_session(DB_ENGINE) as db_session:
        return query_plan_by_id(plan_id=plan_id, db_session=db_session, engine=DB_ENGINE)


@plan_api_router.patch("/{plan_id}/status")
async def update_plan_status_endpoint(
    plan_id: str,
    status: str,
    current_user: TokenPayload = Depends(get_current_user),
):
    """Update the status of a test plan."""
    update_plan_status(plan_id=plan_id, new_status=status, engine=DB_ENGINE)
    return {"status": "success", "message": f"Plan {plan_id} status updated to {status}"}


@plan_api_router.patch("/{plan_id}/deactivate")
async def deactivate_plan_endpoint(
    plan_id: str,
    current_user: TokenPayload = Depends(get_current_user),
):
    """Deactivate a test plan (soft delete)."""
    deactivate_plan(
        plan_id=plan_id, deactivated_by_user_id=current_user.user_id, engine=DB_ENGINE
    )
    return {"status": "success", "message": f"Plan {plan_id} deactivated"}


@plan_api_router.patch("/{plan_id}/reactivate")
async def reactivate_plan_endpoint(
    plan_id: str,
    current_user: TokenPayload = Depends(get_current_user),
):
    """Reactivate a previously deactivated test plan."""
    reactivate_plan(plan_id=plan_id, engine=DB_ENGINE)
    return {"status": "success", "message": f"Plan {plan_id} reactivated"}


@plan_api_router.delete("/{plan_id}")
async def delete_plan(
    plan_id: str,
    current_user: TokenPayload = Depends(get_current_user),
):
    """Hard delete a test plan."""
    drop_plan(plan_id=plan_id, engine=DB_ENGINE)
    return {"status": "success", "message": f"Plan {plan_id} deleted"}
