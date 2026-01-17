"""
Entity tag table model for polymorphic tagging with multi-tenant isolation.
"""

from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

import sqlalchemy as sql
from sqlalchemy.orm import Mapped, mapped_column

from common.service_connections.db_service.database.base import Base


class EntityTagTable(Base):
    """Entity tag table for polymorphic tagging with row-level security.

    Business Logic Documentation:

    1. Define at a high level what this table is suppose to represent in terms of a goal
       or goals that need to be accomplished by a user?
       - Provides flexible tagging system for any entity in the system using polymorphic
         pattern. Enables categorization, filtering, and organization of test plans,
         suites, test cases, actions, and other entities. Supports multi-tenant isolation
         through account_id and row-level security (RLS) policies.

    2. What level of user should be interacting with this table?
       - All Users: Create and manage tags for entities they own (enforced by RLS)
       - Admin: Full CRUD access within their account
       - Super Admin: Cross-account access for system management
       - Test Automation Framework: Read access for tag-based test selection

    3. What are the names of the tables that are either above or below this table in the
       data structure? This is to understand where to put in in a architecture diagram.
       - Above: AccountTable (via account_id for multi-tenant isolation)
       - Below: None (polymorphic references to multiple entity types via entity_id)
       - Related: SuiteTable, TestCaseTable, PlanTable, ActionChainTable, and action
         tables (via entity_type + entity_id polymorphic pattern)

    4. Should a record in this table be deleted based on the deletion of a record in a
       different table? If so, what table?
       - CASCADE delete when AccountTable is deleted (multi-tenant cleanup)
       - Application logic should handle orphaned tags when tagged entities are deleted
         (soft delete recommended - query entity tables to verify entity still active)

    5. Will this table be require a connection a secure cloud provider service?
       - No direct cloud connection required.

    Row-Level Security (RLS) Implementation:
       - PostgreSQL RLS policy filters tags by account_id matching session variable
       - Ensures users can only see/modify tags within their account
       - Policy name: entity_tag_account_isolation_policy
       - Filter: account_id = current_setting('app.current_account_id')::uuid
       - Enable with: ALTER TABLE entity_tag ENABLE ROW LEVEL SECURITY;
       - Create policy SQL (run after table creation):

         CREATE POLICY entity_tag_account_isolation_policy ON entity_tag
         FOR ALL
         USING (account_id = current_setting('app.current_account_id', true)::uuid);

    Polymorphic Pattern Usage:
       - entity_type: Enum value from EntityTypeEnum (suite, test_case, plan, etc.)
       - entity_id: UUID string referencing the actual entity's primary key
       - Example: entity_type='suite', entity_id='uuid-of-suite-record'
       - No foreign key constraint to allow flexibility across multiple entity types
    """

    __tablename__ = "entity_tag"

    tag_id: Mapped[str] = mapped_column(
        sql.String(36), primary_key=True, default=lambda: str(uuid4())
    )
    entity_type: Mapped[str] = mapped_column(sql.String(64), nullable=False, index=True)
    entity_id: Mapped[str] = mapped_column(sql.String(36), nullable=False, index=True)
    tag_name: Mapped[str] = mapped_column(sql.String(128), nullable=False, index=True)
    tag_category: Mapped[str] = mapped_column(sql.String(64), nullable=False, index=True)
    tag_value: Mapped[Optional[str]] = mapped_column(sql.String(255), nullable=True)
    account_id: Mapped[str] = mapped_column(
        sql.String(36),
        sql.ForeignKey("account.account_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_by_user_id: Mapped[str] = mapped_column(
        sql.String(36),
        sql.ForeignKey("auth_users.auth_user_id", ondelete="RESTRICT"),
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(sql.Boolean, nullable=False, default=True)
    deactivated_at: Mapped[Optional[datetime]] = mapped_column(
        sql.DateTime, nullable=True
    )
    deactivated_by_user_id: Mapped[Optional[str]] = mapped_column(
        sql.String(36),
        sql.ForeignKey("auth_users.auth_user_id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        sql.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        sql.DateTime,
        nullable=True,
        onupdate=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        # Primary key index
        sql.Index("idx_entitytag_pk", "tag_id", postgresql_using="btree"),
        # Polymorphic lookup indexes (most common query pattern)
        sql.Index("idx_entitytag_entity", "entity_type", "entity_id"),
        sql.Index(
            "idx_entitytag_entity_active",
            "entity_type",
            "entity_id",
            "is_active",
            postgresql_where=sql.text("is_active = true"),
        ),
        # Multi-tenant isolation index
        sql.Index("idx_entitytag_account", "account_id"),
        # Tag search indexes
        sql.Index("idx_entitytag_category", "tag_category"),
        sql.Index("idx_entitytag_name", "tag_name"),
        sql.Index("idx_entitytag_account_category", "account_id", "tag_category"),
        # Active tags partial index for query optimization
        sql.Index(
            "idx_entitytag_active",
            "is_active",
            postgresql_where=sql.text("is_active = true"),
        ),
        # Composite index for tag filtering within account
        sql.Index(
            "idx_entitytag_account_entity_category",
            "account_id",
            "entity_type",
            "tag_category",
        ),
        # Unique constraint to prevent duplicate tags on same entity
        sql.UniqueConstraint(
            "entity_type",
            "entity_id",
            "tag_name",
            "account_id",
            name="uq_entitytag_entity_name_account",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<EntityTag(id={self.tag_id}, entity_type='{self.entity_type}', "
            f"entity_id='{self.entity_id}', tag='{self.tag_name}', "
            f"category='{self.tag_category}')>"
        )


__all__ = ["EntityTagTable"]
