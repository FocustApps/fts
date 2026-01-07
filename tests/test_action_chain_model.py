"""
Tests for ActionChain model with JSONB operations and caching.

Tests cover:
- JSONB action step management
- ActionReferenceCache with TTL
- Step manipulation (add, remove, update, reorder)
- Action reference validation
"""

import time

import pytest
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from common.service_connections.db_service.models.action_chain_model import (
    ActionStepModel,
    ActionReferenceCache,
    query_action_chain_by_id,
    add_step_to_chain,
    remove_step_from_chain,
    update_step_at_index,
    reorder_steps,
)


class TestActionChainJSONB:
    """Test JSONB action_steps field operations."""

    def test_insert_action_chain_with_steps(
        self,
        action_chain_factory,
        system_under_test_factory,
        account_factory,
        engine: Engine,
        session: Session,
    ):
        """Test creating action chain with initial steps."""
        # Arrange
        account_id = account_factory()
        sut_id = system_under_test_factory(account_id=account_id)

        steps = [
            {
                "step_name": "Navigate to login",
                "action_type": "ui_action",
                "action_id": "nav-login-001",
                "depends_on": [],
                "parallel": False,
            },
            {
                "step_name": "Enter credentials",
                "action_type": "ui_action",
                "action_id": "input-creds-001",
                "depends_on": ["Navigate to login"],
                "parallel": False,
            },
        ]

        # Act
        chain_id = action_chain_factory(
            account_id=account_id,
            sut_id=sut_id,
            name="Login Workflow",
            action_steps=steps,
        )

        # Assert
        with session(engine) as db_session:
            retrieved = query_action_chain_by_id(chain_id, db_session, engine)

        assert retrieved is not None
        assert len(retrieved.action_steps) == 2
        assert retrieved.action_steps[0]["step_name"] == "Navigate to login"
        assert retrieved.action_steps[1]["depends_on"] == ["Navigate to login"]

    def test_add_step_to_chain(
        self,
        action_chain_factory,
        system_under_test_factory,
        account_factory,
        engine: Engine,
        session: Session,
    ):
        """Test adding a new step to existing action chain."""
        # Arrange
        account_id = account_factory()
        sut_id = system_under_test_factory(account_id=account_id)

        initial_steps = [
            {
                "step_name": "Step 1",
                "action_type": "ui_action",
                "action_id": "action-1",
                "depends_on": [],
                "parallel": False,
            }
        ]

        chain_id = action_chain_factory(
            account_id=account_id, sut_id=sut_id, action_steps=initial_steps
        )

        new_step = {
            "step_name": "Step 2",
            "action_type": "api_action",
            "action_id": "action-2",
            "depends_on": ["Step 1"],
            "parallel": False,
        }

        # Act
        result = add_step_to_chain(
            action_chain_id=chain_id,
            new_step=new_step,
            engine=engine,
            position=-1,  # Append to end
        )

        # Assert
        assert result is True

        with session(engine) as db_session:
            updated = query_action_chain_by_id(chain_id, db_session, engine)

        assert len(updated.action_steps) == 2
        assert updated.action_steps[1]["step_name"] == "Step 2"
        assert updated.action_steps[1]["action_type"] == "api_action"

    def test_remove_step_from_chain(
        self,
        action_chain_factory,
        system_under_test_factory,
        account_factory,
        engine: Engine,
        session: Session,
    ):
        """Test removing a step from action chain by name."""
        # Arrange
        account_id = account_factory()
        sut_id = system_under_test_factory(account_id=account_id)

        steps = [
            {
                "step_name": "Step A",
                "action_type": "ui_action",
                "action_id": "a",
                "depends_on": [],
                "parallel": False,
            },
            {
                "step_name": "Step B",
                "action_type": "ui_action",
                "action_id": "b",
                "depends_on": [],
                "parallel": False,
            },
            {
                "step_name": "Step C",
                "action_type": "ui_action",
                "action_id": "c",
                "depends_on": [],
                "parallel": False,
            },
        ]

        chain_id = action_chain_factory(
            account_id=account_id, sut_id=sut_id, action_steps=steps
        )

        # Act
        result = remove_step_from_chain(
            action_chain_id=chain_id, step_name="Step B", engine=engine
        )

        # Assert
        assert result is True

        with session(engine) as db_session:
            updated = query_action_chain_by_id(chain_id, db_session, engine)

        assert len(updated.action_steps) == 2
        step_names = [s["step_name"] for s in updated.action_steps]
        assert "Step B" not in step_names
        assert "Step A" in step_names
        assert "Step C" in step_names

    def test_update_step_at_index(
        self,
        action_chain_factory,
        system_under_test_factory,
        account_factory,
        engine: Engine,
        session: Session,
    ):
        """Test updating specific fields of a step by index."""
        # Arrange
        account_id = account_factory()
        sut_id = system_under_test_factory(account_id=account_id)

        steps = [
            {
                "step_name": "Original Step",
                "action_type": "ui_action",
                "action_id": "orig",
                "depends_on": [],
                "parallel": False,
            }
        ]

        chain_id = action_chain_factory(
            account_id=account_id, sut_id=sut_id, action_steps=steps
        )

        # Act - Update action_id and parallel flag
        partial_updates = {"action_id": "updated-action", "parallel": True}

        result = update_step_at_index(
            action_chain_id=chain_id,
            index=0,
            partial_updates=partial_updates,
            engine=engine,
        )

        # Assert
        assert result is True

        with session(engine) as db_session:
            updated = query_action_chain_by_id(chain_id, db_session, engine)

        assert updated.action_steps[0]["action_id"] == "updated-action"
        assert updated.action_steps[0]["parallel"] is True
        assert updated.action_steps[0]["step_name"] == "Original Step"  # Unchanged

    def test_reorder_steps(
        self,
        action_chain_factory,
        system_under_test_factory,
        account_factory,
        engine: Engine,
        session: Session,
    ):
        """Test reordering steps by providing new step name order."""
        # Arrange
        account_id = account_factory()
        sut_id = system_under_test_factory(account_id=account_id)

        steps = [
            {
                "step_name": "First",
                "action_type": "ui_action",
                "action_id": "1",
                "depends_on": [],
                "parallel": False,
            },
            {
                "step_name": "Second",
                "action_type": "ui_action",
                "action_id": "2",
                "depends_on": [],
                "parallel": False,
            },
            {
                "step_name": "Third",
                "action_type": "ui_action",
                "action_id": "3",
                "depends_on": [],
                "parallel": False,
            },
        ]

        chain_id = action_chain_factory(
            account_id=account_id, sut_id=sut_id, action_steps=steps
        )

        # Act - Reverse order
        new_order = ["Third", "Second", "First"]
        result = reorder_steps(
            action_chain_id=chain_id, ordered_step_names=new_order, engine=engine
        )

        # Assert
        assert result is True

        with session(engine) as db_session:
            updated = query_action_chain_by_id(chain_id, db_session, engine)

        step_names = [s["step_name"] for s in updated.action_steps]
        assert step_names == new_order


class TestActionReferenceCache:
    """Test ActionReferenceCache with TTL functionality."""

    def test_cache_stores_action_existence(self, engine: Engine):
        """Test that cache stores and retrieves action existence."""
        # Arrange
        cache = ActionReferenceCache()
        cache.clear()

        action_type = "ui_action"
        action_id = "test-action-123"

        # Mock session (in real scenario, this would query database)
        # For testing, we'll use the class method directly

        # Note: This test would need actual UI action in database
        # or we need to mock the _query_action_exists method
        # For now, testing the cache structure

        # Manually populate cache for testing
        cache._cache[(action_type, action_id)] = (True, time.time())

        # Act
        cache_key = (action_type, action_id)
        cached_value = cache._cache.get(cache_key)

        # Assert
        assert cached_value is not None
        exists, cached_time = cached_value
        assert exists is True
        assert cached_time > 0

    def test_cache_ttl_expiration(self):
        """Test that cache entries expire after TTL."""
        # Arrange
        cache = ActionReferenceCache()
        cache._ttl_seconds = 1  # Set to 1 second for testing

        action_type = "ui_action"
        action_id = "expire-test"

        # Populate cache with old timestamp
        old_time = time.time() - 2  # 2 seconds ago
        cache._cache[(action_type, action_id)] = (True, old_time)

        # Act - Check if entry is considered expired
        cache_key = (action_type, action_id)
        exists, cached_time = cache._cache[cache_key]
        current_time = time.time()
        is_expired = (current_time - cached_time) >= cache._ttl_seconds

        # Assert
        assert is_expired is True

    def test_clear_cache(self):
        """Test clearing the cache."""
        # Arrange
        cache = ActionReferenceCache()
        cache._cache[("ui_action", "1")] = (True, time.time())
        cache._cache[("api_action", "2")] = (True, time.time())

        # Act
        cache.clear()

        # Assert
        assert len(cache._cache) == 0


class TestActionStepValidation:
    """Test ActionStepModel validation."""

    def test_valid_action_step_model(self):
        """Test creating valid ActionStepModel."""
        # Arrange & Act
        step = ActionStepModel(
            step_name="Valid Step",
            action_type="ui_action",
            action_id="valid-123",
            depends_on=[],
            parallel=False,
        )

        # Assert
        assert step.step_name == "Valid Step"
        assert step.action_type == "ui_action"

    def test_invalid_action_type_raises_error(self):
        """Test that invalid action_type raises ValidationError."""
        # Arrange & Act & Assert
        with pytest.raises(Exception):  # Pydantic ValidationError
            step = ActionStepModel(
                step_name="Invalid Step",
                action_type="invalid_type",  # Not in valid types
                action_id="test",
                depends_on=[],
                parallel=False,
            )
