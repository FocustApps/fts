"""
System Under Test routes for managing applications and systems being tested.
"""

from fastapi import APIRouter, Depends
from typing import List

from common.service_connections.db_service.db_manager import DB_ENGINE
from common.service_connections.db_service.database.engine import (
    get_database_session as get_session,
)
from app.dependencies.authorization_dependency import (
    require_member,
    require_admin,
    validate_account_access,
)
from app.models.auth_models import TokenPayload

from common.service_connections.db_service.models.system_under_test_model import (
    SystemUnderTestModel,
    insert_system_under_test,
    query_system_under_test_by_id,
    query_all_systems_under_test,
    query_systems_under_test_by_account,
    update_system_under_test_by_id,
    drop_system_under_test_by_id,
)


sut_api_router = APIRouter(prefix="/api/systems", tags=["systems-api"])


@sut_api_router.get("/", response_model=List[SystemUnderTestModel])
async def get_all_systems(
    current_user: TokenPayload = Depends(require_member),
):
    """Get all systems under test."""
    with get_session(DB_ENGINE) as db_session:
        return query_all_systems_under_test(session=db_session, engine=DB_ENGINE)


@sut_api_router.get("/account/{account_id}", response_model=List[SystemUnderTestModel])
async def get_systems_by_account(
    account_id: str,
    current_user: TokenPayload = Depends(require_member),
):
    """Get all systems under test for a specific account."""
    validate_account_access(current_user, account_id)
    with get_session(DB_ENGINE) as db_session:
        return query_systems_under_test_by_account(
            account_id=account_id,
            token=current_user,
            session=db_session,
            engine=DB_ENGINE,
        )


@sut_api_router.get("/{sut_id}", response_model=SystemUnderTestModel)
async def get_system_by_id(
    sut_id: str,
    current_user: TokenPayload = Depends(require_member),
):
    """Get a specific system under test by ID."""
    with get_session(DB_ENGINE) as db_session:
        return query_system_under_test_by_id(
            sut_id=sut_id, session=db_session, engine=DB_ENGINE
        )


@sut_api_router.post("/", response_model=SystemUnderTestModel)
async def create_system(
    system: SystemUnderTestModel,
    current_user: TokenPayload = Depends(require_admin),
):
    """Create a new system under test."""
    sut_id = insert_system_under_test(system_under_test=system, engine=DB_ENGINE)
    with get_session(DB_ENGINE) as db_session:
        return query_system_under_test_by_id(
            sut_id=sut_id, session=db_session, engine=DB_ENGINE
        )


@sut_api_router.put("/{sut_id}", response_model=SystemUnderTestModel)
async def update_system(
    sut_id: str,
    system: SystemUnderTestModel,
    current_user: TokenPayload = Depends(require_admin),
):
    """Update a system under test."""
    update_system_under_test_by_id(
        sut_id=sut_id, system_under_test=system, engine=DB_ENGINE
    )
    with get_session(DB_ENGINE) as db_session:
        return query_system_under_test_by_id(
            sut_id=sut_id, session=db_session, engine=DB_ENGINE
        )


@sut_api_router.delete("/{sut_id}")
async def delete_system(
    sut_id: str,
    current_user: TokenPayload = Depends(require_admin),
):
    """Delete a system under test."""
    drop_system_under_test_by_id(sut_id=sut_id, engine=DB_ENGINE)
    return {"status": "success", "message": f"System {sut_id} deleted"}
