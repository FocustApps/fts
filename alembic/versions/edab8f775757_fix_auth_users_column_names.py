"""fix_auth_users_column_names

Revision ID: edab8f775757
Revises: 5b3a509eff29
Create Date: 2026-01-07 16:59:25.823353

"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "edab8f775757"
down_revision = "5b3a509eff29"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Rename columns back to match the Python model
    op.alter_column("auth_users", "auth_user_id", new_column_name="id")
    op.alter_column("auth_users", "auth_user_email", new_column_name="email")
    op.alter_column("auth_users", "auth_username", new_column_name="username")
    op.alter_column("auth_users", "current_auth_token", new_column_name="current_token")


def downgrade() -> None:
    # Revert back to the mismatched names
    op.alter_column("auth_users", "id", new_column_name="auth_user_id")
    op.alter_column("auth_users", "email", new_column_name="auth_user_email")
    op.alter_column("auth_users", "username", new_column_name="auth_username")
    op.alter_column("auth_users", "current_token", new_column_name="current_auth_token")
