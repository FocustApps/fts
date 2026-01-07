"""align_auth_users_with_model

Revision ID: 0ec36ea2a851
Revises: 301ad4c5d899
Create Date: 2026-01-07 15:43:57.179406

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0ec36ea2a851"
down_revision = "d65d974ab1aa"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Align auth_users table columns with Python model
    # Step 1: Rename columns to match model
    op.alter_column("auth_users", "id", new_column_name="auth_user_id")
    op.alter_column("auth_users", "email", new_column_name="auth_user_email")
    op.alter_column("auth_users", "username", new_column_name="auth_username")
    op.alter_column("auth_users", "current_token", new_column_name="current_auth_token")

    # Step 2: Add missing columns
    op.add_column("auth_users", sa.Column("first_name", sa.String(255), nullable=True))
    op.add_column("auth_users", sa.Column("last_name", sa.String(255), nullable=True))
    op.add_column(
        "auth_users",
        sa.Column("is_super_admin", sa.Boolean, nullable=False, server_default="false"),
    )
    op.add_column(
        "auth_users",
        sa.Column(
            "multi_account_user", sa.Boolean, nullable=False, server_default="false"
        ),
    )
    op.add_column("auth_users", sa.Column("account_ids", sa.String(1024), nullable=True))
    op.add_column(
        "auth_users", sa.Column("user_subscription_id", sa.String(36), nullable=True)
    )


def downgrade() -> None:
    # Remove added columns
    op.drop_column("auth_users", "user_subscription_id")
    op.drop_column("auth_users", "account_ids")
    op.drop_column("auth_users", "multi_account_user")
    op.drop_column("auth_users", "is_super_admin")
    op.drop_column("auth_users", "last_name")
    op.drop_column("auth_users", "first_name")

    # Rename columns back
    op.alter_column("auth_users", "current_auth_token", new_column_name="current_token")
    op.alter_column("auth_users", "auth_username", new_column_name="username")
    op.alter_column("auth_users", "auth_user_email", new_column_name="email")
    op.alter_column("auth_users", "auth_user_id", new_column_name="id")
