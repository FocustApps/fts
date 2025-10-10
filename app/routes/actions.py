"""
Action routes for managing Selenium automation actions.

Provides both API and view endpoints for creating, reading, updating, and deleting
actions that represent SeleniumController methods and their documentation.
"""

from typing import List
from fastapi import APIRouter, Request, Form, HTTPException, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from starlette.status import HTTP_400_BAD_REQUEST, HTTP_404_NOT_FOUND

from common.service_connections.db_service.db_manager import DB_ENGINE
from app.dependencies.multi_user_auth_dependency import verify_auth_token
from common.service_connections.db_service.actions_model import (
    ActionModel,
    query_all_actions,
    query_action_by_id,
    query_action_by_action_method,
    insert_action,
    update_action_by_id,
    delete_action_by_id,
)
from app import TEMPLATE_PATH
from common.app_logging import create_logging

logger = create_logging()

# Create routers for API and view endpoints
actions_api_router = APIRouter(prefix="/api/actions", tags=["actions-api"])
actions_views_router = APIRouter(
    prefix="/actions", tags=["actions-views"], include_in_schema=False
)

# Template configuration
templates = Jinja2Templates(directory=TEMPLATE_PATH)


################ VIEW ROUTES ################


@actions_views_router.get("/", response_class=HTMLResponse, name="get_actions_view")
async def get_actions_view(request: Request, token: str = Depends(verify_auth_token)):
    """Display the actions management page."""
    try:
        actions: List[ActionModel] = query_all_actions(engine=DB_ENGINE, session=Session)

        # Handle case where no actions exist yet
        if actions:
            headers = [
                key.replace("_", " ").title() for key in actions[0].model_dump().keys()
            ]
        else:
            # Create default headers for empty table
            headers = [
                "Id",
                "Action Method",
                "Action Documentation",
                "Created At",
                "Updated At",
            ]

        return templates.TemplateResponse(
            "table.html",
            {
                "title": "Actions",
                "request": request,
                "headers": headers,
                "table_rows": actions,
                "view_url": "get_actions_view",
                "view_record_url": "view_action",
                "add_url": "new_action_view",
                "delete_url": "delete_action_view",
            },
        )

    except Exception as e:
        logger.error(f"Error loading actions view: {e}")
        return templates.TemplateResponse(
            "error.html",
            {
                "request": request,
                "error_message": "Failed to load actions",
                "error_details": str(e),
            },
        )


@actions_views_router.get("/{record_id}", response_class=HTMLResponse, name="view_action")
async def view_action(
    request: Request, record_id: int, token: str = Depends(verify_auth_token)
):
    """Display details for a specific action."""
    try:
        action = query_action_by_id(
            action_id=record_id, engine=DB_ENGINE, session=Session
        )

        return templates.TemplateResponse(
            "actions/view_action.html",
            {
                "request": request,
                "action": action,
                "edit_url": "edit_action_view",
            },
        )

    except ValueError as e:
        logger.warning(f"Action not found: {record_id}")
        return templates.TemplateResponse(
            "error.html",
            {
                "request": request,
                "error_message": "Action not found",
                "error_details": f"No action found with ID {record_id}",
            },
        )
    except Exception as e:
        logger.error(f"Error loading action view for {record_id}: {e}")
        return templates.TemplateResponse(
            "error.html",
            {
                "request": request,
                "error_message": "Failed to load action details",
                "error_details": str(e),
            },
        )


@actions_views_router.get("/new", response_class=HTMLResponse, name="new_action_view")
async def new_action_view(request: Request, token: str = Depends(verify_auth_token)):
    """Display form for creating a new action."""
    return templates.TemplateResponse(
        "actions/new_action.html",
        {
            "request": request,
            "action": ActionModel(),  # Empty model for form defaults
        },
    )


@actions_views_router.get(
    "/{record_id}/edit", response_class=HTMLResponse, name="edit_action_view"
)
async def edit_action_view(
    request: Request, record_id: int, token: str = Depends(verify_auth_token)
):
    """Display form for editing an existing action."""
    try:
        action = query_action_by_id(
            action_id=record_id, engine=DB_ENGINE, session=Session
        )

        return templates.TemplateResponse(
            "actions/edit_action.html",
            {
                "request": request,
                "action": action,
            },
        )

    except ValueError as e:
        logger.warning(f"Action not found for editing: {record_id}")
        return templates.TemplateResponse(
            "error.html",
            {
                "request": request,
                "error_message": "Action not found",
                "error_details": f"No action found with ID {record_id}",
            },
        )
    except Exception as e:
        logger.error(f"Error loading edit form for action {record_id}: {e}")
        return templates.TemplateResponse(
            "error.html",
            {
                "request": request,
                "error_message": "Failed to load edit form",
                "error_details": str(e),
            },
        )


@actions_views_router.post("/create", name="create_action_view")
async def create_action_view(
    request: Request,
    action_method: str = Form(...),
    action_documentation: str = Form(...),
    token: str = Depends(verify_auth_token),
):
    """Handle form submission for creating a new action."""
    try:
        # Check if action method already exists
        existing_action = query_action_by_action_method(
            action_method=action_method, engine=DB_ENGINE, session=Session
        )
        if existing_action and isinstance(existing_action, ActionModel):
            return """
            <div class="alert alert-warning alert-dismissible fade show" role="alert">
                <strong>Warning!</strong> An action with this method name already exists.
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
            """

        action = ActionModel(
            action_method=action_method,
            action_documentation=action_documentation,
        )

        new_action = insert_action(action=action, engine=DB_ENGINE, session=Session)
        logger.info(f"Created new action via form: {action_method}")

        return f"""
        <div class="alert alert-success alert-dismissible fade show" role="alert">
            <strong>Success!</strong> Action "{action_method}" has been created.
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
        """

    except Exception as e:
        logger.error(f"Error creating action via form: {e}")
        return """
        <div class="alert alert-danger alert-dismissible fade show" role="alert">
            <strong>Error!</strong> Failed to create action. Please try again.
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
        """


@actions_views_router.post("/{record_id}/update", name="update_action_view")
async def update_action_view(
    request: Request,
    record_id: int,
    action_method: str = Form(...),
    action_documentation: str = Form(...),
    token: str = Depends(verify_auth_token),
):
    """Handle form submission for updating an action."""
    try:
        action_update = ActionModel(
            action_method=action_method,
            action_documentation=action_documentation,
        )

        updated_action = update_action_by_id(
            action_id=record_id,
            action=action_update,
            engine=DB_ENGINE,
            session=Session,
        )
        logger.info(f"Updated action via form: {action_method}")

        return f"""
        <div class="alert alert-success alert-dismissible fade show" role="alert">
            <strong>Success!</strong> Action "{action_method}" has been updated.
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
        """

    except ValueError as e:
        return f"""
        <div class="alert alert-danger alert-dismissible fade show" role="alert">
            <strong>Error!</strong> {str(e)}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
        """
    except Exception as e:
        logger.error(f"Error updating action {record_id} via form: {e}")
        return """
        <div class="alert alert-danger alert-dismissible fade show" role="alert">
            <strong>Error!</strong> Failed to update action. Please try again.
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
        """


@actions_views_router.post("/{record_id}/delete", name="delete_action_view")
async def delete_action_view(
    request: Request, record_id: int, token: str = Depends(verify_auth_token)
):
    """Handle form submission for deleting an action."""
    try:
        # Get action details before deletion for logging
        action = query_action_by_id(
            action_id=record_id, engine=DB_ENGINE, session=Session
        )

        delete_action_by_id(action_id=record_id, engine=DB_ENGINE, session=Session)

        logger.info(f"Deleted action via form: {action.action_method}")

        return f"""
        <div class="alert alert-success alert-dismissible fade show" role="alert">
            <strong>Success!</strong> Action "{action.action_method}" has been deleted.
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
        """

    except ValueError as e:
        return f"""
        <div class="alert alert-danger alert-dismissible fade show" role="alert">
            <strong>Error!</strong> {str(e)}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
        """
    except Exception as e:
        logger.error(f"Error deleting action {record_id}: {e}")
        return """
        <div class="alert alert-danger alert-dismissible fade show" role="alert">
            <strong>Error!</strong> Failed to delete action. Please try again.
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
        """


################ API ROUTES ################


@actions_api_router.get("/", response_model=List[dict])
async def list_actions_api(token: str = Depends(verify_auth_token)):
    """List all actions."""
    try:
        actions = query_all_actions(engine=DB_ENGINE, session=Session)
        return [action.model_dump() for action in actions]
    except Exception as e:
        logger.error(f"Error listing actions: {e}")
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=str(e))


@actions_api_router.get("/{record_id}", response_model=dict, name="get_action_api")
async def get_action_api(record_id: int, token: str = Depends(verify_auth_token)):
    """Get a specific action by ID."""
    try:
        action = query_action_by_id(
            action_id=record_id, engine=DB_ENGINE, session=Session
        )
        return action.model_dump()
    except ValueError as e:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting action {record_id}: {e}")
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=str(e))


@actions_api_router.get(
    "/method/{action_method}", response_model=dict, name="get_action_by_method_api"
)
async def get_action_by_method_api(
    action_method: str, token: str = Depends(verify_auth_token)
):
    """Get a specific action by method name."""
    try:
        action = query_action_by_action_method(
            action_method=action_method, engine=DB_ENGINE, session=Session
        )
        if isinstance(action, str):  # Error message returned
            raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail=action)
        return action.model_dump()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting action by method {action_method}: {e}")
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=str(e))


@actions_api_router.post("/", response_model=dict)
async def create_action_api(action: ActionModel, token: str = Depends(verify_auth_token)):
    """Create a new action."""
    try:
        # Check if action method already exists
        existing_action = query_action_by_action_method(
            action_method=action.action_method, engine=DB_ENGINE, session=Session
        )
        if existing_action and isinstance(existing_action, ActionModel):
            raise HTTPException(
                status_code=HTTP_400_BAD_REQUEST,
                detail=f"Action with method '{action.action_method}' already exists",
            )

        new_action = insert_action(action=action, engine=DB_ENGINE, session=Session)
        logger.info(f"Created new action via API: {action.action_method}")
        return new_action.model_dump()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error creating action via API: {e}")
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST, detail="Failed to create action"
        )


@actions_api_router.put("/{record_id}", response_model=dict, name="update_action_api")
async def update_action_api(
    record_id: int,
    action_update: ActionModel,
    token: str = Depends(verify_auth_token),
):
    """Update an action."""
    try:
        updated_action = update_action_by_id(
            action_id=record_id,
            action=action_update,
            engine=DB_ENGINE,
            session=Session,
        )
        logger.info(f"Updated action via API: {record_id}")
        return updated_action.model_dump()
    except ValueError as e:
        logger.warning(f"Failed to update action via API: {e}")
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error updating action via API: {e}")
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST, detail="Failed to update action"
        )


@actions_api_router.delete("/{record_id}", name="delete_action_api")
async def delete_action_api(record_id: int, token: str = Depends(verify_auth_token)):
    """Delete an action."""
    try:
        action = query_action_by_id(
            action_id=record_id, engine=DB_ENGINE, session=Session
        )

        delete_action_by_id(action_id=record_id, engine=DB_ENGINE, session=Session)

        logger.info(f"Deleted action via API: {action.action_method}")
        return {
            "message": "Action deleted successfully",
            "action_id": record_id,
        }
    except ValueError as e:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Error deleting action {record_id} via API: {e}")
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST, detail="Failed to delete action"
        )
