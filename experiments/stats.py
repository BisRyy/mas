"""Hypothesis tests for headline policy comparisons.

For each metric and each (treatment, baseline) pair this computes:
  - Mann-Whitney U (non-parametric, no normality assumption)
  - Welch's t-test (handles unequal variance)
  - Cohen's d (effect size, pooled-SD variant)

Operates on the per-seed `summary.json` files written by `sweep.py`.
A typical call validates H1 on the no-drift scenario:

    python -m experiments.stats \
        --baseline results/olist_static_rop_no_drift \
        --treatment results/olist_mas_no_drift \
        --metric stockout_rate
"""
from __future__ import annotations

import argparse
import json
import math
import statistics
from pathlib import Path

from scipy import stats as sps


def _values(base: Path, metric: str) -> list[float]:
    out: list[float] = []
    for sub in sorted(base.glob("seed_*")):
        s = sub / "summary.json"
        if not s.exists():
            continue
        with open(s) as f:
            data = json.load(f)
        v = data.get(metric)
        if v is None or isinstance(v, (dict, list)):
            continue
        try:
            out.append(float(v))
        except (TypeError, ValueError):
            continue
    return out


def cohens_d(a: list[float], b: list[float]) -> float:
    """Cohen's d using pooled standard deviation."""
    if len(a) < 2 or len(b) < 2:
        return float("nan")
    var_a = statistics.variance(a)
    var_b = statistics.variance(b)
    pooled = math.sqrt(((len(a) - 1) * var_a + (len(b) - 1) * var_b) /
                       (len(a) + len(b) - 2))
    if pooled == 0:
        return float("nan")
    return (statistics.mean(a) - statistics.mean(b)) / pooled


def compare(treatment: list[float], baseline: list[float]) -> dict:
    if not treatment or not baseline:
        return {"error": "empty sample"}
    mw = sps.mannwhitneyu(treatment, baseline, alternative="two-sided")
    welch = sps.ttest_ind(treatment, baseline, equal_var=False)
    return {
        "n_treatment": len(treatment),
        "n_baseline": len(baseline),
        "treatment_mean": statistics.mean(treatment),
        "baseline_mean": statistics.mean(baseline),
        "abs_diff": statistics.mean(treatment) - statistics.mean(baseline),
        "rel_change": (
            (statistics.mean(treatment) - statistics.mean(baseline))
            / abs(statistics.mean(baseline))
            if statistics.mean(baseline) != 0 else float("nan")
        ),
        "mannwhitney_u": float(mw.statistic),
        "mannwhitney_p": float(mw.pvalue),
        "welch_t": float(welch.statistic),
        "welch_p": float(welch.pvalue),
        "cohens_d": cohens_d(treatment, baseline),
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="python -m experiments.stats")
    p.add_argument("--baseline", required=True, type=Path,
                   help="results/<base_dir> for the baseline condition")
    p.add_argument("--treatment", required=True, type=Path,
                   help="results/<base_dir> for the treatment condition")
    p.add_argument("--metric", default="stockout_rate",
                   help="Metric to test (default: stockout_rate)")
    args = p.parse_args(argv)

    base_vals = _values(args.baseline, args.metric)
    treat_vals = _values(args.treatment, args.metric)
    result = compare(treat_vals, base_vals)
    result["metric"] = args.metric
    result["baseline_dir"] = str(args.baseline)
    result["treatment_dir"] = str(args.treatment)

    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
