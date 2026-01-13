"""
Environments are the configurations that will exist for different applications
under test. This information will contain the URL, the environment designation,
and the status of the environment. This information will be used to determine
which environment to test against and which pages/identifiers to use for the test.
"""

from fastapi import Request, APIRouter, Depends
from sqlalchemy.orm import Session

from common.service_connections.db_service.db_manager import DB_ENGINE
from app.dependencies.jwt_auth_dependency import get_current_user
from app.models.auth_models import TokenPayload


from common.fenrir_enums import EnvironmentEnum
from common.service_connections.db_service.models.environment_model import (
    EnvironmentModel,
    deactivate_environment_by_id,
    insert_environment,
    query_all_environments,
    query_environment_by_id,
    insert_environment,
    update_environment_by_id,
)
from app.config import get_base_app_config


API_VERSION = get_base_app_config().api_version or "v1"

################ API ROUTES ################

env_api_router = APIRouter(prefix="/env/api", tags=["env"], include_in_schema=True)


@env_api_router.post("/")
async def create_environment(
    request: Request,
    environment: EnvironmentModel,
    current_user: TokenPayload = Depends(get_current_user),
) -> EnvironmentModel:
    env_id = insert_environment(environment=environment, engine=DB_ENGINE)
    with Session(DB_ENGINE) as db_session:
        return query_environment_by_id(
            environment_id=env_id, session=db_session, engine=DB_ENGINE
        )


@env_api_router.get("/")
async def view_all_environments(
    request: Request, current_user: TokenPayload = Depends(get_current_user)
):
    with Session(DB_ENGINE) as db_session:
        return query_all_environments(session=db_session, engine=DB_ENGINE)


@env_api_router.get("/{environment_id}")
async def get_environment(
    request: Request, environment_id: str, current_user: TokenPayload = Depends(get_current_user)
):
    with Session(DB_ENGINE) as db_session:
        return query_environment_by_id(
            environment_id=environment_id, session=db_session, engine=DB_ENGINE
        )


@env_api_router.patch("/{environment_id}")
async def update_environment(
    request: Request,
    environment_id: str,
    environment: EnvironmentModel,
    current_user: TokenPayload = Depends(get_current_user),
) -> EnvironmentModel:
    update_environment_by_id(
        environment_id=environment_id,
        environment=environment,
        engine=DB_ENGINE,
    )
    with Session(DB_ENGINE) as db_session:
        return query_environment_by_id(
            environment_id=environment_id, session=db_session, engine=DB_ENGINE
        )


@env_api_router.delete("/{environment_id}")
async def delete_environment(
    request: Request, environment_id: str, current_user: TokenPayload = Depends(get_current_user)
):
    return deactivate_environment_by_id(environment_id=environment_id, engine=DB_ENGINE)
