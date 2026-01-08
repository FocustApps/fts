"""merge_heads

Revision ID: 5b3a509eff29
Revises: 0ec36ea2a851, 301ad4c5d899
Create Date: 2026-01-07 16:46:55.354250

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '5b3a509eff29'
down_revision = ('0ec36ea2a851', '301ad4c5d899')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
