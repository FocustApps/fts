"""add_audit_and_auth_tables

Revision ID: 21bbe2e2f4cc
Revises: 01d551d7392f
Create Date: 2026-01-07 15:40:00.447868

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "21bbe2e2f4cc"
down_revision = "01d551d7392f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create audit_log table
    # Note: Uses auth_users.id (INTEGER) not auth_users.auth_user_id
    op.create_table(
        "audit_log",
        sa.Column("audit_id", sa.String(36), primary_key=True),
        sa.Column("entity_type", sa.String(128), nullable=False),
        sa.Column("entity_id", sa.String(36), nullable=False),
        sa.Column("action", sa.String(64), nullable=False),
        sa.Column(
            "performed_by_user_id",
            sa.Integer,
            sa.ForeignKey("auth_users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "account_id",
            sa.String(36),
            sa.ForeignKey("account.account_id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "timestamp",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.String(512), nullable=True),
        sa.Column("details", sa.dialects.postgresql.JSONB, nullable=True),
        sa.Column("is_sensitive", sa.Boolean, nullable=False, server_default="false"),
    )

    # Create indexes for audit_log
    op.create_index("idx_audit_pk", "audit_log", ["audit_id"], postgresql_using="btree")
    op.create_index("idx_audit_entity", "audit_log", ["entity_type", "entity_id"])
    op.create_index("idx_audit_timestamp", "audit_log", ["timestamp"])
    op.create_index("idx_audit_account", "audit_log", ["account_id"])
    op.create_index("idx_audit_user", "audit_log", ["performed_by_user_id"])

    # Create auth_tokens table
    # Note: Uses auth_users.id (INTEGER) not auth_users.auth_user_id
    op.create_table(
        "auth_tokens",
        sa.Column("token_id", sa.String(36), primary_key=True),
        sa.Column(
            "auth_user_id",
            sa.Integer,
            sa.ForeignKey("auth_users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("token_value", sa.String(64), unique=True, nullable=False),
        sa.Column("token_expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("device_info", sa.String(255), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Create indexes for auth_tokens
    op.create_index(
        "idx_auth_tokens_pk", "auth_tokens", ["token_id"], postgresql_using="btree"
    )
    op.create_index("idx_auth_tokens_user", "auth_tokens", ["auth_user_id"])
    op.create_index("idx_auth_tokens_value", "auth_tokens", ["token_value"])
    op.create_index("idx_auth_tokens_active", "auth_tokens", ["is_active"])


def downgrade() -> None:
    op.drop_index("idx_auth_tokens_active")
    op.drop_index("idx_auth_tokens_value")
    op.drop_index("idx_auth_tokens_user")
    op.drop_index("idx_auth_tokens_pk")
    op.drop_table("auth_tokens")

    op.drop_index("idx_audit_user")
    op.drop_index("idx_audit_account")
    op.drop_index("idx_audit_timestamp")
    op.drop_index("idx_audit_entity")
    op.drop_index("idx_audit_pk")
    op.drop_table("audit_log")
