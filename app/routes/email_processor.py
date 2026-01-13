"""
Email Processor routes for email automation queue management.
"""

from fastapi import APIRouter, Depends
from typing import List
from sqlalchemy.orm import Session

from common.service_connections.db_service.db_manager import DB_ENGINE
from app.dependencies.jwt_auth_dependency import get_current_user
from app.models.auth_models import TokenPayload

from common.service_connections.db_service.models.email_processor_model import (
    EmailProcessorModel,
    insert_email_item,
    query_email_item_by_id,
    query_all_email_items,
    update_email_item_by_id,
    drop_email_item_by_id,
)


email_processor_api_router = APIRouter(
    prefix="/v1/api/email-processor", tags=["email-processor-api"]
)


@email_processor_api_router.get("/", response_model=List[EmailProcessorModel])
async def get_all_email_processors(
    current_user: TokenPayload = Depends(get_current_user),
):
    """Get all email processor entries."""
    return query_all_email_items(session=Session, engine=DB_ENGINE)


@email_processor_api_router.get("/{processor_id}", response_model=EmailProcessorModel)
async def get_email_processor_by_id(
    processor_id: int,
    current_user: TokenPayload = Depends(get_current_user),
):
    """Get a specific email processor entry by ID."""
    return query_email_item_by_id(
        email_item_id=processor_id, session=Session, engine=DB_ENGINE
    )


@email_processor_api_router.post("/", response_model=EmailProcessorModel)
async def create_email_processor(
    processor: EmailProcessorModel,
    current_user: TokenPayload = Depends(get_current_user),
):
    """Create a new email processor entry."""
    return insert_email_item(email_item_id=processor, session=Session, engine=DB_ENGINE)


@email_processor_api_router.put("/{processor_id}", response_model=EmailProcessorModel)
async def update_email_processor(
    processor_id: int,
    processor: EmailProcessorModel,
    current_user: TokenPayload = Depends(get_current_user),
):
    """Update an email processor entry."""
    return update_email_item_by_id(
        email_item_id=processor_id, work_item=processor, session=Session, engine=DB_ENGINE
    )


@email_processor_api_router.delete("/{processor_id}")
async def delete_email_processor(
    processor_id: int,
    current_user: TokenPayload = Depends(get_current_user),
):
    """Delete an email processor entry."""
    drop_email_item_by_id(email_item_id=processor_id, session=Session, engine=DB_ENGINE)
    return {"status": "success", "message": f"Email processor {processor_id} deleted"}
