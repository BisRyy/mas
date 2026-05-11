"""Replenishment Agent.

Decides when to reorder and how much, based on the forecasting agent's
prediction and the monitoring agent's stock levels. Places orders with the
Supplier agent.
"""
from __future__ import annotations

from typing import Any

from .base import BaseInventoryAgent


class ReplenishmentAgent(BaseInventoryAgent):
    def __init__(
        self,
        model: Any,
        service_level_z: float = 1.65,  # ~95% service level
        review_period: int = 1,         # daily review by default
    ) -> None:
        super().__init__(model)
        self.service_level_z = service_level_z
        self.review_period = review_period

    # --- Policy -----------------------------------------------------------
    def decide(self, sku: str) -> int:
        """Return order quantity for `sku` (0 means don't order this step).

        Uses a (s, S) style policy where s is the dynamic reorder point
        (forecasted demand over lead time + safety stock) and S is the
        order-up-to level.
        """
        forecaster = self.model.forecaster
        monitor = self.model.monitor
        supplier = self.model.supplier

        on_hand = monitor.level(sku)
        lead_time = supplier.lead_time(sku)

        # Mean demand over lead time (forecaster predicts horizon-period demand;
        # we rescale to lead-time-period demand).
        horizon = max(forecaster.forecast_horizon, 1)
        mean_lt_demand = forecaster.predict(sku) * (lead_time / horizon)

        # Safety stock is a placeholder until we have demand variance from the
        # forecaster. TODO: pull sigma from forecaster when models are fit.
        safety_stock = 0.0
        reorder_point = mean_lt_demand + safety_stock
        order_up_to = reorder_point + mean_lt_demand  # crude target

        if on_hand <= reorder_point:
            qty = max(int(order_up_to - on_hand), 0)
            self.log(
                "reorder",
                sku=sku,
                on_hand=on_hand,
                rop=reorder_point,
                qty=qty,
            )
            return qty
        return 0

    # --- Mesa hook --------------------------------------------------------
    def step(self) -> None:
        if self.model.steps % self.review_period != 0:
            return
        for sku in self.model.skus:
            qty = self.decide(sku)
            if qty > 0:
                self.model.supplier.place_order(sku, qty)
