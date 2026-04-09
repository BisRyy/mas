"""Walk the simulator's `results/` directory and load everything into SQLite.

This service is idempotent: it upserts experiments + seeds based on
the on-disk layout. Decision logs are *not* persisted by the simulator
today (only aggregate timeseries are), so the decision-log ingestion
is currently a no-op placeholder. Phase 1b adds the simulator hook
that emits a decision-log JSONL per seed.
"""
from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_settings
from ..models import Experiment, Seed, Decision

log = logging.getLogger(__name__)


# Recognised filename patterns:
#   results/<config_name>/seed_NNN/summary.json
#   results/<config_name>/aggregate.json
#   results/<config_name>/seed_NNN/timeseries.csv
#   results/<config_name>/seed_NNN/decisions.jsonl   (Phase 1b)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
_FAMILY_PATTERNS = {
    "h1": re.compile(
        r"^olist_(static_rop|periodic_forecasting|mas)_"
        r"(no_drift|abrupt|gradual|seasonal|severe_abrupt|catastrophic)$"
    ),
    "h3": re.compile(
        r"^olist_scale_(static_rop|periodic_forecasting|mas)_n\d+$"
    ),
    "ablation": re.compile(r"^olist_ablation_(full|no_adwin|ma_only|no_safety)$"),
}


def _classify(config_name: str) -> tuple[str, str, str]:
    """Return (family, scenario, policy) from a config name.

    Examples:
      olist_mas_catastrophic    -> ("h1", "catastrophic", "mas")
      olist_scale_mas_n200      -> ("h3", "n200", "mas")
      olist_ablation_no_adwin   -> ("ablation", "catastrophic", "no_adwin")
    """
    m = _FAMILY_PATTERNS["h1"].match(config_name)
    if m:
        return "h1", m.group(2), m.group(1)
    m = _FAMILY_PATTERNS["h3"].match(config_name)
    if m:
        n = config_name.rsplit("_n", 1)[-1]
        return "h3", f"n{n}", m.group(1)
    m = _FAMILY_PATTERNS["ablation"].match(config_name)
    if m:
        return "ablation", "catastrophic", m.group(1)
    return "custom", "unknown", "unknown"


def _safe_get(d: dict | None, *keys: str, default: Any = None) -> Any:
    cur: Any = d
    for k in keys:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(k)
        if cur is None:
            return default
    return cur


def _metric_mean(agg: dict | None, key: str) -> float | None:
    m = _safe_get(agg, "metrics", key)
    if isinstance(m, dict):
        return m.get("mean")
    return None


def _metric_ci(agg: dict | None, key: str) -> tuple[float | None, float | None]:
    m = _safe_get(agg, "metrics", key)
    if isinstance(m, dict):
        return m.get("ci95_lo"), m.get("ci95_hi")
    return None, None


# ---------------------------------------------------------------------------
# Per-experiment ingestion
# ---------------------------------------------------------------------------
async def _upsert_experiment(
    session: AsyncSession, config_name: str, results_dir: Path
) -> Experiment:
    family, scenario, policy = _classify(config_name)

    agg_path = results_dir / "aggregate.json"
    agg = None
    if agg_path.exists():
        agg = json.loads(agg_path.read_text())

    n_seeds = (agg or {}).get("n_seeds") or 0
    ci_lo, ci_hi = _metric_ci(agg, "stockout_rate")

    drift_start = None
    # Try to read it off any seed summary that includes drift_start_step.
    first_summary = next(results_dir.glob("seed_*/summary.json"), None)
    if first_summary is not None:
        try:
            data = json.loads(first_summary.read_text())
            drift_start = data.get("drift_start_step")
        except Exception:
            pass

    existing = await session.scalar(
        select(Experiment).where(Experiment.config_name == config_name)
    )
    if existing is None:
        exp = Experiment(
            config_name=config_name,
            scenario=scenario,
            policy=policy,
            family=family,
            n_seeds=n_seeds,
            mean_stockout_rate=_metric_mean(agg, "stockout_rate"),
            mean_total_cost=_metric_mean(agg, "total_cost"),
            mean_n_orders=_metric_mean(agg, "n_orders"),
            mean_forecast_mape=_metric_mean(agg, "forecast_mape"),
            mean_runtime_seconds=_metric_mean(agg, "runtime_seconds"),
            mean_n_drift_events=_metric_mean(agg, "n_global_drift_events"),
            ci95_stockout_lo=ci_lo,
            ci95_stockout_hi=ci_hi,
            drift_start_step=drift_start,
            aggregate_json=agg,
        )
        session.add(exp)
        await session.flush()
        return exp

    # Update in place — useful when re-running ingestion after a fresh sweep.
    existing.scenario = scenario
    existing.policy = policy
    existing.family = family
    existing.n_seeds = n_seeds
    existing.mean_stockout_rate = _metric_mean(agg, "stockout_rate")
    existing.mean_total_cost = _metric_mean(agg, "total_cost")
    existing.mean_n_orders = _metric_mean(agg, "n_orders")
    existing.mean_forecast_mape = _metric_mean(agg, "forecast_mape")
    existing.mean_runtime_seconds = _metric_mean(agg, "runtime_seconds")
    existing.mean_n_drift_events = _metric_mean(agg, "n_global_drift_events")
    existing.ci95_stockout_lo = ci_lo
    existing.ci95_stockout_hi = ci_hi
    existing.drift_start_step = drift_start
    existing.aggregate_json = agg
    return existing


async def _upsert_seed(
    session: AsyncSession, experiment: Experiment, seed_dir: Path
) -> Seed | None:
    summary_path = seed_dir / "summary.json"
    if not summary_path.exists():
        return None

    try:
        summary = json.loads(summary_path.read_text())
    except json.JSONDecodeError:
        log.warning("Bad summary.json in %s", seed_dir)
        return None

    seed_num = int(seed_dir.name.removeprefix("seed_"))
    ts_path = seed_dir / "timeseries.csv"

    existing = await session.scalar(
        select(Seed)
        .where(Seed.experiment_id == experiment.id)
        .where(Seed.seed_num == seed_num)
    )
    fields = dict(
        n_skus=summary.get("n_skus_used"),
        stockout_rate=summary.get("stockout_rate"),
        total_cost=summary.get("total_cost"),
        n_orders=summary.get("n_orders"),
        forecast_mape=summary.get("forecast_mape"),
        runtime_seconds=summary.get("runtime_seconds"),
        peak_memory_mb=summary.get("peak_python_mem_mb"),
        n_drift_events=summary.get("n_drift_events"),
        n_global_drift_events=summary.get("n_global_drift_events"),
        n_refits=summary.get("n_refits"),
        summary_json=summary,
        timeseries_path=str(ts_path.relative_to(get_settings().project_root))
        if ts_path.exists() else None,
    )

    if existing is None:
        seed = Seed(
            experiment_id=experiment.id,
            seed_num=seed_num,
            **fields,
        )
        session.add(seed)
        await session.flush()
        return seed

    for k, v in fields.items():
        setattr(existing, k, v)
    return existing


async def _ingest_decisions_for_seed(
    session: AsyncSession, seed: Seed, seed_dir: Path
) -> int:
    """Load decisions.jsonl into the Decision table if present.

    The simulator can be configured to emit per-agent decision logs as
    JSONL alongside summary.json. If the file doesn't exist, we just
    skip (Phase 1b adds the emission hook to the simulator).
    """
    decisions_path = seed_dir / "decisions.jsonl"
    if not decisions_path.exists():
        return 0

    # Idempotency: wipe + re-ingest.
    from sqlalchemy import delete
    await session.execute(delete(Decision).where(Decision.seed_id == seed.id))

    inserted = 0
    batch: list[Decision] = []
    with decisions_path.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            batch.append(Decision(
                seed_id=seed.id,
                step=int(obj.get("step", 0)),
                agent=str(obj.get("agent", "unknown")),
                action=str(obj.get("action", "")),
                sku=obj.get("sku"),
                details_json={k: v for k, v in obj.items()
                              if k not in {"step", "agent", "action", "sku"}},
            ))
            if len(batch) >= 1000:
                session.add_all(batch)
                await session.flush()
                inserted += len(batch)
                batch = []
    if batch:
        session.add_all(batch)
        await session.flush()
        inserted += len(batch)
    return inserted


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
async def ingest_all(session: AsyncSession) -> dict[str, int]:
    """Walk results/ and load everything. Returns counts."""
    settings = get_settings()
    root = settings.results_dir
    if not root.exists():
        log.warning("Results dir not found: %s", root)
        return {"experiments": 0, "seeds": 0, "decisions": 0}

    n_exp = 0
    n_seed = 0
    n_dec = 0
    for cfg_dir in sorted(root.iterdir()):
        if not cfg_dir.is_dir() or cfg_dir.name.startswith("."):
            continue
        # Only ingest directories that look like sweep outputs (have either
        # aggregate.json or at least one seed_NNN/summary.json).
        has_agg = (cfg_dir / "aggregate.json").exists()
        has_seed = any(cfg_dir.glob("seed_*/summary.json"))
        if not (has_agg or has_seed):
            continue

        exp = await _upsert_experiment(session, cfg_dir.name, cfg_dir)
        n_exp += 1
        for seed_dir in sorted(cfg_dir.glob("seed_*")):
            if not seed_dir.is_dir():
                continue
            seed = await _upsert_seed(session, exp, seed_dir)
            if seed is None:
                continue
            n_seed += 1
            n_dec += await _ingest_decisions_for_seed(session, seed, seed_dir)

    await session.commit()
    return {"experiments": n_exp, "seeds": n_seed, "decisions": n_dec}
