"""add_test_case_suite_plan_tables

Revision ID: c30626195c99
Revises: 21bbe2e2f4cc
Create Date: 2026-01-07 15:40:18.168556

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "c30626195c99"
down_revision = "21bbe2e2f4cc"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create test_case table
    # Note: Uses auth_users.id (INTEGER) not auth_users.auth_user_id
    op.create_table(
        "test_case",
        sa.Column("test_case_id", sa.String(36), primary_key=True),
        sa.Column("test_name", sa.String(255), unique=True, nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column(
            "test_type", sa.String(64), nullable=False, server_default="functional"
        ),
        sa.Column(
            "sut_id",
            sa.String(36),
            sa.ForeignKey("system_under_test.sut_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "owner_user_id",
            sa.Integer,
            sa.ForeignKey("auth_users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "account_id",
            sa.String(36),
            sa.ForeignKey("account.account_id", ondelete="CASCADE"),
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

    # Create indexes for test_case
    op.create_index("idx_test_case_sut", "test_case", ["sut_id"])
    op.create_index("idx_test_case_account", "test_case", ["account_id"])
    op.create_index("idx_test_case_owner", "test_case", ["owner_user_id"])
    op.create_index("idx_test_case_active", "test_case", ["is_active"])

    # Create suite table
    # Note: Uses auth_users.id (INTEGER) not auth_users.auth_user_id
    op.create_table(
        "suite",
        sa.Column("suite_id", sa.String(36), primary_key=True),
        sa.Column("suite_name", sa.String(255), unique=True, nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column(
            "sut_id",
            sa.String(36),
            sa.ForeignKey("system_under_test.sut_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "owner_user_id",
            sa.Integer,
            sa.ForeignKey("auth_users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "account_id",
            sa.String(36),
            sa.ForeignKey("account.account_id", ondelete="CASCADE"),
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

    # Create indexes for suite
    op.create_index("idx_suite_sut", "suite", ["sut_id"])
    op.create_index("idx_suite_account", "suite", ["account_id"])
    op.create_index("idx_suite_owner", "suite", ["owner_user_id"])
    op.create_index("idx_suite_active", "suite", ["is_active"])

    # Create plan table (has enum type)
    # Note: Uses auth_users.id (INTEGER) not auth_users.auth_user_id
    # Enum will auto-create via create_type=True during table creation
    plan_status_enum = sa.Enum(
        "active", "inactive", name="plan_status_enum", create_type=True
    )

    op.create_table(
        "plan",
        sa.Column("plan_id", sa.String(36), primary_key=True),
        sa.Column("plan_name", sa.String(255), nullable=False),
        sa.Column("suites_ids", sa.String(1024), nullable=False),  # DEPRECATED field
        sa.Column("suite_tags", sa.dialects.postgresql.JSON, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", plan_status_enum, nullable=False, server_default="active"),
        sa.Column("owner_user_id", sa.Integer, nullable=True),
        sa.Column("account_id", sa.String(36), nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("deactivated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "deactivated_by_user_id",
            sa.Integer,
            sa.ForeignKey("auth_users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )

    # Create indexes for plan
    op.create_index("idx_plan_account", "plan", ["account_id"])
    op.create_index("idx_plan_active", "plan", ["is_active"])


def downgrade() -> None:
    op.drop_index("idx_plan_active")
    op.drop_index("idx_plan_account")
    op.drop_table("plan")

    # Drop enum type
    sa.Enum(name="plan_status_enum").drop(op.get_bind(), checkfirst=True)

    op.drop_index("idx_suite_active")
    op.drop_index("idx_suite_owner")
    op.drop_index("idx_suite_account")
    op.drop_index("idx_suite_sut")
    op.drop_table("suite")

    op.drop_index("idx_test_case_active")
    op.drop_index("idx_test_case_owner")
    op.drop_index("idx_test_case_account")
    op.drop_index("idx_test_case_sut")
    op.drop_table("test_case")
