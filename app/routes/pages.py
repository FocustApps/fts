"""
Page routes for environments Pages are the identifiers for the web pages that
Selenium will interact with.
"""

from fastapi import Request, APIRouter, Depends
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from common.service_connections.db_service.db_manager import DB_ENGINE
from app.dependencies.multi_user_auth_dependency import verify_auth_token

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
)


page_router = APIRouter(prefix="/pages", tags=["pages"], include_in_schema=False)

page_templates = Jinja2Templates(TEMPLATE_PATH)


@page_router.get("/")
async def get_pages(request: Request, token: str = Depends(verify_auth_token)):
    # Get all pages with their data
    pages = query_all_pages(engine=DB_ENGINE, session=Session)

    # Format pages for the table display
    table_rows = []
    for page in pages:
        table_rows.append(
            {
                "id": page.id,
                "page_name": page.page_name,
                "page_url": page.page_url,
                "identifier_count": len(page.identifiers),
                "environments": (
                    ", ".join(page.environments) if page.environments else "None"
                ),
            }
        )

    return page_templates.TemplateResponse(
        "table.html",
        TableDataclass(
            title="Pages",
            request=request,
            headers=["ID", "Page Name", "URL", "Identifiers", "Environments"],
            table_rows=table_rows,
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
    page = query_page_by_id(page_id=record_id, engine=DB_ENGINE, session=Session)

    # Convert PageModel to a dictionary for the template
    page_dict = {
        "id": page.id,
        "page_name": page.page_name,
        "page_url": page.page_url,
        "created_at": page.created_at,
        "environments": ", ".join(page.environments) if page.environments else "None",
        "identifier_count": len(page.identifiers),
    }

    # Convert identifiers to dictionaries for template
    identifiers_list = []
    for identifier in page.identifiers:
        identifier_dict = {
            "id": identifier.id,
            "element_name": identifier.element_name,
            "locator_strategy": identifier.locator_strategy,
            "locator_query": identifier.locator_query,
            "action": identifier.action,
            "environments": identifier.environments if identifier.environments else [],
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


@page_router.get("/{record_id}/edit")
async def edit_page_form(
    request: Request, record_id: int, token: str = Depends(verify_auth_token)
):
    page = query_page_by_id(page_id=record_id, engine=DB_ENGINE, session=Session)
    return page_templates.TemplateResponse(
        "pages/pages_edit.html",
        {
            "request": request,
            "page": page,
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
    updated_page = update_page_by_id(
        page_id=record_id, page=page, engine=DB_ENGINE, session=Session
    )
    return updated_page


@page_router.delete("/{record_id}")
def delete_page(
    request: Request, record_id: int, token: str = Depends(verify_auth_token)
):
    drop_page_by_id(page_id=record_id, engine=DB_ENGINE, session=Session)
    return {"message": "Page deleted successfully"}


page_api_router = APIRouter(prefix="/api/pages", tags=["pages"], include_in_schema=True)


@page_api_router.post("/")
def create_page(
    request: Request, page: PageModel, token: str = Depends(verify_auth_token)
):
    # The identifiers are now proper IdentifierModel objects, no need for JSON conversion
    return insert_page(page=page, engine=DB_ENGINE, session=Session)


@page_api_router.get("/")
def get_pages_api(request: Request, token: str = Depends(verify_auth_token)):
    pages = query_all_pages(engine=DB_ENGINE, session=Session)
    return {"data": [page.model_dump() for page in pages]}


@page_api_router.get("/{record_id}")
def get_page(record_id: int, token: str = Depends(verify_auth_token)):
    return query_page_by_id(page_id=record_id, engine=DB_ENGINE, session=Session)


@page_api_router.patch("/{record_id}")
def edit_page(record_id: int, page: PageModel, token: str = Depends(verify_auth_token)):
    return update_page_by_id(
        page_id=record_id, page=page, engine=DB_ENGINE, session=Session
    )


@page_api_router.delete("/{record_id}")
def delete_page_api(record_id: int, token: str = Depends(verify_auth_token)):
    drop_page_by_id(page_id=record_id, engine=DB_ENGINE, session=Session)
    return {"message": "Page deleted successfully"}
