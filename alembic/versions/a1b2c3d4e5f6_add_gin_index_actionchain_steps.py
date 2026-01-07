"""add GIN index on action_chain.action_steps for JSONB queries

Revision ID: a1b2c3d4e5f6
Revises: 74cc10e65343
Create Date: 2026-01-07 00:00:00.000000

"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "a1b2c3d4e5f6"
down_revision = "74cc10e65343"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Add GIN index on action_chain.action_steps for efficient JSONB querying.

    This is a one-time migration that creates a GIN index using jsonb_path_ops
    for improved performance when querying action_steps by action_type, step names,
    or other JSONB properties. The index self-maintains as data grows.

    Using CONCURRENTLY to avoid locking the table during index creation.
    """
    # Create GIN index concurrently to avoid table locks
    op.execute(
        """
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_actionchain_steps_gin
        ON action_chain USING gin (action_steps jsonb_path_ops)
        """
    )


def downgrade() -> None:
    """Remove the GIN index on action_chain.action_steps."""
    op.execute("DROP INDEX IF EXISTS idx_actionchain_steps_gin")
