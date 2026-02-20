"""Global seeding for reproducibility (Section 3.1 of the proposal)."""
from __future__ import annotations

import os
import random


def set_global_seed(seed: int) -> None:
    random.seed(seed)
    os.environ["PYTHONHASHSEED"] = str(seed)
    try:
        import numpy as np

        np.random.seed(seed)
    except ImportError:
        pass


def jitter_initial_stock(
    initial_stock: dict[str, int],
    jitter_pct: float,
    seed: int,
    min_value: int = 1,
) -> dict[str, int]:
    """Multiply each SKU's starting stock by `1 + uniform(-jitter, +jitter)`.

    Returns a fresh dict so the input is not mutated. Uses an isolated
    RNG keyed on `seed` so stocks are reproducible per seed but independent
    of any other RNG state.
    """
    if jitter_pct <= 0 or not initial_stock:
        return dict(initial_stock)
    rng = random.Random(seed)
    out: dict[str, int] = {}
    for sku, qty in initial_stock.items():
        factor = 1.0 + rng.uniform(-jitter_pct, jitter_pct)
        out[sku] = max(int(round(qty * factor)), min_value)
    return out
