"""Aggregate per-seed summaries into a single mean/std/CI/percentile table.

Reads `results/<base_name>/seed_*/summary.json` and writes
`results/<base_name>/aggregate.json` with descriptive statistics per metric.

Usage:
    python -m experiments.aggregate results/olist_mas_catastrophic
    python -m experiments.aggregate results/olist_*_catastrophic
"""
from __future__ import annotations

import argparse
import json
import math
import statistics
from pathlib import Path


# Numeric metrics we aggregate. Anything else (dicts, strings) is skipped.
METRICS_TO_AGGREGATE = [
    "stockout_rate",
    "total_cost",
    "holding_cost",
    "ordering_cost",
    "stockout_cost",
    "final_total_on_hand",
    "n_orders",
    "total_units_ordered",
    "time_to_recovery_steps",
    "mean_service_level_post_drift",
    "forecast_mape",
    "n_drift_events",
    "n_global_drift_events",
    "n_refits",
    "runtime_seconds",
    "time_per_step_ms",
    "peak_python_mem_mb",
    "delta_rss_mb",
    "n_skus_used",
]


def _load_seed_summaries(base_dir: Path) -> list[dict]:
    summaries: list[dict] = []
    for sub in sorted(base_dir.glob("seed_*")):
        s_path = sub / "summary.json"
        if s_path.exists():
            with open(s_path) as f:
                summaries.append(json.load(f))
    return summaries


def _ci95_mean(values: list[float]) -> tuple[float, float]:
    """95% CI for the mean using the Student-t approximation (n-1 dof)."""
    n = len(values)
    if n < 2:
        return (values[0] if values else 0.0,) * 2  # noqa
    mean = statistics.mean(values)
    sd = statistics.stdev(values)
    se = sd / math.sqrt(n)
    # Normal-approx z=1.96 is fine for n>=10; use slightly wider t for n=2..9.
    t_crit = {1: 12.71, 2: 4.30, 3: 3.18, 4: 2.78, 5: 2.57, 6: 2.45,
              7: 2.36, 8: 2.31, 9: 2.26}.get(n - 1, 1.96)
    half = t_crit * se
    return mean - half, mean + half


def aggregate(base_dir: Path) -> dict:
    summaries = _load_seed_summaries(base_dir)
    if not summaries:
        return {"n_seeds": 0, "metrics": {}}
    metrics: dict[str, dict] = {}
    for key in METRICS_TO_AGGREGATE:
        raw = [s.get(key) for s in summaries]
        values = [float(v) for v in raw if v is not None and not isinstance(v, (dict, list))]
        if not values:
            continue
        ci_lo, ci_hi = _ci95_mean(values)
        metrics[key] = {
            "n": len(values),
            "mean": statistics.mean(values),
            "std": statistics.stdev(values) if len(values) > 1 else 0.0,
            "min": min(values),
            "p25": statistics.quantiles(values, n=4)[0] if len(values) >= 4 else min(values),
            "median": statistics.median(values),
            "p75": statistics.quantiles(values, n=4)[2] if len(values) >= 4 else max(values),
            "max": max(values),
            "ci95_lo": ci_lo,
            "ci95_hi": ci_hi,
            "raw": values,
        }
    return {
        "name": summaries[0].get("policy", base_dir.name),
        "policy": summaries[0].get("policy"),
        "n_seeds": len(summaries),
        "metrics": metrics,
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="python -m experiments.aggregate")
    p.add_argument("paths", nargs="+", type=Path,
                   help="One or more `results/<base_name>` directories.")
    args = p.parse_args(argv)
    for base in args.paths:
        if not base.is_dir():
            print(f"skip {base} (not a directory)")
            continue
        agg = aggregate(base)
        out = base / "aggregate.json"
        with open(out, "w") as f:
            json.dump(agg, f, indent=2, default=str)
        print(f"{base.name}: n_seeds={agg['n_seeds']}  -> {out}")
        # Brief on-screen table
        for k, v in agg["metrics"].items():
            print(f"  {k:32s} mean={v['mean']:>12.4f}  std={v['std']:>10.4f}  "
                  f"95%CI=[{v['ci95_lo']:.4f}, {v['ci95_hi']:.4f}]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
