"""Seed-level endpoints: per-seed summaries, timeseries, decision logs."""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_settings
from ..database import get_db
from ..models import Decision, Experiment, Seed
from ..schemas import (
    DecisionEntry, DecisionPage, SeedDetail, SeedSummary, SeedTimeseries,
    TimeseriesPoint,
)

router = APIRouter(prefix="/api/experiments/{name}/seeds", tags=["seeds"])


async def _resolve_experiment(name: str, db: AsyncSession) -> Experiment:
    exp = await db.scalar(select(Experiment).where(Experiment.config_name == name))
    if not exp:
        raise HTTPException(404, f"Experiment {name!r} not found")
    return exp


@router.get("", response_model=list[SeedSummary])
async def list_seeds(
    name: str,
    db: AsyncSession = Depends(get_db),
):
    exp = await _resolve_experiment(name, db)
    # Compute decision counts per seed in a single query, then merge into
    # the response. We avoid a per-row N+1 by doing one GROUP BY then a
    # Python dict lookup. The count is included in the SeedSummary so
    # callers can render an "audit log: yes/no" badge without a second
    # round trip.
    seeds_rows = (await db.execute(
        select(Seed).where(Seed.experiment_id == exp.id).order_by(Seed.seed_num)
    )).scalars().all()

    counts_rows = await db.execute(
        select(Decision.seed_id, func.count(Decision.id))
        .where(Decision.seed_id.in_([s.id for s in seeds_rows]))
        .group_by(Decision.seed_id)
    )
    n_decisions_by_seed = {sid: int(n) for sid, n in counts_rows.all()}

    out: list[SeedSummary] = []
    for s in seeds_rows:
        summary = SeedSummary.model_validate(s, from_attributes=True)
        # `n_decisions` defaults to 0 — only override when we have a hit.
        summary.n_decisions = n_decisions_by_seed.get(s.id, 0)
        out.append(summary)
    return out


@router.get("/{seed_num}", response_model=SeedDetail)
async def get_seed(
    name: str,
    seed_num: int,
    db: AsyncSession = Depends(get_db),
):
    exp = await _resolve_experiment(name, db)
    seed = await db.scalar(
        select(Seed)
        .where(Seed.experiment_id == exp.id)
        .where(Seed.seed_num == seed_num)
    )
    if not seed:
        raise HTTPException(404, f"Seed {seed_num} not found for {name!r}")
    return seed


@router.get("/{seed_num}/timeseries", response_model=SeedTimeseries)
async def get_seed_timeseries(
    name: str,
    seed_num: int,
    db: AsyncSession = Depends(get_db),
):
    """Stream the per-step timeseries CSV as JSON."""
    exp = await _resolve_experiment(name, db)
    seed = await db.scalar(
        select(Seed)
        .where(Seed.experiment_id == exp.id)
        .where(Seed.seed_num == seed_num)
    )
    if not seed:
        raise HTTPException(404, f"Seed {seed_num} not found for {name!r}")
    if not seed.timeseries_path:
        raise HTTPException(404, "No timeseries on file for this seed")
    p = get_settings().project_root / seed.timeseries_path
    if not p.exists():
        raise HTTPException(404, f"Timeseries file missing on disk: {p}")
    points: list[TimeseriesPoint] = []
    with p.open() as f:
        reader = csv.DictReader(f)
        for row in reader:
            points.append(TimeseriesPoint(
                step=int(row["step"]),
                total_on_hand=int(float(row.get("total_on_hand", 0))),
                stockout_skus_step=int(float(row.get("stockout_skus_step", 0))),
            ))
    return SeedTimeseries(seed_id=seed.id, steps=points)


# ---------------------------------------------------------------------------
# Decision-log endpoints (the audit trail)
# ---------------------------------------------------------------------------
@router.get("/{seed_num}/decisions", response_model=DecisionPage)
async def get_decisions(
    name: str,
    seed_num: int,
    agent: Optional[str] = None,
    action: Optional[str] = None,
    sku: Optional[str] = None,
    step_min: Optional[int] = None,
    step_max: Optional[int] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
):
    exp = await _resolve_experiment(name, db)
    seed = await db.scalar(
        select(Seed)
        .where(Seed.experiment_id == exp.id)
        .where(Seed.seed_num == seed_num)
    )
    if not seed:
        raise HTTPException(404, f"Seed {seed_num} not found for {name!r}")

    base = select(Decision).where(Decision.seed_id == seed.id)
    if agent:
        base = base.where(Decision.agent == agent)
    if action:
        base = base.where(Decision.action == action)
    if sku:
        base = base.where(Decision.sku == sku)
    if step_min is not None:
        base = base.where(Decision.step >= step_min)
    if step_max is not None:
        base = base.where(Decision.step <= step_max)

    total_q = select(func.count()).select_from(base.subquery())
    total = (await db.execute(total_q)).scalar() or 0

    items_q = (
        base.order_by(Decision.step.asc(), Decision.id.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = (await db.execute(items_q)).scalars().all()

    return DecisionPage(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{seed_num}/decisions/skus")
async def list_skus_with_decisions(
    name: str,
    seed_num: int,
    limit: int = Query(500, ge=1, le=5000),
    db: AsyncSession = Depends(get_db),
):
    """List distinct SKUs that appear in this seed's decision log,
    sorted by activity (most decisions first)."""
    exp = await _resolve_experiment(name, db)
    seed = await db.scalar(
        select(Seed)
        .where(Seed.experiment_id == exp.id)
        .where(Seed.seed_num == seed_num)
    )
    if not seed:
        raise HTTPException(404, f"Seed {seed_num} not found for {name!r}")
    res = await db.execute(
        select(Decision.sku, func.count(Decision.id))
        .where(Decision.seed_id == seed.id)
        .where(Decision.sku.is_not(None))
        .group_by(Decision.sku)
        .order_by(func.count(Decision.id).desc())
        .limit(limit)
    )
    return [{"sku": sku, "decisions": count} for sku, count in res.all()]


@router.get("/{seed_num}/decisions/agents")
async def list_decision_agents(
    name: str,
    seed_num: int,
    db: AsyncSession = Depends(get_db),
):
    """Distinct (agent, action) pairs with counts — for filter dropdowns."""
    exp = await _resolve_experiment(name, db)
    seed = await db.scalar(
        select(Seed)
        .where(Seed.experiment_id == exp.id)
        .where(Seed.seed_num == seed_num)
    )
    if not seed:
        raise HTTPException(404, f"Seed {seed_num} not found for {name!r}")
    res = await db.execute(
        select(Decision.agent, Decision.action, func.count(Decision.id))
        .where(Decision.seed_id == seed.id)
        .group_by(Decision.agent, Decision.action)
        .order_by(Decision.agent, Decision.action)
    )
    return [
        {"agent": agent, "action": action, "count": count}
        for agent, action, count in res.all()
    ]
