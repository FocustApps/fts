"""add_system_under_test_table

Revision ID: d65d974ab1aa
Revises: b87e1a3b751b
Create Date: 2026-01-07 15:35:39.592899

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "d65d974ab1aa"
down_revision = "b87e1a3b751b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "system_under_test",
        sa.Column("sut_id", sa.String(36), primary_key=True),
        sa.Column("system_name", sa.String(96), unique=True, nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("wiki_url", sa.String(1024), nullable=True),
        sa.Column(
            "account_id",
            sa.String(36),
            sa.ForeignKey("account.account_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "owner_user_id",
            sa.Integer,
            sa.ForeignKey("auth_users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("deactivated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )

    # Create indexes for common lookups
    op.create_index(
        "ix_system_under_test_account_id", "system_under_test", ["account_id"]
    )
    op.create_index(
        "ix_system_under_test_owner_user_id", "system_under_test", ["owner_user_id"]
    )
    op.create_index("ix_system_under_test_is_active", "system_under_test", ["is_active"])


def downgrade() -> None:
    op.drop_index("ix_system_under_test_is_active")
    op.drop_index("ix_system_under_test_owner_user_id")
    op.drop_index("ix_system_under_test_account_id")
    op.drop_table("system_under_test")
