"""H1 / H3 / Ablation report endpoints.

The reports are computed on the fly from the in-database experiment
catalog, falling back to the pre-generated `results/*_report.json`
files when the simulator emitted them.
"""
from __future__ import annotations

import json
from datetime import datetime  # noqa: F401  (kept for re-export / typing)
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_settings
from ..database import get_db
from ..models.db import utcnow
from ..schemas import (
    AblationReport, AblationRow, H1Report, H3Fit, H3Report, StatTest,
)


router = APIRouter(prefix="/api/reports", tags=["reports"])


def _read_json(path: Path) -> Any | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError:
        return None


# ---------------------------------------------------------------------------
# H1
# ---------------------------------------------------------------------------
@router.get("/h1", response_model=H1Report)
async def get_h1_report(db: AsyncSession = Depends(get_db)):
    """Read the simulator's pre-computed H1 report."""
    settings = get_settings()
    data = _read_json(settings.results_dir / "h1_report.json")
    if not isinstance(data, list):
        return H1Report(generated_at=utcnow(), tests=[])
    tests = [
        StatTest(
            scenario=row.get("scenario", ""),
            baseline=row.get("baseline", ""),
            metric=row.get("metric", ""),
            treatment_mean=row.get("treatment_mean"),
            baseline_mean=row.get("baseline_mean"),
            rel_change=row.get("rel_change"),
            mannwhitney_p=row.get("mannwhitney_p"),
            welch_p=row.get("welch_p"),
            cohens_d=row.get("cohens_d"),
        )
        for row in data
    ]
    return H1Report(generated_at=utcnow(), tests=tests)


# ---------------------------------------------------------------------------
# H3
# ---------------------------------------------------------------------------
@router.get("/h3", response_model=H3Report)
async def get_h3_report(db: AsyncSession = Depends(get_db)):
    settings = get_settings()
    data = _read_json(settings.results_dir / "h3_report.json")
    if not isinstance(data, dict):
        return H3Report(generated_at=utcnow(), fits=[])
    fits_dict = data.get("fits", {})
    rows_list = data.get("rows", [])
    fits: list[H3Fit] = []
    for policy, info in fits_dict.items():
        pl = info.get("runtime_powerlaw", {})
        # Filter raw points for this policy
        pol_points = [r for r in rows_list if r.get("policy") == policy]
        fits.append(H3Fit(
            policy=policy,
            exponent_b=pl.get("b", 0.0),
            a=pl.get("a", 0.0),
            r2=pl.get("r2", 0.0),
            classification=info.get("runtime_classification", ""),
            linear_r2=info.get("runtime_linear_r2"),
            raw_points=pol_points,
        ))
    return H3Report(generated_at=utcnow(), fits=fits)


# ---------------------------------------------------------------------------
# Ablation
# ---------------------------------------------------------------------------
@router.get("/ablation", response_model=AblationReport)
async def get_ablation_report(db: AsyncSession = Depends(get_db)):
    settings = get_settings()
    data = _read_json(settings.results_dir / "ablation_report.json")
    if not isinstance(data, dict):
        return AblationReport(generated_at=utcnow(), rows=[])
    rows = []
    for r in data.get("rows", []):
        rows.append(AblationRow(
            variant=r.get("variant", ""),
            n_seeds=r.get("n_seeds", 0),
            stockout_rate_mean=r.get("stockout_rate_mean"),
            total_cost_mean=r.get("total_cost_mean"),
            forecast_mape_mean=r.get("forecast_mape_mean"),
            n_global_drift_events_mean=r.get("n_global_drift_events_mean"),
            rel_to_full_stockout=r.get("stockout_rate_rel_to_full"),
            rel_to_full_cost=r.get("total_cost_rel_to_full"),
        ))
    return AblationReport(generated_at=utcnow(), rows=rows)
