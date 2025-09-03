"""
Environments are the configurations that will exist for different applications
under test. This information will contain the URL, the environment designation,
and the status of the environment. This information will be used to determine
which environment to test against and which pages/identifiers to use for the test.
"""

from fastapi import Request, APIRouter
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from common.service_connections.db_service.db_manager import DB_ENGINE

from app import TEMPLATE_PATH
from app.routes.template_dataclasses import ViewRecordDataclass
from common.fenrir_enums import EnvironmentEnum
from common.service_connections.db_service.environment_model import (
    EnvironmentModel,
    insert_environment,
    query_all_environments,
    query_environment_by_id,
    insert_environment,
    drop_environment_by_id,
    update_environment_by_id,
)
from app.config import get_base_app_config


API_VERSION = get_base_app_config().api_version or "v1"

env_views_router = APIRouter(
    prefix="/env", tags=["frontend"], include_in_schema=False
)


environments_templates = Jinja2Templates(directory=TEMPLATE_PATH)


@env_views_router.get("/")
async def get_environments(request: Request):
    environments = query_all_environments(engine=DB_ENGINE, session=Session)
    for env in environments:
        del env.status
        del env.created_at
        del env.updated_at

    # Handle empty environments list
    if environments:
        headers = [
            key.replace("_", " ").title() for key in environments[0].model_dump().keys()
        ]
    else:
        # Default headers when no environments exist
        headers = ["Id", "Name", "Environment Designation", "Url", "Api Url", "Users"]

    return environments_templates.TemplateResponse(
        "table.html",
        {
            "title": "Environments",
            "request": request,
            "headers": headers,
            "table_rows": environments,
            "view_url": "get_environments",
            "add_url": "new_environment",
            "view_record_url": "view_environment",
            "delete_url": "delete_environment",
        },
    )


@env_views_router.get("/new-environment")
async def new_environment(request: Request):
    return environments_templates.TemplateResponse(
        "/environments/env_new.html",
        {
            "request": request,
            "view_url": "get_environments",
            "EnvironmentEnum": EnvironmentEnum,
        },
    )


@env_views_router.get("/{record_id}")
async def view_environment(request: Request, record_id: int):
    environment = query_environment_by_id(
        environment_id=record_id, engine=DB_ENGINE, session=Session
    )
    users = [user for user in environment.users]
    return environments_templates.TemplateResponse(
        "view_record.html",
        ViewRecordDataclass(
            request=request,
            record=environment.model_dump(),
            view_url="get_environments",
            edit_url="view_edit_environment",
            users=users,
        ).model_dump(),
    )


@env_views_router.patch("/{record_id}")
async def view_updated_environment(
    request: Request, record_id: int, environment: EnvironmentModel
) -> EnvironmentModel:
    updated_env = update_environment_by_id(
        environment_id=record_id,
        environment=environment,
        engine=DB_ENGINE,
        session=Session,
    )
    return environments_templates.TemplateResponse(
        "view_record.html",
        ViewRecordDataclass(
            request=request,
            record=updated_env.model_dump(),
            view_url="get_environments",
            edit_url="view_edit_environment",
        ).model_dump(),
    )


@env_views_router.get("/{record_id}/edit")
def view_edit_environment(request: Request, record_id: int):
    environment = query_environment_by_id(
        environment_id=record_id, engine=DB_ENGINE, session=Session
    )
    return environments_templates.TemplateResponse(
        "/environments/env_edit.html",
        {
            "request": request,
            "environment": environment.model_dump(),
            "EnvironmentEnum": EnvironmentEnum,
        },
    )


################ API ROUTES ################


env_api_router = APIRouter(prefix="/env/api", tags=["env"], include_in_schema=True)


@env_api_router.post("/")
async def create_environment(
    request: Request, environment: EnvironmentModel
) -> EnvironmentModel:
    return insert_environment(environment=environment, engine=DB_ENGINE, session=Session)


@env_api_router.get("/")
async def view_all_environments(request: Request):
    return query_all_environments(engine=DB_ENGINE, session=Session)


@env_api_router.get("/{record_id}")
async def get_environment(request: Request, record_id: int):
    return query_environment_by_id(
        environment_id=record_id, engine=DB_ENGINE, session=Session
    )


@env_api_router.patch("/{record_id}")
async def update_environment(
    request: Request, record_id: int, environment: EnvironmentModel
) -> EnvironmentModel:
    return update_environment_by_id(
        environment_id=record_id,
        environment=environment,
        engine=DB_ENGINE,
        session=Session,
    )


@env_api_router.delete("/{record_id}")
async def delete_environment(request: Request, record_id: int):
    drop_environment_by_id(environment_id=record_id, engine=DB_ENGINE, session=Session)
    return
