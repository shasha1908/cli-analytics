"""Add recommendations and experiments tables

Revision ID: 003_recommendations_experiments
Revises: 002_api_keys
Create Date: 2025-01-25

"""
from typing import Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "003_recommendations_experiments"
down_revision: Union[str, None] = "002_api_keys"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Experiments table for A/B testing
    op.create_table(
        "experiments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(128), unique=True, nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("variants", JSONB(), nullable=False),  # ["control", "variant_a"]
        sa.Column("target_commands", JSONB(), nullable=True),  # ["deploy", "build"]
        sa.Column("traffic_pct", sa.Integer(), default=100),  # % of users in experiment
        sa.Column("is_active", sa.Boolean(), default=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Variant assignments - consistent assignment per actor
    op.create_table(
        "variant_assignments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("experiment_id", sa.Integer(), sa.ForeignKey("experiments.id"), nullable=False),
        sa.Column("actor_id_hash", sa.String(64), nullable=False),
        sa.Column("variant", sa.String(64), nullable=False),
        sa.Column("assigned_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("experiment_id", "actor_id_hash", name="uq_experiment_actor"),
    )

    # Add experiment tracking to events
    op.add_column("raw_events", sa.Column("experiment_id", sa.Integer(), nullable=True))
    op.add_column("raw_events", sa.Column("variant", sa.String(64), nullable=True))


def downgrade() -> None:
    op.drop_column("raw_events", "variant")
    op.drop_column("raw_events", "experiment_id")
    op.drop_table("variant_assignments")
    op.drop_table("experiments")
