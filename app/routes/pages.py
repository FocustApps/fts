"""
Page routes for environments Pages are the identifiers for the web pages that
Selenium will interact with.
"""

from fastapi import Request, APIRouter, Depends
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import List

from common.service_connections.db_service.db_manager import DB_ENGINE
from app.dependencies.multi_user_auth_dependency import verify_auth_token

from common.service_connections.db_service.models.user_interface_models.page_model import (
    PageModel,
    drop_page_by_id,
    insert_page,
    query_all_pages,
    query_page_by_id,
    update_page_by_id,
)
from app import TEMPLATE_PATH


page_router = APIRouter(prefix="/pages", tags=["pages"], include_in_schema=False)

page_templates = Jinja2Templates(TEMPLATE_PATH)


@page_router.get("/", name="get_pages")
async def get_pages(request: Request, token: str = Depends(verify_auth_token)):
    # Get all pages with their data
    with Session(DB_ENGINE) as db_session:
        pages: List[PageModel] = query_all_pages(session=db_session, engine=DB_ENGINE)

    for page in pages:
        del page.created_at

    headers = ["Page Id", "Page Name", "URL", "Identifiers"]

    return page_templates.TemplateResponse(
        "table.html",
        {
            "title": "Pages",
            "request": request,
            "headers": headers,
            "table_rows": pages,
            "view_url": "get_pages",
            "view_record_url": "view_page",
            "add_url": "new_page",
            "delete_url": "delete_page",
        },
    )


@page_router.get("/new", name="new_page")
async def new_page(request: Request, token: str = Depends(verify_auth_token)):
    return page_templates.TemplateResponse(
        "/pages/pages_new.html",
        {"request": request, "view_url": "get_pages"},
    )


@page_router.get("/{record_id}", name="view_page")
async def view_page(
    request: Request, record_id: int, token: str = Depends(verify_auth_token)
):
    with Session(DB_ENGINE) as db_session:
        page = query_page_by_id(page_id=record_id, session=db_session, engine=DB_ENGINE)

    # Convert PageModel to a dictionary for the template
    page_dict = {
        "page_id": page.page_id,
        "page_name": page.page_name,
        "page_url": page.page_url,
        "created_at": page.created_at,
        "identifier_count": len(page.identifiers),
    }

    # Convert identifiers to dictionaries for template
    identifiers_list = []
    for identifier in page.identifiers:
        identifier_dict = {
            "identifier_id": identifier.identifier_id,
            "element_name": identifier.element_name,
            "locator_strategy": identifier.locator_strategy,
            "locator_query": identifier.locator_query,
        }
        identifiers_list.append(identifier_dict)

    return page_templates.TemplateResponse(
        "pages/view_page.html",
        {
            "request": request,
            "page": page_dict,
            "identifiers": identifiers_list,
            "view_url": "get_pages",
            "edit_url": "edit_page",
        },
    )


@page_router.get("/{record_id}/edit", name="edit_page")
async def edit_page_form(
    request: Request, record_id: int, token: str = Depends(verify_auth_token)
):
    with Session(DB_ENGINE) as db_session:
        page = query_page_by_id(page_id=record_id, session=db_session, engine=DB_ENGINE)

    # Create a page dictionary with serializable identifiers
    page_dict = page.model_dump()
    page_dict["identifiers"] = [
        identifier.model_dump() for identifier in page.identifiers
    ]

    return page_templates.TemplateResponse(
        "pages/pages_edit.html",
        {
            "request": request,
            "page": page_dict,
            "view_url": "get_pages",
        },
    )


@page_router.patch("/{record_id}")
def edit_page(
    request: Request,
    record_id: int,
    page: PageModel,
    token: str = Depends(verify_auth_token),
):
    update_page_by_id(page_id=record_id, page=page, engine=DB_ENGINE)
    with Session(DB_ENGINE) as db_session:
        updated_page = query_page_by_id(
            page_id=record_id, session=db_session, engine=DB_ENGINE
        )
    return updated_page


@page_router.delete("/{record_id}", name="delete_page")
def delete_page(
    request: Request, record_id: int, token: str = Depends(verify_auth_token)
):
    drop_page_by_id(page_id=record_id, engine=DB_ENGINE)
    return {"message": "Page deleted successfully"}


page_api_router = APIRouter(prefix="/api/pages", tags=["pages"], include_in_schema=True)


@page_api_router.post("/")
def create_page(
    request: Request, page: PageModel, token: str = Depends(verify_auth_token)
):
    # The identifiers are now proper IdentifierModel objects, no need for JSON conversion
    page_id = insert_page(page=page, engine=DB_ENGINE)
    with Session(DB_ENGINE) as db_session:
        return query_page_by_id(page_id=page_id, session=db_session, engine=DB_ENGINE)


@page_api_router.get("/")
def get_pages_api(request: Request, token: str = Depends(verify_auth_token)):
    with Session(DB_ENGINE) as db_session:
        pages = query_all_pages(session=db_session, engine=DB_ENGINE)
    return {"data": [page.model_dump() for page in pages]}


@page_api_router.get("/{record_id}")
def get_page(record_id: int, token: str = Depends(verify_auth_token)):
    with Session(DB_ENGINE) as db_session:
        return query_page_by_id(page_id=record_id, session=db_session, engine=DB_ENGINE)


@page_api_router.patch("/{record_id}")
def edit_page(record_id: int, page: PageModel, token: str = Depends(verify_auth_token)):
    update_page_by_id(page_id=record_id, page=page, engine=DB_ENGINE)
    with Session(DB_ENGINE) as db_session:
        return query_page_by_id(page_id=record_id, session=db_session, engine=DB_ENGINE)


@page_api_router.delete("/{record_id}")
def delete_page_api(record_id: int, token: str = Depends(verify_auth_token)):
    drop_page_by_id(page_id=record_id, engine=DB_ENGINE)
    return {"message": "Page deleted successfully"}
