"""Inventory Monitoring Agent.

Tracks real-time stock levels per SKU. Receives demand events from the
simulation environment, decrements stock on fulfillment, records stockouts,
and broadcasts observed demand to the forecaster and analytics agents.
"""
from __future__ import annotations

from typing import Any

from .base import BaseInventoryAgent


class InventoryMonitoringAgent(BaseInventoryAgent):
    def __init__(
        self,
        model: Any,
        initial_stock: dict[str, int] | None = None,
    ) -> None:
        super().__init__(model)
        self.stock: dict[str, int] = dict(initial_stock or {})
        self.stockout_steps: dict[str, int] = {}  # sku -> count of stockout steps

    # --- API --------------------------------------------------------------
    def fulfill(self, sku: str, qty: int) -> tuple[int, int]:
        """Try to fulfill `qty` units of `sku`.

        Returns (fulfilled, shorted). Records stockout when shorted > 0.
        """
        on_hand = self.stock.get(sku, 0)
        fulfilled = min(on_hand, qty)
        shorted = qty - fulfilled
        self.stock[sku] = on_hand - fulfilled
        if shorted > 0:
            self.stockout_steps[sku] = self.stockout_steps.get(sku, 0) + 1
            self.log("stockout", sku=sku, shorted=shorted)
        self.log("fulfill", sku=sku, qty=qty, fulfilled=fulfilled, shorted=shorted)
        return fulfilled, shorted

    def receive(self, sku: str, qty: int) -> None:
        """Add inventory from an arriving supplier shipment."""
        self.stock[sku] = self.stock.get(sku, 0) + qty
        self.log("receive", sku=sku, qty=qty)

    def level(self, sku: str) -> int:
        return self.stock.get(sku, 0)

    # --- Mesa hook --------------------------------------------------------
    def step(self) -> None:
        # Broadcast on-hand snapshot for the analytics agent.
        self.log("snapshot", n_skus=len(self.stock))
