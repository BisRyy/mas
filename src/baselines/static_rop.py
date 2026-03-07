"""Baseline 1: Static Reorder Point.

Fixed reorder points and order quantities derived from initial historical
data. No adaptation during the run — the proposal explicitly contrasts MAS
adaptability against this rigidity.

Q* is computed using the textbook EOQ formula

    Q* = sqrt(2 * D * K / h)

where D is the **annualised** mean demand for the SKU, K is the fixed
ordering cost, and h the per-unit holding cost. Both costs default to the
project-wide defaults from `src.metrics.cost` so the policy is internally
consistent with the cost metric used to evaluate it. Q is bounded below by
one lead-time of mean demand (a real operator never orders less than a
single replenishment cycle).
"""
from __future__ import annotations

from dataclasses import dataclass
import math
import pandas as pd

from src.metrics.cost import DEFAULT_HOLDING_COST, DEFAULT_ORDERING_COST


@dataclass
class StaticROPBaseline:
    """Fixed (s, Q) policy per SKU."""

    reorder_points: dict[str, int]
    order_quantities: dict[str, int]

    @classmethod
    def fit(
        cls,
        history: pd.DataFrame,
        lead_time: int,
        service_level_z: float = 1.65,
        ordering_cost: float = DEFAULT_ORDERING_COST,
        holding_cost: float = DEFAULT_HOLDING_COST,
        steps_per_year: int = 365,
    ) -> "StaticROPBaseline":
        """Fit per-SKU (s, Q) from a `step,sku,qty` history frame.

        Reorder point:
            s = mean_per_day * lead_time + z * std_per_day * sqrt(lead_time)

        Order quantity (EOQ):
            Q* = sqrt(2 * D_annual * K / h)
        with a floor of one lead-time of mean demand to avoid micro-orders
        when EOQ rounds to 0 for low-volume SKUs.
        """
        agg = history.groupby("sku")["qty"].agg(["mean", "std"]).fillna(0.0)
        rop = (
            agg["mean"] * lead_time
            + service_level_z * agg["std"] * (lead_time ** 0.5)
        ).round().astype(int)

        # EOQ formula using rates in matching units: D and h both per-step.
        # Q* = sqrt(2 * D_per_step * K / h_per_step). The `steps_per_year`
        # parameter is kept on the signature for clarity but no longer used
        # (units already match without rescaling).
        del steps_per_year  # silence linters
        denom = max(holding_cost, 1e-9)
        eoq = (2.0 * agg["mean"] * ordering_cost / denom).pow(0.5)
        lt_floor = agg["mean"] * lead_time
        oq = eoq.combine(lt_floor, max).round().astype(int).clip(lower=1)
        return cls(reorder_points=rop.to_dict(), order_quantities=oq.to_dict())

    def decide(self, sku: str, on_hand: int) -> int:
        if on_hand <= self.reorder_points.get(sku, 0):
            return self.order_quantities.get(sku, 0)
        return 0
