"""add_is_primary_to_auth_user_account_association

Revision ID: c5b23c24c460
Revises: 202a95fe15b2
Create Date: 2026-01-14 21:42:59.790829

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "c5b23c24c460"
down_revision = "202a95fe15b2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add is_primary column
    op.add_column(
        "auth_user_account_association",
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default="false"),
    )

    # Create index for faster primary account lookups
    op.create_index(
        "idx_user_primary",
        "auth_user_account_association",
        ["auth_user_id"],
        unique=False,
        postgresql_where=sa.text("is_primary = true"),
    )


def downgrade() -> None:
    # Drop index
    op.drop_index("idx_user_primary", table_name="auth_user_account_association")

    # Drop column
    op.drop_column("auth_user_account_association", "is_primary")
