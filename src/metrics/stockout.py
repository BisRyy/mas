"""Stockout rate and duration."""
from __future__ import annotations


def stockout_rate(stockout_steps: int, total_steps: int) -> float:
    """Fraction of steps in which at least one fulfillment was short."""
    if total_steps <= 0:
        return 0.0
    return stockout_steps / total_steps


def stockout_duration(per_sku_stockout_steps: dict[str, int]) -> dict[str, int]:
    """Per-SKU number of steps spent in stockout."""
    return dict(per_sku_stockout_steps)
