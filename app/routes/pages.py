"""
Page routes for environments Pages are the identifiers for the web pages that
Selenium will interact with.
"""

from fastapi import Request, APIRouter, Depends

from sqlalchemy.orm import Session

from common.service_connections.db_service.db_manager import DB_ENGINE
from app.dependencies.jwt_auth_dependency import get_current_user
from app.models.auth_models import TokenPayload

from common.service_connections.db_service.models.user_interface_models.page_model import (
    PageModel,
    drop_page_by_id,
    insert_page,
    query_all_pages,
    query_page_by_id,
    update_page_by_id,
)

page_api_router = APIRouter(prefix="/api/pages", tags=["pages"], include_in_schema=True)


@page_api_router.post("/")
def create_page(
    request: Request, page: PageModel, current_user: TokenPayload = Depends(get_current_user)
):
    # The identifiers are now proper IdentifierModel objects, no need for JSON conversion
    page_id = insert_page(page=page, engine=DB_ENGINE)
    with Session(DB_ENGINE) as db_session:
        return query_page_by_id(page_id=page_id, session=db_session, engine=DB_ENGINE)


@page_api_router.get("/")
def get_pages_api(request: Request, current_user: TokenPayload = Depends(get_current_user)):
    with Session(DB_ENGINE) as db_session:
        pages = query_all_pages(session=db_session, engine=DB_ENGINE)
    return {"data": [page.model_dump() for page in pages]}


@page_api_router.get("/{record_id}")
def get_page(record_id: int, current_user: TokenPayload = Depends(get_current_user)):
    with Session(DB_ENGINE) as db_session:
        return query_page_by_id(page_id=record_id, session=db_session, engine=DB_ENGINE)


@page_api_router.patch("/{record_id}")
def edit_page(record_id: int, page: PageModel, current_user: TokenPayload = Depends(get_current_user)):
    update_page_by_id(page_id=record_id, page=page, engine=DB_ENGINE)
    with Session(DB_ENGINE) as db_session:
        return query_page_by_id(page_id=record_id, session=db_session, engine=DB_ENGINE)


@page_api_router.delete("/{record_id}")
def delete_page_api(record_id: int, current_user: TokenPayload = Depends(get_current_user)):
    drop_page_by_id(page_id=record_id, engine=DB_ENGINE)
    return {"message": "Page deleted successfully"}
