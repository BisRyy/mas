"""Baseline 2: Periodic Centralized Forecasting.

Re-fits a forecasting model on a fixed schedule (default every 30 days)
and updates per-SKU (s, Q) accordingly. No drift detection — the schedule
is blind to data changes. This is the second baseline against which the
proposed MAS is evaluated.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import pandas as pd

from .static_rop import StaticROPBaseline


@dataclass
class PeriodicForecastingBaseline:
    refit_interval: int = 30
    lead_time: int = 7
    service_level_z: float = 1.65
    history: pd.DataFrame | None = None
    _policy: StaticROPBaseline | None = field(default=None, init=False)
    _last_refit_step: int = field(default=-(10**9), init=False)

    def observe(self, step: int, sku: str, qty: int) -> None:
        row = pd.DataFrame([{"step": step, "sku": sku, "qty": qty}])
        self.history = (
            row if self.history is None else pd.concat([self.history, row], ignore_index=True)
        )

    def maybe_refit(self, step: int) -> bool:
        if self.history is None:
            return False
        if step - self._last_refit_step >= self.refit_interval:
            self._policy = StaticROPBaseline.fit(
                self.history, self.lead_time, self.service_level_z
            )
            self._last_refit_step = step
            return True
        return False

    def decide(self, sku: str, on_hand: int) -> int:
        if self._policy is None:
            return 0
        return self._policy.decide(sku, on_hand)
