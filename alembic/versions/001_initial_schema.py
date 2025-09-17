"""Initial database schema

Revision ID: 001_initial_schema
Revises: 
Create Date: 2025-09-17 13:05:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001_initial_schema'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### Create all tables from scratch ###
    
    # Create user table
    op.create_table('user',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('username', sa.String(length=96), nullable=False),
        sa.Column('email', sa.String(length=96), nullable=False),
        sa.Column('password', sa.String(length=96), nullable=True),
        sa.Column('secret_provider', sa.String(length=96), nullable=True),
        sa.Column('secret_url', sa.String(length=1024), nullable=True),
        sa.Column('secret_name', sa.String(length=1024), nullable=True),
        sa.Column('environment_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('username')
    )
    
    # Create environment table
    op.create_table('environment',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=96), nullable=False),
        sa.Column('environment_designation', sa.String(length=80), nullable=False),
        sa.Column('url', sa.String(length=512), nullable=False),
        sa.Column('api_url', sa.String(length=512), nullable=True),
        sa.Column('status', sa.String(length=96), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('users', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    
    # Create page table
    op.create_table('page',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('page_name', sa.String(length=96), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('environments', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('identifiers', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('page_name')
    )
    
    # Create identifier table
    op.create_table('identifier',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('page_id', sa.Integer(), nullable=False),
        sa.Column('element_name', sa.String(length=96), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('locator_strategy', sa.String(length=96), nullable=False),
        sa.Column('locator_query', sa.String(length=96), nullable=False),
        sa.Column('environments', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('element_name')
    )
    
    # Create emailProcessorTable
    op.create_table('emailProcessorTable',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email_item_id', sa.Integer(), nullable=False),
        sa.Column('multi_item_email_ids', postgresql.JSONB(), nullable=True),
        sa.Column('multi_email_flag', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('multi_attachment_flag', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('test_name', sa.String(), nullable=True),
        sa.Column('requires_processing', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('system', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('last_processed_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email_item_id')
    )


def downgrade() -> None:
    # ### Drop all tables ###
    op.drop_table('emailProcessorTable')
    op.drop_table('identifier')
    op.drop_table('page')
    op.drop_table('environment')
    op.drop_table('user')