"""Common interface for drift detectors."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass
class DriftSignal:
    detected: bool
    step: int
    detector: str
    statistic: float | None = None


class BaseDriftDetector(Protocol):
    name: str

    def update(self, value: float, step: int) -> DriftSignal: ...

    def reset(self) -> None: ...
