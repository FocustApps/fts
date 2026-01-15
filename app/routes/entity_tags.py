"""
Entity Tag routes for polymorphic tagging and categorization.
"""

from fastapi import APIRouter, Depends, Query
from typing import List, Optional

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

from common.service_connections.db_service.models.entity_tag_model import (
    EntityTagModel,
    insert_entity_tag,
    query_entity_tag_by_id,
    query_all_entity_tags,
    query_tags_for_entity,
    query_entities_by_tag,
    query_tags_by_category,
    query_unique_tag_names,
    add_tags_to_entity,
    replace_entity_tags,
    update_entity_tag,
    deactivate_entity_tag,
    reactivate_entity_tag,
    drop_entity_tag,
)


tag_api_router = APIRouter(prefix="/api/tags", tags=["tags-api"])


@tag_api_router.get("/", response_model=List[EntityTagModel])
async def get_all_tags(
    current_user: TokenPayload = Depends(require_member),
):
    """Get all entity tags."""
    with get_session(DB_ENGINE) as db_session:
        return query_all_entity_tags(session=db_session, engine=DB_ENGINE)


@tag_api_router.get(
    "/entity/{entity_type}/{entity_id}", response_model=List[EntityTagModel]
)
async def get_tags_for_entity(
    entity_type: str,
    entity_id: str,
    account_id: str = Query(...),
    current_user: TokenPayload = Depends(require_member),
):
    """Get all tags for a specific entity."""
    validate_account_access(current_user, account_id)
    with get_session(DB_ENGINE) as db_session:
        return query_tags_for_entity(
            entity_type=entity_type,
            entity_id=entity_id,
            account_id=account_id,
            token=current_user,
            session=db_session,
            engine=DB_ENGINE,
        )


@tag_api_router.get("/search/{tag_name}", response_model=List[str])
async def get_entities_by_tag(
    tag_name: str,
    entity_type: str = Query(...),
    account_id: str = Query(...),
    current_user: TokenPayload = Depends(require_member),
):
    """Get all entity IDs with a specific tag."""
    validate_account_access(current_user, account_id)
    with get_session(DB_ENGINE) as db_session:
        return query_entities_by_tag(
            tag_name=tag_name,
            entity_type=entity_type,
            account_id=account_id,
            token=current_user,
            session=db_session,
            engine=DB_ENGINE,
        )


@tag_api_router.get("/category/{category}", response_model=List[EntityTagModel])
async def get_tags_by_category(
    category: str,
    account_id: str = Query(...),
    current_user: TokenPayload = Depends(require_member),
):
    """Get all tags in a specific category."""
    validate_account_access(current_user, account_id)
    with get_session(DB_ENGINE) as db_session:
        return query_tags_by_category(
            category=category,
            account_id=account_id,
            token=current_user,
            session=db_session,
            engine=DB_ENGINE,
        )


@tag_api_router.get("/names/unique", response_model=List[str])
async def get_unique_tag_names(
    account_id: str = Query(...),
    category: Optional[str] = Query(None),
    current_user: TokenPayload = Depends(require_member),
):
    """Get unique tag names for autocomplete (optionally filtered by category)."""
    validate_account_access(current_user, account_id)
    with get_session(DB_ENGINE) as db_session:
        return query_unique_tag_names(
            account_id=account_id,
            token=current_user,
            category=category,
            session=db_session,
            engine=DB_ENGINE,
        )


@tag_api_router.get("/{tag_id}", response_model=EntityTagModel)
async def get_tag_by_id(
    tag_id: str,
    current_user: TokenPayload = Depends(require_member),
):
    """Get a specific entity tag by ID."""
    with get_session(DB_ENGINE) as db_session:
        return query_entity_tag_by_id(tag_id=tag_id, session=db_session, engine=DB_ENGINE)


@tag_api_router.post("/", response_model=EntityTagModel)
async def create_tag(
    tag: EntityTagModel,
    current_user: TokenPayload = Depends(require_admin),
):
    """Create a new entity tag."""
    tag_id = insert_entity_tag(tag=tag, engine=DB_ENGINE)
    with get_session(DB_ENGINE) as db_session:
        return query_entity_tag_by_id(tag_id=tag_id, session=db_session, engine=DB_ENGINE)


@tag_api_router.post("/bulk/add")
async def add_tags_bulk(
    entity_type: str,
    entity_id: str,
    tag_names: List[str],
    tag_category: str,
    account_id: str,
    current_user: TokenPayload = Depends(require_admin),
):
    """Add multiple tags to an entity."""
    validate_account_access(current_user, account_id)
    tag_ids = add_tags_to_entity(
        entity_type=entity_type,
        entity_id=entity_id,
        tag_names=tag_names,
        tag_category=tag_category,
        account_id=account_id,
        created_by_user_id=current_user.user_id,
        engine=DB_ENGINE,
    )
    return {"status": "success", "tag_ids": tag_ids, "count": len(tag_ids)}


@tag_api_router.post("/bulk/replace")
async def replace_tags_bulk(
    entity_type: str,
    entity_id: str,
    new_tag_names: List[str],
    tag_category: str,
    account_id: str,
    current_user: TokenPayload = Depends(require_admin),
):
    """Replace all tags on an entity with new tags."""
    validate_account_access(current_user, account_id)
    result = replace_entity_tags(
        entity_type=entity_type,
        entity_id=entity_id,
        new_tag_names=new_tag_names,
        tag_category=tag_category,
        account_id=account_id,
        created_by_user_id=current_user.user_id,
        deactivated_by_user_id=current_user.user_id,
        engine=DB_ENGINE,
    )
    return {
        "status": "success",
        "deactivated_count": result["deactivated_count"],
        "new_tag_ids": result["new_tag_ids"],
    }


@tag_api_router.put("/{tag_id}", response_model=EntityTagModel)
async def update_tag(
    tag_id: str,
    tag: EntityTagModel,
    current_user: TokenPayload = Depends(require_admin),
):
    """Update an entity tag."""
    update_entity_tag(tag_id=tag_id, tag=tag, engine=DB_ENGINE)
    with get_session(DB_ENGINE) as db_session:
        return query_entity_tag_by_id(tag_id=tag_id, session=db_session, engine=DB_ENGINE)


@tag_api_router.patch("/{tag_id}/deactivate")
async def deactivate_tag(
    tag_id: str,
    current_user: TokenPayload = Depends(require_admin),
):
    """Deactivate an entity tag (soft delete)."""
    deactivate_entity_tag(
        tag_id=tag_id,
        deactivated_by_user_id=current_user.user_id,
        engine=DB_ENGINE,
    )
    return {"status": "success", "message": f"Tag {tag_id} deactivated"}


@tag_api_router.patch("/{tag_id}/reactivate")
async def reactivate_tag(
    tag_id: str,
    current_user: TokenPayload = Depends(require_admin),
):
    """Reactivate a previously deactivated tag."""
    reactivate_entity_tag(tag_id=tag_id, engine=DB_ENGINE)
    return {"status": "success", "message": f"Tag {tag_id} reactivated"}


@tag_api_router.delete("/{tag_id}")
async def delete_tag(
    tag_id: str,
    current_user: TokenPayload = Depends(require_admin),
):
    """Hard delete an entity tag."""
    drop_entity_tag(tag_id=tag_id, engine=DB_ENGINE)
    return {"status": "success", "message": f"Tag {tag_id} deleted"}
