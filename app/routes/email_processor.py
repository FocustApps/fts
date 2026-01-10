import logging
from fastapi import Request, APIRouter, Depends
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from common.service_connections.db_service.db_manager import DB_ENGINE
from app.dependencies.multi_user_auth_dependency import verify_auth_token

from app import TEMPLATE_PATH
from app.routes.template_dataclasses import ViewRecordDataclass

from common.service_connections.db_service.models.email_processor_model import (
    SystemEnum,
    EmailProcessorModel,
    insert_email_item,
    query_email_item_by_id,
    query_email_item_by_email_item_id,
    update_email_item_by_id,
    query_all_email_items,
    drop_email_item_by_id,
)

email_processor_views_router = APIRouter(
    prefix="/email_processor", tags=["frontend"], include_in_schema=False
)

email_processor_templates = Jinja2Templates(directory=TEMPLATE_PATH)


@email_processor_views_router.get("/", response_class=HTMLResponse)
async def get_email_processing_items(
    request: Request, token: str = Depends(verify_auth_token)
):
    with Session(DB_ENGINE) as db_session:
        email_items = query_all_email_items(session=db_session, engine=DB_ENGINE)
    for email_item in email_items:
        del email_item.created_at
        del email_item.updated_at

    # Handle empty email_items list
    if email_items:
        headers = [
            key.replace("_", " ").title() for key in email_items[0].model_dump().keys()
        ]
    else:
        # Default headers when no email items exist
        headers = [
            "Email Processor Id",
            "Email Item Id",
            "Multi Item Email Ids",
            "Multi Email Flag",
            "Multi Attachment Flag",
            "Test Name",
            "Requires Processing",
            "Last Processed At",
        ]

    return email_processor_templates.TemplateResponse(
        "table.html",
        {
            "title": "Email Items",
            "request": request,
            "headers": headers,
            "table_rows": email_items,
            "view_url": "get_email_processing_items",
            "add_url": "create_email_item",
            "view_record_url": "view_email_item",
            "delete_url": "delete_email_item",
        },
    )


@email_processor_views_router.get("/email-item/{record_id}", response_class=HTMLResponse)
async def view_email_item(
    request: Request, record_id: int, token: str = Depends(verify_auth_token)
):

    with Session(DB_ENGINE) as db_session:
        email_item = query_email_item_by_id(
            email_item_id=record_id, session=db_session, engine=DB_ENGINE
        )
    return email_processor_templates.TemplateResponse(
        "view_record.html",
        ViewRecordDataclass(
            request=request,
            record=email_item.model_dump(),
            view_url="get_email_processing_items",
            edit_url="view_edit_email_item",
        ).model_dump(),
    )


@email_processor_views_router.get("/new-email-item", response_class=HTMLResponse)
async def new_email_item(request: Request, token: str = Depends(verify_auth_token)):
    return email_processor_templates.TemplateResponse(
        "email_processor/email_processor_new.html",
        {
            "request": request,
            "view_url": "get_email_processing_items",
            "system_choices": SystemEnum.get_valid_systems(),
        },
    )


@email_processor_views_router.post("/new-email-item", response_class=HTMLResponse)
async def create_email_item(
    request: Request,
    email_item: EmailProcessorModel,
    token: str = Depends(verify_auth_token),
):
    from common.service_connections.test_case_service.azure_devops_test_cases import (
        get_work_item_by_id,
    )

    logging.info(f"Email Item ID: {email_item.email_item_id}")

    try:
        valid_email_item = get_work_item_by_id(email_item.email_item_id.__str__())
    except:
        return f"Email Item ID {email_item.email_item_id} not found."
    try:
        with Session(DB_ENGINE) as db_session:
            if query_email_item_by_email_item_id(
                email_item.email_item_id.__str__(), session=db_session, engine=DB_ENGINE
            ):
                return f"Email Item ID {email_item.email_item_id} already exists."
    except ValueError:
        pass

    if valid_email_item.id:
        email_item = insert_email_item(email_item, engine=DB_ENGINE)
        return email_processor_templates.TemplateResponse(
            "view_record.html",
            ViewRecordDataclass(
                request=request,
                record=email_item.model_dump(),
                view_url="get_email_processing_items",
                edit_url="update_email_item",
            ).model_dump(),
        )


@email_processor_views_router.patch("/{record_id}", response_class=HTMLResponse)
async def update_email_item(
    request: Request, record_id: int, email_item: EmailProcessorModel
):
    if email_item.multi_attachment_flag:
        email_item.multi_attachment_flag = True

    email_item = update_email_item_by_id(
        email_item_id=record_id, email_item=email_item, engine=DB_ENGINE
    )
    return email_processor_templates.TemplateResponse(
        "view_record.html",
        ViewRecordDataclass(
            request=request,
            record=email_item.model_dump(),
            view_url="get_email_processing_items",
            edit_url="view_edit_email_item",
        ).model_dump(),
    )


@email_processor_views_router.get(
    "/email-item/{record_id}/edit", response_class=HTMLResponse
)
async def view_edit_email_item(
    request: Request, record_id: int, token: str = Depends(verify_auth_token)
):
    with Session(DB_ENGINE) as db_session:
        email_item = query_email_item_by_id(
            email_item_id=record_id, session=db_session, engine=DB_ENGINE
        )
    return email_processor_templates.TemplateResponse(
        name="email_processor/email_processor_edit.html",
        context=ViewRecordDataclass(
            request=request,
            record=email_item.model_dump(),
            view_url="get_email_processing_items",
            edit_url="update_email_item",
            system_choices=SystemEnum.get_valid_systems(),
        ).model_dump(),
    )


@email_processor_views_router.delete("/{record_id}")
async def delete_email_item(
    request: Request, record_id: int, token: str = Depends(verify_auth_token)
):

    email_item = drop_email_item_by_id(email_item_id=record_id, engine=DB_ENGINE)
    return email_item
