"""Reporting endpoints for workflow analytics."""
import logging
from collections import Counter
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, case
from sqlalchemy.orm import Session as DBSession

from app.db import get_db
from app.models import RawEvent, WorkflowRun, WorkflowStep
from app.models import Session as SessionModel
from app.schemas import (
    FailureHotPath,
    SummaryReport,
    WorkflowDetail,
    WorkflowSummary,
)

logger = logging.getLogger(__name__)

router = APIRouter()


def calculate_median(values: list[int]) -> Optional[int]:
    """Calculate median of a list of integers."""
    if not values:
        return None
    sorted_values = sorted(values)
    n = len(sorted_values)
    mid = n // 2
    if n % 2 == 0:
        return (sorted_values[mid - 1] + sorted_values[mid]) // 2
    return sorted_values[mid]


@router.get("/reports/summary", response_model=SummaryReport)
def get_summary_report(db: DBSession = Depends(get_db)) -> SummaryReport:
    """
    Get overall summary report including:
    - Top workflows by count
    - Success rate per workflow
    - Median time to success per workflow
    - Top failure hot paths
    """
    # Total counts
    total_events = db.query(func.count(RawEvent.id)).scalar() or 0
    total_sessions = db.query(func.count(SessionModel.id)).scalar() or 0
    total_workflows = db.query(func.count(WorkflowRun.id)).scalar() or 0

    # Get workflow statistics using case expressions
    workflow_stats = db.query(
        WorkflowRun.workflow_name,
        func.count(WorkflowRun.id).label("total"),
        func.sum(case((WorkflowRun.outcome == "SUCCESS", 1), else_=0)).label("success"),
        func.sum(case((WorkflowRun.outcome == "FAILED", 1), else_=0)).label("failed"),
        func.sum(case((WorkflowRun.outcome == "ABANDONED", 1), else_=0)).label("abandoned"),
    ).group_by(WorkflowRun.workflow_name).order_by(func.count(WorkflowRun.id).desc()).limit(10).all()

    top_workflows = []
    for stat in workflow_stats:
        # Get durations for successful workflows
        durations = db.query(WorkflowRun.duration_ms).filter(
            WorkflowRun.workflow_name == stat.workflow_name,
            WorkflowRun.outcome == "SUCCESS",
            WorkflowRun.duration_ms.isnot(None),
        ).all()
        duration_values = [d[0] for d in durations if d[0] is not None]

        total = stat.total or 0
        success = stat.success or 0
        failed = stat.failed or 0
        abandoned = stat.abandoned or 0

        top_workflows.append(WorkflowSummary(
            workflow_name=stat.workflow_name,
            total_runs=total,
            success_count=success,
            failed_count=failed,
            abandoned_count=abandoned,
            success_rate=round(success / total * 100, 2) if total > 0 else 0.0,
            median_duration_ms=calculate_median(duration_values),
        ))

    # Get failure hot paths
    failed_workflows = db.query(WorkflowRun).filter(
        WorkflowRun.outcome == "FAILED",
        WorkflowRun.command_fingerprint.isnot(None),
    ).all()

    fingerprint_counter: Counter = Counter()
    fingerprint_workflow: dict[str, str] = {}

    for wf in failed_workflows:
        if wf.command_fingerprint:
            fingerprint_counter[wf.command_fingerprint] += 1
            fingerprint_workflow[wf.command_fingerprint] = wf.workflow_name

    failure_hot_paths = [
        FailureHotPath(
            command_fingerprint=fp,
            failure_count=count,
            workflow_name=fingerprint_workflow.get(fp, "unknown"),
        )
        for fp, count in fingerprint_counter.most_common(10)
    ]

    return SummaryReport(
        total_events=total_events,
        total_sessions=total_sessions,
        total_workflows=total_workflows,
        top_workflows=top_workflows,
        failure_hot_paths=failure_hot_paths,
    )


@router.get("/reports/workflows/{workflow_name}", response_model=WorkflowDetail)
def get_workflow_detail(
    workflow_name: str,
    db: DBSession = Depends(get_db),
) -> WorkflowDetail:
    """
    Get detailed view of a specific workflow including:
    - Success rate and outcome breakdown
    - Common command paths
    - Recent runs
    """
    # Check if workflow exists
    exists = db.query(WorkflowRun).filter(
        WorkflowRun.workflow_name == workflow_name
    ).first()

    if not exists:
        raise HTTPException(status_code=404, detail=f"Workflow '{workflow_name}' not found")

    # Get totals and outcomes
    total_runs = db.query(func.count(WorkflowRun.id)).filter(
        WorkflowRun.workflow_name == workflow_name
    ).scalar() or 0

    outcomes = {}
    for outcome in ["SUCCESS", "FAILED", "ABANDONED"]:
        count = db.query(func.count(WorkflowRun.id)).filter(
            WorkflowRun.workflow_name == workflow_name,
            WorkflowRun.outcome == outcome,
        ).scalar() or 0
        outcomes[outcome] = count

    # Success rate
    success_rate = round(outcomes.get("SUCCESS", 0) / total_runs * 100, 2) if total_runs > 0 else 0.0

    # Median duration for successful runs
    durations = db.query(WorkflowRun.duration_ms).filter(
        WorkflowRun.workflow_name == workflow_name,
        WorkflowRun.outcome == "SUCCESS",
        WorkflowRun.duration_ms.isnot(None),
    ).all()
    duration_values = [d[0] for d in durations if d[0] is not None]
    median_duration = calculate_median(duration_values)

    # Common paths
    path_counter: Counter = Counter()
    workflows = db.query(WorkflowRun).filter(
        WorkflowRun.workflow_name == workflow_name,
        WorkflowRun.command_fingerprint.isnot(None),
    ).all()

    for wf in workflows:
        if wf.command_fingerprint:
            path_counter[wf.command_fingerprint] += 1

    common_paths = [
        {"path": path, "count": count}
        for path, count in path_counter.most_common(5)
    ]

    # Recent runs
    recent = db.query(WorkflowRun).filter(
        WorkflowRun.workflow_name == workflow_name
    ).order_by(WorkflowRun.started_at.desc()).limit(10).all()

    recent_runs = [
        {
            "id": r.id,
            "outcome": r.outcome,
            "started_at": r.started_at.isoformat() if r.started_at else None,
            "duration_ms": r.duration_ms,
            "step_count": r.step_count,
        }
        for r in recent
    ]

    return WorkflowDetail(
        workflow_name=workflow_name,
        total_runs=total_runs,
        success_rate=success_rate,
        median_duration_ms=median_duration,
        outcomes=outcomes,
        common_paths=common_paths,
        recent_runs=recent_runs,
    )
