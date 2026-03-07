"""Inventory cost metrics.

The proposal (§3.5) lists holding cost as a primary metric and notes that
ordering cost should be tracked where applicable. We expose:

- `holding_cost(on_hand_per_step, h)`              — h * sum(on_hand)
- `ordering_cost(n_orders, K)`                     — K * n_orders
- `stockout_cost(stockout_sku_steps, p)`           — p * sum(SKU-days in stockout)
- `total_cost(...)`                                — sum of the three

Default weights are set so that, in roughly typical e-commerce ratios,
stockouts hurt more than holding, and ordering has a non-trivial fixed
component. Override per-experiment via the `costs:` block in YAML.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


DEFAULT_HOLDING_COST = 0.01           # per unit, per step
DEFAULT_ORDERING_COST = 50.0          # per order placed
DEFAULT_STOCKOUT_COST = 5.0           # per SKU, per step it spends in stockout


@dataclass
class CostWeights:
    holding: float = DEFAULT_HOLDING_COST
    ordering: float = DEFAULT_ORDERING_COST
    stockout: float = DEFAULT_STOCKOUT_COST

    @classmethod
    def from_config(cls, cfg: dict | None) -> "CostWeights":
        cfg = cfg or {}
        return cls(
            holding=float(cfg.get("holding", DEFAULT_HOLDING_COST)),
            ordering=float(cfg.get("ordering", DEFAULT_ORDERING_COST)),
            stockout=float(cfg.get("stockout", DEFAULT_STOCKOUT_COST)),
        )


def holding_cost(on_hand_per_step: Iterable[int], h: float) -> float:
    return float(sum(on_hand_per_step) * h)


def ordering_cost(n_orders: int, K: float) -> float:
    return float(n_orders * K)


def stockout_cost(stockout_sku_steps: int, p: float) -> float:
    """`stockout_sku_steps` is the sum across SKUs of step-counts in stockout."""
    return float(stockout_sku_steps * p)


def total_cost(
    on_hand_per_step: Iterable[int],
    n_orders: int,
    stockout_sku_steps: int,
    weights: CostWeights,
) -> dict[str, float]:
    h = holding_cost(on_hand_per_step, weights.holding)
    o = ordering_cost(n_orders, weights.ordering)
    s = stockout_cost(stockout_sku_steps, weights.stockout)
    return {
        "holding_cost": h,
        "ordering_cost": o,
        "stockout_cost": s,
        "total_cost": h + o + s,
    }
