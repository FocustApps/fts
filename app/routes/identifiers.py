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
from common.service_connections.db_service.models.user_interface_models.identifier_model import (
    IdentifierModel,
    query_all_identifiers,
    query_identifier_by_id,
    insert_identifier,
    update_identifier_by_id,
    drop_identifier_by_id,
)
from common.service_connections.db_service.models.user_interface_models.page_model import (
    query_all_pages,
    query_page_by_id,
)
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


@identifiers_views_router.get(
    "/", response_class=HTMLResponse, name="get_identifiers_view"
)
async def get_identifiers_view(request: Request, token: str = Depends(verify_auth_token)):
    """Display the identifiers management page."""
    try:
        with Session(DB_ENGINE) as db_session:
            identifiers: List[IdentifierModel] = query_all_identifiers(
                session=db_session, engine=DB_ENGINE
            )

        headers = [
            key.replace("_", " ").title() for key in identifiers[0].model_dump().keys()
        ]

        return templates.TemplateResponse(
            "table.html",
            {
                "title": "Identifiers",
                "request": request,
                "headers": headers,
                "table_rows": identifiers,
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


@identifiers_views_router.get(
    "/{record_id}", response_class=HTMLResponse, name="view_identifier"
)
async def view_identifier(
    request: Request, record_id: int, token: str = Depends(verify_auth_token)
):
    """Display details for a specific identifier."""
    try:
        with Session(DB_ENGINE) as db_session:
            identifier = query_identifier_by_id(
                identifier_id=record_id, session=db_session, engine=DB_ENGINE
            )

            # Get the associated page
            page = query_page_by_id(
                page_id=identifier.page_id, session=db_session, engine=DB_ENGINE
            )

        identifier_dict = {
            "identifier_id": identifier.identifier_id,
            "element_name": identifier.element_name,
            "locator_strategy": identifier.locator_strategy,
            "locator_query": identifier.locator_query,
            "page_id": identifier.page_id,
            "page_name": page.page_name,
            "created_at": identifier.created_at.strftime("%Y-%m-%d %H:%M UTC"),
        }

        return templates.TemplateResponse(
            "identifiers/view_identifier.html",
            {
                "request": request,
                "identifier": identifier_dict,
                "page": page,
                "view_url": "get_identifiers_view",
                "edit_url": "edit_identifier",
            },
        )

    except ValueError as e:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Error viewing identifier {record_id}: {e}")
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=str(e))


@identifiers_views_router.get(
    "/new/", response_class=HTMLResponse, name="new_identifier_view"
)
async def new_identifier_view(
    request: Request,
    page_id: Optional[int] = None,
    token: str = Depends(verify_auth_token),
):
    """Display form for adding a new identifier."""
    page = None
    pages = []

    if page_id:
        try:
            with Session(DB_ENGINE) as db_session:
                page = query_page_by_id(
                    page_id=page_id, session=db_session, engine=DB_ENGINE
                )
        except ValueError:
            # Page not found, fall back to generic mode
            page = None
            with Session(DB_ENGINE) as db_session:
                pages = query_all_pages(session=db_session, engine=DB_ENGINE)
    else:
        # Generic mode - load all pages for selection
        with Session(DB_ENGINE) as db_session:
            pages = query_all_pages(session=db_session, engine=DB_ENGINE)

    return templates.TemplateResponse(
        "identifiers/new_identifier.html",
        {
            "request": request,
            "page": page,
            "pages": pages,
            "view_url": "get_identifiers_view",
        },
    )


@identifiers_views_router.post(
    "/new", response_class=HTMLResponse, name="create_identifier"
)
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
        with Session(DB_ENGINE) as db_session:
            page = query_page_by_id(page_id=page_id, session=db_session, engine=DB_ENGINE)

        # Clean up form data
        action = action.strip() if action else None

        # Create identifier model
        identifier = IdentifierModel(
            identifier_id=None,  # Will be set by database
            page_id=page_id,
            element_name=element_name.strip(),
            locator_strategy=locator_strategy.strip(),
            locator_query=locator_query.strip(),
            created_at=None,  # Will be set by database
        )

        new_identifier_id = insert_identifier(identifier=identifier, engine=DB_ENGINE)

        logger.info(f"Created new identifier: {element_name} (ID: {new_identifier_id})")

        return f"""
        <div class="alert alert-success alert-dismissible fade show" role="alert">
            <strong>Success!</strong> Identifier created successfully.
            <a href="/identifiers/{new_identifier_id}" class="alert-link">View identifier details</a>
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


@identifiers_views_router.get(
    "/{record_id}/edit", response_class=HTMLResponse, name="edit_identifier"
)
async def edit_identifier_view(
    request: Request, record_id: int, token: str = Depends(verify_auth_token)
):
    """Display form for editing an identifier."""
    try:
        with Session(DB_ENGINE) as db_session:
            identifier = query_identifier_by_id(
                identifier_id=record_id, session=db_session, engine=DB_ENGINE
            )
            page = query_page_by_id(
                page_id=identifier.page_id, session=db_session, engine=DB_ENGINE
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


@identifiers_views_router.post(
    "/{record_id}/edit", response_class=HTMLResponse, name="update_identifier"
)
async def update_identifier_view(
    request: Request,
    record_id: int,
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
        with Session(DB_ENGINE) as db_session:
            page = query_page_by_id(page_id=page_id, session=db_session, engine=DB_ENGINE)

        # Clean up form data
        action = action.strip() if action else None

        # Create identifier model for update
        identifier_update = IdentifierModel(
            identifier_id=record_id,
            page_id=page_id,
            element_name=element_name.strip(),
            locator_strategy=locator_strategy.strip(),
            locator_query=locator_query.strip(),
            created_at=None,  # This will be ignored in update
        )

        update_identifier_by_id(
            identifier_id=record_id,
            identifier_update=identifier_update,
            engine=DB_ENGINE,
        )

        logger.info(f"Updated identifier: {element_name} (ID: {record_id})")

        return f"""
        <div class="alert alert-success alert-dismissible fade show" role="alert">
            <strong>Success!</strong> Identifier updated successfully.
            <a href="/identifiers/{record_id}" class="alert-link">View identifier details</a>
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
        """

    except ValueError as e:
        logger.warning(f"Failed to update identifier {record_id}: {e}")
        return f"""
        <div class="alert alert-danger alert-dismissible fade show" role="alert">
            <strong>Error!</strong> {str(e)}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
        """
    except Exception as e:
        logger.error(f"Unexpected error updating identifier {record_id}: {e}")
        return """
        <div class="alert alert-danger alert-dismissible fade show" role="alert">
            <strong>Error!</strong> Failed to update identifier. Please try again.
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
        """


@identifiers_views_router.post(
    "/{record_id}/delete", response_class=HTMLResponse, name="delete_identifier_view"
)
async def delete_identifier_view(
    request: Request, record_id: int, token: str = Depends(verify_auth_token)
):
    """Delete an identifier (HTMX endpoint)."""
    try:
        with Session(DB_ENGINE) as db_session:
            identifier = query_identifier_by_id(
                identifier_id=record_id, session=db_session, engine=DB_ENGINE
            )

        drop_identifier_by_id(identifier_id=record_id, engine=DB_ENGINE)

        logger.info(f"Deleted identifier: {identifier.element_name} (ID: {record_id})")

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
        logger.error(f"Error deleting identifier {record_id}: {e}")
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
        with Session(DB_ENGINE) as db_session:
            identifiers = query_all_identifiers(session=db_session, engine=DB_ENGINE)
        return [identifier.model_dump() for identifier in identifiers]
    except Exception as e:
        logger.error(f"Error listing identifiers: {e}")
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=str(e))


@identifiers_api_router.get(
    "/{record_id}", response_model=dict, name="get_identifier_api"
)
async def get_identifier_api(record_id: int, token: str = Depends(verify_auth_token)):
    """Get a specific identifier by ID."""
    try:
        with Session(DB_ENGINE) as db_session:
            identifier = query_identifier_by_id(
                identifier_id=record_id, session=db_session, engine=DB_ENGINE
            )
        return identifier.model_dump()
    except ValueError as e:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting identifier {record_id}: {e}")
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=str(e))


@identifiers_api_router.post("/", response_model=dict)
async def create_identifier_api(
    identifier: IdentifierModel, token: str = Depends(verify_auth_token)
):
    """Create a new identifier."""
    try:
        # Validate page exists
        with Session(DB_ENGINE) as db_session:
            page = query_page_by_id(
                page_id=identifier.page_id, session=db_session, engine=DB_ENGINE
            )

        new_identifier_id = insert_identifier(identifier=identifier, engine=DB_ENGINE)

        with Session(DB_ENGINE) as db_session:
            new_identifier = query_identifier_by_id(
                identifier_id=new_identifier_id, session=db_session, engine=DB_ENGINE
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


@identifiers_api_router.patch(
    "/{record_id}", response_model=dict, name="update_identifier_api"
)
async def update_identifier_api(
    record_id: int,
    identifier_update: IdentifierModel,
    token: str = Depends(verify_auth_token),
):
    """Update an identifier."""
    try:
        update_identifier_by_id(
            identifier_id=record_id,
            identifier_update=identifier_update,
            engine=DB_ENGINE,
        )

        with Session(DB_ENGINE) as db_session:
            updated_identifier = query_identifier_by_id(
                identifier_id=record_id, session=db_session, engine=DB_ENGINE
            )

        logger.info(f"Updated identifier via API: {record_id}")
        return updated_identifier.model_dump()
    except ValueError as e:
        logger.warning(f"Failed to update identifier via API: {e}")
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error updating identifier via API: {e}")
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST, detail="Failed to update identifier"
        )


@identifiers_api_router.delete("/{record_id}", name="delete_identifier_api")
async def delete_identifier_api(record_id: int, token: str = Depends(verify_auth_token)):
    """Delete an identifier."""
    try:
        with Session(DB_ENGINE) as db_session:
            identifier = query_identifier_by_id(
                identifier_id=record_id, session=db_session, engine=DB_ENGINE
            )

        drop_identifier_by_id(identifier_id=record_id, engine=DB_ENGINE)

        logger.info(f"Deleted identifier via API: {identifier.element_name}")
        return {
            "message": "Identifier deleted successfully",
            "identifier_id": record_id,
        }
    except ValueError as e:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Error deleting identifier {record_id} via API: {e}")
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST, detail="Failed to delete identifier"
        )
