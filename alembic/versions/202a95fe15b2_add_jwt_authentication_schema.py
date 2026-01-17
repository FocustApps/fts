"""add_jwt_authentication_schema

ONE-WAY MIGRATION - NO DOWNGRADE

This migration converts the authentication system from plaintext tokens
to JWT-based authentication with bcrypt password hashing. Database will
be wiped during deployment - no backward compatibility guaranteed.

Revision ID: 202a95fe15b2
Revises: 001_initial_complete_schema
Create Date: 2026-01-09 22:40:10.532033

"""

# revision identifiers, used by Alembic.
revision = "202a95fe15b2"
down_revision = "001_initial_complete_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    JWT authentication schema setup - NO-OP for fresh database.

    This migration was created to convert legacy authentication to JWT.
    However, the 001_initial_complete_schema migration already creates
    all tables (auth_users, auth_tokens, revoked_tokens) with the correct
    JWT schema from the SQLAlchemy models.

    This migration is kept for historical reference but performs no operations.
    """
    pass  # All tables already created with correct schema


def downgrade() -> None:
    """
    NO DOWNGRADE - This is a one-way migration.

    The database will be wiped during deployment. Rolling back is not supported
    as there is no way to convert JWT refresh token hashes back to plaintext tokens.
    """
    raise NotImplementedError(
        "Downgrade not supported for JWT authentication migration. "
        "Database must be recreated from scratch to revert."
    )
