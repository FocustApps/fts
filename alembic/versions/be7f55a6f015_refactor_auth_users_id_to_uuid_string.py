"""refactor_auth_users_id_to_uuid_string

Revision ID: be7f55a6f015
Revises: edab8f775757
Create Date: 2026-01-07 17:16:27.910855

This migration refactors auth_users table to use auth_user_id (String UUID)
instead of id (Integer autoincrement). This requires dropping and recreating
auth_users and all dependent tables due to foreign key constraints.

Since the database is fresh, we're using a clean slate approach:
1. Drop all tables that reference auth_users
2. Drop auth_users table
3. Recreate auth_users with auth_user_id
4. Recreate all dependent tables with updated foreign keys
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision = "be7f55a6f015"
down_revision = "edab8f775757"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop tables in correct dependency order (only those that exist)
    # Drop association tables first
    op.execute("DROP TABLE IF EXISTS suite_test_case_association CASCADE")
    op.execute("DROP TABLE IF EXISTS plan_suite_association CASCADE")

    # Drop tables that reference auth_users
    op.execute("DROP TABLE IF EXISTS auth_tokens CASCADE")
    op.execute("DROP TABLE IF EXISTS auth_user_account_association CASCADE")
    op.execute("DROP TABLE IF EXISTS entity_tag CASCADE")
    op.execute("DROP TABLE IF EXISTS action_chain CASCADE")
    op.execute("DROP TABLE IF EXISTS test_case CASCADE")
    op.execute("DROP TABLE IF EXISTS suite CASCADE")
    op.execute("DROP TABLE IF EXISTS plan CASCADE")
    op.execute("DROP TABLE IF EXISTS identifier CASCADE")
    op.execute("DROP TABLE IF EXISTS page CASCADE")
    op.execute("DROP TABLE IF EXISTS audit_log CASCADE")
    op.execute("DROP TABLE IF EXISTS environment CASCADE")
    op.execute("DROP TABLE IF EXISTS system_under_test CASCADE")

    # Drop auth_users table
    op.execute("DROP TABLE IF EXISTS auth_users CASCADE")

    # Recreate auth_users with auth_user_id as primary key (String UUID)
    op.create_table(
        "auth_users",
        sa.Column("auth_user_id", sa.String(36), primary_key=True),
        sa.Column("email", sa.String(255), unique=True, nullable=False),
        sa.Column("username", sa.String(96), nullable=True),
        sa.Column("first_name", sa.String(255), nullable=True),
        sa.Column("last_name", sa.String(255), nullable=True),
        sa.Column("current_token", sa.String(64), nullable=True),
        sa.Column("token_expires_at", sa.DateTime(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        sa.Column("is_admin", sa.Boolean(), nullable=False, default=False),
        sa.Column("is_super_admin", sa.Boolean(), nullable=False, default=False),
        sa.Column("multi_account_user", sa.Boolean(), nullable=False, default=False),
        sa.Column("account_ids", sa.String(1024), nullable=True),
        sa.Column("user_subscription_id", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("last_login_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )

    # Create indexes for auth_users
    op.create_index("idx_auth_users_email", "auth_users", ["email"], unique=True)
    op.create_index("idx_auth_users_username", "auth_users", ["username"], unique=True)
    op.create_index("idx_auth_users_pk", "auth_users", ["auth_user_id"])

    # Recreate auth_tokens
    op.create_table(
        "auth_tokens",
        sa.Column("token_id", sa.String(36), primary_key=True),
        sa.Column(
            "auth_user_id",
            sa.String(36),
            sa.ForeignKey("auth_users.auth_user_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("token_value", sa.String(64), unique=True, nullable=False),
        sa.Column("token_expires_at", sa.DateTime(), nullable=False),
        sa.Column("device_info", sa.String(255), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("last_used_at", sa.DateTime(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
    )
    op.create_index("idx_auth_tokens_pk", "auth_tokens", ["token_id"])
    op.create_index("idx_auth_tokens_user", "auth_tokens", ["auth_user_id"])

    # Recreate auth_user_account_association
    op.create_table(
        "auth_user_account_association",
        sa.Column("association_id", sa.String(36), primary_key=True),
        sa.Column(
            "auth_user_id",
            sa.String(36),
            sa.ForeignKey("auth_users.auth_user_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "account_id",
            sa.String(36),
            sa.ForeignKey("account.account_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("role", sa.String(64), nullable=False, default="member"),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        sa.Column(
            "invited_by_user_id",
            sa.String(36),
            sa.ForeignKey("auth_users.auth_user_id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("auth_user_id", "account_id", name="uq_user_account"),
    )
    op.create_index(
        "idx_user_account_user", "auth_user_account_association", ["auth_user_id"]
    )
    op.create_index(
        "idx_user_account_account", "auth_user_account_association", ["account_id"]
    )

    # Recreate system_under_test with updated FK
    op.create_table(
        "system_under_test",
        sa.Column("sut_id", sa.String(36), primary_key=True),
        sa.Column("system_name", sa.String(255), unique=True, nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "owner_user_id",
            sa.String(36),
            sa.ForeignKey("auth_users.auth_user_id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "account_id",
            sa.String(36),
            sa.ForeignKey("account.account_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        sa.Column("deactivated_at", sa.DateTime(), nullable=True),
        sa.Column(
            "deactivated_by_user_id",
            sa.String(36),
            sa.ForeignKey("auth_users.auth_user_id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index("idx_sut_name", "system_under_test", ["system_name"], unique=True)

    # Recreate test_case with updated FK
    op.create_table(
        "test_case",
        sa.Column("test_case_id", sa.String(36), primary_key=True),
        sa.Column("test_name", sa.String(255), unique=True, nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "sut_id",
            sa.String(36),
            sa.ForeignKey("system_under_test.sut_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "owner_user_id",
            sa.String(36),
            sa.ForeignKey("auth_users.auth_user_id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "account_id",
            sa.String(36),
            sa.ForeignKey("account.account_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        sa.Column("deactivated_at", sa.DateTime(), nullable=True),
        sa.Column(
            "deactivated_by_user_id",
            sa.String(36),
            sa.ForeignKey("auth_users.auth_user_id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index("idx_test_case_name", "test_case", ["test_name"], unique=True)

    # Recreate suite with updated FK
    op.create_table(
        "suite",
        sa.Column("suite_id", sa.String(36), primary_key=True),
        sa.Column("suite_name", sa.String(255), unique=True, nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "sut_id",
            sa.String(36),
            sa.ForeignKey("system_under_test.sut_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "owner_user_id",
            sa.String(36),
            sa.ForeignKey("auth_users.auth_user_id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "account_id",
            sa.String(36),
            sa.ForeignKey("account.account_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        sa.Column("deactivated_at", sa.DateTime(), nullable=True),
        sa.Column(
            "deactivated_by_user_id",
            sa.String(36),
            sa.ForeignKey("auth_users.auth_user_id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index("idx_suite_name", "suite", ["suite_name"], unique=True)

    # Recreate plan with updated FK (using simple string for status to avoid enum issues)
    op.create_table(
        "plan",
        sa.Column("plan_id", sa.String(36), primary_key=True),
        sa.Column("plan_name", sa.String(255), unique=True, nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, default="active"),
        sa.Column(
            "owner_user_id",
            sa.String(36),
            sa.ForeignKey("auth_users.auth_user_id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("account_id", sa.String(36), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        sa.Column("deactivated_at", sa.DateTime(), nullable=True),
        sa.Column(
            "deactivated_by_user_id",
            sa.String(36),
            sa.ForeignKey("auth_users.auth_user_id", ondelete="SET NULL"),
            nullable=True,
        ),
    )

    # Recreate action_chain with updated FK
    op.create_table(
        "action_chain",
        sa.Column("action_chain_id", sa.String(36), primary_key=True),
        sa.Column("chain_name", sa.String(255), unique=True, nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("action_steps", JSONB, nullable=False),
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
            sa.String(36),
            sa.ForeignKey("auth_users.auth_user_id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        sa.Column("deactivated_at", sa.DateTime(), nullable=True),
        sa.Column(
            "deactivated_by_user_id",
            sa.String(36),
            sa.ForeignKey("auth_users.auth_user_id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )

    # Recreate entity_tag with updated FK
    op.create_table(
        "entity_tag",
        sa.Column("tag_id", sa.String(36), primary_key=True),
        sa.Column("entity_type", sa.String(64), nullable=False, index=True),
        sa.Column("entity_id", sa.String(36), nullable=False, index=True),
        sa.Column("tag_name", sa.String(128), nullable=False, index=True),
        sa.Column("tag_category", sa.String(64), nullable=False, index=True),
        sa.Column("tag_value", sa.String(255), nullable=True),
        sa.Column(
            "account_id",
            sa.String(36),
            sa.ForeignKey("account.account_id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "created_by_user_id",
            sa.String(36),
            sa.ForeignKey("auth_users.auth_user_id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        sa.Column("deactivated_at", sa.DateTime(), nullable=True),
        sa.Column(
            "deactivated_by_user_id",
            sa.String(36),
            sa.ForeignKey("auth_users.auth_user_id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )

    # Recreate page with updated FK
    op.create_table(
        "page",
        sa.Column("page_id", sa.Integer(), primary_key=True),
        sa.Column("page_name", sa.String(96), unique=True, nullable=False),
        sa.Column("page_url", sa.String(1024), nullable=False),
        sa.Column("environments", JSONB, nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        sa.Column("deactivated_at", sa.DateTime(), nullable=True),
        sa.Column(
            "deactivated_by_user_id",
            sa.String(36),
            sa.ForeignKey("auth_users.auth_user_id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )

    # Recreate identifier with updated FK
    op.create_table(
        "identifier",
        sa.Column("identifier_id", sa.Integer(), primary_key=True),
        sa.Column(
            "page_id",
            sa.Integer(),
            sa.ForeignKey("page.page_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("element_name", sa.String(96), unique=True, nullable=False),
        sa.Column("locator_strategy", sa.String(96), nullable=False),
        sa.Column("locator_query", sa.String(96), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        sa.Column("deactivated_at", sa.DateTime(), nullable=True),
        sa.Column(
            "deactivated_by_user_id",
            sa.String(36),
            sa.ForeignKey("auth_users.auth_user_id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )

    # Recreate environment with updated FK
    op.create_table(
        "environment",
        sa.Column("environment_id", sa.String(36), primary_key=True),
        sa.Column("environment_name", sa.String(255), unique=True, nullable=False),
        sa.Column("base_url", sa.String(1024), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        sa.Column(
            "created_by_user_id",
            sa.String(36),
            sa.ForeignKey("auth_users.auth_user_id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )

    # Recreate audit_log with updated FK
    op.create_table(
        "audit_log",
        sa.Column("log_id", sa.String(36), primary_key=True),
        sa.Column("entity_type", sa.String(64), nullable=False),
        sa.Column("entity_id", sa.String(36), nullable=False),
        sa.Column("action", sa.String(64), nullable=False),
        sa.Column(
            "user_id",
            sa.String(36),
            sa.ForeignKey("auth_users.auth_user_id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("changes", JSONB, nullable=True),
        sa.Column("timestamp", sa.DateTime(), nullable=False),
    )

    # Recreate system_under_test_user with updated FK
    op.create_table(
        "system_under_test_user",
        sa.Column("sut_user_id", sa.String(36), primary_key=True),
        sa.Column(
            "sut_id",
            sa.String(36),
            sa.ForeignKey("system_under_test.sut_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("username", sa.String(255), nullable=False),
        sa.Column("password", sa.String(255), nullable=False),
        sa.Column(
            "added_by_user_id",
            sa.String(36),
            sa.ForeignKey("auth_users.auth_user_id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )

    # Recreate association tables
    op.create_table(
        "suite_test_case_association",
        sa.Column(
            "suite_id",
            sa.String(36),
            sa.ForeignKey("suite.suite_id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "test_case_id",
            sa.String(36),
            sa.ForeignKey("test_case.test_case_id", ondelete="CASCADE"),
            primary_key=True,
        ),
    )

    op.create_table(
        "plan_suite_association",
        sa.Column(
            "plan_id",
            sa.String(36),
            sa.ForeignKey("plan.plan_id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "suite_id",
            sa.String(36),
            sa.ForeignKey("suite.suite_id", ondelete="CASCADE"),
            primary_key=True,
        ),
    )


def downgrade() -> None:
    # Drop all tables in reverse order
    op.drop_table("plan_suite_association")
    op.drop_table("suite_test_case_association")
    op.drop_table("system_under_test_user")
    op.drop_table("audit_log")
    op.drop_table("environment")
    op.drop_table("identifier")
    op.drop_table("page")
    op.drop_table("entity_tag")
    op.drop_table("action_chain")
    op.drop_table("plan")
    op.drop_table("suite")
    op.drop_table("test_case")
    op.drop_table("system_under_test")
    op.drop_table("auth_user_account_association")
    op.drop_table("auth_tokens")

    # Recreate auth_users with old structure (id as Integer)
    op.create_table(
        "auth_users",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("email", sa.String(255), unique=True, nullable=False),
        sa.Column("username", sa.String(255), unique=True, nullable=False),
        sa.Column("first_name", sa.String(255), nullable=False),
        sa.Column("last_name", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        sa.Column("is_admin", sa.Boolean(), nullable=False, default=False),
        sa.Column("is_super_admin", sa.Boolean(), nullable=False, default=False),
        sa.Column("current_token", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )

    # Note: Would need to recreate all dependent tables here in proper order
    # Omitted for brevity as downgrade is not expected to be used
