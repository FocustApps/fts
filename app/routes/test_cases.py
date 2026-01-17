"""
Test Case routes for managing individual test definitions.
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

from common.service_connections.db_service.models.test_case_model import (
    TestCaseModel,
    insert_test_case,
    query_test_case_by_id,
    query_all_test_cases,
    query_test_cases_by_account,
    query_test_cases_by_sut,
    query_test_cases_by_type,
    update_test_case_by_id,
    drop_test_case_by_id,
)


test_case_api_router = APIRouter(prefix="/api/test-cases", tags=["test-cases-api"])


@test_case_api_router.get("/", response_model=List[TestCaseModel])
async def get_all_test_cases(
    current_user: TokenPayload = Depends(require_member),
):
    """Get all test cases."""
    with get_session(DB_ENGINE) as db_session:
        return query_all_test_cases(session=db_session, engine=DB_ENGINE)


@test_case_api_router.get("/account/{account_id}", response_model=List[TestCaseModel])
async def get_test_cases_by_account(
    account_id: str,
    current_user: TokenPayload = Depends(require_member),
):
    """Get all test cases for a specific account."""
    validate_account_access(current_user, account_id)
    with get_session(DB_ENGINE) as db_session:
        return query_test_cases_by_account(
            account_id=account_id,
            token=current_user,
            session=db_session,
            engine=DB_ENGINE,
        )


@test_case_api_router.get("/sut/{sut_id}", response_model=List[TestCaseModel])
async def get_test_cases_by_sut(
    sut_id: str,
    current_user: TokenPayload = Depends(require_member),
):
    """Get all test cases for a specific system under test."""
    with get_session(DB_ENGINE) as db_session:
        return query_test_cases_by_sut(
            sut_id=sut_id, session=db_session, engine=DB_ENGINE
        )


@test_case_api_router.get("/type/{test_type}", response_model=List[TestCaseModel])
async def get_test_cases_by_type(
    test_type: str,
    current_user: TokenPayload = Depends(require_member),
):
    """Get all test cases of a specific type."""
    with get_session(DB_ENGINE) as db_session:
        return query_test_cases_by_type(
            test_type=test_type, session=db_session, engine=DB_ENGINE
        )


@test_case_api_router.get("/{test_case_id}", response_model=TestCaseModel)
async def get_test_case_by_id(
    test_case_id: str,
    current_user: TokenPayload = Depends(require_member),
):
    """Get a specific test case by ID."""
    with get_session(DB_ENGINE) as db_session:
        return query_test_case_by_id(
            test_case_id=test_case_id, session=db_session, engine=DB_ENGINE
        )


@test_case_api_router.post("/", response_model=TestCaseModel)
async def create_test_case(
    test_case: TestCaseModel,
    current_user: TokenPayload = Depends(require_admin),
):
    """Create a new test case."""
    test_case_id = insert_test_case(test_case=test_case, engine=DB_ENGINE)
    with get_session(DB_ENGINE) as db_session:
        return query_test_case_by_id(
            test_case_id=test_case_id, session=db_session, engine=DB_ENGINE
        )


@test_case_api_router.put("/{test_case_id}", response_model=TestCaseModel)
async def update_test_case(
    test_case_id: str,
    test_case: TestCaseModel,
    current_user: TokenPayload = Depends(require_admin),
):
    """Update a test case."""
    update_test_case_by_id(
        test_case_id=test_case_id, test_case=test_case, engine=DB_ENGINE
    )
    with get_session(DB_ENGINE) as db_session:
        return query_test_case_by_id(
            test_case_id=test_case_id, session=db_session, engine=DB_ENGINE
        )


@test_case_api_router.delete("/{test_case_id}")
async def delete_test_case(
    test_case_id: str,
    current_user: TokenPayload = Depends(require_admin),
):
    """Delete a test case."""
    drop_test_case_by_id(test_case_id=test_case_id, engine=DB_ENGINE)
    return {"status": "success", "message": f"Test case {test_case_id} deleted"}
