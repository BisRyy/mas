"""Baseline 1: Static Reorder Point.

Fixed reorder points and order quantities derived from initial historical
data. No adaptation during the run — the proposal explicitly contrasts MAS
adaptability against this rigidity.
"""
from __future__ import annotations

from dataclasses import dataclass
import pandas as pd


@dataclass
class StaticROPBaseline:
    """Fixed (s, Q) policy per SKU.

    Compute `reorder_point` and `order_qty` once from historical demand,
    then apply unchanged for the entire run.
    """

    reorder_points: dict[str, int]
    order_quantities: dict[str, int]

    @classmethod
    def fit(
        cls,
        history: pd.DataFrame,
        lead_time: int,
        service_level_z: float = 1.65,
    ) -> "StaticROPBaseline":
        """Fit per-SKU (s, Q) from a `step,sku,qty` history frame.

        s = mean_demand * lead_time + z * std_demand * sqrt(lead_time)
        Q = EOQ-style proxy (placeholder: 2 * mean_demand * lead_time).
        """
        # TODO: implement EOQ properly using ordering & holding costs.
        agg = history.groupby("sku")["qty"].agg(["mean", "std"]).fillna(0.0)
        rop = (
            agg["mean"] * lead_time + service_level_z * agg["std"] * (lead_time ** 0.5)
        ).round().astype(int)
        oq = (2 * agg["mean"] * lead_time).round().astype(int).clip(lower=1)
        return cls(reorder_points=rop.to_dict(), order_quantities=oq.to_dict())

    def decide(self, sku: str, on_hand: int) -> int:
        if on_hand <= self.reorder_points.get(sku, 0):
            return self.order_quantities.get(sku, 0)
        return 0
