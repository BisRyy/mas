"""Run-level summary used by `AnalyticsAgent.summary()`."""
from __future__ import annotations

from typing import Any

from .stockout import stockout_rate, stockout_duration
from .forecast import mape


def _aggregate_mape(forecaster: Any) -> float:
    """Mean MAPE across SKUs that have at least one prediction-actual pair."""
    per_sku: list[float] = []
    for sku, preds in getattr(forecaster, "predictions", {}).items():
        actuals = forecaster.actuals.get(sku, [])
        # Align lengths: predictions[t] vs actuals[t] for shared indices.
        k = min(len(preds), len(actuals))
        if k == 0:
            continue
        per_sku.append(mape(actuals[:k], preds[:k]))
    return float(sum(per_sku) / len(per_sku)) if per_sku else 0.0


def _refit_methods_breakdown(forecaster: Any) -> dict[str, int]:
    breakdown: dict[str, int] = {"ma": 0, "ses": 0, "hw": 0}
    for fitted in getattr(forecaster, "models", {}).values():
        method = getattr(fitted, "method", None)
        if method in breakdown:
            breakdown[method] += 1
    return breakdown


def summarize_run(analytics_agent: Any) -> dict[str, Any]:
    """Aggregate per-step snapshots and per-agent logs into a single dict."""
    timeseries = analytics_agent.timeseries
    monitor = analytics_agent.model.monitor
    n_steps = len(timeseries)

    steps_with_stockout = sum(1 for s in timeseries if s["stockout_skus_step"] > 0)

    supplier = analytics_agent.model.supplier
    forecaster = analytics_agent.model.forecaster

    return {
        "n_steps": n_steps,
        "stockout_rate": stockout_rate(steps_with_stockout, n_steps),
        "stockout_duration_per_sku": stockout_duration(monitor.stockout_steps),
        "final_total_on_hand": timeseries[-1]["total_on_hand"] if timeseries else 0,
        "n_orders": getattr(supplier, "n_orders", 0),
        "total_units_ordered": getattr(supplier, "total_units_ordered", 0),
        "forecast_mape": _aggregate_mape(forecaster),
        "n_drift_events": len(getattr(forecaster, "drift_events", [])),
        "n_global_drift_events": len(
            getattr(forecaster, "global_drift_steps", [])
        ),
        "n_refits": getattr(forecaster, "refit_count", 0),
        "active_model_methods": _refit_methods_breakdown(forecaster),
    }
