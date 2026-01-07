"""add_simple_tables_group_1

Revision ID: 01d551d7392f
Revises: d65d974ab1aa
Create Date: 2026-01-07 15:39:34.247811

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "01d551d7392f"
down_revision = "d65d974ab1aa"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create purgeTable
    op.create_table(
        "purgeTable",
        sa.Column("purge_id", sa.String(36), primary_key=True),
        sa.Column("table_name", sa.String(255), nullable=False),
        sa.Column(
            "last_purged_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("purge_interval_days", sa.Integer, nullable=False, server_default="30"),
    )

    # Create entity_tag table
    # Note: Uses auth_users.id (INTEGER) not auth_users.auth_user_id
    op.create_table(
        "entity_tag",
        sa.Column("tag_id", sa.String(36), primary_key=True),
        sa.Column("entity_type", sa.String(64), nullable=False),
        sa.Column("entity_id", sa.String(36), nullable=False),
        sa.Column("tag_name", sa.String(128), nullable=False),
        sa.Column("tag_category", sa.String(64), nullable=False),
        sa.Column("tag_value", sa.String(255), nullable=True),
        sa.Column(
            "account_id",
            sa.String(36),
            sa.ForeignKey("account.account_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "created_by_user_id",
            sa.Integer,
            sa.ForeignKey("auth_users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("deactivated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "deactivated_by_user_id",
            sa.Integer,
            sa.ForeignKey("auth_users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Create indexes for entity_tag
    op.create_index("idx_entity_tag_entity_type", "entity_tag", ["entity_type"])
    op.create_index("idx_entity_tag_entity_id", "entity_tag", ["entity_id"])
    op.create_index("idx_entity_tag_name", "entity_tag", ["tag_name"])
    op.create_index("idx_entity_tag_category", "entity_tag", ["tag_category"])
    op.create_index("idx_entity_tag_account_id", "entity_tag", ["account_id"])
    op.create_index(
        "idx_entity_tag_composite",
        "entity_tag",
        ["entity_type", "entity_id", "tag_category"],
    )


def downgrade() -> None:
    op.drop_index("idx_entity_tag_composite")
    op.drop_index("idx_entity_tag_account_id")
    op.drop_index("idx_entity_tag_category")
    op.drop_index("idx_entity_tag_name")
    op.drop_index("idx_entity_tag_entity_id")
    op.drop_index("idx_entity_tag_entity_type")
    op.drop_table("entity_tag")
    op.drop_table("purgeTable")
