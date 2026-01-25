"""A/B testing experiments."""
import hashlib
import random
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, case
from sqlalchemy.orm import Session as DBSession
from pydantic import BaseModel
from typing import Optional
from app.db import get_db
from app.models import Experiment, VariantAssignment, RawEvent, WorkflowRun

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
    variants: dict  # variant -> {events, success_rate, avg_duration}
    winner: Optional[str]
    confidence: Optional[float]


@router.post("/experiments", response_model=ExperimentResponse)
def create_experiment(
    req: CreateExperimentRequest,
    db: DBSession = Depends(get_db),
) -> ExperimentResponse:
    """Create a new A/B test experiment."""
    existing = db.query(Experiment).filter(Experiment.name == req.name).first()
    if existing:
        raise HTTPException(400, "Experiment with this name already exists")

    exp = Experiment(
        name=req.name,
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
def list_experiments(db: DBSession = Depends(get_db)) -> list[ExperimentResponse]:
    """List all experiments."""
    exps = db.query(Experiment).all()
    return [
        ExperimentResponse(id=e.id, name=e.name, variants=e.variants, is_active=e.is_active)
        for e in exps
    ]


@router.get("/experiments/{name}/variant", response_model=VariantResponse)
def get_variant(
    name: str,
    actor_id: str,
    db: DBSession = Depends(get_db),
) -> VariantResponse:
    """Get consistent variant assignment for an actor."""
    exp = db.query(Experiment).filter(Experiment.name == name, Experiment.is_active == True).first()
    if not exp:
        raise HTTPException(404, "Experiment not found or inactive")

    # Hash actor_id for privacy
    actor_hash = hashlib.sha256(actor_id.encode()).hexdigest()[:16]

    # Check existing assignment
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

    # Check if user is in traffic percentage
    hash_int = int(hashlib.md5(f"{exp.id}:{actor_hash}".encode()).hexdigest(), 16)
    if (hash_int % 100) >= exp.traffic_pct:
        # User not in experiment, return control
        return VariantResponse(experiment=name, variant=exp.variants[0], actor_id_hash=actor_hash)

    # Assign variant deterministically based on hash
    variant_idx = hash_int % len(exp.variants)
    variant = exp.variants[variant_idx]

    # Save assignment
    assignment = VariantAssignment(
        experiment_id=exp.id,
        actor_id_hash=actor_hash,
        variant=variant,
    )
    db.add(assignment)
    db.commit()

    return VariantResponse(experiment=name, variant=variant, actor_id_hash=actor_hash)


@router.get("/experiments/{name}/results", response_model=ExperimentResults)
def get_results(
    name: str,
    db: DBSession = Depends(get_db),
) -> ExperimentResults:
    """Get experiment results comparing variants."""
    exp = db.query(Experiment).filter(Experiment.name == name).first()
    if not exp:
        raise HTTPException(404, "Experiment not found")

    results = {}
    for variant in exp.variants:
        # Get events for this variant
        events = db.query(RawEvent).filter(
            RawEvent.experiment_id == exp.id,
            RawEvent.variant == variant,
        ).all()

        success_count = sum(1 for e in events if e.exit_code == 0)
        total = len(events)
        avg_duration = None
        if events:
            durations = [e.duration_ms for e in events if e.duration_ms]
            if durations:
                avg_duration = sum(durations) // len(durations)

        results[variant] = {
            "events": total,
            "success_rate": round(success_count / total * 100, 2) if total > 0 else 0,
            "avg_duration_ms": avg_duration,
        }

    # Determine winner (simple: highest success rate with enough samples)
    winner = None
    confidence = None
    valid = {k: v for k, v in results.items() if v["events"] >= 10}
    if len(valid) >= 2:
        sorted_variants = sorted(valid.keys(), key=lambda x: valid[x]["success_rate"], reverse=True)
        best = sorted_variants[0]
        second = sorted_variants[1]
        if valid[best]["success_rate"] > valid[second]["success_rate"] + 5:  # 5% threshold
            winner = best
            confidence = min(0.95, 0.5 + (valid[best]["events"] / 200))

    return ExperimentResults(
        experiment=name,
        variants=results,
        winner=winner,
        confidence=round(confidence, 2) if confidence else None,
    )


@router.post("/experiments/{name}/stop")
def stop_experiment(name: str, db: DBSession = Depends(get_db)):
    """Stop an experiment."""
    exp = db.query(Experiment).filter(Experiment.name == name).first()
    if not exp:
        raise HTTPException(404, "Experiment not found")
    exp.is_active = False
    db.commit()
    return {"status": "stopped", "experiment": name}
