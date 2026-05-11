"""Olist order replay engine.

Reads preprocessed Olist orders and exposes per-step demand events
(SKU -> quantity).

Expected processed format (CSV under data/processed/orders.csv):
    step, sku, qty
"""
from __future__ import annotations

from collections import defaultdict
from pathlib import Path
import pandas as pd


class OrderReplay:
    def __init__(self, events_by_step: dict[int, dict[str, int]]) -> None:
        self._events = events_by_step

    @classmethod
    def from_csv(cls, path: str | Path) -> "OrderReplay":
        df = pd.read_csv(path)
        events: dict[int, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        for row in df.itertuples(index=False):
            events[int(row.step)][str(row.sku)] += int(row.qty)
        return cls({k: dict(v) for k, v in events.items()})

    def events_for_step(self, step: int) -> dict[str, int]:
        return dict(self._events.get(step, {}))

    @property
    def n_steps(self) -> int:
        return (max(self._events) + 1) if self._events else 0

    @property
    def skus(self) -> list[str]:
        seen: set[str] = set()
        for day in self._events.values():
            seen.update(day.keys())
        return sorted(seen)
