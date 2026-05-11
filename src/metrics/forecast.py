"""Forecast accuracy."""
from __future__ import annotations

from typing import Sequence


def mape(actual: Sequence[float], predicted: Sequence[float]) -> float:
    """Mean Absolute Percentage Error.

    Skips entries where actual is 0 to avoid division-by-zero. Returns the
    mean over the surviving entries; 0.0 when none survive.
    """
    if len(actual) != len(predicted):
        raise ValueError("actual and predicted must have the same length")
    errs = []
    for a, p in zip(actual, predicted):
        if a == 0:
            continue
        errs.append(abs((a - p) / a))
    return float(sum(errs) / len(errs)) if errs else 0.0
