"""Experiment-level endpoints."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models import Decision, Experiment, Seed
from ..schemas import ExperimentDetail, ExperimentSummary, IngestionResult
from ..services.ingestion import ingest_all


router = APIRouter(prefix="/api/experiments", tags=["experiments"])


@router.get("", response_model=list[ExperimentSummary])
async def list_experiments(
    family: Optional[str] = Query(None, description="h1 | h3 | ablation | custom"),
    scenario: Optional[str] = None,
    policy: Optional[str] = None,
    sort: str = Query(
        "config_name", pattern="^(config_name|mean_stockout_rate|mean_total_cost|updated_at)$",
    ),
    descending: bool = False,
    limit: int = Query(200, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Experiment)
    if family:
        stmt = stmt.where(Experiment.family == family)
    if scenario:
        stmt = stmt.where(Experiment.scenario == scenario)
    if policy:
        stmt = stmt.where(Experiment.policy == policy)
    col = getattr(Experiment, sort)
    stmt = stmt.order_by(col.desc() if descending else col.asc()).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/{name}", response_model=ExperimentDetail)
async def get_experiment(name: str, db: AsyncSession = Depends(get_db)):
    exp = await db.scalar(select(Experiment).where(Experiment.config_name == name))
    if not exp:
        raise HTTPException(404, f"Experiment {name!r} not found")
    return exp


@router.post("/ingest", response_model=IngestionResult)
async def trigger_ingest(db: AsyncSession = Depends(get_db)):
    """Re-walk results/ and refresh the database. Idempotent."""
    counts = await ingest_all(db)
    return IngestionResult(**counts)


@router.get("/_stats/families")
async def family_breakdown(db: AsyncSession = Depends(get_db)):
    """Counts per family — used by the overview page."""
    result = await db.execute(
        select(Experiment.family, func.count(Experiment.id))
        .group_by(Experiment.family)
    )
    return {fam: count for fam, count in result.all()}


@router.get("/_stats/decision_coverage")
async def decision_coverage(db: AsyncSession = Depends(get_db)):
    """Per-experiment audit-log coverage.

    For each experiment returns the total seeds, how many of them have at
    least one decision-log row, and the seed_num of one seed that has
    data (so the UI can deep-link to a populated page rather than always
    /seed_1 which may be empty). Powers the &#39;has audit log&#39;
    badges and 'first populated seed' links on /decisions.
    """
    # Single round-trip: experiments LEFT JOIN seeds LEFT JOIN decisions,
    # grouped by experiment + seed, then aggregated in Python.
    rows = await db.execute(
        select(
            Experiment.id.label("exp_id"),
            Experiment.config_name,
            Seed.seed_num,
            func.count(Decision.id).label("n_decisions"),
        )
        .select_from(Experiment)
        .join(Seed, Seed.experiment_id == Experiment.id, isouter=True)
        .join(Decision, Decision.seed_id == Seed.id, isouter=True)
        .group_by(Experiment.id, Seed.seed_num)
    )

    out: dict[str, dict] = {}
    for exp_id, name, seed_num, n_decisions in rows.all():
        entry = out.setdefault(
            name,
            {"n_seeds": 0, "n_seeds_with_decisions": 0, "first_populated_seed": None},
        )
        if seed_num is not None:
            entry["n_seeds"] += 1
            if n_decisions and int(n_decisions) > 0:
                entry["n_seeds_with_decisions"] += 1
                if entry["first_populated_seed"] is None:
                    entry["first_populated_seed"] = seed_num
    return out
