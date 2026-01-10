"""
Entity tag model with polymorphic queries and row-level security context manager.

This module provides:
1. AccountRLSContext: Thread-safe context manager for PostgreSQL RLS session variables
2. EntityTagModel: Pydantic model with validation for polymorphic tagging
3. CRUD operations for entity tags with multi-tenant isolation
4. Polymorphic query helpers for tag-based entity filtering
"""

import logging
import threading
import traceback
from datetime import datetime, timezone
from typing import Dict, List, Optional

from pydantic import BaseModel, field_validator
from sqlalchemy import and_, func, select
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from common.config import should_validate_write
from common.service_connections.db_service.database.engine import (
    get_database_session as session,
)
from common.service_connections.db_service.database.tables.entity_tag import (
    EntityTagTable,
)

logger = logging.getLogger(__name__)


# Thread-local storage for RLS context stack
_thread_local = threading.local()


class AccountRLSContext:
    """Thread-safe context manager for PostgreSQL row-level security session variables.

    Sets the app.current_account_id session variable for PostgreSQL RLS policies.
    Supports nested contexts with maximum stack depth of 10 to prevent infinite recursion.
    Includes verification mode to detect session variable reset failures.

    Usage:
        with AccountRLSContext(session, account_id="uuid-here"):
            # All queries in this block filtered by account_id via RLS policy
            tags = query_all_entity_tags(session, engine)

        # Nested contexts (up to 10 levels):
        with AccountRLSContext(session, account_id="account-1"):
            with AccountRLSContext(session, account_id="account-2"):
                # Inner context uses account-2
                pass
            # Restored to account-1

    Thread Safety:
        - Uses threading.local() for isolated context stacks per thread
        - Safe for concurrent test execution with pytest-xdist

    Stack Limit Protection:
        - Maximum depth of 10 contexts to prevent accidental infinite loops
        - Logs full stack trace showing all account_ids when limit reached
        - Raises RuntimeError on exceeding limit

    Verification Mode:
        - verify_reset=True: Queries session variable after __exit__ to confirm reset
        - Logs warning if session variable doesn't match expected value
        - Useful for debugging RLS policy issues in tests
    """

    MAX_STACK_DEPTH = 10

    def __init__(self, session: Session, account_id: str, verify_reset: bool = False):
        """Initialize RLS context manager.

        Args:
            session: SQLAlchemy session to set variable on
            account_id: UUID string to set as current account
            verify_reset: If True, verify session variable reset after __exit__
        """
        self.session = session
        self.account_id = account_id
        self.verify_reset = verify_reset
        self.previous_account_id: Optional[str] = None

    def __enter__(self):
        """Push account_id onto context stack and set session variable."""
        # Initialize thread-local stack if not exists
        if not hasattr(_thread_local, "rls_stack"):
            _thread_local.rls_stack = []

        # Check stack depth limit
        if len(_thread_local.rls_stack) >= self.MAX_STACK_DEPTH:
            # Log full stack trace of account IDs for debugging
            stack_info = "\n".join(
                [
                    f"  [{i}] account_id={acc_id}"
                    for i, acc_id in enumerate(_thread_local.rls_stack)
                ]
            )
            logger.error(
                f"AccountRLSContext stack limit reached ({self.MAX_STACK_DEPTH})\n"
                f"Current stack:\n{stack_info}\n"
                f"Attempted to push: account_id={self.account_id}\n"
                f"Traceback:\n{''.join(traceback.format_stack())}"
            )
            raise RuntimeError(
                f"Maximum RLS context depth ({self.MAX_STACK_DEPTH}) exceeded. "
                "Check for infinite recursion or excessive context nesting."
            )

        # Save previous account_id if stack has entries
        if _thread_local.rls_stack:
            self.previous_account_id = _thread_local.rls_stack[-1]

        # Push new account_id onto stack
        _thread_local.rls_stack.append(self.account_id)

        # Set PostgreSQL session variable for RLS policy
        try:
            self.session.execute(
                func.set_config("app.current_account_id", self.account_id, False)
            )
            logger.debug(
                f"Set RLS account_id={self.account_id} "
                f"(stack depth: {len(_thread_local.rls_stack)})"
            )
        except SQLAlchemyError as e:
            # Rollback stack push on failure
            _thread_local.rls_stack.pop()
            logger.error(f"Failed to set RLS session variable: {e}")
            raise

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Pop account_id from stack and restore previous or reset."""
        # Pop current account_id from stack
        if hasattr(_thread_local, "rls_stack") and _thread_local.rls_stack:
            _thread_local.rls_stack.pop()

        # Restore previous account_id or reset to empty
        try:
            if self.previous_account_id is not None:
                # Restore previous context
                self.session.execute(
                    func.set_config(
                        "app.current_account_id", self.previous_account_id, False
                    )
                )
                expected_value = self.previous_account_id
                logger.debug(
                    f"Restored RLS account_id={self.previous_account_id} "
                    f"(stack depth: {len(_thread_local.rls_stack)})"
                )
            else:
                # Reset to empty (no active context)
                self.session.execute(func.set_config("app.current_account_id", "", False))
                expected_value = ""
                logger.debug("Reset RLS account_id (stack empty)")

            # Verify reset if requested
            if self.verify_reset:
                self._verify_reset(expected_value)

        except SQLAlchemyError as e:
            logger.error(f"Failed to restore/reset RLS session variable: {e}")
            # Don't raise to avoid masking original exception

    def _verify_reset(self, expected_value: str):
        """Verify session variable was reset correctly.

        Args:
            expected_value: Expected value of app.current_account_id
        """
        try:
            result = self.session.execute(
                select(func.current_setting("app.current_account_id", True))
            ).scalar()

            actual_value = result if result else ""

            if actual_value != expected_value:
                logger.warning(
                    f"RLS session variable mismatch after reset. "
                    f"Expected: '{expected_value}', Actual: '{actual_value}'"
                )
        except SQLAlchemyError as e:
            logger.warning(f"Failed to verify RLS reset: {e}")


class EntityTagModel(BaseModel):
    """Pydantic model for entity tag validation and serialization.

    Validates polymorphic entity references and tag naming conventions.
    """

    tag_id: Optional[str] = None
    entity_type: str
    entity_id: str
    tag_name: str
    tag_category: str
    tag_value: Optional[str] = None
    account_id: str
    created_by_user_id: str
    is_active: bool = True
    deactivated_at: Optional[datetime] = None
    deactivated_by_user_id: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @field_validator("entity_type")
    def validate_entity_type(cls, v: str) -> str:
        """Validate entity_type against known entity types."""
        if not should_validate_write():
            return v

        # Known entity types (expand as needed)
        valid_types = {
            "suite",
            "test_case",
            "plan",
            "action_chain",
            "ui_action",
            "api_action",
            "db_action",
            "file_action",
            "system_under_test",
            "environment",
        }

        if v not in valid_types:
            raise ValueError(
                f"Invalid entity_type '{v}'. Must be one of: {', '.join(sorted(valid_types))}"
            )

        return v

    @field_validator("tag_name")
    def validate_tag_name(cls, v: str) -> str:
        """Validate tag_name length and format."""
        if not should_validate_write():
            return v

        if len(v) > 128:
            raise ValueError(f"tag_name exceeds 128 characters: {len(v)}")

        if not v.strip():
            raise ValueError("tag_name cannot be empty or whitespace")

        return v

    @field_validator("tag_category")
    def validate_tag_category(cls, v: str) -> str:
        """Validate tag_category length."""
        if not should_validate_write():
            return v

        if len(v) > 64:
            raise ValueError(f"tag_category exceeds 64 characters: {len(v)}")

        return v

    @field_validator("tag_value")
    def validate_tag_value(cls, v: Optional[str]) -> Optional[str]:
        """Validate tag_value length if provided."""
        if not should_validate_write():
            return v

        if v is not None and len(v) > 255:
            raise ValueError(f"tag_value exceeds 255 characters: {len(v)}")

        return v


# ============================================================================
# CRUD Operations
# ============================================================================


def insert_entity_tag(model: EntityTagModel, engine: Engine) -> str:
    """Insert new entity tag record.

    Args:
        model: EntityTagModel with tag data
        engine: Database engine

    Returns:
        tag_id of inserted record

    Raises:
        ValueError: If validation fails
        SQLAlchemyError: If database operation fails
    """
    tag_dict = model.model_dump(exclude_unset=True)

    with session(engine) as db_session:
        new_tag = EntityTagTable(**tag_dict)
        db_session.add(new_tag)
        db_session.commit()
        return new_tag.tag_id


def query_entity_tag_by_id(
    tag_id: str, db_session: Session, engine: Engine
) -> Optional[EntityTagModel]:
    """Query entity tag by tag_id.

    Args:
        tag_id: Tag ID to query
        db_session: Active database session
        engine: Database engine

    Returns:
        EntityTagModel if found, None otherwise
    """
    tag = db_session.get(EntityTagTable, tag_id)
    if tag:
        return EntityTagModel(**tag.__dict__)
    return None


def query_all_entity_tags(db_session: Session, engine: Engine) -> List[EntityTagModel]:
    """Query all entity tags (filtered by RLS if active).

    Args:
        db_session: Active database session
        engine: Database engine

    Returns:
        List of EntityTagModel instances
    """
    tags = db_session.query(EntityTagTable).all()
    return [EntityTagModel(**tag.__dict__) for tag in tags]


def update_entity_tag(tag_id: str, updates: EntityTagModel, engine: Engine) -> bool:
    """Update entity tag record.

    Args:
        tag_id: Tag ID to update
        updates: EntityTagModel with updated fields
        engine: Database engine

    Returns:
        True if updated, False if not found

    Raises:
        ValueError: If validation fails
        SQLAlchemyError: If database operation fails
    """
    update_dict = updates.model_dump(exclude_unset=True)

    with session(engine) as db_session:
        tag = db_session.get(EntityTagTable, tag_id)
        if not tag:
            return False

        for key, value in update_dict.items():
            setattr(tag, key, value)

        db_session.commit()
        return True


def drop_entity_tag(tag_id: str, engine: Engine, db_session: Session) -> bool:
    """Permanently delete entity tag record.

    Args:
        tag_id: Tag ID to delete
        engine: Database engine

    Returns:
        True if deleted, False if not found
    """
    with session(engine) as db_session:
        tag = db_session.get(EntityTagTable, tag_id)
        if not tag:
            return False

        db_session.delete(tag)
        db_session.commit()
        return True


def deactivate_entity_tag(
    tag_id: str, deactivated_by_user_id: str, engine: Engine
) -> bool:
    """Soft delete entity tag by setting is_active=False.

    Args:
        tag_id: Tag ID to deactivate
        deactivated_by_user_id: User performing deactivation
        engine: Database engine

    Returns:
        True if deactivated, False if not found
    """
    with session(engine) as db_session:
        tag = db_session.get(EntityTagTable, tag_id)
        if not tag:
            return False

        tag.is_active = False
        tag.deactivated_at = datetime.now(timezone.utc)
        tag.deactivated_by_user_id = deactivated_by_user_id

        db_session.commit()
        return True


def reactivate_entity_tag(tag_id: str, engine: Engine, db_session: Session) -> bool:
    """Reactivate soft-deleted entity tag.

    Args:
        tag_id: Tag ID to reactivate
        engine: Database engine

    Returns:
        True if reactivated, False if not found
    """
    with session(engine) as db_session:
        tag = db_session.get(EntityTagTable, tag_id)
        if not tag:
            return False

        tag.is_active = True
        tag.deactivated_at = None
        tag.deactivated_by_user_id = None

        db_session.commit()
        return True


# ============================================================================
# Polymorphic Query Helpers
# ============================================================================


def query_tags_for_entity(
    entity_type: str,
    entity_id: str,
    account_id: str,
    db_session: Session,
    engine: Engine,
    active_only: bool = True,
) -> List[EntityTagModel]:
    """Query all tags for a specific entity.

    Args:
        entity_type: Type of entity (suite, test_case, etc.)
        entity_id: Entity's primary key
        account_id: Account ID for multi-tenant filtering
        session: Active database session
        engine: Database engine
        active_only: If True, only return active tags

    Returns:
        List of EntityTagModel instances
    """
    with session(engine) as db_session:
        query = db_session.query(EntityTagTable).filter(
            and_(
                EntityTagTable.entity_type == entity_type,
                EntityTagTable.entity_id == entity_id,
                EntityTagTable.account_id == account_id,
            )
        )

        if active_only:
            query = query.filter(EntityTagTable.is_active == True)

        tags = query.all()
        return [EntityTagModel(**tag.__dict__) for tag in tags]


def query_entities_by_tag(
    tag_name: str,
    entity_type: str,
    account_id: str,
    db_session: Session,
    engine: Engine,
    active_only: bool = True,
) -> List[str]:
    """Query entity IDs that have a specific tag.

    Args:
        tag_name: Tag name to search for
        entity_type: Type of entity to filter (suite, test_case, etc.)
        account_id: Account ID for multi-tenant filtering
        session: Active database session
        engine: Database engine
        active_only: If True, only return tags on active entities

    Returns:
        List of entity_id strings
    """
    query = db_session.query(EntityTagTable.entity_id).filter(
        and_(
            EntityTagTable.tag_name == tag_name,
            EntityTagTable.entity_type == entity_type,
            EntityTagTable.account_id == account_id,
        )
    )

    if active_only:
        query = query.filter(EntityTagTable.is_active == True)

    results = query.all()
    return [row[0] for row in results]


def query_tags_by_category(
    tag_category: str,
    account_id: str,
    db_session: Session,
    engine: Engine,
    entity_type: Optional[str] = None,
    active_only: bool = True,
) -> List[EntityTagModel]:
    """Query all tags in a specific category.

    Args:
        tag_category: Tag category to filter by
        account_id: Account ID for multi-tenant filtering
        session: Active database session
        engine: Database engine
        entity_type: Optional entity type filter
        active_only: If True, only return active tags

    Returns:
        List of EntityTagModel instances
    """
    filters = [
        EntityTagTable.tag_category == tag_category,
        EntityTagTable.account_id == account_id,
    ]

    if entity_type:
        filters.append(EntityTagTable.entity_type == entity_type)

    if active_only:
        filters.append(EntityTagTable.is_active == True)

    query = db_session.query(EntityTagTable).filter(and_(*filters))

    tags = query.all()
    return [EntityTagModel(**tag.__dict__) for tag in tags]


def query_unique_tag_names(
    account_id: str,
    db_session: Session,
    engine: Engine,
    entity_type: Optional[str] = None,
) -> List[str]:
    """Query unique tag names for autocomplete/dropdown.

    Args:
        account_id: Account ID for multi-tenant filtering
        session: Active database session
        engine: Database engine
        entity_type: Optional entity type filter

    Returns:
        Sorted list of unique tag names
    """
    filters = [EntityTagTable.account_id == account_id]

    if entity_type:
        filters.append(EntityTagTable.entity_type == entity_type)

    query = db_session.query(EntityTagTable.tag_name).filter(and_(*filters)).distinct()

    results = query.all()
    return sorted([row[0] for row in results])


# ============================================================================
# Bulk Operations
# ============================================================================


def add_tags_to_entity(
    entity_type: str,
    entity_id: str,
    tag_names: List[str],
    tag_category: str,
    account_id: str,
    created_by_user_id: str,
    engine: Engine,
    tag_values: Optional[Dict[str, str]] = None,
) -> List[str]:
    """Add multiple tags to an entity in a single transaction.

    Args:
        entity_type: Type of entity
        entity_id: Entity's primary key
        tag_names: List of tag names to add
        tag_category: Category for all tags
        account_id: Account ID
        created_by_user_id: User creating tags
        engine: Database engine
        session: Active database session
        tag_values: Optional dict mapping tag_name -> tag_value

    Returns:
        List of created tag_ids

    Raises:
        ValueError: If validation fails
        SQLAlchemyError: If database operation fails
    """
    tag_ids = []
    tag_values = tag_values or {}

    with session(engine) as db_session:
        for tag_name in tag_names:
            tag_model = EntityTagModel(
                entity_type=entity_type,
                entity_id=entity_id,
                tag_name=tag_name,
                tag_category=tag_category,
                tag_value=tag_values.get(tag_name),
                account_id=account_id,
                created_by_user_id=created_by_user_id,
            )

            new_tag = EntityTagTable(**tag_model.model_dump(exclude_unset=True))
            db_session.add(new_tag)
            tag_ids.append(new_tag.tag_id)

        db_session.commit()
        return tag_ids


def replace_entity_tags(
    entity_type: str,
    entity_id: str,
    new_tag_names: List[str],
    tag_category: str,
    account_id: str,
    created_by_user_id: str,
    deactivated_by_user_id: str,
    engine: Engine,
    tag_values: Optional[Dict[str, str]] = None,
) -> Dict[str, List[str]]:
    """Replace all tags for an entity (deactivate old, add new).

    Args:
        entity_type: Type of entity
        entity_id: Entity's primary key
        new_tag_names: List of new tag names
        tag_category: Category for tags
        account_id: Account ID
        created_by_user_id: User creating new tags
        deactivated_by_user_id: User deactivating old tags
        engine: Database engine
        tag_values: Optional dict mapping tag_name -> tag_value

    Returns:
        Dict with 'deactivated' and 'created' tag_id lists

    Raises:
        ValueError: If validation fails
        SQLAlchemyError: If database operation fails
    """
    result = {"deactivated": [], "created": []}
    tag_values = tag_values or {}

    with session(engine) as db_session:
        # Deactivate existing tags
        existing_tags = (
            db_session.query(EntityTagTable)
            .filter(
                and_(
                    EntityTagTable.entity_type == entity_type,
                    EntityTagTable.entity_id == entity_id,
                    EntityTagTable.account_id == account_id,
                    EntityTagTable.tag_category == tag_category,
                    EntityTagTable.is_active == True,
                )
            )
            .all()
        )

        for tag in existing_tags:
            tag.is_active = False
            tag.deactivated_at = datetime.now(timezone.utc)
            tag.deactivated_by_user_id = deactivated_by_user_id
            result["deactivated"].append(tag.tag_id)

        # Create new tags
        for tag_name in new_tag_names:
            tag_model = EntityTagModel(
                entity_type=entity_type,
                entity_id=entity_id,
                tag_name=tag_name,
                tag_category=tag_category,
                tag_value=tag_values.get(tag_name),
                account_id=account_id,
                created_by_user_id=created_by_user_id,
            )

            new_tag = EntityTagTable(**tag_model.model_dump(exclude_unset=True))
            db_session.add(new_tag)
            result["created"].append(new_tag.tag_id)

        db_session.commit()
        return result
