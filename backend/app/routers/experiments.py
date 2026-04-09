"""Experiment-level endpoints."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models import Experiment, Seed
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
