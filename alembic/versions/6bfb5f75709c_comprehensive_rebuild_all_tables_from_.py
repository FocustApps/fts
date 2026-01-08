"""comprehensive_rebuild_all_tables_from_models

Revision ID: 6bfb5f75709c
Revises: be7f55a6f015
Create Date: 2026-01-07 17:51:47.012884

This migration performs a comprehensive rebuild of all tables to ensure
perfect alignment between SQLAlchemy models and the database schema.

Steps:
1. Drop all tables with CASCADE (clean slate)
2. Recreate all tables from current model definitions using Base.metadata

This approach ensures:
- All columns match model definitions exactly
- All foreign keys are correctly defined
- All indexes are properly created
- No drift between models and database
"""

from alembic import op

# Import Base and all table models to ensure metadata is populated
from common.service_connections.db_service.database import Base

# Import all tables - this populates Base.metadata with all table definitions
# The __init__.py already imports all the tables we need

# Import action tables explicitly since they may not be in tables.__init__


# revision identifiers, used by Alembic.
revision = "6bfb5f75709c"
down_revision = "be7f55a6f015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Drop all tables and recreate from models."""

    # Get list of all tables currently in database
    conn = op.get_bind()

    # Drop all tables with CASCADE to handle foreign key dependencies
    # Order doesn't matter because CASCADE handles dependencies
    tables_to_drop = [
        "page_fenrir_action_association",
        "plan_suite_association",
        "suite_test_case_association",
        "system_environment_association",
        "auth_user_account_association",
        "purge",
        "audit_log",
        "entity_tag",
        "auth_token",
        "auth_user_subscription",
        "account_subscription",
        "action",
        "action_chain",
        "test_case",
        "suite",
        "plan",
        "page",
        "identifier",
        "fenrir_actions",
        "email_processor",
        "user",  # SystemUnderTestUserTable
        "environment",
        "system_under_test",
        "account",
        "auth_users",
    ]

    for table in tables_to_drop:
        op.execute(f'DROP TABLE IF EXISTS "{table}" CASCADE')

    # Recreate all tables from models using Base.metadata
    # This ensures perfect alignment with model definitions
    Base.metadata.create_all(bind=conn)


def downgrade() -> None:
    """Cannot downgrade from a comprehensive rebuild."""
    raise NotImplementedError(
        "Cannot downgrade from comprehensive rebuild. "
        "This migration drops and recreates all tables. "
        "To revert, restore from backup or use previous migration state."
    )
