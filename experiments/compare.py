"""Compare summary.json across multiple runs side-by-side.

Usage:
    python -m experiments.compare results/olist_*_no_drift
"""
from __future__ import annotations

from pathlib import Path
import json
import click


METRICS = [
    ("stockout_rate", "Stockout rate", "{:.2%}"),
    ("total_cost", "Total cost", "{:,.0f}"),
    ("holding_cost", " - holding", "{:,.0f}"),
    ("ordering_cost", " - ordering", "{:,.0f}"),
    ("stockout_cost", " - stockout", "{:,.0f}"),
    ("final_total_on_hand", "Final on-hand", "{:,}"),
    ("n_orders", "Orders placed", "{:,}"),
    ("total_units_ordered", "Units ordered", "{:,}"),
    ("time_to_recovery_steps", "Recovery (days)", "{}"),
    ("mean_service_level_post_drift", "Mean SL post-drift", "{:.2%}"),
    ("drift_start_step", "Drift onset step", "{}"),
    ("forecast_mape", "Forecast MAPE", "{:.2%}"),
    ("n_drift_events", "Per-SKU drift events", "{:,}"),
    ("n_global_drift_events", "Global drift events", "{:,}"),
    ("n_refits", "Refits", "{:,}"),
    ("n_steps", "Test steps", "{}"),
    ("fit_window", "Fit window", "{}"),
]


def _load(run_dir: Path) -> dict:
    with open(run_dir / "summary.json") as f:
        data = json.load(f)
    data["_run"] = run_dir.name
    return data


def _fmt(value, template: str) -> str:
    if value is None:
        return "—"
    try:
        return template.format(value)
    except (TypeError, ValueError):
        return str(value)


@click.command()
@click.argument(
    "run_dirs",
    nargs=-1,
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    required=True,
)
def main(run_dirs: tuple[Path, ...]) -> None:
    runs = [_load(p) for p in run_dirs]
    name_w = max(len(label) for _, label, _ in METRICS) + 2
    col_w = max(max(len(r["_run"]) for r in runs), 14) + 2

    header = "Metric".ljust(name_w) + "".join(r["_run"].ljust(col_w) for r in runs)
    click.echo(header)
    click.echo("-" * len(header))
    policies = "policy".ljust(name_w) + "".join(
        r.get("policy", "—").ljust(col_w) for r in runs
    )
    click.echo(policies)
    click.echo("")
    for key, label, template in METRICS:
        row = label.ljust(name_w) + "".join(
            _fmt(r.get(key), template).ljust(col_w) for r in runs
        )
        click.echo(row)


if __name__ == "__main__":
    main()
