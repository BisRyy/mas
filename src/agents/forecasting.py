"""Demand Forecasting Agent.

Predicts future per-SKU demand. Hosts a forecasting model (ARIMA, exponential
smoothing, or a regression model) and re-fits it when the drift detector
signals a distribution change.
"""
from __future__ import annotations

from collections import defaultdict, deque
from typing import Any

from .base import BaseInventoryAgent


class DemandForecastingAgent(BaseInventoryAgent):
    def __init__(
        self,
        model: Any,
        history_window: int = 90,
        forecast_horizon: int = 7,
    ) -> None:
        super().__init__(model)
        self.history_window = history_window
        self.forecast_horizon = forecast_horizon
        # Per-SKU rolling demand history.
        self.history: dict[str, deque[float]] = defaultdict(
            lambda: deque(maxlen=self.history_window)
        )
        # Per-SKU fitted models — populated by `fit_models`.
        self.models: dict[str, Any] = {}

    # --- API used by the Replenishment agent ------------------------------
    def predict(self, sku: str) -> float:
        """Return expected demand for `sku` over the forecast horizon.

        TODO: replace the naive moving-average with a real model
        (statsmodels SARIMAX or sklearn ridge) once the simulation loop runs.
        """
        hist = self.history.get(sku)
        if not hist:
            return 0.0
        return float(sum(hist) / len(hist) * self.forecast_horizon)

    # --- Mesa hook --------------------------------------------------------
    def step(self) -> None:
        # Pull observed demand from the Inventory Monitoring agent's broadcast.
        for msg in self.drain_inbox():
            if msg.get("type") == "demand_observed":
                self.history[msg["sku"]].append(msg["qty"])

        # If a drift signal arrived, refit; otherwise keep current models.
        # TODO: wire to drift detector in src/drift/.
        self.log("forecast_step", n_skus=len(self.history))

    def refit(self, skus: list[str] | None = None) -> None:
        """Refit per-SKU models. Called when drift is detected."""
        # TODO: implement actual fitting.
        self.log("refit", skus=skus or list(self.history.keys()))
