"""
The users module contains the API and views for users that have
access to environments.
"""

from fastapi import Request, APIRouter, Depends

from sqlalchemy.orm import Session

from app.config import get_base_app_config
from common.service_connections.db_service.db_manager import DB_ENGINE
from app.dependencies.jwt_auth_dependency import get_current_user
from app.models.auth_models import TokenPayload

from common.service_connections.db_service.models.environment_model import (
    EnvironmentModel,
    update_environment_by_id,
)
from common.service_connections.db_service.models.account_models.user_model import (
    UserModel,
    insert_user,
    query_all_users,
    query_user_by_id,
    insert_user,
    drop_user_by_id,
    update_user_by_id,
)

API_VERSION = get_base_app_config().api_version or "v1"

################ API ROUTES ################

user_api_router = APIRouter(prefix="/user/api", tags=["user"], include_in_schema=True)


@user_api_router.post("/user")
def create_user(
    request: Request,
    user: UserModel,
    current_user: TokenPayload = Depends(get_current_user),
) -> UserModel:
    user_id = insert_user(user=user, engine=DB_ENGINE)
    with Session(DB_ENGINE) as db_session:
        new_user = query_user_by_id(user_id=user_id, session=db_session, engine=DB_ENGINE)
    update_environment_by_id(
        environment_id=user.environment_id,
        environment=EnvironmentModel(users=[new_user]),
        engine=DB_ENGINE,
    )
    return new_user


@user_api_router.get("/all-users")
def get_all_users(
    request: Request, current_user: TokenPayload = Depends(get_current_user)
):
    with Session(DB_ENGINE) as db_session:
        return query_all_users(session=db_session, engine=DB_ENGINE)


@user_api_router.get("/user/{record_id}")
def get_user_by_id(
    request: Request,
    record_id: int,
    current_user: TokenPayload = Depends(get_current_user),
):
    with Session(DB_ENGINE) as db_session:
        return query_user_by_id(user_id=record_id, session=db_session, engine=DB_ENGINE)


@user_api_router.put("/user/{record_id}")
def update_user(
    request: Request,
    record_id: int,
    user: UserModel,
    current_user: TokenPayload = Depends(get_current_user),
):
    return update_user_by_id(user_id=record_id, user=user, engine=DB_ENGINE)


@user_api_router.delete("/user/{record_id}")
def delete_user_by_id(
    request: Request,
    record_id: int,
    current_user: TokenPayload = Depends(get_current_user),
):
    return drop_user_by_id(user_id=record_id, engine=DB_ENGINE)
