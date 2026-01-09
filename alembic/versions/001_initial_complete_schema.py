"""initial_complete_schema

Revision ID: 001_initial_complete_schema
Revises:
Create Date: 2026-01-08

This is a consolidated migration that creates all tables from the current
SQLAlchemy models. It replaces 19 previous incremental migrations with a
single comprehensive schema definition.

All tables, foreign keys, and constraints are defined to match the exact
state of the SQLAlchemy ORM models as of January 8, 2026.
"""

from alembic import op

# Import Base to get all table metadata
from common.service_connections.db_service.database import Base

# revision identifiers, used by Alembic
revision = "001_initial_complete_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create all tables from SQLAlchemy models."""
    # Use Base.metadata.create_all to create all tables
    # This ensures perfect alignment with model definitions
    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    """Drop all tables."""
    # Drop all tables in reverse dependency order
    Base.metadata.drop_all(bind=op.get_bind())
