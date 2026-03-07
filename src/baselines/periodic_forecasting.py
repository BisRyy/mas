"""Baseline 2: Periodic Centralized Forecasting.

Re-fits a forecasting model on a fixed schedule (default every 30 days).
No drift detection — the schedule is blind to data changes. This is the
second baseline against which the proposed MAS is evaluated.

Key implementation detail: by default we only refit on the most recent
`recent_window` steps of history (default 90 days). Without this, the
fitted mean drags toward the run's long-run average and the policy
*lags* current demand — making Periodic structurally worse than it
would be in a real deployment. A 90-day window roughly matches the
fit_window used elsewhere in the project.
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
    recent_window: int = 90      # steps of history used in each refit
    history: pd.DataFrame | None = None
    _policy: StaticROPBaseline | None = field(default=None, init=False)
    _last_refit_step: int = field(default=-(10**9), init=False)

    def observe(self, step: int, sku: str, qty: int) -> None:
        row = pd.DataFrame([{"step": step, "sku": sku, "qty": qty}])
        self.history = (
            row if self.history is None
            else pd.concat([self.history, row], ignore_index=True)
        )

    def _recent_history(self, step: int) -> pd.DataFrame | None:
        if self.history is None:
            return None
        cutoff = step - self.recent_window
        recent = self.history[self.history["step"] >= cutoff]
        return recent if not recent.empty else self.history

    def maybe_refit(self, step: int) -> bool:
        if self.history is None:
            return False
        if step - self._last_refit_step >= self.refit_interval:
            window = self._recent_history(step)
            self._policy = StaticROPBaseline.fit(
                window, self.lead_time, self.service_level_z
            )
            self._last_refit_step = step
            return True
        return False

    def decide(self, sku: str, on_hand: int) -> int:
        if self._policy is None:
            return 0
        return self._policy.decide(sku, on_hand)
