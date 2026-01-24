"""Pydantic schemas for request/response validation."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class EventInput(BaseModel):
    """Input schema for a single CLI event."""

    timestamp: datetime = Field(..., description="ISO8601 timestamp when event occurred")
    tool_name: str = Field(..., min_length=1, max_length=128, description="Name of the CLI tool")
    tool_version: Optional[str] = Field(None, max_length=64, description="Version of the tool")
    command_path: list[str] = Field(
        ..., min_length=1, description="Command hierarchy, e.g. ['tool', 'deploy']"
    )
    flags_present: list[str] = Field(
        default_factory=list, description="List of flag names (without values)"
    )
    exit_code: Optional[int] = Field(None, description="Exit code of the command")
    duration_ms: Optional[int] = Field(None, ge=0, description="Duration in milliseconds")
    error_type: Optional[str] = Field(None, max_length=256, description="Error classification")
    actor_id: str = Field(..., min_length=1, max_length=256, description="Anonymous user identifier")
    machine_id: str = Field(..., min_length=1, max_length=256, description="Anonymous machine identifier")
    session_hint: Optional[str] = Field(None, max_length=128, description="Optional session identifier")
    ci_detected: bool = Field(False, description="Whether running in CI environment")

    @field_validator("command_path")
    @classmethod
    def validate_command_path(cls, v: list[str]) -> list[str]:
        """Ensure command path elements are non-empty strings."""
        return [str(cmd).strip() for cmd in v if cmd]

    @field_validator("flags_present")
    @classmethod
    def validate_flags(cls, v: list[str]) -> list[str]:
        """Sanitize flag names - keep only the flag name, not values."""
        sanitized = []
        for flag in v:
            # Strip any potential value after = or :
            flag_name = str(flag).split("=")[0].split(":")[0].strip()
            if flag_name:
                sanitized.append(flag_name)
        return sanitized


class BatchEventInput(BaseModel):
    """Input schema for batch event ingestion."""

    events: list[EventInput] = Field(..., min_length=1, max_length=1000)


class IngestResponse(BaseModel):
    """Response schema for event ingestion."""

    accepted: int
    rejected: int
    event_ids: list[str]


class InferResponse(BaseModel):
    """Response schema for inference run."""

    events_processed: int
    sessions_created: int
    sessions_updated: int
    workflows_created: int


class WorkflowSummary(BaseModel):
    """Summary of a workflow type."""

    workflow_name: str
    total_runs: int
    success_count: int
    failed_count: int
    abandoned_count: int
    success_rate: float
    median_duration_ms: Optional[int]


class FailureHotPath(BaseModel):
    """A common failing command sequence."""

    command_fingerprint: str
    failure_count: int
    workflow_name: str


class SummaryReport(BaseModel):
    """Overall summary report."""

    total_events: int
    total_sessions: int
    total_workflows: int
    top_workflows: list[WorkflowSummary]
    failure_hot_paths: list[FailureHotPath]


class WorkflowDetail(BaseModel):
    """Detailed view of a specific workflow."""

    workflow_name: str
    total_runs: int
    success_rate: float
    median_duration_ms: Optional[int]
    outcomes: dict[str, int]
    common_paths: list[dict]
    recent_runs: list[dict]


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    database: str
