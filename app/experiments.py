"""A/B testing experiments."""
import hashlib
from fastapi import APIRouter, Depends, HTTPException, Security
from sqlalchemy import func, case
from sqlalchemy.orm import Session as DBSession
from pydantic import BaseModel
from typing import Optional
from app.db import get_db
from app.auth import verify_api_key
from app.models import ApiKey, Experiment, VariantAssignment, RawEvent, WorkflowRun

router = APIRouter()


class CreateExperimentRequest(BaseModel):
    name: str
    description: Optional[str] = None
    variants: list[str] = ["control", "variant_a"]
    target_commands: Optional[list[str]] = None
    traffic_pct: int = 100


class ExperimentResponse(BaseModel):
    id: int
    name: str
    variants: list[str]
    is_active: bool


class VariantResponse(BaseModel):
    experiment: str
    variant: str
    actor_id_hash: str


class ExperimentResults(BaseModel):
    experiment: str
    variants: dict
    winner: Optional[str]
    confidence: Optional[float]


@router.post("/experiments", response_model=ExperimentResponse)
def create_experiment(
    req: CreateExperimentRequest,
    db: DBSession = Depends(get_db),
    api_key: ApiKey = Security(verify_api_key),
) -> ExperimentResponse:
    """Create a new A/B test experiment for this tool."""
    tool_name = api_key.tool_name

    existing = db.query(Experiment).filter(
        Experiment.name == req.name,
        Experiment.tool_name == tool_name
    ).first()
    if existing:
        raise HTTPException(400, "Experiment with this name already exists")

    exp = Experiment(
        name=req.name,
        tool_name=tool_name,
        description=req.description,
        variants=req.variants,
        target_commands=req.target_commands,
        traffic_pct=req.traffic_pct,
        is_active=True,
    )
    db.add(exp)
    db.commit()
    db.refresh(exp)

    return ExperimentResponse(
        id=exp.id,
        name=exp.name,
        variants=exp.variants,
        is_active=exp.is_active,
    )


@router.get("/experiments", response_model=list[ExperimentResponse])
def list_experiments(
    db: DBSession = Depends(get_db),
    api_key: ApiKey = Security(verify_api_key),
) -> list[ExperimentResponse]:
    """List all experiments for this tool."""
    tool_name = api_key.tool_name
    exps = db.query(Experiment).filter(Experiment.tool_name == tool_name).all()
    return [
        ExperimentResponse(id=e.id, name=e.name, variants=e.variants, is_active=e.is_active)
        for e in exps
    ]


@router.get("/experiments/{name}/variant", response_model=VariantResponse)
def get_variant(
    name: str,
    actor_id: str,
    db: DBSession = Depends(get_db),
    api_key: ApiKey = Security(verify_api_key),
) -> VariantResponse:
    """Get consistent variant assignment for an actor."""
    tool_name = api_key.tool_name

    exp = db.query(Experiment).filter(
        Experiment.name == name,
        Experiment.tool_name == tool_name,
        Experiment.is_active == True
    ).first()
    if not exp:
        raise HTTPException(404, "Experiment not found or inactive")

    actor_hash = hashlib.sha256(actor_id.encode()).hexdigest()[:16]

    assignment = db.query(VariantAssignment).filter(
        VariantAssignment.experiment_id == exp.id,
        VariantAssignment.actor_id_hash == actor_hash,
    ).first()

    if assignment:
        return VariantResponse(
            experiment=name,
            variant=assignment.variant,
            actor_id_hash=actor_hash,
        )

    # Deterministic assignment based on hash
    hash_int = int(actor_hash, 16)
    variant_idx = hash_int % len(exp.variants)
    variant = exp.variants[variant_idx]

    assignment = VariantAssignment(
        experiment_id=exp.id,
        actor_id_hash=actor_hash,
        variant=variant,
    )
    db.add(assignment)
    db.commit()

    return VariantResponse(
        experiment=name,
        variant=variant,
        actor_id_hash=actor_hash,
    )


@router.get("/experiments/{name}/results", response_model=ExperimentResults)
def get_results(
    name: str,
    db: DBSession = Depends(get_db),
    api_key: ApiKey = Security(verify_api_key),
) -> ExperimentResults:
    """Get experiment results for this tool."""
    tool_name = api_key.tool_name

    exp = db.query(Experiment).filter(
        Experiment.name == name,
        Experiment.tool_name == tool_name
    ).first()
    if not exp:
        raise HTTPException(404, "Experiment not found")

    variants_data = {}
    for variant in exp.variants:
        events = db.query(RawEvent).filter(
            RawEvent.tool_name == tool_name,
            RawEvent.experiment_id == exp.id,
            RawEvent.variant == variant,
        ).all()

        success = sum(1 for e in events if e.exit_code == 0)
        total = len(events)
        durations = [e.duration_ms for e in events if e.duration_ms]

        variants_data[variant] = {
            "events": total,
            "success_rate": round(success / total * 100, 2) if total > 0 else 0,
            "avg_duration_ms": round(sum(durations) / len(durations)) if durations else None,
        }

    winner = None
    confidence = None
    if len(variants_data) >= 2:
        sorted_variants = sorted(
            variants_data.items(),
            key=lambda x: x[1]["success_rate"],
            reverse=True
        )
        if sorted_variants[0][1]["events"] >= 30 and sorted_variants[1][1]["events"] >= 30:
            rate_diff = sorted_variants[0][1]["success_rate"] - sorted_variants[1][1]["success_rate"]
            if rate_diff > 5:
                winner = sorted_variants[0][0]
                confidence = min(0.95, 0.5 + rate_diff / 100)

    return ExperimentResults(
        experiment=name,
        variants=variants_data,
        winner=winner,
        confidence=confidence,
    )


@router.post("/experiments/{name}/stop")
def stop_experiment(
    name: str,
    db: DBSession = Depends(get_db),
    api_key: ApiKey = Security(verify_api_key),
):
    """Stop an experiment for this tool."""
    tool_name = api_key.tool_name

    exp = db.query(Experiment).filter(
        Experiment.name == name,
        Experiment.tool_name == tool_name
    ).first()
    if not exp:
        raise HTTPException(404, "Experiment not found")

    exp.is_active = False
    db.commit()
    return {"status": "stopped", "experiment": name}
