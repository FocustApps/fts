"""
Action Chain model for managing sequential action execution workflows.

This module provides the ActionChainModel Pydantic model and database operations
for managing action chain records in the Fenrir Testing System, including JSONB
action_steps manipulation and validation with caching.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
import logging
import time

from pydantic import BaseModel, field_validator
from sqlalchemy import Engine
from sqlalchemy.orm import Session, attributes

from common.service_connections.db_service.database import ActionChainTable
from common.service_connections.db_service.database.engine import (
    get_database_session as session,
)
from common.config import should_validate_write


# TODO: Add cache warming strategy at app startup for frequently accessed action references


class ActionStepModel(BaseModel):
    """
    Pydantic model for individual action step validation.

    Represents a single step in an action chain with dependencies and execution metadata.

    Fields:
    - step_name: str - Unique step identifier within chain
    - action_type: str - Type of action (api_action, ui_action, database_action, etc.)
    - action_id: str - UUID reference to actual action in respective table
    - depends_on: List[str] - List of step names this step depends on
    - parallel: bool - Whether this step can run in parallel with others
    """

    step_name: str
    action_type: str
    action_id: str
    depends_on: List[str] = []
    parallel: bool = False

    @field_validator("step_name")
    @classmethod
    def validate_step_name(cls, v: str) -> str:
        """Validate step_name is not empty."""
        if not should_validate_write():
            return v
        if not v or not v.strip():
            raise ValueError("step_name cannot be empty")
        return v.strip()

    @field_validator("action_type")
    @classmethod
    def validate_action_type(cls, v: str) -> str:
        """Validate action_type against known types."""
        if not should_validate_write():
            return v
        valid_types = [
            "api_action",
            "ui_action",
            "database_action",
            "infrastructure_action",
            "repository_action",
        ]
        if v not in valid_types:
            raise ValueError(
                f"Invalid action_type: {v}. Must be one of: {', '.join(valid_types)}"
            )
        return v


class ActionReferenceCache:
    """
    Cache for action existence validation with 10-minute TTL.

    Stores (action_type, action_id) -> exists mapping to avoid repeated queries
    during action chain validation.
    """

    _cache: Dict[tuple, tuple] = {}  # (action_type, action_id) -> (exists, timestamp)
    _ttl_seconds = 600  # 10 minutes

    @classmethod
    def check_exists(cls, action_type: str, action_id: str, db_session: Session) -> bool:
        """
        Check if action exists, using cache if available.

        Returns cached result if within TTL, otherwise queries database and updates cache.
        """
        cache_key = (action_type, action_id)
        current_time = time.time()

        # Check cache
        if cache_key in cls._cache:
            exists, cached_time = cls._cache[cache_key]
            if current_time - cached_time < cls._ttl_seconds:
                return exists

        # Query database based on action_type
        exists = cls._query_action_exists(action_type, action_id, session)

        # Update cache
        cls._cache[cache_key] = (exists, current_time)
        return exists

    @classmethod
    def _query_action_exists(
        cls, action_type: str, action_id: str, db_session: Session
    ) -> bool:
        """Query specific action table to check if action exists."""
        # Import action tables dynamically to avoid circular imports
        from common.service_connections.db_service.database.tables.action_tables.user_interface_action.fenrir_actions import (
            FenrirActionsTable,
        )

        table_map = {
            "ui_action": FenrirActionsTable,
            # Add other action types when tables are implemented
            # "api_action": APIActionTable,
            # "database_action": DatabaseActionTable,
            # "infrastructure_action": InfrastructureActionTable,
            # "repository_action": RepositoryActionTable,
        }

        table_class = table_map.get(action_type)
        if not table_class:
            logging.warning(f"Unknown action_type: {action_type}, skipping validation")
            return True  # Assume valid if table not implemented yet

        # Query the appropriate table
        result = (
            session.query(table_class)
            .filter_by(**{f"{action_type}_id": action_id})
            .first()
        )

        return result is not None

    @classmethod
    def clear(cls):
        """Clear the entire cache. Useful for testing or manual cache invalidation."""
        cls._cache.clear()
        logging.info("Action reference cache cleared")


class ActionChainModel(BaseModel):
    """
    Pydantic model for Action Chain data validation and serialization.

    Defines sequences of actions to be executed in order for complex test workflows.

    Fields:
    - action_chain_id: str | None - UUID primary key (auto-generated)
    - chain_name: str - Unique chain name
    - description: str | None - Optional chain description
    - action_steps: List[ActionStepModel] - Ordered list of action steps (JSONB)
    - sut_id: str - System under test reference
    - account_id: str - Multi-tenant account ID
    - owner_user_id: str - Chain owner reference
    - is_active: bool - Soft delete flag
    - deactivated_at: datetime | None - Soft delete timestamp
    - deactivated_by_user_id: str | None - Who deactivated
    - created_at: datetime - Creation timestamp
    - updated_at: datetime | None - Last update timestamp
    """

    action_chain_id: Optional[str] = None
    chain_name: str
    description: Optional[str] = None
    action_steps: List[Dict[str, Any]] = []
    sut_id: str
    account_id: str
    owner_user_id: str
    is_active: bool = True
    deactivated_at: Optional[datetime] = None
    deactivated_by_user_id: Optional[str] = None
    created_at: datetime = datetime.now(tz=timezone.utc)
    updated_at: Optional[datetime] = None

    @field_validator("chain_name")
    @classmethod
    def validate_chain_name(cls, v: str) -> str:
        """Validate chain_name is not empty and within length limits."""
        if not should_validate_write():
            return v
        if not v or not v.strip():
            raise ValueError("chain_name cannot be empty")
        if len(v) > 255:
            raise ValueError("chain_name cannot exceed 255 characters")
        return v.strip()

    @field_validator("action_steps")
    @classmethod
    def validate_action_steps(cls, v: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Validate action_steps structure."""
        if not should_validate_write():
            return v

        for step in v:
            # Validate required fields
            required_fields = ["step_name", "action_type", "action_id"]
            for field in required_fields:
                if field not in step:
                    raise ValueError(f"Action step missing required field: {field}")

            # Validate step using ActionStepModel
            ActionStepModel(**step)

        return v


################ Action Chain CRUD Operations ################


def insert_action_chain(
    action_chain: ActionChainModel, db_session: Session, engine: Engine
) -> ActionChainModel:
    """Create a new action chain in the database."""
    if action_chain.action_chain_id:
        action_chain.action_chain_id = None
        logging.warning("Action Chain ID will only be set by the system")

    with session() as db_session:
        action_chain.created_at = datetime.now(timezone.utc)
        db_chain = ActionChainTable(**action_chain.model_dump())
        db_session.add(db_chain)
        db_session.commit()
        db_session.refresh(db_chain)
        return ActionChainModel(**db_chain.__dict__)


def query_action_chain_by_id(
    action_chain_id: str, db_session: Session, engine: Engine
) -> ActionChainModel:
    """Retrieve an action chain by ID."""
    db_chain = (
        db_session.query(ActionChainTable)
        .filter(ActionChainTable.action_chain_id == action_chain_id)
        .first()
    )
    if not db_chain:
        raise ValueError(f"Action Chain ID {action_chain_id} not found.")

    return ActionChainModel(**db_chain.__dict__)


def query_all_action_chains(
    db_session: Session, engine: Engine
) -> List[ActionChainModel]:
    """Retrieve all active action chains."""
    chains = (
        db_session.query(ActionChainTable)
        .filter(ActionChainTable.is_active == True)
        .all()
    )
    return [ActionChainModel(**chain.__dict__) for chain in chains]


def update_action_chain_by_id(
    action_chain_id: str,
    action_chain: ActionChainModel,
    db_session: Session,
    engine: Engine,
) -> ActionChainModel:
    """Update an existing action chain."""
    db_chain = db_session.get(ActionChainTable, action_chain_id)
    if not db_chain:
        raise ValueError(f"Action Chain ID {action_chain_id} not found.")

        action_chain.updated_at = datetime.now(timezone.utc)
        chain_data = action_chain.model_dump(exclude_unset=True)

        for key, value in chain_data.items():
            setattr(db_chain, key, value)

        db_session.commit()
        db_session.refresh(db_chain)
        return ActionChainModel(**db_chain.__dict__)


def drop_action_chain_by_id(
    action_chain_id: str, db_session: Session, engine: Engine
) -> int:
    """Hard delete an action chain (use with caution - prefer soft delete)."""
    db_chain = db_session.get(ActionChainTable, action_chain_id)
    if not db_chain:
        raise ValueError(f"Action Chain ID {action_chain_id} not found.")
    db_session.delete(db_chain)
    db_session.commit()
    logging.info(f"Action Chain ID {action_chain_id} deleted.")
    return 1


################ Multi-Tenant & Soft Delete Operations ################


def query_action_chains_by_account(
    account_id: str, db_session: Session, engine: Engine
) -> List[ActionChainModel]:
    """Query active action chains filtered by account_id."""
    chains = (
        db_session.query(ActionChainTable)
        .filter(ActionChainTable.account_id == account_id)
        .filter(ActionChainTable.is_active == True)
        .all()
    )
    return [ActionChainModel(**chain.__dict__) for chain in chains]


def query_action_chains_by_sut(
    sut_id: str, db_session: Session, engine: Engine
) -> List[ActionChainModel]:
    """Query active action chains for a specific system under test."""
    chains = (
        db_session.query(ActionChainTable)
        .filter(ActionChainTable.sut_id == sut_id)
        .filter(ActionChainTable.is_active == True)
        .all()
    )
    return [ActionChainModel(**chain.__dict__) for chain in chains]


def deactivate_action_chain_by_id(
    action_chain_id: str, deactivated_by_user_id: str, db_session: Session, engine: Engine
) -> ActionChainModel:
    """Soft delete an action chain."""
    db_chain = db_session.get(ActionChainTable, action_chain_id)
    if not db_chain:
        raise ValueError(f"Action Chain ID {action_chain_id} not found.")

        db_chain.is_active = False
        db_chain.deactivated_at = datetime.now(timezone.utc)
        db_chain.deactivated_by_user_id = deactivated_by_user_id

        db_session.commit()
        db_session.refresh(db_chain)
        return ActionChainModel(**db_chain.__dict__)


def reactivate_action_chain_by_id(
    action_chain_id: str, db_session: Session, engine: Engine
) -> ActionChainModel:
    """Reactivate a soft-deleted action chain."""
    db_chain = db_session.get(ActionChainTable, action_chain_id)
    if not db_chain:
        raise ValueError(f"Action Chain ID {action_chain_id} not found.")

        db_chain.is_active = True
        db_chain.deactivated_at = None
        db_chain.deactivated_by_user_id = None
        db_chain.updated_at = datetime.now(timezone.utc)

        db_session.commit()
        db_session.refresh(db_chain)
        return ActionChainModel(**db_chain.__dict__)


################ JSONB Action Steps Helper Methods ################


def add_step_to_chain(
    action_chain_id: str,
    step: ActionStepModel,
    engine: Engine,
    position: int = -1,
) -> ActionChainModel:
    """
    Add a new step to an action chain at specified position.

    Args:
        action_chain_id: ID of the chain to modify
        step: ActionStepModel to add
        position: Position to insert (-1 for append, 0 for beginning)
        session: Database session factory
        engine: Database engine

    Returns:
        Updated ActionChainModel
    """
    with session() as db_session:
        db_chain = db_session.get(ActionChainTable, action_chain_id)
        if not db_chain:
            raise ValueError(f"Action Chain ID {action_chain_id} not found.")

        steps = db_chain.action_steps or []
        step_dict = step.model_dump()

        if position == -1 or position >= len(steps):
            steps.append(step_dict)
        else:
            steps.insert(position, step_dict)

        db_chain.action_steps = steps
        attributes.flag_modified(db_chain, "action_steps")
        db_chain.updated_at = datetime.now(timezone.utc)

        db_session.commit()
        db_session.refresh(db_chain)
        return ActionChainModel(**db_chain.__dict__)


def remove_step_from_chain(
    action_chain_id: str, step_name: str, engine: Engine
) -> ActionChainModel:
    """
    Remove a step from an action chain by step_name.

    Args:
        action_chain_id: ID of the chain to modify
        step_name: Name of the step to remove
        session: Database session factory
        engine: Database engine

    Returns:
        Updated ActionChainModel
    """
    with session() as db_session:
        db_chain = db_session.get(ActionChainTable, action_chain_id)
        if not db_chain:
            raise ValueError(f"Action Chain ID {action_chain_id} not found.")

        steps = db_chain.action_steps or []
        updated_steps = [s for s in steps if s.get("step_name") != step_name]

        if len(updated_steps) == len(steps):
            raise ValueError(f"Step '{step_name}' not found in chain.")

        db_chain.action_steps = updated_steps
        db_chain.updated_at = datetime.now(timezone.utc)

        db_session.commit()
        db_session.refresh(db_chain)
        return ActionChainModel(**db_chain.__dict__)


def update_step_at_index(
    action_chain_id: str, index: int, partial_updates: Dict[str, Any], engine: Engine
) -> ActionChainModel:
    """
    Update a specific step at index using jsonb_set for efficient partial updates.

    Args:
        action_chain_id: ID of the chain to modify
        index: Index of the step to update (0-based)
        partial_updates: Dictionary of fields to update
        session: Database session factory
        engine: Database engine

    Returns:
        Updated ActionChainModel
    """
    with session() as db_session:
        db_chain = db_session.get(ActionChainTable, action_chain_id)
        if not db_chain:
            raise ValueError(f"Action Chain ID {action_chain_id} not found.")

        steps = db_chain.action_steps or []
        if index < 0 or index >= len(steps):
            raise ValueError(f"Index {index} out of range for action_steps.")

        # Update step fields
        for key, value in partial_updates.items():
            steps[index][key] = value

        db_chain.action_steps = steps
        attributes.flag_modified(db_chain, "action_steps")
        db_chain.updated_at = datetime.now(timezone.utc)

        db_session.commit()
        db_session.refresh(db_chain)
        return ActionChainModel(**db_chain.__dict__)


def reorder_steps(
    action_chain_id: str, ordered_step_names: List[str], engine: Engine
) -> ActionChainModel:
    """
    Reorder action steps based on ordered list of step names.

    Args:
        action_chain_id: ID of the chain to modify
        ordered_step_names: List of step names in desired order
        session: Database session factory
        engine: Database engine

    Returns:
        Updated ActionChainModel
    """
    with session() as db_session:
        db_chain = db_session.get(ActionChainTable, action_chain_id)
        if not db_chain:
            raise ValueError(f"Action Chain ID {action_chain_id} not found.")

        steps = db_chain.action_steps or []
        step_map = {s["step_name"]: s for s in steps}

        # Validate all step names exist
        for name in ordered_step_names:
            if name not in step_map:
                raise ValueError(f"Step '{name}' not found in chain.")

        if len(ordered_step_names) != len(steps):
            raise ValueError("ordered_step_names must contain all existing steps.")

        # Reorder steps
        reordered_steps = [step_map[name] for name in ordered_step_names]

        db_chain.action_steps = reordered_steps
        attributes.flag_modified(db_chain, "action_steps")
        db_chain.updated_at = datetime.now(timezone.utc)

        db_session.commit()
        db_session.refresh(db_chain)
        return ActionChainModel(**db_chain.__dict__)


def validate_action_references(
    action_chain_id: str, db_session: Session, engine: Engine, use_cache: bool = True
) -> Dict[str, Any]:
    """
    Validate that all action references in action_steps exist in their respective tables.

    Args:
        action_chain_id: ID of the chain to validate
        session: Database session factory
        engine: Database engine
        use_cache: Whether to use ActionReferenceCache (default: True)

    Returns:
        Dictionary with validation results:
        {
            "valid": bool,
            "invalid_steps": [{"step_name": str, "action_type": str, "action_id": str}],
            "total_steps": int
        }
    """
    with session() as db_session:
        db_chain = db_session.get(ActionChainTable, action_chain_id)
        if not db_chain:
            raise ValueError(f"Action Chain ID {action_chain_id} not found.")

        steps = db_chain.action_steps or []
        invalid_steps = []

        for step in steps:
            action_type = step.get("action_type")
            action_id = step.get("action_id")
            step_name = step.get("step_name")

            if use_cache:
                exists = ActionReferenceCache.check_exists(
                    action_type, action_id, db_session
                )
            else:
                exists = ActionReferenceCache._query_action_exists(
                    action_type, action_id, db_session
                )

            if not exists:
                invalid_steps.append(
                    {
                        "step_name": step_name,
                        "action_type": action_type,
                        "action_id": action_id,
                    }
                )

    return {
        "valid": len(invalid_steps) == 0,
        "invalid_steps": invalid_steps,
        "total_steps": len(steps),
    }


def clear_action_cache():
    """Clear the action reference cache. Useful for testing or manual invalidation."""
    ActionReferenceCache.clear()
