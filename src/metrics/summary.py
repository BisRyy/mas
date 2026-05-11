"""Run-level summary used by `AnalyticsAgent.summary()`."""
from __future__ import annotations

from typing import Any

from .stockout import stockout_rate, stockout_duration


def summarize_run(analytics_agent: Any) -> dict[str, Any]:
    """Aggregate per-step snapshots and per-agent logs into a single dict.

    Lightweight on purpose — full analyses live in notebooks. The runner
    serializes this dict alongside the raw per-step JSONL log.
    """
    timeseries = analytics_agent.timeseries
    monitor = analytics_agent.model.monitor
    n_steps = len(timeseries)

    steps_with_stockout = sum(1 for s in timeseries if s["stockout_skus_step"] > 0)

    return {
        "n_steps": n_steps,
        "stockout_rate": stockout_rate(steps_with_stockout, n_steps),
        "stockout_duration_per_sku": stockout_duration(monitor.stockout_steps),
        "final_total_on_hand": timeseries[-1]["total_on_hand"] if timeseries else 0,
    }
