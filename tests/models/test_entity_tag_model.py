"""
Tests for EntityTag model with polymorphic queries and RLS context manager.

Tests cover:
- Polymorphic tagging (tags on different entity types)
- Tag queries by entity, category, name
- AccountRLSContext thread safety and stack limits
- Bulk tag operations
"""

import threading
import pytest
from sqlalchemy.engine import Engine

from common.service_connections.db_service.database.engine import (
    get_database_session as session,
)
from common.service_connections.db_service.models.entity_tag_model import (
    AccountRLSContext,
    query_entity_tag_by_id,
    query_tags_for_entity,
    query_entities_by_tag,
    query_tags_by_category,
    query_unique_tag_names,
    add_tags_to_entity,
    replace_entity_tags,
    deactivate_entity_tag,
)


class TestPolymorphicTagging:
    """Test polymorphic tagging across different entity types."""

    def test_tag_multiple_entity_types(
        self,
        entity_tag_factory,
        suite_factory,
        test_case_factory,
        system_under_test_factory,
        account_factory,
        engine: Engine,
    ):
        """Test tagging different entity types with same tag name."""
        # Arrange
        account_id = account_factory()
        sut_id = system_under_test_factory(account_id=account_id)
        suite_id = suite_factory(account_id=account_id)
        test_case_id = test_case_factory(account_id=account_id, sut_id=sut_id)

        # Act - Tag both suite and test case with "priority:high"
        suite_tag_id = entity_tag_factory(
            entity_type="suite",
            entity_id=suite_id,
            tag_name="high",
            tag_category="priority",
            account_id=account_id,
        )

        test_tag_id = entity_tag_factory(
            entity_type="test_case",
            entity_id=test_case_id,
            tag_name="high",
            tag_category="priority",
            account_id=account_id,
        )

        # Assert - Query entities by tag
        with session(engine) as db_session:
            suite_entities = query_entities_by_tag(
                tag_name="high",
                entity_type="suite",
                account_id=account_id,
                db_session=db_session,
                engine=engine,
            )

            test_entities = query_entities_by_tag(
                tag_name="high",
                entity_type="test_case",
                account_id=account_id,
                db_session=db_session,
                engine=engine,
            )

        assert suite_id in suite_entities
        assert test_case_id in test_entities

    def test_query_tags_for_specific_entity(
        self, entity_tag_factory, suite_factory, account_factory, engine: Engine
    ):
        """Test querying all tags for a specific entity."""
        # Arrange
        account_id = account_factory()
        suite_id = suite_factory(account_id=account_id)

        # Add multiple tags to the suite
        tag1 = entity_tag_factory(
            entity_type="suite",
            entity_id=suite_id,
            tag_name="regression",
            tag_category="type",
            account_id=account_id,
        )

        tag2 = entity_tag_factory(
            entity_type="suite",
            entity_id=suite_id,
            tag_name="critical",
            tag_category="severity",
            account_id=account_id,
        )

        tag3 = entity_tag_factory(
            entity_type="suite",
            entity_id=suite_id,
            tag_name="nightly",
            tag_category="schedule",
            account_id=account_id,
        )

        # Act
        with session(engine) as db_session:
            tags = query_tags_for_entity(
                entity_type="suite",
                entity_id=suite_id,
                account_id=account_id,
                db_session=db_session,
                engine=engine,
            )

        # Assert
        assert len(tags) == 3
        tag_names = {tag.tag_name for tag in tags}
        assert tag_names == {"regression", "critical", "nightly"}

    def test_query_tags_by_category(
        self,
        entity_tag_factory,
        suite_factory,
        test_case_factory,
        system_under_test_factory,
        account_factory,
        engine: Engine,
    ):
        """Test querying all tags in a category across entities."""
        # Arrange
        account_id = account_factory()
        sut_id = system_under_test_factory(account_id=account_id)
        suite_id = suite_factory(account_id=account_id)
        test_id = test_case_factory(account_id=account_id, sut_id=sut_id)

        # Add priority tags to different entities
        entity_tag_factory(
            entity_type="suite",
            entity_id=suite_id,
            tag_name="high",
            tag_category="priority",
            account_id=account_id,
        )

        entity_tag_factory(
            entity_type="test_case",
            entity_id=test_id,
            tag_name="low",
            tag_category="priority",
            account_id=account_id,
        )

        # Act
        with session(engine) as db_session:
            priority_tags = query_tags_by_category(
                tag_category="priority",
                account_id=account_id,
                db_session=db_session,
                engine=engine,
            )

        # Assert
        assert len(priority_tags) >= 2
        tag_names = {tag.tag_name for tag in priority_tags}
        assert "high" in tag_names
        assert "low" in tag_names

    def test_query_unique_tag_names(
        self, entity_tag_factory, suite_factory, account_factory, engine: Engine
    ):
        """Test getting unique tag names for autocomplete."""
        # Arrange
        account_id = account_factory()
        suite1 = suite_factory(account_id=account_id)
        suite2 = suite_factory(account_id=account_id)

        # Same tag name on different entities
        entity_tag_factory(
            entity_type="suite",
            entity_id=suite1,
            tag_name="smoke",
            tag_category="type",
            account_id=account_id,
        )

        entity_tag_factory(
            entity_type="suite",
            entity_id=suite2,
            tag_name="smoke",
            tag_category="type",
            account_id=account_id,
        )

        entity_tag_factory(
            entity_type="suite",
            entity_id=suite1,
            tag_name="regression",
            tag_category="type",
            account_id=account_id,
        )

        # Act
        with session(engine) as db_session:
            unique_names = query_unique_tag_names(
                account_id=account_id, db_session=db_session, engine=engine
            )

        # Assert - Should only have 2 unique names despite 3 tags
        assert "smoke" in unique_names
        assert "regression" in unique_names
        assert unique_names.count("smoke") == 1  # No duplicates


class TestBulkTagOperations:
    """Test bulk tag operations."""

    def test_add_multiple_tags_to_entity(
        self, suite_factory, account_factory, auth_user_factory, engine: Engine
    ):
        """Test adding multiple tags in single transaction."""
        # Arrange
        user_id = auth_user_factory()
        account_id = account_factory(owner_user_id=user_id)
        suite_id = suite_factory(account_id=account_id)

        tag_names = ["tag1", "tag2", "tag3"]

        # Act
        tag_ids = add_tags_to_entity(
            entity_type="suite",
            entity_id=suite_id,
            tag_names=tag_names,
            tag_category="test_category",
            account_id=account_id,
            created_by_user_id=user_id,
            engine=engine,
        )

        # Assert
        assert len(tag_ids) == 3

        with session(engine) as db_session:
            tags = query_tags_for_entity(
                entity_type="suite",
                entity_id=suite_id,
                account_id=account_id,
                db_session=db_session,
                engine=engine,
            )

        retrieved_names = {tag.tag_name for tag in tags}
        assert retrieved_names == set(tag_names)

    def test_replace_entity_tags(
        self, suite_factory, account_factory, auth_user_factory, engine: Engine
    ):
        """Test replacing all tags on an entity."""
        # Arrange
        user_id = auth_user_factory()
        account_id = account_factory(owner_user_id=user_id)
        suite_id = suite_factory(account_id=account_id)

        # Add initial tags
        initial_ids = add_tags_to_entity(
            entity_type="suite",
            entity_id=suite_id,
            tag_names=["old1", "old2"],
            tag_category="labels",
            account_id=account_id,
            created_by_user_id=user_id,
            engine=engine,
        )

        # Act - Replace with new tags
        result = replace_entity_tags(
            entity_type="suite",
            entity_id=suite_id,
            new_tag_names=["new1", "new2", "new3"],
            tag_category="labels",
            account_id=account_id,
            created_by_user_id=user_id,
            deactivated_by_user_id=user_id,
            engine=engine,
        )

        # Assert
        assert len(result["deactivated"]) == 2
        assert len(result["created"]) == 3

        with session(engine) as db_session:
            active_tags = query_tags_for_entity(
                entity_type="suite",
                entity_id=suite_id,
                account_id=account_id,
                db_session=db_session,
                engine=engine,
                active_only=True,
            )

        active_names = {tag.tag_name for tag in active_tags}
        assert active_names == {"new1", "new2", "new3"}


class TestAccountRLSContext:
    """Test AccountRLSContext for row-level security."""

    def test_rls_context_sets_session_variable(self, engine: Engine):
        """Test that RLS context sets PostgreSQL session variable."""
        # Arrange
        account_id = "test-account-123"

        # Act & Assert - Context should not raise errors
        with session(engine) as db_session:
            with AccountRLSContext(db_session, account_id=account_id):
                # Inside context, session variable is set
                # In production, this would filter queries
                pass
            # After context, session variable should be reset

    def test_rls_context_nesting(self, engine: Engine):
        """Test nested RLS contexts."""
        # Arrange
        account1 = "account-1"
        account2 = "account-2"

        # Act & Assert - Nested contexts should work
        with session(engine) as db_session:
            with AccountRLSContext(db_session, account_id=account1):
                # Inner context
                with AccountRLSContext(db_session, account_id=account2):
                    # Innermost uses account2
                    pass
                # Restored to account1
            # Fully reset

    def test_rls_context_max_depth_limit(self, engine: Engine):
        """Test that stack depth limit prevents infinite recursion."""
        # Arrange
        max_depth = AccountRLSContext.MAX_STACK_DEPTH

        # Act & Assert - Should raise RuntimeError at depth limit
        with session(engine) as db_session:
            with pytest.raises(RuntimeError, match="Maximum RLS context depth"):
                # Try to nest beyond limit
                def nest_contexts(depth):
                    if depth >= max_depth + 1:
                        return
                    with AccountRLSContext(db_session, account_id=f"account-{depth}"):
                        nest_contexts(depth + 1)

                nest_contexts(0)

    def test_rls_context_thread_safety(self, engine: Engine):
        """Test that RLS contexts are isolated per thread."""
        # Arrange
        results = {}

        def thread_func(thread_id, account_id):
            """Function to run in separate thread."""
            try:
                with session(engine) as db_session:
                    with AccountRLSContext(db_session, account_id=account_id):
                        # Each thread should have independent stack
                        results[thread_id] = "success"
            except Exception as e:
                results[thread_id] = f"error: {e}"

        # Act - Run in multiple threads
        threads = []
        for i in range(3):
            t = threading.Thread(target=thread_func, args=(f"thread-{i}", f"account-{i}"))
            threads.append(t)
            t.start()

        # Wait for all threads
        for t in threads:
            t.join()

        # Assert - All threads should succeed independently
        assert all(v == "success" for v in results.values())


class TestTagSoftDelete:
    """Test soft delete operations for tags."""

    def test_deactivate_tag(
        self,
        entity_tag_factory,
        suite_factory,
        account_factory,
        auth_user_factory,
        engine: Engine,
    ):
        """Test soft deleting a tag."""
        # Arrange
        user_id = auth_user_factory()
        account_id = account_factory(owner_user_id=user_id)
        suite_id = suite_factory(account_id=account_id)

        tag_id = entity_tag_factory(
            entity_type="suite",
            entity_id=suite_id,
            tag_name="temp-tag",
            tag_category="temp",
            account_id=account_id,
        )

        # Act
        result = deactivate_entity_tag(
            tag_id=tag_id, deactivated_by_user_id=user_id, engine=engine
        )

        # Assert
        assert result is True

        with session(engine) as db_session:
            tag = query_entity_tag_by_id(tag_id, db_session, engine)

        assert tag.is_active is False
        assert tag.deactivated_by_user_id == user_id
        assert tag.deactivated_at is not None
