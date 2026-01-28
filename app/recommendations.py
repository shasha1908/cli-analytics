"""CLI recommendations based on usage patterns."""
from fastapi import APIRouter, Depends, Query, Security
from sqlalchemy import func
from sqlalchemy.orm import Session as DBSession
from pydantic import BaseModel
from typing import Optional
from app.db import get_db
from app.auth import verify_api_key
from app.models import ApiKey, RawEvent, WorkflowRun

router = APIRouter()


class Recommendation(BaseModel):
    type: str
    message: str
    confidence: float
    based_on_samples: int


class RecommendationsResponse(BaseModel):
    command: str
    recommendations: list[Recommendation]


@router.get("/recommendations", response_model=RecommendationsResponse)
def get_recommendations(
    command: str = Query(..., description="Command to get recommendations for"),
    context: Optional[str] = Query(None, description="Previous command for context"),
    failed: bool = Query(False, description="Whether the command failed"),
    db: DBSession = Depends(get_db),
    api_key: ApiKey = Security(verify_api_key),
) -> RecommendationsResponse:
    """Get recommendations for a command based on usage patterns for this tool."""
    tool_name = api_key.tool_name
    recommendations = []
    command_lower = command.lower()

    # Analyze sequences for this tool only
    events_by_workflow = db.query(
        RawEvent.workflow_run_id,
        RawEvent.command_path,
        RawEvent.exit_code
    ).filter(
        RawEvent.tool_name == tool_name,
        RawEvent.workflow_run_id.isnot(None)
    ).order_by(RawEvent.workflow_run_id, RawEvent.timestamp).all()

    command_pairs = {}
    current_wf = None
    prev_cmd = None
    for wf_id, cmd_path, exit_code in events_by_workflow:
        cmd = cmd_path[-1].lower() if cmd_path else None
        if wf_id != current_wf:
            current_wf = wf_id
            prev_cmd = None
        if cmd and prev_cmd:
            key = (prev_cmd, cmd)
            if key not in command_pairs:
                command_pairs[key] = {"success": 0, "fail": 0}
            if exit_code == 0:
                command_pairs[key]["success"] += 1
            else:
                command_pairs[key]["fail"] += 1
        prev_cmd = cmd

    # If command failed, find what usually helps
    if failed:
        recovery_cmds = {}
        for (prev, curr), stats in command_pairs.items():
            if prev == command_lower and stats["success"] > 2:
                recovery_cmds[curr] = stats["success"]

        if recovery_cmds:
            best_recovery = max(recovery_cmds, key=recovery_cmds.get)
            recommendations.append(Recommendation(
                type="after_failure",
                message=f"After '{command}' fails, users often succeed by running '{best_recovery}' next",
                confidence=min(0.9, recovery_cmds[best_recovery] / 10),
                based_on_samples=recovery_cmds[best_recovery]
            ))

    # Find common prerequisites
    prereqs = {}
    for (prev, curr), stats in command_pairs.items():
        if curr == command_lower:
            total = stats["success"] + stats["fail"]
            if total > 2:
                prereqs[prev] = {"total": total, "success_rate": stats["success"] / total}

    if prereqs:
        best_prereq = max(prereqs, key=lambda x: prereqs[x]["total"])
        if prereqs[best_prereq]["total"] >= 3:
            recommendations.append(Recommendation(
                type="before_command",
                message=f"'{best_prereq}' is commonly run before '{command}'",
                confidence=prereqs[best_prereq]["success_rate"],
                based_on_samples=prereqs[best_prereq]["total"]
            ))

    # Find common next steps
    next_steps = {}
    for (prev, curr), stats in command_pairs.items():
        if prev == command_lower and stats["success"] > 0:
            next_steps[curr] = stats["success"]

    if next_steps and not failed:
        best_next = max(next_steps, key=next_steps.get)
        if next_steps[best_next] >= 3:
            recommendations.append(Recommendation(
                type="common_sequence",
                message=f"Users typically run '{best_next}' after '{command}'",
                confidence=min(0.9, next_steps[best_next] / 10),
                based_on_samples=next_steps[best_next]
            ))

    return RecommendationsResponse(command=command, recommendations=recommendations)
