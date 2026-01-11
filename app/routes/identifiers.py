"""
Identifier routes for managing web element identifiers.

Provides both API and view endpoints for creating, reading, updating, and deleting
identifiers that belong to pages in the selenium automation framework.
"""

from typing import List, Optional
from fastapi import APIRouter, Request, Form, HTTPException, Depends

from sqlalchemy.orm import Session
from starlette.status import HTTP_400_BAD_REQUEST, HTTP_404_NOT_FOUND

from common.service_connections.db_service.db_manager import DB_ENGINE
from app.dependencies.jwt_auth_dependency import get_current_user
from app.models.auth_models import TokenPayload
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

################ API ROUTES ################


@identifiers_api_router.get("/", response_model=List[dict])
async def list_identifiers_api(current_user: TokenPayload = Depends(get_current_user)):
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
async def get_identifier_api(
    record_id: int, current_user: TokenPayload = Depends(get_current_user)
):
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
    identifier: IdentifierModel, current_user: TokenPayload = Depends(get_current_user)
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
    current_user: TokenPayload = Depends(get_current_user),
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
async def delete_identifier_api(
    record_id: int, current_user: TokenPayload = Depends(get_current_user)
):
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
