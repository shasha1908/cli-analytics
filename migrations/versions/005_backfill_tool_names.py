"""Backfill tool_name from events to sessions and workflows.

Revision ID: 005_backfill_tool_names
Revises: 004_add_tool_name_isolation
Create Date: 2025-01-27
"""
from alembic import op

revision = '005_backfill_tool_names'
down_revision = '004_add_tool_name_isolation'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Update sessions.tool_name from their first event
    op.execute("""
        UPDATE sessions s
        SET tool_name = COALESCE(
            (SELECT e.tool_name FROM raw_events e WHERE e.session_id = s.id LIMIT 1),
            'default'
        )
        WHERE s.tool_name = 'default' OR s.tool_name IS NULL
    """)

    # Update workflow_runs.tool_name from their first event
    op.execute("""
        UPDATE workflow_runs w
        SET tool_name = COALESCE(
            (SELECT e.tool_name FROM raw_events e WHERE e.workflow_run_id = w.id LIMIT 1),
            'default'
        )
        WHERE w.tool_name = 'default' OR w.tool_name IS NULL
    """)

    # Update old API keys that have 'default' to match their most common tool
    # (This is a best-effort migration for existing keys)


def downgrade() -> None:
    # Reset to default
    op.execute("UPDATE sessions SET tool_name = 'default'")
    op.execute("UPDATE workflow_runs SET tool_name = 'default'")
