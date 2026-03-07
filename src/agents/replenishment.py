"""Replenishment Agent.

Decides when to reorder and how much, based on the forecasting agent's
prediction and the monitoring agent's stock levels. Places orders with the
Supplier agent.
"""
from __future__ import annotations

import math
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

        Continuous (s, S) policy:
          mean_lt_demand   = predict(sku) * lead_time
          safety_stock     = z * std(sku) * sqrt(lead_time)
          reorder_point s  = mean_lt_demand + safety_stock
          order-up-to  S   = s + review_period * mean_per_day
        """
        forecaster = self.model.forecaster
        monitor = self.model.monitor
        supplier = self.model.supplier

        on_hand = monitor.level(sku)
        lead_time = supplier.lead_time(sku)

        # The forecaster exposes per-day mean and residual std.
        mean_per_day = max(forecaster.predict(sku), 0.0)
        std_per_day = max(forecaster.predict_std(sku), 0.0)

        mean_lt_demand = mean_per_day * lead_time
        safety_stock = self.service_level_z * std_per_day * math.sqrt(lead_time)
        reorder_point = mean_lt_demand + safety_stock
        # Order-up-to leaves an extra lead_time of demand above the ROP so
        # each order brings in a meaningful quantity and we don't ping the
        # supplier almost every day. (S - s) approximates a simple EOQ.
        order_up_to = reorder_point + lead_time * mean_per_day

        if on_hand <= reorder_point:
            qty = max(int(order_up_to - on_hand), 0)
            self.log(
                "reorder",
                sku=sku,
                on_hand=on_hand,
                rop=reorder_point,
                safety=safety_stock,
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
