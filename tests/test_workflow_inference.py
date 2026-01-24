"""Tests for workflow inference logic."""
import pytest
from datetime import datetime, timedelta, timezone

from app.infer import (
    infer_workflows,
    is_entry_command,
    is_terminal_command,
    determine_outcome,
    infer_workflow_name,
    get_command_fingerprint,
)
from app.models import RawEvent, Session as SessionModel
from app.privacy import hash_identifier


class TestWorkflowHelpers:
    """Test helper functions for workflow inference."""

    def test_entry_commands(self):
        """Test entry command detection."""
        assert is_entry_command(["terraform", "init"]) is True
        assert is_entry_command(["npm", "login"]) is True
        assert is_entry_command(["cli", "setup"]) is True
        assert is_entry_command(["tool", "config"]) is True
        assert is_entry_command(["app", "create"]) is True

        assert is_entry_command(["terraform", "plan"]) is False
        assert is_entry_command(["npm", "install"]) is False
        assert is_entry_command([]) is False

    def test_terminal_commands(self):
        """Test terminal command detection."""
        assert is_terminal_command(["terraform", "apply"]) is True
        assert is_terminal_command(["npm", "publish"]) is True
        assert is_terminal_command(["docker", "push"]) is True
        assert is_terminal_command(["kubectl", "deploy"]) is False  # deploy not in TERMINAL_COMMANDS for kubectl
        assert is_terminal_command(["npm", "test"]) is True
        assert is_terminal_command(["npm", "build"]) is True

        assert is_terminal_command(["terraform", "init"]) is False
        assert is_terminal_command(["npm", "install"]) is False
        assert is_terminal_command([]) is False

    def test_determine_outcome(self):
        """Test outcome determination logic."""
        assert determine_outcome(exit_code=0, is_terminal=True, is_timeout=False) == "SUCCESS"
        assert determine_outcome(exit_code=1, is_terminal=True, is_timeout=False) == "FAILED"
        assert determine_outcome(exit_code=0, is_terminal=False, is_timeout=False) == "ABANDONED"
        assert determine_outcome(exit_code=0, is_terminal=True, is_timeout=True) == "ABANDONED"
        assert determine_outcome(exit_code=None, is_terminal=True, is_timeout=False) == "ABANDONED"

    def test_command_fingerprint(self):
        """Test command fingerprint generation."""
        assert get_command_fingerprint(["npm", "test"], []) == "npm/test"
        assert get_command_fingerprint(["npm", "test"], ["--coverage"]) == "npm/test[--coverage]"
        assert get_command_fingerprint(["npm", "test"], ["--coverage", "-v"]) == "npm/test[--coverage,-v]"


class TestWorkflowInference:
    """Test workflow inference logic."""

    def test_simple_workflow_success(self, in_memory_db):
        """Test inference of a successful workflow."""
        db = in_memory_db
        base_time = datetime(2025, 1, 24, 10, 0, 0, tzinfo=timezone.utc)

        # Create a session
        session = SessionModel(
            actor_id_hash=hash_identifier("user-1"),
            machine_id_hash=hash_identifier("machine-1"),
            ci_detected=False,
            started_at=base_time,
            event_count=3,
        )
        db.add(session)
        db.flush()

        # Create events for a terraform workflow
        commands = [
            (["terraform", "init"], 0),
            (["terraform", "plan"], 0),
            (["terraform", "apply"], 0),  # Terminal with success
        ]

        raw_events = []
        for i, (cmd, exit_code) in enumerate(commands):
            raw_event = RawEvent(
                id=i + 1,
                event_id=f"evt_{i}",
                timestamp=base_time + timedelta(minutes=i * 5),
                tool_name=cmd[0],
                tool_version="1.7.0",
                command_path=cmd,
                flags_present=[],
                exit_code=exit_code,
                actor_id_hash=hash_identifier("user-1"),
                machine_id_hash=hash_identifier("machine-1"),
                ci_detected=False,
                session_id=session.id,
            )
            db.add(raw_event)
            raw_events.append(raw_event)
        db.commit()

        # Run inference
        session_events = {session.id: raw_events}
        workflows_created = infer_workflows(db, session_events)
        db.commit()

        # Should create one workflow
        assert workflows_created == 1

        # Check workflow details
        from app.models import WorkflowRun
        workflow = db.query(WorkflowRun).first()
        assert workflow is not None
        assert workflow.outcome == "SUCCESS"
        assert workflow.workflow_name == "apply_workflow"
        assert workflow.step_count == 3

    def test_workflow_failure(self, in_memory_db):
        """Test inference of a failed workflow."""
        db = in_memory_db
        base_time = datetime(2025, 1, 24, 10, 0, 0, tzinfo=timezone.utc)

        session = SessionModel(
            actor_id_hash=hash_identifier("user-1"),
            machine_id_hash=hash_identifier("machine-1"),
            ci_detected=False,
            started_at=base_time,
            event_count=2,
        )
        db.add(session)
        db.flush()

        commands = [
            (["npm", "install"], 0),
            (["npm", "test"], 1),  # Terminal with failure
        ]

        raw_events = []
        for i, (cmd, exit_code) in enumerate(commands):
            raw_event = RawEvent(
                id=i + 1,
                event_id=f"evt_{i}",
                timestamp=base_time + timedelta(minutes=i * 5),
                tool_name=cmd[0],
                tool_version="10.0.0",
                command_path=cmd,
                flags_present=[],
                exit_code=exit_code,
                actor_id_hash=hash_identifier("user-1"),
                machine_id_hash=hash_identifier("machine-1"),
                ci_detected=False,
                session_id=session.id,
            )
            db.add(raw_event)
            raw_events.append(raw_event)
        db.commit()

        session_events = {session.id: raw_events}
        workflows_created = infer_workflows(db, session_events)
        db.commit()

        from app.models import WorkflowRun
        workflow = db.query(WorkflowRun).first()
        assert workflow is not None
        assert workflow.outcome == "FAILED"
        assert workflow.workflow_name == "test_workflow"

    def test_entry_command_starts_new_workflow(self, in_memory_db):
        """Test that entry commands start a new workflow."""
        db = in_memory_db
        base_time = datetime(2025, 1, 24, 10, 0, 0, tzinfo=timezone.utc)

        session = SessionModel(
            actor_id_hash=hash_identifier("user-1"),
            machine_id_hash=hash_identifier("machine-1"),
            ci_detected=False,
            started_at=base_time,
            event_count=4,
        )
        db.add(session)
        db.flush()

        # First workflow
        commands = [
            (["terraform", "init"], 0),
            (["terraform", "apply"], 0),
            # Entry command starts new workflow
            (["terraform", "init"], 0),
            (["terraform", "apply"], 0),
        ]

        raw_events = []
        for i, (cmd, exit_code) in enumerate(commands):
            raw_event = RawEvent(
                id=i + 1,
                event_id=f"evt_{i}",
                timestamp=base_time + timedelta(minutes=i * 5),
                tool_name=cmd[0],
                tool_version="1.7.0",
                command_path=cmd,
                flags_present=[],
                exit_code=exit_code,
                actor_id_hash=hash_identifier("user-1"),
                machine_id_hash=hash_identifier("machine-1"),
                ci_detected=False,
                session_id=session.id,
            )
            db.add(raw_event)
            raw_events.append(raw_event)
        db.commit()

        session_events = {session.id: raw_events}
        workflows_created = infer_workflows(db, session_events)
        db.commit()

        # Should create 2 workflows (init starts a new one)
        assert workflows_created == 2

    def test_infer_workflow_name(self):
        """Test workflow name inference from events."""
        base_time = datetime(2025, 1, 24, 10, 0, 0, tzinfo=timezone.utc)

        # Create mock events
        events = [
            RawEvent(
                id=1,
                event_id="e1",
                timestamp=base_time,
                tool_name="npm",
                command_path=["npm", "install"],
                flags_present=[],
                actor_id_hash="a",
                machine_id_hash="m",
                ci_detected=False,
            ),
            RawEvent(
                id=2,
                event_id="e2",
                timestamp=base_time,
                tool_name="npm",
                command_path=["npm", "build"],
                flags_present=[],
                actor_id_hash="a",
                machine_id_hash="m",
                ci_detected=False,
            ),
            RawEvent(
                id=3,
                event_id="e3",
                timestamp=base_time,
                tool_name="npm",
                command_path=["npm", "deploy"],
                flags_present=[],
                actor_id_hash="a",
                machine_id_hash="m",
                ci_detected=False,
            ),
        ]

        name = infer_workflow_name(events)
        # Should use the most common terminal command
        assert "deploy" in name or "build" in name
