"""add_account_table_only

Revision ID: b87e1a3b751b
Revises: 9eb266ae2f1b
Create Date: 2026-01-07 15:25:19.656612

"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "b87e1a3b751b"
down_revision = "14f5c85198e4"  # Point to the last successfully applied migration
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create account table if it doesn't exist
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS account (
            account_id VARCHAR(36) PRIMARY KEY,
            account_name VARCHAR(255) UNIQUE NOT NULL,
            owner_user_id VARCHAR(36) UNIQUE,
            is_active BOOLEAN DEFAULT TRUE NOT NULL,
            logo_url VARCHAR(512),
            primary_contact VARCHAR(36),
            subscription_id VARCHAR(36),
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP
        )
    """
    )


def downgrade() -> None:
    op.drop_table("account")
