"""
Action Chain routes for managing sequential action execution workflows.
"""

from fastapi import Request, APIRouter, Depends
from typing import List

from common.service_connections.db_service.db_manager import DB_ENGINE
from common.service_connections.db_service.database.engine import (
    get_database_session as Session,
)
from app.dependencies.jwt_auth_dependency import get_current_user
from app.models.auth_models import TokenPayload

from common.service_connections.db_service.models.action_chain_model import (
    ActionChainModel,
    drop_action_chain_by_id,
    insert_action_chain,
    query_all_action_chains,
    query_action_chain_by_id,
    update_action_chain_by_id,
)


actions_views_router = APIRouter(
    prefix="/actions", tags=["actions"], include_in_schema=False
)

actions_api_router = APIRouter(prefix="/api/actions", tags=["actions-api"])   


# ============================================================================
# API Routes
# ============================================================================


@actions_api_router.get("/", response_model=List[ActionChainModel])
async def get_all_action_chains_api(
    current_user: TokenPayload = Depends(get_current_user),
):
    """API endpoint to get all action chains."""
    with Session(DB_ENGINE) as db_session:
        return query_all_action_chains(db_session=db_session, engine=DB_ENGINE)


@actions_api_router.get("/{action_chain_id}", response_model=ActionChainModel)
async def get_action_chain_by_id_api(
    action_chain_id: str, current_user: TokenPayload = Depends(get_current_user)
):
    """API endpoint to get a specific action chain by ID."""
    with Session(DB_ENGINE) as db_session:
        return query_action_chain_by_id(
            action_chain_id=action_chain_id, db_session=db_session, engine=DB_ENGINE
        )


@actions_api_router.post("/", response_model=ActionChainModel)
async def create_action_chain_api(
    action_chain: ActionChainModel, current_user: TokenPayload = Depends(get_current_user)
):
    """API endpoint to create a new action chain."""
    with Session(DB_ENGINE) as db_session:
        return insert_action_chain(
            action_chain=action_chain, db_session=db_session, engine=DB_ENGINE
        )


@actions_api_router.put("/{action_chain_id}", response_model=ActionChainModel)
async def update_action_chain_api(
    action_chain_id: str,
    action_chain: ActionChainModel,
    current_user: TokenPayload = Depends(get_current_user),
):
    """API endpoint to update an action chain."""
    with Session(DB_ENGINE) as db_session:
        return update_action_chain_by_id(
            action_chain_id=action_chain_id,
            action_chain=action_chain,
            db_session=db_session,
            engine=DB_ENGINE,
        )


@actions_api_router.delete("/{action_chain_id}")
async def delete_action_chain_api(
    action_chain_id: str, current_user: TokenPayload = Depends(get_current_user)
):
    """API endpoint to delete an action chain."""
    with Session(DB_ENGINE) as db_session:
        drop_action_chain_by_id(
            action_chain_id=action_chain_id, db_session=db_session, engine=DB_ENGINE
        )
    return {"status": "success", "message": f"Action chain {action_chain_id} deleted"}
