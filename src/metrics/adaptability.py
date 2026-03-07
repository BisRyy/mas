"""Adaptability metrics — drift detection delay and time-to-recovery.

These directly address H2 and RQ3 from the proposal.
"""
from __future__ import annotations

from typing import Sequence


def detection_delay(drift_step: int, detected_step: int | None) -> int | None:
    """Number of steps between true drift onset and detector firing.

    Returns None if the detector never fires.
    """
    if detected_step is None:
        return None
    return max(detected_step - drift_step, 0)


def time_to_recovery(
    service_levels: Sequence[float],
    drift_step: int,
    target: float = 0.95,
    sustained_window: int = 7,
) -> int | None:
    """Steps after `drift_step` to first hit (and sustain) `target` service level.

    `service_levels` is indexed by **offset within the sequence**, so callers
    must pass a sequence whose index 0 corresponds to the start of the test
    window. `drift_step` is the same kind of offset.

    Returns the step offset where service level >= target for at least
    `sustained_window` consecutive steps, or None if never recovered.
    """
    n = len(service_levels)
    if drift_step >= n:
        return None
    streak = 0
    for i in range(drift_step, n):
        if service_levels[i] >= target:
            streak += 1
            if streak >= sustained_window:
                return i - sustained_window + 1 - drift_step
        else:
            streak = 0
    return None
