"""Pytest fixtures for testing."""
import pytest
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models import Base
from app.schemas import EventInput


@pytest.fixture
def in_memory_db():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def sample_events():
    """Generate sample events for testing."""
    base_time = datetime(2025, 1, 24, 10, 0, 0, tzinfo=timezone.utc)

    events = [
        EventInput(
            timestamp=base_time,
            tool_name="terraform",
            tool_version="1.7.0",
            command_path=["terraform", "init"],
            flags_present=[],
            exit_code=0,
            duration_ms=5000,
            actor_id="user-123",
            machine_id="machine-abc",
            ci_detected=False,
        ),
        EventInput(
            timestamp=base_time.replace(minute=5),
            tool_name="terraform",
            tool_version="1.7.0",
            command_path=["terraform", "plan"],
            flags_present=["--var-file"],
            exit_code=0,
            duration_ms=15000,
            actor_id="user-123",
            machine_id="machine-abc",
            ci_detected=False,
        ),
        EventInput(
            timestamp=base_time.replace(minute=10),
            tool_name="terraform",
            tool_version="1.7.0",
            command_path=["terraform", "apply"],
            flags_present=["--auto-approve"],
            exit_code=0,
            duration_ms=60000,
            actor_id="user-123",
            machine_id="machine-abc",
            ci_detected=False,
        ),
    ]
    return events


@pytest.fixture
def multi_session_events():
    """Generate events that should create multiple sessions."""
    base_time = datetime(2025, 1, 24, 10, 0, 0, tzinfo=timezone.utc)

    events = [
        # Session 1: User A
        EventInput(
            timestamp=base_time,
            tool_name="npm",
            command_path=["npm", "install"],
            exit_code=0,
            actor_id="user-a",
            machine_id="machine-1",
            ci_detected=False,
        ),
        EventInput(
            timestamp=base_time.replace(minute=5),
            tool_name="npm",
            command_path=["npm", "test"],
            exit_code=0,
            actor_id="user-a",
            machine_id="machine-1",
            ci_detected=False,
        ),
        # Session 2: User B (different actor)
        EventInput(
            timestamp=base_time.replace(minute=2),
            tool_name="docker",
            command_path=["docker", "build"],
            exit_code=0,
            actor_id="user-b",
            machine_id="machine-2",
            ci_detected=False,
        ),
        # Session 3: User A, 40 minutes later (timeout)
        EventInput(
            timestamp=base_time.replace(minute=45),
            tool_name="npm",
            command_path=["npm", "publish"],
            exit_code=0,
            actor_id="user-a",
            machine_id="machine-1",
            ci_detected=False,
        ),
    ]
    return events
