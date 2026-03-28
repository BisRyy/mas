"""Experiment runner.

Dispatches on `cfg.policy`:
  - static_rop          -> BaselineModel with StaticROPBaseline
  - periodic_forecasting -> BaselineModel with PeriodicForecastingBaseline
  - mas                 -> InventoryModel (the proposed multi-agent system)

All three policies run on the same test window `[fit_window, fit_window + n_steps)`
of the same processed Olist data, so summaries are directly comparable.

Usage:
    python -m experiments.run --config experiments/configs/<name>.yaml
"""
from __future__ import annotations

from collections import defaultdict
from pathlib import Path
import csv
import json
import click

from src.utils import load_config, set_global_seed, jitter_initial_stock
from src.simulation import (
    InventoryModel,
    BaselineModel,
    OrderReplay,
    DriftInjector,
    build_scenarios_from_config,
    primary_drift_start,
)
from src.metrics.adaptability import time_to_recovery
from src.metrics.cost import CostWeights, total_cost


def _build_warmup_history(
    replay: OrderReplay, fit_window: int
) -> dict[str, list[float]]:
    """Aggregate per-SKU demand over [0, fit_window) for forecaster warm-up."""
    history: dict[str, list[float]] = defaultdict(list)
    for step in range(fit_window):
        events = replay.events_for_step(step)
        for sku, qty in events.items():
            history[sku].append(float(qty))
    return dict(history)


def _build_drift_injector(cfg: dict, replay: OrderReplay) -> DriftInjector:
    scenarios_cfg = cfg.get("drift", {}).get("scenarios", []) or []
    return DriftInjector(scenarios=build_scenarios_from_config(scenarios_cfg, replay))


def _resolved_initial_stock(cfg: dict) -> dict[str, int] | None:
    """Apply per-seed jitter to the configured initial_stock dict.

    Jitter is keyed on `(cfg.seed, "initial_stock")` so different seeds
    produce different starting stocks but all three policies within the
    same seed see the *same* starting stocks — preserving fair comparison.
    """
    initial = cfg.get("initial_stock")
    if not initial:
        return None
    jitter = float(cfg.get("stochastic", {}).get("initial_stock_jitter", 0.0))
    if jitter <= 0:
        return dict(initial)
    seed = int(cfg.get("seed", 42))
    # Sub-key the RNG so it's independent of the model's main seed.
    return jitter_initial_stock(initial, jitter_pct=jitter, seed=seed * 7919 + 1)


def _run_baseline(cfg: dict, policy_name: str, replay: OrderReplay) -> tuple[dict, list[dict], object]:
    fit_window = int(cfg.get("fit_window", 90))
    drift = _build_drift_injector(cfg, replay)
    model = BaselineModel(
        skus=replay.skus,
        replay=replay,
        policy_name=policy_name,
        drift_injector=drift,
        initial_stock=_resolved_initial_stock(cfg),
        lead_time=int(cfg.get("lead_time", 7)),
        fit_window=fit_window,
        service_level_z=float(cfg.get("service_level_z", 1.65)),
        refit_interval=int(cfg.get("refit_interval", 30)),
        recent_window=int(cfg.get("recent_window", 90)),
    )
    model.fit_warmup()
    test_n_steps = int(cfg["n_steps"]) - fit_window
    if test_n_steps <= 0:
        raise ValueError(
            f"n_steps ({cfg['n_steps']}) must exceed fit_window ({fit_window})."
        )
    result = model.run(n_steps=test_n_steps)
    return result.to_summary(), result.timeseries, model


def _run_mas(cfg: dict, replay: OrderReplay) -> tuple[dict, list[dict], object]:
    fit_window = int(cfg.get("fit_window", 90))
    drift = _build_drift_injector(cfg, replay)
    warmup = _build_warmup_history(replay, fit_window)
    mas_cfg = cfg.get("mas", {}) or {}
    forecaster_kwargs = {
        k: v for k, v in mas_cfg.get("forecaster", {}).items()
    }
    replenisher_kwargs = {
        k: v for k, v in mas_cfg.get("replenisher", {}).items()
    }
    supplier_kwargs = {
        k: v for k, v in mas_cfg.get("supplier", {}).items()
    }
    # Allow `lead_time` at top level (shared with baselines) to flow to supplier.
    if "lead_time" in cfg and "default_lead_time" not in supplier_kwargs:
        supplier_kwargs["default_lead_time"] = int(cfg["lead_time"])
    # Same for service_level_z.
    if "service_level_z" in cfg and "service_level_z" not in replenisher_kwargs:
        replenisher_kwargs["service_level_z"] = float(cfg["service_level_z"])

    model = InventoryModel(
        skus=replay.skus,
        replay=replay,
        drift_injector=drift,
        initial_stock=_resolved_initial_stock(cfg),
        seed=int(cfg.get("seed", 42)),
        warmup_history=warmup,
        start_step=fit_window,
        forecaster_kwargs=forecaster_kwargs,
        replenisher_kwargs=replenisher_kwargs,
        supplier_kwargs=supplier_kwargs,
    )
    test_n_steps = int(cfg["n_steps"]) - fit_window
    if test_n_steps <= 0:
        raise ValueError(
            f"n_steps ({cfg['n_steps']}) must exceed fit_window ({fit_window})."
        )
    summary = model.run(n_steps=test_n_steps)
    return summary, list(model.analytics.timeseries), model


POLICY_HANDLERS = {
    "static_rop": lambda cfg, replay: _run_baseline(cfg, "static_rop", replay),
    "periodic_forecasting": lambda cfg, replay: _run_baseline(
        cfg, "periodic_forecasting", replay
    ),
    "mas": _run_mas,
}


def _write_timeseries_csv(timeseries: list[dict], path: Path) -> None:
    if not timeseries:
        return
    fields = sorted({k for row in timeseries for k in row.keys()})
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(timeseries)


def _augment_with_costs(summary: dict, timeseries: list[dict], cfg: dict) -> None:
    """Attach holding/ordering/stockout/total cost using cfg['costs'] weights.

    Holding is integrated across the test-window timeseries; stockout cost
    treats `stockout_duration_per_sku` as the sum of SKU-step pairs spent
    in stockout (the proposal's "stockout duration" metric).
    """
    weights = CostWeights.from_config(cfg.get("costs"))
    on_hand_series = [row.get("total_on_hand", 0) for row in timeseries]
    stockout_sku_steps = sum((summary.get("stockout_duration_per_sku") or {}).values())
    costs = total_cost(
        on_hand_per_step=on_hand_series,
        n_orders=int(summary.get("n_orders", 0)),
        stockout_sku_steps=int(stockout_sku_steps),
        weights=weights,
    )
    summary.update(costs)
    summary["cost_weights"] = {
        "holding": weights.holding,
        "ordering": weights.ordering,
        "stockout": weights.stockout,
    }


def _augment_with_recovery(
    summary: dict, timeseries: list[dict], cfg: dict, n_total_skus: int
) -> None:
    """If drift was configured, compute time-to-recovery from per-step snapshots."""
    drift_start = primary_drift_start(cfg.get("drift", {}).get("scenarios", []))
    if drift_start is None or not timeseries:
        return
    fit_window = int(cfg.get("fit_window", 90))
    # Convert absolute drift step -> offset within the test-window timeseries.
    drift_offset = drift_start - fit_window
    if drift_offset < 0:
        # Drift began during warm-up; report 0 so we still get a number.
        drift_offset = 0
    # Service level per step: 1 - (stockout_skus_step / total_skus).
    service_levels = [
        1.0 - (row.get("stockout_skus_step", 0) / max(n_total_skus, 1))
        for row in timeseries
    ]
    ttr = time_to_recovery(
        service_levels,
        drift_step=drift_offset,
        target=float(cfg.get("recovery_target", 0.95)),
        sustained_window=int(cfg.get("recovery_window", 7)),
    )
    summary["drift_start_step"] = drift_start
    summary["time_to_recovery_steps"] = ttr
    summary["mean_service_level_post_drift"] = (
        sum(service_levels[drift_offset:]) / max(len(service_levels) - drift_offset, 1)
    )


@click.command()
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    required=True,
    help="Path to a YAML experiment config.",
)
def main(config: Path) -> None:
    cfg = load_config(config)
    set_global_seed(int(cfg.get("seed", 42)))

    policy = cfg.get("policy", "mas")
    if policy not in POLICY_HANDLERS:
        raise click.ClickException(
            f"Unknown policy {policy!r}. Choose from {sorted(POLICY_HANDLERS)}."
        )

    replay = OrderReplay.from_csv(cfg["data"]["processed_path"])
    summary, timeseries, model = POLICY_HANDLERS[policy](cfg, replay)
    summary["policy"] = policy
    summary["fit_window"] = int(cfg.get("fit_window", 90))
    summary["config"] = str(config)
    _augment_with_costs(summary, timeseries, cfg)
    _augment_with_recovery(summary, timeseries, cfg, n_total_skus=len(replay.skus))

    out_dir = Path(cfg.get("results_dir", "results")) / cfg.get("name", "default")
    out_dir.mkdir(parents=True, exist_ok=True)
    with open(out_dir / "summary.json", "w") as f:
        json.dump(summary, f, indent=2, default=str)
    _write_timeseries_csv(timeseries, out_dir / "timeseries.csv")

    # Optional decision-log dump for the dashboard's audit-trail viewer.
    from src.utils.decision_export import write_decisions_jsonl
    n_decisions = write_decisions_jsonl(model, out_dir)
    if n_decisions:
        click.echo(f"[{policy}] wrote {n_decisions} decisions to "
                   f"{out_dir / 'decisions.jsonl'}")

    click.echo(f"[{policy}] wrote {out_dir / 'summary.json'}")


if __name__ == "__main__":
    main()
