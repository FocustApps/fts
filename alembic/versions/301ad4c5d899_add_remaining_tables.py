"""add_remaining_tables

Revision ID: 301ad4c5d899
Revises: d383b58287f7
Create Date: 2026-01-07 15:41:24.107355

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "301ad4c5d899"
down_revision = "d383b58287f7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create fenrir_actions table (no FK dependencies)
    op.create_table(
        "fenrir_actions",
        sa.Column("fenrir_action_id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("method_name", sa.String(128), unique=True, nullable=False),
        sa.Column("docstring", sa.Text, nullable=False),
        sa.Column("parameters", sa.dialects.postgresql.JSONB, nullable=True),
        sa.Column("return_type", sa.String(256), nullable=False),
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
    op.create_index("idx_fenrir_actions_method", "fenrir_actions", ["method_name"])

    # Create action_chain table
    # Note: Uses auth_users.id (INTEGER) not auth_users.auth_user_id
    op.create_table(
        "action_chain",
        sa.Column("action_chain_id", sa.String(36), primary_key=True),
        sa.Column("chain_name", sa.String(255), unique=True, nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("action_steps", sa.dialects.postgresql.JSONB, nullable=False),
        sa.Column(
            "sut_id",
            sa.String(36),
            sa.ForeignKey("system_under_test.sut_id", ondelete="CASCADE"),
            nullable=False,
        ),
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
    op.create_index("idx_action_chain_sut", "action_chain", ["sut_id"])
    op.create_index("idx_action_chain_account", "action_chain", ["account_id"])

    # Create account_subscription table with enum types
    # Enums will auto-create via create_type=True during table creation
    plan_type_enum = sa.Enum(
        "small", "medium", "large", "big_af", name="plan_type_enum", create_type=True
    )
    payment_term_enum = sa.Enum(
        "monthly", "yearly", "perpetual", name="payment_term_enum", create_type=True
    )
    payment_type_enum = sa.Enum(
        "credit_card",
        "paypal",
        "bank_transfer",
        "system",
        name="payment_type_enum",
        create_type=True,
    )

    op.create_table(
        "account_subscription",
        sa.Column("account_subscription_id", sa.String(36), primary_key=True),
        sa.Column("subscription_plan_type", plan_type_enum, nullable=False),
        sa.Column("payment_term", payment_term_enum, nullable=False),
        sa.Column("payment_type", payment_type_enum, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("account_subscription")

    # Drop enum types
    sa.Enum(name="payment_type_enum").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="payment_term_enum").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="plan_type_enum").drop(op.get_bind(), checkfirst=True)

    op.drop_index("idx_action_chain_account")
    op.drop_index("idx_action_chain_sut")
    op.drop_table("action_chain")

    op.drop_index("idx_fenrir_actions_method")
    op.drop_table("fenrir_actions")
