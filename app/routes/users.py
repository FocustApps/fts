"""
The users module contains the API and views for users that have
access to environments.
"""

from fastapi import Request, APIRouter, Depends
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.config import get_base_app_config
from common.service_connections.db_service.db_manager import DB_ENGINE
from app.dependencies.multi_user_auth_dependency import verify_auth_token

from app import TEMPLATE_PATH
from app.routes.template_dataclasses import ViewRecordDataclass
from common.fenrir_enums import CloudProviderEnum
from common.service_connections.db_service.environment_model import (
    EnvironmentModel,
    query_all_environments,
    update_environment_by_id,
)
from common.service_connections.db_service.user_model import (
    UserModel,
    insert_user,
    query_all_users,
    query_user_by_id,
    insert_user,
    drop_user_by_id,
    update_user_by_id,
)

API_VERSION = get_base_app_config().api_version or "v1"

user_views_router = APIRouter(prefix="/user", tags=["frontend"], include_in_schema=False)

user_templates = Jinja2Templates(directory=TEMPLATE_PATH)


@user_views_router.get("/", response_class=HTMLResponse)
async def get_users(request: Request):
    users = query_all_users(engine=DB_ENGINE, session=Session)
    for user in users:
        del user.created_at
        del user.updated_at
        del user.password
        del user.secret_provider

    # Handle empty users list
    if users:
        headers = [key.replace("_", " ").title() for key in users[0].model_dump().keys()]
    else:
        # Default headers when no users exist
        headers = [
            "Id",
            "Username",
            "Email",
            "Secret Url",
            "Secret Name",
            "Environment Id",
        ]

    return user_templates.TemplateResponse(
        "table.html",
        {
            "title": "Users",
            "request": request,
            "headers": headers,
            "table_rows": users,
            "view_url": "get_users",
            "view_record_url": "view_user",
            "add_url": "new_user_view",
            "delete_url": "delete_user_by_id",
        },
    )


@user_views_router.get("/{record_id}", response_class=HTMLResponse)
async def view_user(request: Request, record_id: int):
    user = query_user_by_id(user_id=record_id, engine=DB_ENGINE, session=Session)
    user.password = len(user.password) * "*"
    return user_templates.TemplateResponse(
        "view_record.html",
        ViewRecordDataclass(
            request=request,
            record=user.model_dump(),
            view_url="get_users",
            edit_url="edit_user",
        ).model_dump(),
    )


@user_views_router.get("/new/", response_class=HTMLResponse)
async def new_user_view(request: Request):
    environments = query_all_environments(engine=DB_ENGINE, session=Session)
    return user_templates.TemplateResponse(
        "users/user_new.html",
        {
            "request": request,
            "environments": environments,
            "view_url": "get_users",
            "secret_providers": CloudProviderEnum.get_valid_providers(),
        },
    )


@user_views_router.patch("/{record_id}", response_class=HTMLResponse)
async def update_user(request: Request, record_id: int, user: UserModel) -> UserModel:
    updated_user = update_user_by_id(
        user_id=record_id, user=user, engine=DB_ENGINE, session=Session
    )
    updated_user.password = len(updated_user.password) * "*"
    return user_templates.TemplateResponse(
        "view_record.html", {"request": request, "user": updated_user.model_dump()}
    )


@user_views_router.get("/{record_id}/edit", response_class=HTMLResponse)
async def edit_user(request: Request, record_id: int):
    user = query_user_by_id(user_id=record_id, engine=DB_ENGINE, session=Session)
    user.password = len(user.password) * "*"
    return user_templates.TemplateResponse(
        "users/user_edit.html",
        {
            "request": request,
            "user": user.model_dump(),
            "secret_providers": CloudProviderEnum.get_valid_providers(),
        },
    )


################ API ROUTES ################

user_api_router = APIRouter(prefix="/user/api", tags=["user"], include_in_schema=True)


@user_api_router.post("/user")
def create_user(
    request: Request, user: UserModel, token: str = Depends(verify_auth_token)
) -> UserModel:
    new_user = insert_user(user=user, engine=DB_ENGINE, session=Session)
    update_environment_by_id(
        environment_id=user.environment_id,
        environment=EnvironmentModel(users=[new_user]),
        engine=DB_ENGINE,
        session=Session,
    )
    return new_user


@user_api_router.get("/all-users")
def get_all_users(request: Request, token: str = Depends(verify_auth_token)):
    return query_all_users(engine=DB_ENGINE, session=Session)


@user_api_router.get("/user/{record_id}")
def get_user_by_id(
    request: Request, record_id: int, token: str = Depends(verify_auth_token)
):
    return query_user_by_id(user_id=record_id, engine=DB_ENGINE, session=Session)


@user_api_router.put("/user/{record_id}")
def update_user(
    request: Request,
    record_id: int,
    user: UserModel,
    token: str = Depends(verify_auth_token),
):
    return update_user_by_id(user_id=record_id, engine=DB_ENGINE, session=Session)


@user_api_router.delete("/user/{record_id}")
def delete_user_by_id(
    request: Request, record_id: int, token: str = Depends(verify_auth_token)
):
    return drop_user_by_id(user_id=record_id, engine=DB_ENGINE, session=Session)
