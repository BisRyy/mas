"""Ablation study report.

Compares the full MAS against three ablations on the catastrophic scenario:

  full       — all components enabled (control)
  no_adwin   — drift detector disabled (adwin_delta=1000)
  ma_only    — forecaster forced to moving-average tier
  no_safety  — replenisher uses zero safety stock

Outputs:
  - results/ablation_report.json
  - results/ablation_report.csv
  - stdout markdown table
"""
from __future__ import annotations

import csv
import json
from pathlib import Path


VARIANTS = ["full", "no_adwin", "ma_only", "no_safety"]
METRICS = [
    "stockout_rate", "total_cost",
    "holding_cost", "ordering_cost", "stockout_cost",
    "n_orders", "total_units_ordered",
    "forecast_mape", "n_drift_events", "n_global_drift_events", "n_refits",
    "time_per_step_ms",
]


def _load_agg(variant: str) -> dict | None:
    p = Path(f"results/olist_ablation_{variant}/aggregate.json")
    if not p.exists():
        return None
    with open(p) as f:
        return json.load(f)


def main() -> int:
    aggs = {v: _load_agg(v) for v in VARIANTS}
    full = aggs.get("full")
    if not full:
        print("Missing results/olist_ablation_full/aggregate.json. Run the sweep first.")
        return 1

    rows = []
    full_metrics = full.get("metrics", {})
    for v in VARIANTS:
        agg = aggs.get(v)
        if not agg:
            print(f"warning: missing aggregate for {v!r}")
            continue
        m = agg.get("metrics", {})
        row = {"variant": v, "n_seeds": agg.get("n_seeds", 0)}
        for k in METRICS:
            if k not in m:
                continue
            row[f"{k}_mean"] = m[k]["mean"]
            row[f"{k}_std"] = m[k]["std"]
            if v != "full" and k in full_metrics:
                base = full_metrics[k]["mean"]
                if base != 0:
                    row[f"{k}_rel_to_full"] = (m[k]["mean"] - base) / abs(base)
        rows.append(row)

    Path("results/ablation_report.json").write_text(
        json.dumps({"rows": rows}, indent=2, default=str)
    )
    fields = sorted({k for r in rows for k in r.keys()})
    with open("results/ablation_report.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

    # Markdown summary.
    headline_metrics = [
        ("stockout_rate", "Stockout rate", "{:.2%}"),
        ("total_cost", "Total cost", "${:,.0f}"),
        ("holding_cost", "  - holding", "${:,.0f}"),
        ("ordering_cost", "  - ordering", "${:,.0f}"),
        ("stockout_cost", "  - stockout", "${:,.0f}"),
        ("forecast_mape", "Forecast MAPE", "{:.1%}"),
        ("n_global_drift_events", "Global drift events", "{:.1f}"),
        ("n_refits", "Refits", "{:.0f}"),
    ]

    print("\n## Ablation results on the catastrophic drift scenario\n")
    headers = ["Metric"] + [v for v in VARIANTS if any(r["variant"] == v for r in rows)]
    print("| " + " | ".join(headers) + " |")
    print("|" + "|".join(["---"] * len(headers)) + "|")
    for key, label, fmt in headline_metrics:
        row_cells = [label]
        for v in headers[1:]:
            r = next((r for r in rows if r["variant"] == v), None)
            if r and f"{key}_mean" in r:
                cell = fmt.format(r[f"{key}_mean"])
                if v != "full" and f"{key}_rel_to_full" in r:
                    delta = r[f"{key}_rel_to_full"]
                    cell += f" ({delta:+.1%})"
            else:
                cell = "—"
            row_cells.append(cell)
        print("| " + " | ".join(row_cells) + " |")

    print("\nDeltas in parentheses are relative to `full` (control). "
          "Negative = ablation improves that metric (rare); positive = ablation hurts.")
    print("\nWrote: results/ablation_report.{json,csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
