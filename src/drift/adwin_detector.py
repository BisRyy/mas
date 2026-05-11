"""ADWIN drift detector (thin wrapper around `river.drift.ADWIN`)."""
from __future__ import annotations

from .base import DriftSignal


class ADWINDetector:
    name = "ADWIN"

    def __init__(self, delta: float = 0.002) -> None:
        # Lazy import so the package can be inspected without river installed.
        from river import drift

        self._adwin = drift.ADWIN(delta=delta)

    def update(self, value: float, step: int) -> DriftSignal:
        self._adwin.update(value)
        return DriftSignal(
            detected=bool(self._adwin.drift_detected),
            step=step,
            detector=self.name,
            statistic=getattr(self._adwin, "estimation", None),
        )

    def reset(self) -> None:
        from river import drift

        self._adwin = drift.ADWIN()
