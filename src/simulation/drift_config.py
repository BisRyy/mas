"""Turn YAML drift config into concrete `DriftScenario` instances.

Schema (per scenario):

    type: abrupt | gradual | seasonal_pulse
    # abrupt:
    start: <int absolute step>
    duration: <int days>
    pct: <float; 0.5 = +50%>
    # gradual:
    start: <int>
    duration: <int>
    per_day_pct: <float; 0.005 = +0.5%/day>
    # seasonal_pulse:
    pulse_steps: [<int>, <int>, ...]
    pct: <float; 2.0 = +200%>

    # SKU selection (every scenario):
    affected:
      kind: top_n | random_fraction | all | explicit
      n: <int>            # for top_n
      fraction: <float>   # for random_fraction
      seed: <int>         # for random_fraction
      skus: [<id>, ...]   # for explicit
"""
from __future__ import annotations

from collections import defaultdict
import random
from typing import Any

from .drift_injector import (
    AbruptDrift,
    GradualDrift,
    SeasonalPulse,
    DriftScenario,
)
from .replay import OrderReplay


# ---------------------------------------------------------------------------
# SKU selection
# ---------------------------------------------------------------------------
def _all_skus(replay: OrderReplay) -> list[str]:
    return list(replay.skus)


def _sku_volumes(replay: OrderReplay) -> list[tuple[str, int]]:
    """Per-SKU total demand across the full replay, sorted desc."""
    totals: dict[str, int] = defaultdict(int)
    for step in range(replay.n_steps):
        for sku, qty in replay.events_for_step(step).items():
            totals[sku] += qty
    return sorted(totals.items(), key=lambda kv: kv[1], reverse=True)


def resolve_affected(spec: dict | None, replay: OrderReplay) -> set[str]:
    """Resolve an `affected:` spec into a concrete set of SKU ids."""
    if not spec:
        return set(_all_skus(replay))
    kind = spec.get("kind", "all")
    if kind == "all":
        return set(_all_skus(replay))
    if kind == "top_n":
        n = int(spec["n"])
        return {sku for sku, _ in _sku_volumes(replay)[:n]}
    if kind == "random_fraction":
        fraction = float(spec["fraction"])
        if not 0.0 < fraction <= 1.0:
            raise ValueError(f"random_fraction must be in (0, 1], got {fraction}")
        seed = int(spec.get("seed", 0))
        skus = _all_skus(replay)
        rng = random.Random(seed)
        k = max(1, int(round(len(skus) * fraction)))
        return set(rng.sample(skus, k))
    if kind == "explicit":
        return set(map(str, spec["skus"]))
    raise ValueError(f"Unknown affected.kind: {kind!r}")


# ---------------------------------------------------------------------------
# Scenario builders
# ---------------------------------------------------------------------------
def _build_abrupt(c: dict, affected: set[str]) -> AbruptDrift:
    return AbruptDrift(
        start=int(c["start"]),
        duration=int(c.get("duration", 30)),
        pct=float(c.get("pct", 0.50)),
        affected_skus=affected,
    )


def _build_gradual(c: dict, affected: set[str]) -> GradualDrift:
    return GradualDrift(
        start=int(c["start"]),
        duration=int(c.get("duration", 60)),
        per_day_pct=float(c.get("per_day_pct", 0.005)),
        affected_skus=affected,
    )


def _build_seasonal(c: dict, affected: set[str]) -> SeasonalPulse:
    pulse_steps = c.get("pulse_steps")
    if pulse_steps is None:
        # Allow shorthand: start + 3 weekly pulses.
        start = int(c["start"])
        pulse_steps = [start, start + 7, start + 14]
    return SeasonalPulse(
        pulse_days=set(int(s) for s in pulse_steps),
        pct=float(c.get("pct", 2.00)),
        affected_skus=affected,
    )


_BUILDERS = {
    "abrupt": _build_abrupt,
    "gradual": _build_gradual,
    "seasonal_pulse": _build_seasonal,
}


def build_scenarios_from_config(
    scenarios_cfg: list[dict[str, Any]] | None,
    replay: OrderReplay,
) -> list[DriftScenario]:
    """Return a list of DriftScenario instances built from config."""
    if not scenarios_cfg:
        return []
    out: list[DriftScenario] = []
    for c in scenarios_cfg:
        kind = c.get("type")
        if kind not in _BUILDERS:
            raise ValueError(
                f"Unknown drift type: {kind!r}. Expected one of {sorted(_BUILDERS)}."
            )
        affected = resolve_affected(c.get("affected"), replay)
        out.append(_BUILDERS[kind](c, affected))
    return out


def primary_drift_start(scenarios_cfg: list[dict[str, Any]] | None) -> int | None:
    """Best-effort primary onset step for downstream recovery metrics.

    Returns the smallest `start` (or first pulse step) across configured
    scenarios, or None if no scenarios are configured.
    """
    if not scenarios_cfg:
        return None
    candidates: list[int] = []
    for c in scenarios_cfg:
        if "start" in c:
            candidates.append(int(c["start"]))
        elif "pulse_steps" in c:
            ps = c["pulse_steps"]
            if ps:
                candidates.append(int(min(ps)))
    return min(candidates) if candidates else None
