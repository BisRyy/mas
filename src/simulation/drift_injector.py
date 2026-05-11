"""Drift injection for the three scenarios specified in the proposal.

Scenarios (Section 3.2 of the proposal):
    1. Abrupt   — +50% demand on top SKUs at step `start`, sustained 30 days.
    2. Gradual  — +0.5%/day over 60 days, affecting 30% of SKUs.
    3. Seasonal — +200% weekly spikes for 3 consecutive weeks.

Each scenario implements `multiplier(step, sku)` returning the factor to
apply to the base demand for that (step, sku). The injector composes
multipliers by multiplication.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Protocol


class DriftScenario(Protocol):
    name: str

    def multiplier(self, step: int, sku: str) -> float: ...


@dataclass
class AbruptDrift:
    """+pct demand on `affected_skus` between [start, start + duration)."""
    start: int
    duration: int = 30
    pct: float = 0.50
    affected_skus: set[str] = field(default_factory=set)
    name: str = "abrupt"

    def multiplier(self, step: int, sku: str) -> float:
        if self.start <= step < self.start + self.duration and sku in self.affected_skus:
            return 1.0 + self.pct
        return 1.0


@dataclass
class GradualDrift:
    """Linear +per_day_pct over `duration` days, affecting `affected_skus`."""
    start: int
    duration: int = 60
    per_day_pct: float = 0.005
    affected_skus: set[str] = field(default_factory=set)
    name: str = "gradual"

    def multiplier(self, step: int, sku: str) -> float:
        if self.start <= step < self.start + self.duration and sku in self.affected_skus:
            elapsed = step - self.start
            return 1.0 + self.per_day_pct * elapsed
        return 1.0


@dataclass
class SeasonalPulse:
    """+pct on `pulse_days` (e.g., one day per week for 3 weeks)."""
    pulse_days: set[int]
    pct: float = 2.00  # +200% means total demand is 3x
    affected_skus: set[str] = field(default_factory=set)
    name: str = "seasonal_pulse"

    def multiplier(self, step: int, sku: str) -> float:
        if step in self.pulse_days and (
            not self.affected_skus or sku in self.affected_skus
        ):
            return 1.0 + self.pct
        return 1.0


@dataclass
class DriftInjector:
    scenarios: list[DriftScenario]

    def apply(self, step: int, events: dict[str, int]) -> dict[str, int]:
        if not self.scenarios:
            return events
        out: dict[str, int] = {}
        for sku, qty in events.items():
            factor = 1.0
            for s in self.scenarios:
                factor *= s.multiplier(step, sku)
            out[sku] = max(int(round(qty * factor)), 0)
        return out
