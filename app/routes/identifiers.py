"""
Identifier routes for managing web element identifiers.

Provides both API and view endpoints for creating, reading, updating, and deleting
identifiers that belong to pages in the selenium automation framework.
"""

from typing import List, Optional
from fastapi import APIRouter, Request, Form, HTTPException, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from starlette.status import HTTP_400_BAD_REQUEST, HTTP_404_NOT_FOUND

from common.service_connections.db_service.db_manager import DB_ENGINE
from app.dependencies.multi_user_auth_dependency import verify_auth_token
from common.service_connections.db_service.identifier_model import (
    IdentifierModel,
    query_all_identifiers,
    query_identifier_by_id,
    insert_identifier,
    update_identifier_by_id,
    drop_identifier_by_id,
)
from common.service_connections.db_service.page_model import query_page_by_id
from app import TEMPLATE_PATH
from common.app_logging import create_logging

logger = create_logging()

# Create routers for API and view endpoints
identifiers_api_router = APIRouter(prefix="/api/identifiers", tags=["identifiers-api"])
identifiers_views_router = APIRouter(
    prefix="/identifiers", tags=["identifiers-views"], include_in_schema=False
)

# Template configuration
templates = Jinja2Templates(directory=TEMPLATE_PATH)


################ VIEW ROUTES ################


@identifiers_views_router.get("/", response_class=HTMLResponse)
async def get_identifiers_view(request: Request, token: str = Depends(verify_auth_token)):
    """Display the identifiers management page."""
    try:
        identifiers = query_all_identifiers(engine=DB_ENGINE, session=Session)

        # Format identifiers for table display
        identifier_data = []
        for identifier in identifiers:
            identifier_display = {
                "id": identifier.id,
                "element_name": identifier.element_name,
                "locator_strategy": identifier.locator_strategy,
                "locator_query": (
                    identifier.locator_query[:50] + "..."
                    if len(identifier.locator_query) > 50
                    else identifier.locator_query
                ),
                "action": identifier.action or "—",
                "page_id": identifier.page_id,
                "environments": (
                    ", ".join(identifier.environments)
                    if identifier.environments
                    else "None"
                ),
            }
            identifier_data.append(identifier_display)

        return templates.TemplateResponse(
            "table.html",
            {
                "title": "Identifiers",
                "request": request,
                "headers": [
                    "ID",
                    "Element Name",
                    "Strategy",
                    "Query",
                    "Action",
                    "Page ID",
                    "Environments",
                ],
                "table_rows": identifier_data,
                "view_url": "get_identifiers_view",
                "view_record_url": "view_identifier",
                "add_url": "new_identifier_view",
                "delete_url": "delete_identifier_view",
            },
        )

    except Exception as e:
        logger.error(f"Error loading identifiers view: {e}")
        return templates.TemplateResponse(
            "error.html",
            {
                "request": request,
                "error_message": "Failed to load identifiers",
                "error_details": str(e),
            },
        )


@identifiers_views_router.get("/{identifier_id}", response_class=HTMLResponse)
async def view_identifier(
    request: Request, identifier_id: int, token: str = Depends(verify_auth_token)
):
    """Display details for a specific identifier."""
    try:
        identifier = query_identifier_by_id(
            identifier_id=identifier_id, engine=DB_ENGINE, session=Session
        )

        # Get the associated page
        page = query_page_by_id(
            page_id=identifier.page_id, engine=DB_ENGINE, session=Session
        )

        identifier_dict = {
            "id": identifier.id,
            "element_name": identifier.element_name,
            "locator_strategy": identifier.locator_strategy,
            "locator_query": identifier.locator_query,
            "action": identifier.action or "None",
            "page_id": identifier.page_id,
            "page_name": page.page_name,
            "environments": (
                ", ".join(identifier.environments) if identifier.environments else "None"
            ),
            "created_at": identifier.created_at.strftime("%Y-%m-%d %H:%M UTC"),
        }

        return templates.TemplateResponse(
            "identifiers/view_identifier.html",
            {
                "request": request,
                "identifier": identifier_dict,
                "page": page,
                "view_url": "get_identifiers_view",
                "edit_url": "edit_identifier_view",
            },
        )

    except ValueError as e:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Error viewing identifier {identifier_id}: {e}")
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=str(e))


@identifiers_views_router.get("/new/", response_class=HTMLResponse)
async def new_identifier_view(
    request: Request,
    page_id: Optional[int] = None,
    token: str = Depends(verify_auth_token),
):
    """Display form for adding a new identifier."""
    page = None
    if page_id:
        try:
            page = query_page_by_id(page_id=page_id, engine=DB_ENGINE, session=Session)
        except ValueError:
            pass  # Page not found, let user select

    return templates.TemplateResponse(
        "identifiers/new_identifier.html",
        {
            "request": request,
            "page": page,
            "view_url": "get_identifiers_view",
        },
    )


@identifiers_views_router.post("/new", response_class=HTMLResponse)
async def create_identifier_view(
    request: Request,
    page_id: int = Form(...),
    element_name: str = Form(...),
    locator_strategy: str = Form(...),
    locator_query: str = Form(...),
    action: str = Form(""),
    environments: List[str] = Form([]),
    token: str = Depends(verify_auth_token),
):
    """Handle form submission for creating a new identifier."""
    try:
        # Validate page exists
        page = query_page_by_id(page_id=page_id, engine=DB_ENGINE, session=Session)

        # Clean up form data
        action = action.strip() if action else None

        # Create identifier model
        identifier = IdentifierModel(
            id=0,  # Will be set by database
            page_id=page_id,
            element_name=element_name.strip(),
            locator_strategy=locator_strategy.strip(),
            locator_query=locator_query.strip(),
            action=action,
            environments=environments,
            created_at=None,  # Will be set by database
        )

        new_identifier = insert_identifier(
            identifier=identifier, engine=DB_ENGINE, session=Session
        )

        logger.info(f"Created new identifier: {element_name} (ID: {new_identifier.id})")

        return f"""
        <div class="alert alert-success alert-dismissible fade show" role="alert">
            <strong>Success!</strong> Identifier created successfully.
            <a href="/identifiers/{new_identifier.id}" class="alert-link">View identifier details</a>
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
        """

    except ValueError as e:
        logger.warning(f"Failed to create identifier: {e}")
        return f"""
        <div class="alert alert-danger alert-dismissible fade show" role="alert">
            <strong>Error!</strong> {str(e)}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
        """
    except Exception as e:
        logger.error(f"Unexpected error creating identifier: {e}")
        return """
        <div class="alert alert-danger alert-dismissible fade show" role="alert">
            <strong>Error!</strong> Failed to create identifier. Please try again.
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
        """


@identifiers_views_router.get("/{identifier_id}/edit", response_class=HTMLResponse)
async def edit_identifier_view(
    request: Request, identifier_id: int, token: str = Depends(verify_auth_token)
):
    """Display form for editing an identifier."""
    try:
        identifier = query_identifier_by_id(
            identifier_id=identifier_id, engine=DB_ENGINE, session=Session
        )
        page = query_page_by_id(
            page_id=identifier.page_id, engine=DB_ENGINE, session=Session
        )

        return templates.TemplateResponse(
            "identifiers/edit_identifier.html",
            {
                "request": request,
                "identifier": identifier,
                "page": page,
                "view_url": "get_identifiers_view",
            },
        )
    except ValueError as e:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail=str(e))


@identifiers_views_router.post("/{identifier_id}/edit", response_class=HTMLResponse)
async def update_identifier_view(
    request: Request,
    identifier_id: int,
    page_id: int = Form(...),
    element_name: str = Form(...),
    locator_strategy: str = Form(...),
    locator_query: str = Form(...),
    action: str = Form(""),
    environments: List[str] = Form([]),
    token: str = Depends(verify_auth_token),
):
    """Handle form submission for updating an identifier."""
    try:
        # Validate page exists
        page = query_page_by_id(page_id=page_id, engine=DB_ENGINE, session=Session)

        # Clean up form data
        action = action.strip() if action else None

        # Create identifier model for update
        identifier_update = IdentifierModel(
            id=identifier_id,
            page_id=page_id,
            element_name=element_name.strip(),
            locator_strategy=locator_strategy.strip(),
            locator_query=locator_query.strip(),
            action=action,
            environments=environments,
            created_at=None,  # This will be ignored in update
        )

        updated_identifier = update_identifier_by_id(
            identifier_id=identifier_id,
            identifier_update=identifier_update,
            engine=DB_ENGINE,
            session=Session,
        )

        logger.info(f"Updated identifier: {element_name} (ID: {identifier_id})")

        return f"""
        <div class="alert alert-success alert-dismissible fade show" role="alert">
            <strong>Success!</strong> Identifier updated successfully.
            <a href="/identifiers/{identifier_id}" class="alert-link">View identifier details</a>
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
        """

    except ValueError as e:
        logger.warning(f"Failed to update identifier {identifier_id}: {e}")
        return f"""
        <div class="alert alert-danger alert-dismissible fade show" role="alert">
            <strong>Error!</strong> {str(e)}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
        """
    except Exception as e:
        logger.error(f"Unexpected error updating identifier {identifier_id}: {e}")
        return """
        <div class="alert alert-danger alert-dismissible fade show" role="alert">
            <strong>Error!</strong> Failed to update identifier. Please try again.
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
        """


@identifiers_views_router.post("/{identifier_id}/delete", response_class=HTMLResponse)
async def delete_identifier_view(
    request: Request, identifier_id: int, token: str = Depends(verify_auth_token)
):
    """Delete an identifier (HTMX endpoint)."""
    try:
        identifier = query_identifier_by_id(
            identifier_id=identifier_id, engine=DB_ENGINE, session=Session
        )

        drop_identifier_by_id(
            identifier_id=identifier_id, engine=DB_ENGINE, session=Session
        )

        logger.info(
            f"Deleted identifier: {identifier.element_name} (ID: {identifier_id})"
        )

        return f"""
        <div class="alert alert-success alert-dismissible fade show" role="alert">
            <strong>Success!</strong> Identifier "{identifier.element_name}" has been deleted.
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
        logger.error(f"Error deleting identifier {identifier_id}: {e}")
        return """
        <div class="alert alert-danger alert-dismissible fade show" role="alert">
            <strong>Error!</strong> Failed to delete identifier. Please try again.
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
        """


################ API ROUTES ################


@identifiers_api_router.get("/", response_model=List[dict])
async def list_identifiers_api(token: str = Depends(verify_auth_token)):
    """List all identifiers."""
    try:
        identifiers = query_all_identifiers(engine=DB_ENGINE, session=Session)
        return [identifier.model_dump() for identifier in identifiers]
    except Exception as e:
        logger.error(f"Error listing identifiers: {e}")
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=str(e))


@identifiers_api_router.get("/{identifier_id}", response_model=dict)
async def get_identifier_api(identifier_id: int, token: str = Depends(verify_auth_token)):
    """Get a specific identifier by ID."""
    try:
        identifier = query_identifier_by_id(
            identifier_id=identifier_id, engine=DB_ENGINE, session=Session
        )
        return identifier.model_dump()
    except ValueError as e:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting identifier {identifier_id}: {e}")
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=str(e))


@identifiers_api_router.post("/", response_model=dict)
async def create_identifier_api(
    identifier: IdentifierModel, token: str = Depends(verify_auth_token)
):
    """Create a new identifier."""
    try:
        # Validate page exists
        page = query_page_by_id(
            page_id=identifier.page_id, engine=DB_ENGINE, session=Session
        )

        new_identifier = insert_identifier(
            identifier=identifier, engine=DB_ENGINE, session=Session
        )
        logger.info(f"Created new identifier via API: {identifier.element_name}")
        return new_identifier.model_dump()
    except ValueError as e:
        logger.warning(f"Failed to create identifier via API: {e}")
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error creating identifier via API: {e}")
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST, detail="Failed to create identifier"
        )


@identifiers_api_router.patch("/{identifier_id}", response_model=dict)
async def update_identifier_api(
    identifier_id: int,
    identifier_update: IdentifierModel,
    token: str = Depends(verify_auth_token),
):
    """Update an identifier."""
    try:
        updated_identifier = update_identifier_by_id(
            identifier_id=identifier_id,
            identifier_update=identifier_update,
            engine=DB_ENGINE,
            session=Session,
        )
        logger.info(f"Updated identifier via API: {identifier_id}")
        return updated_identifier.model_dump()
    except ValueError as e:
        logger.warning(f"Failed to update identifier via API: {e}")
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error updating identifier via API: {e}")
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST, detail="Failed to update identifier"
        )


@identifiers_api_router.delete("/{identifier_id}")
async def delete_identifier_api(
    identifier_id: int, token: str = Depends(verify_auth_token)
):
    """Delete an identifier."""
    try:
        identifier = query_identifier_by_id(
            identifier_id=identifier_id, engine=DB_ENGINE, session=Session
        )

        drop_identifier_by_id(
            identifier_id=identifier_id, engine=DB_ENGINE, session=Session
        )

        logger.info(f"Deleted identifier via API: {identifier.element_name}")
        return {
            "message": "Identifier deleted successfully",
            "identifier_id": identifier_id,
        }
    except ValueError as e:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Error deleting identifier {identifier_id} via API: {e}")
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST, detail="Failed to delete identifier"
        )
