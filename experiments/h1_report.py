"""H1 hypothesis tests across every scenario.

Proposal §1.5, H1: MAS reduces daily stockout rate by at least 10% vs Static
ROP, with statistical significance p < 0.05.

Produces:
  - A summary table to stdout (markdown)
  - results/h1_report.json
  - results/h1_report.csv

For each scenario, runs Mann-Whitney U and Welch's t-test on
`stockout_rate` and `total_cost` for MAS vs each baseline.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

from experiments.stats import compare, _values


SCENARIOS = ["no_drift", "abrupt", "gradual", "seasonal", "severe_abrupt", "catastrophic"]
BASELINES = ["static_rop", "periodic_forecasting"]
METRICS = ["stockout_rate", "total_cost"]


def dir_for(policy: str, scen: str) -> Path:
    return Path("results") / f"olist_{policy}_{scen}"


def main() -> int:
    results: list[dict] = []
    for scen in SCENARIOS:
        treat = _values(dir_for("mas", scen), "stockout_rate")
        if not treat:
            print(f"skip {scen}: no MAS values"); continue
        for baseline in BASELINES:
            for metric in METRICS:
                treat_vals = _values(dir_for("mas", scen), metric)
                base_vals = _values(dir_for(baseline, scen), metric)
                stat = compare(treat_vals, base_vals)
                stat.update({
                    "scenario": scen,
                    "baseline": baseline,
                    "treatment": "mas",
                    "metric": metric,
                })
                results.append(stat)

    out_json = Path("results/h1_report.json")
    with open(out_json, "w") as f:
        json.dump(results, f, indent=2, default=str)

    out_csv = Path("results/h1_report.csv")
    fields = [
        "scenario", "baseline", "metric", "n_treatment", "n_baseline",
        "treatment_mean", "baseline_mean", "abs_diff", "rel_change",
        "mannwhitney_u", "mannwhitney_p", "welch_t", "welch_p", "cohens_d",
    ]
    with open(out_csv, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(results)

    # Markdown summary -- pivots on (scenario × baseline) for stockout_rate.
    print("\n## H1 — stockout_rate: MAS vs baselines\n")
    print("| Scenario | Baseline | MAS mean | Baseline mean | Rel Δ | MW p | Welch p | Cohen d |")
    print("|---|---|---:|---:|---:|---:|---:|---:|")
    for r in results:
        if r["metric"] != "stockout_rate":
            continue
        sig = " **<0.05**" if r["mannwhitney_p"] < 0.05 else ""
        print(
            f"| {r['scenario']} | {r['baseline']} | {r['treatment_mean']:.2%} | "
            f"{r['baseline_mean']:.2%} | {r['rel_change']:+.1%} | "
            f"{r['mannwhitney_p']:.4f}{sig} | {r['welch_p']:.2e} | {r['cohens_d']:+.1f} |"
        )

    print("\n## Cost differential: MAS vs baselines\n")
    print("| Scenario | Baseline | MAS mean | Baseline mean | Rel Δ | MW p | Welch p | Cohen d |")
    print("|---|---|---:|---:|---:|---:|---:|---:|")
    for r in results:
        if r["metric"] != "total_cost":
            continue
        sig = " **<0.05**" if r["mannwhitney_p"] < 0.05 else ""
        print(
            f"| {r['scenario']} | {r['baseline']} | ${r['treatment_mean']:,.0f} | "
            f"${r['baseline_mean']:,.0f} | {r['rel_change']:+.1%} | "
            f"{r['mannwhitney_p']:.4f}{sig} | {r['welch_p']:.2e} | {r['cohens_d']:+.1f} |"
        )

    print(f"\nWrote: {out_json}, {out_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
