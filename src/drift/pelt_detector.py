"""PELT change-point detector (thin wrapper around `ruptures`).

PELT operates on a buffer of recent observations rather than streaming, so
this detector accumulates values and re-runs PELT on the buffer when it
exceeds `min_size`. For long runs, callers should periodically `reset()`.
"""
from __future__ import annotations

from collections import deque

from .base import DriftSignal


class PELTDetector:
    name = "PELT"

    def __init__(self, penalty: float = 10.0, min_size: int = 30) -> None:
        self.penalty = penalty
        self.min_size = min_size
        self._buffer: deque[float] = deque()
        self._last_breakpoint: int | None = None

    def update(self, value: float, step: int) -> DriftSignal:
        self._buffer.append(value)
        if len(self._buffer) < self.min_size:
            return DriftSignal(detected=False, step=step, detector=self.name)

        import numpy as np
        import ruptures as rpt

        signal = np.array(self._buffer, dtype=float)
        algo = rpt.Pelt(model="rbf").fit(signal)
        breakpoints = algo.predict(pen=self.penalty)
        # ruptures returns the end index too; ignore it.
        cps = [bp for bp in breakpoints if bp < len(signal)]
        latest = cps[-1] if cps else None
        if latest is not None and latest != self._last_breakpoint:
            self._last_breakpoint = latest
            return DriftSignal(
                detected=True, step=step, detector=self.name, statistic=float(latest)
            )
        return DriftSignal(detected=False, step=step, detector=self.name)

    def reset(self) -> None:
        self._buffer.clear()
        self._last_breakpoint = None
