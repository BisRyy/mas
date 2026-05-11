"""Inventory cost metrics."""
from __future__ import annotations

from typing import Iterable


def holding_cost(
    on_hand_per_step: Iterable[int],
    holding_cost_per_unit_per_step: float,
) -> float:
    """Sum of holding costs across the run."""
    return float(sum(on_hand_per_step) * holding_cost_per_unit_per_step)


def ordering_cost(n_orders: int, fixed_cost_per_order: float) -> float:
    return float(n_orders * fixed_cost_per_order)
