"""Add tool_name for tenant isolation.

Revision ID: 004
Revises: 003
Create Date: 2025-01-27
"""
from alembic import op
import sqlalchemy as sa

revision = '004'
down_revision = '003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add tool_name to api_keys
    op.add_column('api_keys', sa.Column('tool_name', sa.String(128), nullable=True))
    op.execute("UPDATE api_keys SET tool_name = 'default' WHERE tool_name IS NULL")
    op.alter_column('api_keys', 'tool_name', nullable=False)

    # Add tool_name to experiments
    op.add_column('experiments', sa.Column('tool_name', sa.String(128), nullable=True))
    op.execute("UPDATE experiments SET tool_name = 'default' WHERE tool_name IS NULL")
    op.alter_column('experiments', 'tool_name', nullable=False)

    # Add tool_name to sessions
    op.add_column('sessions', sa.Column('tool_name', sa.String(128), nullable=True))
    op.execute("UPDATE sessions SET tool_name = 'default' WHERE tool_name IS NULL")
    op.alter_column('sessions', 'tool_name', nullable=False)

    # Add tool_name to workflow_runs
    op.add_column('workflow_runs', sa.Column('tool_name', sa.String(128), nullable=True))
    op.execute("UPDATE workflow_runs SET tool_name = 'default' WHERE tool_name IS NULL")
    op.alter_column('workflow_runs', 'tool_name', nullable=False)

    # Remove unique constraint on experiment name (now unique per tool)
    op.drop_constraint('experiments_name_key', 'experiments', type_='unique')
    op.create_unique_constraint('experiments_tool_name_key', 'experiments', ['tool_name', 'name'])


def downgrade() -> None:
    op.drop_constraint('experiments_tool_name_key', 'experiments', type_='unique')
    op.create_unique_constraint('experiments_name_key', 'experiments', ['name'])
    op.drop_column('workflow_runs', 'tool_name')
    op.drop_column('sessions', 'tool_name')
    op.drop_column('experiments', 'tool_name')
    op.drop_column('api_keys', 'tool_name')
