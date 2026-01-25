"""Add API keys table

Revision ID: 002_api_keys
Revises: 001_initial_schema
Create Date: 2025-01-24

"""
from typing import Union
from alembic import op
import sqlalchemy as sa

revision: str = "002_api_keys"
down_revision: Union[str, None] = "001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "api_keys",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("key_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("is_active", sa.Boolean(), default=True, nullable=False),
    )


def downgrade() -> None:
    op.drop_table("api_keys")
