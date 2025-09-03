"""
Page routes for environments Pages are the identifiers for the web pages that
Selenium will interact with.
"""

import json
from fastapi import Request, APIRouter
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from common.service_connections.db_service.db_manager import DB_ENGINE

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
async def get_pages(request: Request):
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
async def new_page(request: Request):
    return page_templates.TemplateResponse(
        "/pages/pages_new.html",
        {"request": request, "view_url": "get_pages"},
    )


@page_router.get("/{record_id}")
async def view_page(request: Request, record_id: int):
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
def delete_page(request: Request, record_id: int):
    pass


page_api_router = APIRouter(prefix="/api/pages", tags=["pages"], include_in_schema=True)


@page_api_router.post("/")
def create_page(request: Request, page: PageModel):
    page.identifiers = json.dumps(page.identifiers)
    return insert_page(page=page, engine=DB_ENGINE, session=Session)


@page_api_router.get("/")
def get_pages(request: Request):
    return {
        "request": request,
        "data": query_all_pages(engine=DB_ENGINE, session=Session),
    }


@page_api_router.get("/{record_id}")
def get_page(record_id: int):
    return query_page_by_id(page_id=record_id, engine=DB_ENGINE, session=Session)


@page_api_router.patch("/{record_id}")
def edit_page(record_id: int, page: PageModel):
    return update_page_by_id(
        page_id=record_id, page=page, engine=DB_ENGINE, session=Session
    )


@page_api_router.delete("/{record_id}")
def delete_page(record_id: int):
    drop_page_by_id(page_id=record_id, engine=DB_ENGINE, session=Session)
    return
