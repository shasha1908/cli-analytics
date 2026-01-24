"""Sessionization and workflow inference logic."""
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy import func, update
from sqlalchemy.orm import Session as DBSession

from app.db import get_db
from app.models import InferenceCursor, RawEvent, WorkflowRun, WorkflowStep
from app.models import Session as SessionModel
from app.schemas import InferResponse
from app.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter()

# Entry commands that start a new workflow
ENTRY_COMMANDS = {"init", "login", "setup", "config", "create", "new", "start", "begin", "configure"}

# Terminal commands that end a workflow
TERMINAL_COMMANDS = {"deploy", "apply", "release", "publish", "scan", "test", "build", "push", "run", "execute"}


def get_command_fingerprint(command_path: list[str], flags: list[str]) -> str:
    """Create a fingerprint from command path and flags."""
    path_str = "/".join(command_path)
    if flags:
        flags_str = ",".join(sorted(flags))
        return f"{path_str}[{flags_str}]"
    return path_str


def is_entry_command(command_path: list[str]) -> bool:
    """Check if command is an entry command."""
    if not command_path:
        return False
    # Check the last element (the actual subcommand)
    last_cmd = command_path[-1].lower()
    return last_cmd in ENTRY_COMMANDS


def is_terminal_command(command_path: list[str]) -> bool:
    """Check if command is a terminal command."""
    if not command_path:
        return False
    last_cmd = command_path[-1].lower()
    return last_cmd in TERMINAL_COMMANDS


def determine_outcome(exit_code: Optional[int], is_terminal: bool, is_timeout: bool) -> str:
    """Determine workflow outcome."""
    if is_timeout:
        return "ABANDONED"
    if not is_terminal:
        return "ABANDONED"
    if exit_code is None:
        return "ABANDONED"
    return "SUCCESS" if exit_code == 0 else "FAILED"


def infer_workflow_name(events: list[RawEvent]) -> str:
    """
    Infer workflow name from the dominant terminal command.
    """
    terminal_commands = []
    for event in events:
        if is_terminal_command(event.command_path):
            terminal_commands.append(event.command_path[-1].lower())

    if terminal_commands:
        # Use the most common terminal command
        from collections import Counter
        most_common = Counter(terminal_commands).most_common(1)[0][0]
        return f"{most_common}_workflow"

    # Fallback: use the first command's tool name
    if events:
        return f"{events[0].tool_name}_workflow"

    return "unknown_workflow"


def sessionize_events(db: DBSession, events: list[RawEvent]) -> dict[int, list[RawEvent]]:
    """
    Group events into sessions.
    Returns a dict of session_id -> list of events.
    """
    if not events:
        return {}

    timeout_delta = timedelta(minutes=settings.session_timeout_minutes)
    session_events: dict[int, list[RawEvent]] = {}

    # Group by (actor_id_hash, machine_id_hash)
    actor_machine_groups: dict[tuple[str, str], list[RawEvent]] = {}
    for event in events:
        key = (event.actor_id_hash, event.machine_id_hash)
        if key not in actor_machine_groups:
            actor_machine_groups[key] = []
        actor_machine_groups[key].append(event)

    sessions_created = 0
    sessions_updated = 0

    for (actor_hash, machine_hash), group_events in actor_machine_groups.items():
        # Sort by timestamp
        group_events.sort(key=lambda e: e.timestamp)

        current_session: Optional[SessionModel] = None
        current_session_events: list[RawEvent] = []

        # Find the most recent open session for this actor/machine
        existing_session = db.query(SessionModel).filter(
            SessionModel.actor_id_hash == actor_hash,
            SessionModel.machine_id_hash == machine_hash,
            SessionModel.ended_at.is_(None),
        ).order_by(SessionModel.started_at.desc()).first()

        for event in group_events:
            should_start_new_session = False

            if current_session is None and existing_session is None:
                # No existing session, start new
                should_start_new_session = True
            elif current_session is None and existing_session is not None:
                # Check if we can continue the existing session
                last_event_time = existing_session.started_at

                # Get the actual last event time from this session
                last_session_event = db.query(RawEvent).filter(
                    RawEvent.session_id == existing_session.id
                ).order_by(RawEvent.timestamp.desc()).first()

                if last_session_event:
                    last_event_time = last_session_event.timestamp

                time_diff = event.timestamp - last_event_time

                # Check hard boundaries
                if (existing_session.session_hint != event.session_hint or
                    existing_session.ci_detected != event.ci_detected or
                    time_diff > timeout_delta):
                    # Close existing session and start new
                    existing_session.ended_at = last_event_time
                    sessions_updated += 1
                    should_start_new_session = True
                else:
                    # Continue existing session
                    current_session = existing_session
                    current_session_events = []
            else:
                # We have a current session, check if we should continue
                last_event = current_session_events[-1] if current_session_events else None
                if last_event:
                    time_diff = event.timestamp - last_event.timestamp
                else:
                    time_diff = timedelta(0)

                # Check hard boundaries
                if (current_session.session_hint != event.session_hint or
                    current_session.ci_detected != event.ci_detected or
                    time_diff > timeout_delta):
                    # Close current session
                    if current_session_events:
                        current_session.ended_at = current_session_events[-1].timestamp
                        current_session.event_count += len(current_session_events)

                    # Save events for this session
                    if current_session.id not in session_events:
                        session_events[current_session.id] = []
                    session_events[current_session.id].extend(current_session_events)

                    sessions_updated += 1
                    should_start_new_session = True
                    current_session = None
                    current_session_events = []

            if should_start_new_session:
                # Create new session
                new_session = SessionModel(
                    actor_id_hash=actor_hash,
                    machine_id_hash=machine_hash,
                    session_hint=event.session_hint,
                    ci_detected=event.ci_detected,
                    started_at=event.timestamp,
                    event_count=0,
                )
                db.add(new_session)
                db.flush()
                current_session = new_session
                current_session_events = []
                sessions_created += 1

            # Add event to current session
            event.session_id = current_session.id
            current_session_events.append(event)

        # Finalize current session
        if current_session and current_session_events:
            current_session.event_count += len(current_session_events)
            if current_session.id not in session_events:
                session_events[current_session.id] = []
            session_events[current_session.id].extend(current_session_events)

    logger.info(f"Sessionization: created {sessions_created}, updated {sessions_updated}")
    return session_events


def infer_workflows(db: DBSession, session_events: dict[int, list[RawEvent]]) -> int:
    """
    Infer workflows within each session.
    Returns number of workflows created.
    """
    workflows_created = 0
    timeout_delta = timedelta(minutes=settings.session_timeout_minutes)

    for session_id, events in session_events.items():
        if not events:
            continue

        events.sort(key=lambda e: e.timestamp)

        current_workflow_events: list[RawEvent] = []

        for i, event in enumerate(events):
            should_start_new = False
            should_end_current = False

            if not current_workflow_events:
                # Start new workflow
                should_start_new = True
            else:
                # Check if this is an entry command (starts new workflow)
                if is_entry_command(event.command_path):
                    should_end_current = True
                    should_start_new = True

                # Check timeout between events
                last_event = current_workflow_events[-1]
                if event.timestamp - last_event.timestamp > timeout_delta:
                    should_end_current = True
                    should_start_new = True

            # Check if previous event was terminal
            if current_workflow_events:
                last_event = current_workflow_events[-1]
                if is_terminal_command(last_event.command_path) and last_event.exit_code is not None:
                    should_end_current = True
                    should_start_new = True

            # End current workflow if needed
            if should_end_current and current_workflow_events:
                workflow = create_workflow(db, session_id, current_workflow_events, is_timeout=False)
                if workflow:
                    workflows_created += 1
                current_workflow_events = []

            if should_start_new:
                current_workflow_events = [event]
            else:
                current_workflow_events.append(event)

        # Handle remaining events
        if current_workflow_events:
            # Check if last event is terminal
            last_event = current_workflow_events[-1]
            is_terminal = is_terminal_command(last_event.command_path)
            workflow = create_workflow(db, session_id, current_workflow_events, is_timeout=not is_terminal)
            if workflow:
                workflows_created += 1

    return workflows_created


def create_workflow(
    db: DBSession,
    session_id: int,
    events: list[RawEvent],
    is_timeout: bool,
) -> Optional[WorkflowRun]:
    """Create a workflow run from a list of events."""
    if not events:
        return None

    # Determine outcome
    last_event = events[-1]
    is_terminal = is_terminal_command(last_event.command_path)
    outcome = determine_outcome(last_event.exit_code, is_terminal, is_timeout)

    # Calculate duration
    duration_ms = None
    if len(events) > 1:
        duration = events[-1].timestamp - events[0].timestamp
        duration_ms = int(duration.total_seconds() * 1000)
    elif events[0].duration_ms:
        duration_ms = events[0].duration_ms

    # Build command fingerprint for hot-path analysis
    fingerprints = []
    for event in events:
        fp = get_command_fingerprint(event.command_path, event.flags_present)
        fingerprints.append(fp)
    command_fingerprint = " -> ".join(fingerprints)

    # Infer workflow name
    workflow_name = infer_workflow_name(events)

    # Create workflow run
    workflow = WorkflowRun(
        session_id=session_id,
        workflow_name=workflow_name,
        outcome=outcome,
        started_at=events[0].timestamp,
        ended_at=events[-1].timestamp,
        duration_ms=duration_ms,
        step_count=len(events),
        command_fingerprint=command_fingerprint,
    )
    db.add(workflow)
    db.flush()

    # Create workflow steps and update events
    for i, event in enumerate(events):
        step = WorkflowStep(
            workflow_run_id=workflow.id,
            event_id=event.id,
            step_order=i,
            command_fingerprint=get_command_fingerprint(event.command_path, event.flags_present),
        )
        db.add(step)
        event.workflow_run_id = workflow.id

    return workflow


@router.post("/infer", response_model=InferResponse)
def run_inference(db: DBSession = Depends(get_db)) -> InferResponse:
    """
    Run sessionization and workflow inference on new events.

    This processes events that haven't been processed yet (based on inference_cursor).
    """
    # Get or create cursor
    cursor = db.query(InferenceCursor).filter(InferenceCursor.id == 1).first()
    if not cursor:
        cursor = InferenceCursor(id=1, last_event_id=0)
        db.add(cursor)
        db.flush()

    # Get unprocessed events
    events = db.query(RawEvent).filter(
        RawEvent.id > cursor.last_event_id,
        RawEvent.session_id.is_(None),  # Not yet sessionized
    ).order_by(RawEvent.id).limit(10000).all()

    if not events:
        logger.info("No new events to process")
        return InferResponse(
            events_processed=0,
            sessions_created=0,
            sessions_updated=0,
            workflows_created=0,
        )

    logger.info(f"Processing {len(events)} events")

    # Sessionize
    session_events = sessionize_events(db, events)

    # Count sessions
    sessions_created = len([s for s in session_events.keys()])

    # Infer workflows
    workflows_created = infer_workflows(db, session_events)

    # Update cursor
    max_event_id = max(e.id for e in events)
    cursor.last_event_id = max_event_id
    cursor.last_run_at = datetime.now(timezone.utc)

    db.commit()

    logger.info(f"Inference complete: {len(events)} events, {sessions_created} sessions, {workflows_created} workflows")

    return InferResponse(
        events_processed=len(events),
        sessions_created=sessions_created,
        sessions_updated=0,  # Simplified for MVP
        workflows_created=workflows_created,
    )
