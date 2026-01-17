"""add_notification_preference_and_in_app_notification_tables

Revision ID: 3346963c8a10
Revises: c5b23c24c460
Create Date: 2026-01-14 22:00:00.000000

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision = "3346963c8a10"
down_revision = "c5b23c24c460"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create notification_preference table
    op.create_table(
        "notification_preference",
        sa.Column("preference_id", sa.String(36), primary_key=True),
        sa.Column(
            "auth_user_id",
            sa.String(36),
            sa.ForeignKey("auth_users.auth_user_id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        # Account membership notifications
        sa.Column(
            "account_added_email", sa.Boolean(), nullable=False, server_default="true"
        ),
        sa.Column(
            "account_added_in_app", sa.Boolean(), nullable=False, server_default="true"
        ),
        sa.Column(
            "account_removed_email", sa.Boolean(), nullable=False, server_default="true"
        ),
        sa.Column(
            "account_removed_in_app", sa.Boolean(), nullable=False, server_default="true"
        ),
        # Role change notifications
        sa.Column(
            "role_changed_email", sa.Boolean(), nullable=False, server_default="true"
        ),
        sa.Column(
            "role_changed_in_app", sa.Boolean(), nullable=False, server_default="true"
        ),
        # Primary account notifications
        sa.Column(
            "primary_account_changed_email",
            sa.Boolean(),
            nullable=False,
            server_default="true",
        ),
        sa.Column(
            "primary_account_changed_in_app",
            sa.Boolean(),
            nullable=False,
            server_default="true",
        ),
        # Bulk operation summary notifications
        sa.Column(
            "bulk_operation_email", sa.Boolean(), nullable=False, server_default="true"
        ),
        sa.Column(
            "bulk_operation_in_app", sa.Boolean(), nullable=False, server_default="false"
        ),
        # Account-level change notifications
        sa.Column(
            "account_updated_email", sa.Boolean(), nullable=False, server_default="false"
        ),
        sa.Column(
            "account_updated_in_app", sa.Boolean(), nullable=False, server_default="true"
        ),
        # Metadata
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )

    # Create index for notification_preference
    op.create_index(
        "idx_notification_pref_user", "notification_preference", ["auth_user_id"]
    )

    # Create in_app_notification table
    op.create_table(
        "in_app_notification",
        sa.Column("notification_id", sa.String(36), primary_key=True),
        sa.Column(
            "auth_user_id",
            sa.String(36),
            sa.ForeignKey("auth_users.auth_user_id", ondelete="CASCADE"),
            nullable=False,
        ),
        # Notification content
        sa.Column("notification_type", sa.String(64), nullable=False),
        sa.Column("title", sa.String(256), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        # Related entities (nullable to preserve context)
        sa.Column(
            "related_account_id",
            sa.String(36),
            sa.ForeignKey("account.account_id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "related_user_id",
            sa.String(36),
            sa.ForeignKey("auth_users.auth_user_id", ondelete="SET NULL"),
            nullable=True,
        ),
        # Additional context
        sa.Column("metadata_json", JSONB, nullable=True),
        # Status tracking
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("read_at", sa.DateTime(), nullable=True),
        # Priority
        sa.Column("priority", sa.String(16), nullable=False, server_default="normal"),
        # Metadata
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )

    # Create indexes for in_app_notification
    op.create_index("idx_notification_user", "in_app_notification", ["auth_user_id"])
    op.create_index(
        "idx_notification_user_unread", "in_app_notification", ["auth_user_id", "is_read"]
    )
    op.create_index("idx_notification_type", "in_app_notification", ["notification_type"])
    op.create_index("idx_notification_created", "in_app_notification", ["created_at"])
    op.create_index(
        "idx_notification_account", "in_app_notification", ["related_account_id"]
    )


def downgrade() -> None:
    # Drop in_app_notification table and indexes
    op.drop_index("idx_notification_account", table_name="in_app_notification")
    op.drop_index("idx_notification_created", table_name="in_app_notification")
    op.drop_index("idx_notification_type", table_name="in_app_notification")
    op.drop_index("idx_notification_user_unread", table_name="in_app_notification")
    op.drop_index("idx_notification_user", table_name="in_app_notification")
    op.drop_table("in_app_notification")

    # Drop notification_preference table and indexes
    op.drop_index("idx_notification_pref_user", table_name="notification_preference")
    op.drop_table("notification_preference")
