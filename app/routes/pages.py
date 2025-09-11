"""
Page routes for environments Pages are the identifiers for the web pages that
Selenium will interact with.
"""

import json
from fastapi import Request, APIRouter, Depends
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from common.service_connections.db_service.db_manager import DB_ENGINE
from app.dependencies.auth_dependency import verify_auth_token

from common.service_connections.db_service.page_model import (
    PageModel,
    drop_page_by_id,
    insert_page,
    query_all_pages,
    query_page_by_id,
    update_page_by_id,
)
from app import TEMPLATE_PATH
from app.routes.template_dataclasses import (
    TableDataclass,
    ViewRecordDataclass,
)


page_router = APIRouter(prefix="/pages", tags=["pages"], include_in_schema=False)

page_templates = Jinja2Templates(TEMPLATE_PATH)


@page_router.get("/")
async def get_pages(request: Request, token: str = Depends(verify_auth_token)):
    return page_templates.TemplateResponse(
        "table.html",
        TableDataclass(
            title="Pages",
            request=request,
            headers=["ID", "Page Name", "URL"],
            table_rows=[],
            view_url="get_pages",
            view_record_url="view_page",
            add_url="new_page",
            delete_url="delete_page",
        ).model_dump(),
    )


@page_router.get("/new")
async def new_page(request: Request, token: str = Depends(verify_auth_token)):
    return page_templates.TemplateResponse(
        "/pages/pages_new.html",
        {"request": request, "view_url": "get_pages"},
    )


@page_router.get("/{record_id}")
async def view_page(
    request: Request, record_id: int, token: str = Depends(verify_auth_token)
):
    record = query_page_by_id(page_id=record_id, engine=DB_ENGINE, session=Session)
    return page_templates.TemplateResponse(
        "view_record.html",
        ViewRecordDataclass(
            request=request,
            record=record,
            view_url="get_pages",
            edit_url="edit_page",
        ).model_dump(),
    )


@page_router.patch("/{record_id}")
def edit_page(request: Request, record_id: int, page: PageModel):
    pass


@page_router.delete("/{record_id}")
def delete_page(
    request: Request, record_id: int, token: str = Depends(verify_auth_token)
):
    pass


page_api_router = APIRouter(prefix="/api/pages", tags=["pages"], include_in_schema=True)


@page_api_router.post("/")
def create_page(
    request: Request, page: PageModel, token: str = Depends(verify_auth_token)
):
    page.identifiers = json.dumps(page.identifiers)
    return insert_page(page=page, engine=DB_ENGINE, session=Session)


@page_api_router.get("/")
def get_pages(request: Request, token: str = Depends(verify_auth_token)):
    return {
        "request": request,
        "data": query_all_pages(engine=DB_ENGINE, session=Session),
    }


@page_api_router.get("/{record_id}")
def get_page(record_id: int, token: str = Depends(verify_auth_token)):
    return query_page_by_id(page_id=record_id, engine=DB_ENGINE, session=Session)


@page_api_router.patch("/{record_id}")
def edit_page(record_id: int, page: PageModel, token: str = Depends(verify_auth_token)):
    return update_page_by_id(
        page_id=record_id, page=page, engine=DB_ENGINE, session=Session
    )


@page_api_router.delete("/{record_id}")
def delete_page(record_id: int, token: str = Depends(verify_auth_token)):
    drop_page_by_id(page_id=record_id, engine=DB_ENGINE, session=Session)
    return
