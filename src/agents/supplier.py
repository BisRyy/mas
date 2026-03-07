"""Supplier Agent.

Simulates external suppliers. Owns lead-time distributions per SKU, accepts
purchase orders, and delivers them to the Inventory Monitoring agent after
the lead time elapses.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Any

from .base import BaseInventoryAgent


@dataclass
class _PendingOrder:
    sku: str
    qty: int
    arrives_at_step: int


class SupplierAgent(BaseInventoryAgent):
    def __init__(
        self,
        model: Any,
        default_lead_time: int = 7,
        lead_times: dict[str, int] | None = None,
    ) -> None:
        super().__init__(model)
        self.default_lead_time = default_lead_time
        self.lead_times: dict[str, int] = dict(lead_times or {})
        self.pending: deque[_PendingOrder] = deque()

    # --- API --------------------------------------------------------------
    def lead_time(self, sku: str) -> int:
        return self.lead_times.get(sku, self.default_lead_time)

    def place_order(self, sku: str, qty: int) -> None:
        arrives = self.model.steps + self.lead_time(sku)
        self.pending.append(_PendingOrder(sku=sku, qty=qty, arrives_at_step=arrives))
        # Surface aggregate counters for comparison vs baselines.
        self.n_orders = getattr(self, "n_orders", 0) + 1
        self.total_units_ordered = getattr(self, "total_units_ordered", 0) + qty
        self.log("po_placed", sku=sku, qty=qty, arrives=arrives)

    # --- Mesa hook --------------------------------------------------------
    def step(self) -> None:
        now = self.model.steps
        delivered: list[_PendingOrder] = []
        remaining: deque[_PendingOrder] = deque()
        while self.pending:
            order = self.pending.popleft()
            if order.arrives_at_step <= now:
                self.model.monitor.receive(order.sku, order.qty)
                delivered.append(order)
            else:
                remaining.append(order)
        self.pending = remaining
        if delivered:
            self.log("po_delivered", n=len(delivered))
