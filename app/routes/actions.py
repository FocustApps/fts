"""
Action Chain routes for managing sequential action execution workflows.
"""

from fastapi import Request, APIRouter, Depends
from fastapi.templating import Jinja2Templates
from typing import List

from common.service_connections.db_service.db_manager import DB_ENGINE
from common.service_connections.db_service.database.engine import (
    get_database_session as Session,
)
from app.dependencies.multi_user_auth_dependency import verify_auth_token

from common.service_connections.db_service.models.action_chain_model import (
    ActionChainModel,
    drop_action_chain_by_id,
    insert_action_chain,
    query_all_action_chains,
    query_action_chain_by_id,
    update_action_chain_by_id,
)
from app import TEMPLATE_PATH


actions_views_router = APIRouter(
    prefix="/actions", tags=["actions"], include_in_schema=False
)

actions_api_router = APIRouter(prefix="/api/actions", tags=["actions-api"])

actions_templates = Jinja2Templates(TEMPLATE_PATH)


@actions_views_router.get("/", name="get_actions_view")
async def get_actions_view(request: Request, token: str = Depends(verify_auth_token)):
    """Get all action chains for display in table view."""
    # Get all action chains with their data
    with Session(DB_ENGINE) as db_session:
        action_chains: List[ActionChainModel] = query_all_action_chains(
            db_session=db_session, engine=DB_ENGINE
        )

    # Clean up created_at for display
    for action_chain in action_chains:
        if hasattr(action_chain, "created_at"):
            del action_chain.created_at

    headers = [
        "Action Chain Id",
        "Chain Name",
        "Description",
        "System Under Test",
        "Account",
        "Steps Count",
    ]

    return actions_templates.TemplateResponse(
        "table.html",
        {
            "title": "Action Chains",
            "request": request,
            "headers": headers,
            "table_rows": action_chains,
            "view_url": "get_actions_view",
            "view_record_url": "view_action_chain",
            "add_url": "new_action_chain",
            "delete_url": "delete_action_chain",
        },
    )


@actions_views_router.get("/new", name="new_action_chain")
async def new_action_chain(request: Request, token: str = Depends(verify_auth_token)):
    """Display form for creating a new action chain."""
    return actions_templates.TemplateResponse(
        "/actions/actions_new.html",
        {"request": request, "view_url": "get_actions_view"},
    )


@actions_views_router.get("/{record_id}", name="view_action_chain")
async def view_action_chain(
    request: Request, record_id: str, token: str = Depends(verify_auth_token)
):
    """View details of a specific action chain."""
    with Session(DB_ENGINE) as db_session:
        action_chain = query_action_chain_by_id(
            action_chain_id=record_id, db_session=db_session, engine=DB_ENGINE
        )

    # Convert ActionChainModel to a dictionary for the template
    action_chain_dict = {
        "action_chain_id": action_chain.action_chain_id,
        "chain_name": action_chain.chain_name,
        "description": action_chain.description or "No description",
        "system_under_test_id": action_chain.system_under_test_id,
        "account_id": action_chain.account_id,
        "created_at": action_chain.created_at,
        "updated_at": action_chain.updated_at,
        "steps_count": len(action_chain.action_steps or []),
    }

    # Convert action steps to list of dicts for template
    action_steps_list = []
    if action_chain.action_steps:
        for step in action_chain.action_steps:
            step_dict = {
                "step_name": step.get("step_name", "Unknown"),
                "action_type": step.get("action_type", "Unknown"),
                "action_id": step.get("action_id", "N/A"),
                "depends_on": ", ".join(step.get("depends_on", [])) or "None",
                "parallel": "Yes" if step.get("parallel", False) else "No",
            }
            action_steps_list.append(step_dict)

    return actions_templates.TemplateResponse(
        "actions/view_action_chain.html",
        {
            "request": request,
            "action_chain": action_chain_dict,
            "action_steps": action_steps_list,
            "view_url": "get_actions_view",
            "edit_url": "edit_action_chain",
        },
    )


@actions_views_router.get("/{record_id}/edit", name="edit_action_chain")
async def edit_action_chain(
    request: Request, record_id: str, token: str = Depends(verify_auth_token)
):
    """Display form for editing an action chain."""
    with Session(DB_ENGINE) as db_session:
        action_chain = query_action_chain_by_id(
            action_chain_id=record_id, db_session=db_session, engine=DB_ENGINE
        )

    return actions_templates.TemplateResponse(
        "actions/edit_action_chain.html",
        {
            "request": request,
            "action_chain": action_chain,
            "view_url": "get_actions_view",
        },
    )


@actions_views_router.delete("/{record_id}", name="delete_action_chain")
async def delete_action_chain(
    request: Request, record_id: str, token: str = Depends(verify_auth_token)
):
    """Delete an action chain."""
    with Session(DB_ENGINE) as db_session:
        drop_action_chain_by_id(
            action_chain_id=record_id, db_session=db_session, engine=DB_ENGINE
        )
    return {"status": "success", "message": f"Action chain {record_id} deleted"}


# ============================================================================
# API Routes
# ============================================================================


@actions_api_router.get("/", response_model=List[ActionChainModel])
async def get_all_action_chains_api(token: str = Depends(verify_auth_token)):
    """API endpoint to get all action chains."""
    with Session(DB_ENGINE) as db_session:
        return query_all_action_chains(db_session=db_session, engine=DB_ENGINE)


@actions_api_router.get("/{action_chain_id}", response_model=ActionChainModel)
async def get_action_chain_by_id_api(
    action_chain_id: str, token: str = Depends(verify_auth_token)
):
    """API endpoint to get a specific action chain by ID."""
    with Session(DB_ENGINE) as db_session:
        return query_action_chain_by_id(
            action_chain_id=action_chain_id, db_session=db_session, engine=DB_ENGINE
        )


@actions_api_router.post("/", response_model=ActionChainModel)
async def create_action_chain_api(
    action_chain: ActionChainModel, token: str = Depends(verify_auth_token)
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
    token: str = Depends(verify_auth_token),
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
    action_chain_id: str, token: str = Depends(verify_auth_token)
):
    """API endpoint to delete an action chain."""
    with Session(DB_ENGINE) as db_session:
        drop_action_chain_by_id(
            action_chain_id=action_chain_id, db_session=db_session, engine=DB_ENGINE
        )
    return {"status": "success", "message": f"Action chain {action_chain_id} deleted"}
