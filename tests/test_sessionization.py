"""Tests for sessionization logic."""
import pytest
from datetime import datetime, timedelta, timezone

from app.infer import sessionize_events
from app.models import RawEvent, InferenceCursor
from app.privacy import hash_identifier


class TestSessionization:
    """Test session grouping logic."""

    def test_same_actor_machine_single_session(self, in_memory_db, sample_events):
        """Events from same actor/machine within timeout form one session."""
        db = in_memory_db

        # Insert events
        raw_events = []
        for i, event in enumerate(sample_events):
            raw_event = RawEvent(
                id=i + 1,
                event_id=f"evt_{i}",
                timestamp=event.timestamp,
                tool_name=event.tool_name,
                tool_version=event.tool_version,
                command_path=event.command_path,
                flags_present=event.flags_present,
                exit_code=event.exit_code,
                duration_ms=event.duration_ms,
                actor_id_hash=hash_identifier(event.actor_id),
                machine_id_hash=hash_identifier(event.machine_id),
                ci_detected=event.ci_detected,
            )
            db.add(raw_event)
            raw_events.append(raw_event)
        db.commit()

        # Sessionize
        session_events = sessionize_events(db, raw_events)

        # Should create exactly one session
        assert len(session_events) == 1

        # All events should be in the same session
        session_id = list(session_events.keys())[0]
        assert len(session_events[session_id]) == 3

    def test_timeout_creates_new_session(self, in_memory_db):
        """Events separated by > 30 min should create separate sessions."""
        db = in_memory_db
        base_time = datetime(2025, 1, 24, 10, 0, 0, tzinfo=timezone.utc)

        # Create events with 40 minute gap
        raw_events = []
        for i, minutes in enumerate([0, 5, 45, 50]):  # Gap between 5 and 45
            raw_event = RawEvent(
                id=i + 1,
                event_id=f"evt_{i}",
                timestamp=base_time + timedelta(minutes=minutes),
                tool_name="npm",
                tool_version="10.0.0",
                command_path=["npm", "test"],
                flags_present=[],
                exit_code=0,
                actor_id_hash=hash_identifier("user-1"),
                machine_id_hash=hash_identifier("machine-1"),
                ci_detected=False,
            )
            db.add(raw_event)
            raw_events.append(raw_event)
        db.commit()

        session_events = sessionize_events(db, raw_events)

        # Should create 2 sessions
        assert len(session_events) == 2

    def test_session_hint_change_creates_new_session(self, in_memory_db):
        """Changing session_hint should force a new session."""
        db = in_memory_db
        base_time = datetime(2025, 1, 24, 10, 0, 0, tzinfo=timezone.utc)

        raw_events = []
        hints = ["session-a", "session-a", "session-b", "session-b"]

        for i, hint in enumerate(hints):
            raw_event = RawEvent(
                id=i + 1,
                event_id=f"evt_{i}",
                timestamp=base_time + timedelta(minutes=i * 2),
                tool_name="terraform",
                tool_version="1.7.0",
                command_path=["terraform", "plan"],
                flags_present=[],
                exit_code=0,
                actor_id_hash=hash_identifier("user-1"),
                machine_id_hash=hash_identifier("machine-1"),
                session_hint=hint,
                ci_detected=False,
            )
            db.add(raw_event)
            raw_events.append(raw_event)
        db.commit()

        session_events = sessionize_events(db, raw_events)

        # Should create 2 sessions (one per hint)
        assert len(session_events) == 2

    def test_ci_change_creates_new_session(self, in_memory_db):
        """Changing ci_detected should force a new session."""
        db = in_memory_db
        base_time = datetime(2025, 1, 24, 10, 0, 0, tzinfo=timezone.utc)

        raw_events = []
        ci_flags = [False, False, True, True]

        for i, ci in enumerate(ci_flags):
            raw_event = RawEvent(
                id=i + 1,
                event_id=f"evt_{i}",
                timestamp=base_time + timedelta(minutes=i * 2),
                tool_name="npm",
                tool_version="10.0.0",
                command_path=["npm", "build"],
                flags_present=[],
                exit_code=0,
                actor_id_hash=hash_identifier("user-1"),
                machine_id_hash=hash_identifier("machine-1"),
                ci_detected=ci,
            )
            db.add(raw_event)
            raw_events.append(raw_event)
        db.commit()

        session_events = sessionize_events(db, raw_events)

        # Should create 2 sessions (one per CI flag value)
        assert len(session_events) == 2

    def test_different_actors_different_sessions(self, in_memory_db, multi_session_events):
        """Different actors should have separate sessions."""
        db = in_memory_db

        raw_events = []
        for i, event in enumerate(multi_session_events):
            raw_event = RawEvent(
                id=i + 1,
                event_id=f"evt_{i}",
                timestamp=event.timestamp,
                tool_name=event.tool_name,
                tool_version="1.0.0",
                command_path=event.command_path,
                flags_present=[],
                exit_code=event.exit_code,
                actor_id_hash=hash_identifier(event.actor_id),
                machine_id_hash=hash_identifier(event.machine_id),
                ci_detected=event.ci_detected,
            )
            db.add(raw_event)
            raw_events.append(raw_event)
        db.commit()

        session_events = sessionize_events(db, raw_events)

        # Should have 3 sessions:
        # 1. User A's first session
        # 2. User B's session
        # 3. User A's second session (after timeout)
        assert len(session_events) == 3
