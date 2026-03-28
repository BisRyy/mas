"""H3 — Scalability hypothesis test.

Proposal §1.5, H3: "The system's computational overhead will grow linearly
with the number of agents, remaining feasible for standard commodity
hardware."

Operates on aggregated `results/olist_scale_<policy>_n<N>/aggregate.json`
files and produces:

  - results/h3_report.json
  - results/h3_report.csv  (one row per (policy, n_skus))
  - stdout markdown table + complexity classification

Methodology:
  1. For each policy, fit a power-law `t = a * n^b` to (n_skus, runtime).
     The exponent `b` classifies the complexity:
       b ≈ 1.0  -> linear (validates H3)
       b < 1.0  -> sublinear (better than H3)
       b > 1.2  -> super-linear (rejects H3)
  2. Also fit a linear `t = a + b*n` and report R² for that model.
  3. Report peak Python memory vs n_skus likewise.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

POLICIES = ["static_rop", "periodic_forecasting", "mas"]


def _load_aggregate(policy: str, n: int) -> dict | None:
    p = Path(f"results/olist_scale_{policy}_n{n}/aggregate.json")
    if not p.exists():
        return None
    with open(p) as f:
        return json.load(f)


def _power_law_fit(xs: list[float], ys: list[float]) -> tuple[float, float, float]:
    """Fit y = a * x^b via least squares on log-log. Returns (a, b, R²)."""
    if len(xs) < 2:
        return float("nan"), float("nan"), float("nan")
    lx = [math.log(x) for x in xs]
    ly = [math.log(max(y, 1e-12)) for y in ys]
    n = len(lx)
    sx = sum(lx); sy = sum(ly)
    sxx = sum(v * v for v in lx)
    sxy = sum(a * b for a, b in zip(lx, ly))
    denom = (n * sxx - sx * sx)
    if denom == 0:
        return float("nan"), float("nan"), float("nan")
    b = (n * sxy - sx * sy) / denom
    log_a = (sy - b * sx) / n
    a = math.exp(log_a)
    # R² on log-log scale.
    mean_ly = sy / n
    ss_tot = sum((v - mean_ly) ** 2 for v in ly)
    ss_res = sum((ly[i] - (log_a + b * lx[i])) ** 2 for i in range(n))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else float("nan")
    return a, b, r2


def _linear_fit(xs: list[float], ys: list[float]) -> tuple[float, float, float]:
    """Fit y = a + b*x. Returns (a, b, R²)."""
    if len(xs) < 2:
        return float("nan"), float("nan"), float("nan")
    n = len(xs)
    sx = sum(xs); sy = sum(ys)
    sxx = sum(v * v for v in xs)
    sxy = sum(xs[i] * ys[i] for i in range(n))
    denom = (n * sxx - sx * sx)
    if denom == 0:
        return float("nan"), float("nan"), float("nan")
    b = (n * sxy - sx * sy) / denom
    a = (sy - b * sx) / n
    mean_y = sy / n
    ss_tot = sum((v - mean_y) ** 2 for v in ys)
    ss_res = sum((ys[i] - (a + b * xs[i])) ** 2 for i in range(n))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else float("nan")
    return a, b, r2


def _classify_complexity(exponent: float) -> str:
    if math.isnan(exponent):
        return "insufficient data"
    if exponent < 0.5:
        return "near-constant"
    if exponent < 0.9:
        return "sublinear"
    if exponent <= 1.1:
        return "linear"
    if exponent <= 1.5:
        return "near-linear"
    if exponent <= 2.1:
        return "quadratic-ish"
    return "super-quadratic"


def main() -> int:
    sizes_per_policy: dict[str, list[int]] = {p: [] for p in POLICIES}
    rows: list[dict] = []
    for policy in POLICIES:
        for path in sorted(Path("results").glob(f"olist_scale_{policy}_n*")):
            try:
                n = int(path.name.rsplit("_n", 1)[1])
            except ValueError:
                continue
            agg = _load_aggregate(policy, n)
            if not agg:
                continue
            m = agg.get("metrics", {})
            row = {
                "policy": policy,
                "n_skus": n,
                "n_seeds": agg.get("n_seeds", 0),
            }
            for key in (
                "runtime_seconds", "time_per_step_ms",
                "peak_python_mem_mb", "delta_rss_mb",
                "stockout_rate", "total_cost",
                "n_orders", "n_refits", "n_global_drift_events",
            ):
                if key in m:
                    row[f"{key}_mean"] = m[key]["mean"]
                    row[f"{key}_std"] = m[key]["std"]
            rows.append(row)
            sizes_per_policy[policy].append(n)

    if not rows:
        print("No scalability results found.")
        return 1

    fits: dict[str, dict] = {}
    for policy in POLICIES:
        pol_rows = [r for r in rows if r["policy"] == policy]
        pol_rows.sort(key=lambda r: r["n_skus"])
        ns = [float(r["n_skus"]) for r in pol_rows]
        rts = [float(r["runtime_seconds_mean"]) for r in pol_rows if "runtime_seconds_mean" in r]
        mems = [float(r["peak_python_mem_mb_mean"]) for r in pol_rows if "peak_python_mem_mb_mean" in r]
        if len(rts) >= 2:
            a, b, r2 = _power_law_fit(ns[:len(rts)], rts)
            la, lb, lr2 = _linear_fit(ns[:len(rts)], rts)
            ma, mb, mr2 = _power_law_fit(ns[:len(mems)], mems) if mems else (float("nan"),)*3
            fits[policy] = {
                "n_points": len(rts),
                "runtime_powerlaw": {"a": a, "b": b, "r2": r2,
                                     "complexity": _classify_complexity(b)},
                "runtime_linear":   {"intercept": la, "slope": lb, "r2": lr2},
                "memory_powerlaw":  {"a": ma, "b": mb, "r2": mr2,
                                     "complexity": _classify_complexity(mb)},
            }

    # Write outputs.
    Path("results/h3_report.json").write_text(
        json.dumps({"rows": rows, "fits": fits}, indent=2, default=str)
    )
    import csv
    fields = sorted({k for r in rows for k in r.keys()})
    with open("results/h3_report.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

    # Stdout report.
    print("\n## H3 — Runtime scaling: power-law fit `t = a * n^b`\n")
    print("| Policy | b (exponent) | R² | Classification | Linear R² |")
    print("|---|---:|---:|---|---:|")
    for policy, fit in fits.items():
        rp = fit["runtime_powerlaw"]; rl = fit["runtime_linear"]
        print(
            f"| {policy} | {rp['b']:.3f} | {rp['r2']:.4f} | "
            f"{rp['complexity']} | {rl['r2']:.4f} |"
        )

    print("\n## Memory scaling: power-law fit on peak Python heap\n")
    print("| Policy | b (exponent) | R² | Classification |")
    print("|---|---:|---:|---|")
    for policy, fit in fits.items():
        mp = fit["memory_powerlaw"]
        print(
            f"| {policy} | {mp['b']:.3f} | {mp['r2']:.4f} | {mp['complexity']} |"
        )

    print("\n## Raw data\n")
    print("| Policy | N SKUs | Runtime (s) | t/step (ms) | Peak heap (MB) | Stockout |")
    print("|---|---:|---:|---:|---:|---:|")
    for r in sorted(rows, key=lambda r: (r["policy"], r["n_skus"])):
        print(
            f"| {r['policy']} | {r['n_skus']:,} | "
            f"{r.get('runtime_seconds_mean', 0):.2f} | "
            f"{r.get('time_per_step_ms_mean', 0):.2f} | "
            f"{r.get('peak_python_mem_mb_mean', 0):.1f} | "
            f"{r.get('stockout_rate_mean', 0):.2%} |"
        )
    print("\nWrote: results/h3_report.json, results/h3_report.csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
