"""Initial schema

Revision ID: 001_initial_schema
Revises:
Create Date: 2025-01-24

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # raw_events table
    op.create_table(
        "raw_events",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("event_id", sa.String(64), nullable=False, unique=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("tool_name", sa.String(128), nullable=False),
        sa.Column("tool_version", sa.String(64), nullable=True),
        sa.Column("command_path", postgresql.JSONB(), nullable=False),
        sa.Column("flags_present", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("exit_code", sa.Integer(), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("error_type", sa.String(256), nullable=True),
        sa.Column("actor_id_hash", sa.String(64), nullable=False),
        sa.Column("machine_id_hash", sa.String(64), nullable=False),
        sa.Column("session_hint", sa.String(128), nullable=True),
        sa.Column("ci_detected", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("ingested_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("session_id", sa.BigInteger(), nullable=True),
        sa.Column("workflow_run_id", sa.BigInteger(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_raw_events_timestamp", "raw_events", ["timestamp"])
    op.create_index("ix_raw_events_actor_machine", "raw_events", ["actor_id_hash", "machine_id_hash"])
    op.create_index("ix_raw_events_session_id", "raw_events", ["session_id"])
    op.create_index("ix_raw_events_ingested_at", "raw_events", ["ingested_at"])

    # sessions table
    op.create_table(
        "sessions",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("actor_id_hash", sa.String(64), nullable=False),
        sa.Column("machine_id_hash", sa.String(64), nullable=False),
        sa.Column("session_hint", sa.String(128), nullable=True),
        sa.Column("ci_detected", sa.Boolean(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("event_count", sa.Integer(), nullable=False, server_default="0"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sessions_actor_machine", "sessions", ["actor_id_hash", "machine_id_hash"])

    # workflow_runs table
    op.create_table(
        "workflow_runs",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("session_id", sa.BigInteger(), sa.ForeignKey("sessions.id"), nullable=False),
        sa.Column("workflow_name", sa.String(128), nullable=False),
        sa.Column("outcome", sa.String(32), nullable=False),  # SUCCESS, FAILED, ABANDONED
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("step_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("command_fingerprint", sa.Text(), nullable=True),  # serialized path for hot-path analysis
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_workflow_runs_session_id", "workflow_runs", ["session_id"])
    op.create_index("ix_workflow_runs_workflow_name", "workflow_runs", ["workflow_name"])
    op.create_index("ix_workflow_runs_outcome", "workflow_runs", ["outcome"])

    # workflow_steps table
    op.create_table(
        "workflow_steps",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("workflow_run_id", sa.BigInteger(), sa.ForeignKey("workflow_runs.id"), nullable=False),
        sa.Column("event_id", sa.BigInteger(), sa.ForeignKey("raw_events.id"), nullable=False),
        sa.Column("step_order", sa.Integer(), nullable=False),
        sa.Column("command_fingerprint", sa.String(512), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_workflow_steps_workflow_run_id", "workflow_steps", ["workflow_run_id"])

    # inference_cursor table
    op.create_table(
        "inference_cursor",
        sa.Column("id", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("last_event_id", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    # Insert initial cursor row
    op.execute("INSERT INTO inference_cursor (id, last_event_id) VALUES (1, 0)")


def downgrade() -> None:
    op.drop_table("inference_cursor")
    op.drop_table("workflow_steps")
    op.drop_table("workflow_runs")
    op.drop_table("sessions")
    op.drop_table("raw_events")
