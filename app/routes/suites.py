"""
Suite routes for managing test suite organization.
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

from common.service_connections.db_service.models.suite_model import (
    SuiteModel,
    insert_suite,
    query_suite_by_id,
    query_all_suites,
    query_suites_by_account,
    update_suite_by_id,
    drop_suite_by_id,
)


suite_api_router = APIRouter(prefix="/api/suites", tags=["suites-api"])


@suite_api_router.get("/", response_model=List[SuiteModel])
async def get_all_suites(
    current_user: TokenPayload = Depends(require_member),
):
    """Get all test suites."""
    with get_session(DB_ENGINE) as db_session:
        return query_all_suites(session=db_session, engine=DB_ENGINE)


@suite_api_router.get("/account/{account_id}", response_model=List[SuiteModel])
async def get_suites_by_account(
    account_id: str,
    current_user: TokenPayload = Depends(require_member),
):
    """Get all test suites for a specific account."""
    validate_account_access(current_user, account_id)
    with get_session(DB_ENGINE) as db_session:
        return query_suites_by_account(
            account_id=account_id,
            token=current_user,
            session=db_session,
            engine=DB_ENGINE,
        )


@suite_api_router.get("/{suite_id}", response_model=SuiteModel)
async def get_suite_by_id(
    suite_id: str,
    current_user: TokenPayload = Depends(require_member),
):
    """Get a specific test suite by ID."""
    with get_session(DB_ENGINE) as db_session:
        return query_suite_by_id(suite_id=suite_id, session=db_session, engine=DB_ENGINE)


@suite_api_router.post("/", response_model=SuiteModel)
async def create_suite(
    suite: SuiteModel,
    current_user: TokenPayload = Depends(require_admin),
):
    """Create a new test suite."""
    suite_id = insert_suite(suite=suite, engine=DB_ENGINE)
    with get_session(DB_ENGINE) as db_session:
        return query_suite_by_id(suite_id=suite_id, session=db_session, engine=DB_ENGINE)


@suite_api_router.put("/{suite_id}", response_model=SuiteModel)
async def update_suite(
    suite_id: str,
    suite: SuiteModel,
    current_user: TokenPayload = Depends(require_admin),
):
    """Update a test suite."""
    update_suite_by_id(suite_id=suite_id, suite=suite, engine=DB_ENGINE)
    with get_session(DB_ENGINE) as db_session:
        return query_suite_by_id(suite_id=suite_id, session=db_session, engine=DB_ENGINE)


@suite_api_router.delete("/{suite_id}")
async def delete_suite(
    suite_id: str,
    current_user: TokenPayload = Depends(require_admin),
):
    """Delete a test suite."""
    drop_suite_by_id(suite_id=suite_id, engine=DB_ENGINE)
    return {"status": "success", "message": f"Suite {suite_id} deleted"}
