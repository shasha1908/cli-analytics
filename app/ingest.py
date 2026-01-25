"""Event ingestion endpoint and logic."""
import hashlib
import logging
import uuid
from datetime import datetime, timezone
from typing import Union

from fastapi import APIRouter, Depends, HTTPException, Security
from sqlalchemy.orm import Session as DBSession

from app.db import get_db
from app.auth import verify_api_key
from app.models import RawEvent
from app.privacy import (
    hash_identifier,
    sanitize_command_path,
    sanitize_error_type,
    sanitize_flags,
    sanitize_tool_name,
    sanitize_tool_version,
)
from app.schemas import BatchEventInput, EventInput, IngestResponse

logger = logging.getLogger(__name__)

router = APIRouter()


def generate_event_id(event: EventInput) -> str:
    """Generate a unique, deterministic event ID."""
    # Create a hash from event content to detect duplicates
    content = f"{event.timestamp.isoformat()}:{event.actor_id}:{event.machine_id}:{event.tool_name}:{':'.join(event.command_path)}"
    content_hash = hashlib.sha256(content.encode()).hexdigest()[:12]
    return f"evt_{content_hash}_{uuid.uuid4().hex[:8]}"


def process_event(event: EventInput, db: DBSession) -> tuple[bool, str]:
    """
    Process and store a single event.
    Returns (success, event_id or error message).
    """
    try:
        # Generate event ID
        event_id = generate_event_id(event)

        # Apply privacy sanitization
        sanitized_command_path = sanitize_command_path(event.command_path)
        sanitized_flags = sanitize_flags(event.flags_present)
        sanitized_error_type = sanitize_error_type(event.error_type)
        sanitized_tool_name = sanitize_tool_name(event.tool_name)
        sanitized_tool_version = sanitize_tool_version(event.tool_version)

        # Hash identifiers
        actor_id_hash = hash_identifier(event.actor_id)
        machine_id_hash = hash_identifier(event.machine_id)

        # Ensure timestamp is timezone-aware
        timestamp = event.timestamp
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)

        # Create raw event record
        raw_event = RawEvent(
            event_id=event_id,
            timestamp=timestamp,
            tool_name=sanitized_tool_name,
            tool_version=sanitized_tool_version,
            command_path=sanitized_command_path,
            flags_present=sanitized_flags,
            exit_code=event.exit_code,
            duration_ms=event.duration_ms,
            error_type=sanitized_error_type,
            actor_id_hash=actor_id_hash,
            machine_id_hash=machine_id_hash,
            session_hint=event.session_hint,
            ci_detected=event.ci_detected,
        )

        db.add(raw_event)
        db.flush()  # Get the ID without committing

        logger.debug(f"Processed event {event_id} for tool {sanitized_tool_name}")
        return True, event_id

    except Exception as e:
        logger.error(f"Error processing event: {e}")
        return False, str(e)


@router.post("/ingest", response_model=IngestResponse)
def ingest_events(
    payload: Union[EventInput, BatchEventInput],
    db: DBSession = Depends(get_db),
    _: None = Security(verify_api_key),
) -> IngestResponse:
    """
    Ingest one or more CLI events.

    Accepts either a single event or a batch of events.
    All events are validated, sanitized for privacy, and stored.
    """
    # Normalize to list
    if isinstance(payload, EventInput):
        events = [payload]
    else:
        events = payload.events

    accepted = 0
    rejected = 0
    event_ids = []

    for event in events:
        success, result = process_event(event, db)
        if success:
            accepted += 1
            event_ids.append(result)
        else:
            rejected += 1
            logger.warning(f"Rejected event: {result}")

    # Commit all successful events
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to commit events: {e}")
        raise HTTPException(status_code=500, detail="Failed to store events")

    logger.info(f"Ingested {accepted} events, rejected {rejected}")

    return IngestResponse(
        accepted=accepted,
        rejected=rejected,
        event_ids=event_ids,
    )
