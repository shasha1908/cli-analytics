"""SQLAlchemy ORM models."""
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all models."""
    pass


class RawEvent(Base):
    """Raw ingested events from CLI tools."""

    __tablename__ = "raw_events"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    event_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    tool_name: Mapped[str] = mapped_column(String(128), nullable=False)
    tool_version: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    command_path: Mapped[list] = mapped_column(JSONB, nullable=False)
    flags_present: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    exit_code: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    error_type: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    actor_id_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    machine_id_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    session_hint: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    ci_detected: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    session_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    workflow_run_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    experiment_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    variant: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)


class Session(Base):
    """User sessions grouped by actor and machine."""

    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    actor_id_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    machine_id_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    session_hint: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    ci_detected: Mapped[bool] = mapped_column(Boolean, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    event_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    workflow_runs: Mapped[list["WorkflowRun"]] = relationship(back_populates="session")


class WorkflowRun(Base):
    """Detected workflow runs within sessions."""

    __tablename__ = "workflow_runs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("sessions.id"), nullable=False)
    workflow_name: Mapped[str] = mapped_column(String(128), nullable=False)
    outcome: Mapped[str] = mapped_column(String(32), nullable=False)  # SUCCESS, FAILED, ABANDONED
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    step_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    command_fingerprint: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    session: Mapped["Session"] = relationship(back_populates="workflow_runs")
    steps: Mapped[list["WorkflowStep"]] = relationship(back_populates="workflow_run")


class WorkflowStep(Base):
    """Individual steps within a workflow run."""

    __tablename__ = "workflow_steps"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    workflow_run_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("workflow_runs.id"), nullable=False
    )
    event_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("raw_events.id"), nullable=False)
    step_order: Mapped[int] = mapped_column(Integer, nullable=False)
    command_fingerprint: Mapped[str] = mapped_column(String(512), nullable=False)

    workflow_run: Mapped["WorkflowRun"] = relationship(back_populates="steps")


class InferenceCursor(Base):
    """Tracks the last processed event for incremental inference."""

    __tablename__ = "inference_cursor"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    last_event_id: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    last_run_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class ApiKey(Base):
    """API keys for authentication."""

    __tablename__ = "api_keys"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Experiment(Base):
    """A/B test experiments."""

    __tablename__ = "experiments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    variants: Mapped[list] = mapped_column(JSONB, nullable=False)
    target_commands: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    traffic_pct: Mapped[int] = mapped_column(Integer, default=100)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class VariantAssignment(Base):
    """Consistent variant assignment per actor."""

    __tablename__ = "variant_assignments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    experiment_id: Mapped[int] = mapped_column(Integer, ForeignKey("experiments.id"), nullable=False)
    actor_id_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    variant: Mapped[str] = mapped_column(String(64), nullable=False)
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
