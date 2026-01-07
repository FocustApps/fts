"""add_association_tables

Revision ID: d383b58287f7
Revises: c30626195c99
Create Date: 2026-01-07 15:40:41.312491

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "d383b58287f7"
down_revision = "c30626195c99"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create auth_user_account_association
    # Note: Uses auth_users.id (INTEGER) not auth_users.auth_user_id
    op.create_table(
        "auth_user_account_association",
        sa.Column("association_id", sa.String(36), primary_key=True),
        sa.Column(
            "auth_user_id",
            sa.Integer,
            sa.ForeignKey("auth_users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "account_id",
            sa.String(36),
            sa.ForeignKey("account.account_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("role", sa.String(64), nullable=False, server_default="member"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column(
            "invited_by_user_id",
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
    op.create_index(
        "idx_auth_user_account_user", "auth_user_account_association", ["auth_user_id"]
    )
    op.create_index(
        "idx_auth_user_account_account", "auth_user_account_association", ["account_id"]
    )

    # Create suite_test_case_association
    op.create_table(
        "suite_test_case_association",
        sa.Column("association_id", sa.String(36), primary_key=True),
        sa.Column(
            "suite_id",
            sa.String(36),
            sa.ForeignKey("suite.suite_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "test_case_id",
            sa.String(36),
            sa.ForeignKey("test_case.test_case_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("execution_order", sa.Integer, nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("idx_suite_tc_suite", "suite_test_case_association", ["suite_id"])
    op.create_index(
        "idx_suite_tc_testcase", "suite_test_case_association", ["test_case_id"]
    )

    # Create plan_suite_association
    op.create_table(
        "plan_suite_association",
        sa.Column("association_id", sa.String(36), primary_key=True),
        sa.Column(
            "plan_id",
            sa.String(36),
            sa.ForeignKey("plan.plan_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "suite_id",
            sa.String(36),
            sa.ForeignKey("suite.suite_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("execution_order", sa.Integer, nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("idx_plan_suite_plan", "plan_suite_association", ["plan_id"])
    op.create_index("idx_plan_suite_suite", "plan_suite_association", ["suite_id"])

    # Create system_environment_association
    op.create_table(
        "system_environment_association",
        sa.Column("association_id", sa.String(36), primary_key=True),
        sa.Column(
            "sut_id",
            sa.String(36),
            sa.ForeignKey("system_under_test.sut_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "environment_id",
            sa.Integer,
            sa.ForeignKey("environment.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("idx_sys_env_sut", "system_environment_association", ["sut_id"])
    op.create_index(
        "idx_sys_env_env", "system_environment_association", ["environment_id"]
    )


def downgrade() -> None:
    op.drop_index("idx_sys_env_env")
    op.drop_index("idx_sys_env_sut")
    op.drop_table("system_environment_association")

    op.drop_index("idx_plan_suite_suite")
    op.drop_index("idx_plan_suite_plan")
    op.drop_table("plan_suite_association")

    op.drop_index("idx_suite_tc_testcase")
    op.drop_index("idx_suite_tc_suite")
    op.drop_table("suite_test_case_association")

    op.drop_index("idx_auth_user_account_account")
    op.drop_index("idx_auth_user_account_user")
    op.drop_table("auth_user_account_association")
