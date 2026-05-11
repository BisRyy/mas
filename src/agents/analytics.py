"""Analytics Agent.

Continuously evaluates system performance. Aggregates per-step metrics from
the other agents (stockouts, holding, ordering, forecast error) and exposes
a results object the experiment runner can serialize.
"""
from __future__ import annotations

from typing import Any

from .base import BaseInventoryAgent


class AnalyticsAgent(BaseInventoryAgent):
    def __init__(self, model: Any) -> None:
        super().__init__(model)
        self.timeseries: list[dict] = []

    def step(self) -> None:
        monitor = self.model.monitor
        snapshot = {
            "step": self.model.steps,
            "total_on_hand": sum(monitor.stock.values()),
            "stockout_skus_step": sum(
                1 for sku in self.model.skus if monitor.level(sku) == 0
            ),
        }
        self.timeseries.append(snapshot)
        self.log("metrics_snapshot", **snapshot)

    def summary(self) -> dict[str, Any]:
        """Return aggregated metrics for the current run.

        Real metric computation lives in `src/metrics/`; this method just
        delegates so the experiment runner has a single call site.
        """
        from src.metrics import summarize_run  # local import to avoid cycles

        return summarize_run(self)
