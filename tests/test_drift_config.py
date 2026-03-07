"""Tests for the YAML -> DriftScenario builder."""
from __future__ import annotations

import pytest

from src.simulation import OrderReplay, build_scenarios_from_config, primary_drift_start
from src.simulation.drift_config import resolve_affected
from src.simulation.drift_injector import (
    AbruptDrift,
    GradualDrift,
    SeasonalPulse,
    DriftInjector,
)


@pytest.fixture
def replay() -> OrderReplay:
    # 3 steps, 3 SKUs with different total volumes.
    return OrderReplay(
        events_by_step={
            0: {"A": 10, "B": 5, "C": 1},
            1: {"A": 8, "B": 4},
            2: {"A": 7, "B": 5, "C": 2},
        }
    )


# --- SKU resolvers ---------------------------------------------------------
def test_resolve_all_returns_full_universe(replay):
    assert resolve_affected({"kind": "all"}, replay) == {"A", "B", "C"}


def test_resolve_all_when_spec_is_none(replay):
    assert resolve_affected(None, replay) == {"A", "B", "C"}


def test_resolve_top_n_uses_total_volume(replay):
    # A=25, B=14, C=3. Top 2 should be {A, B}.
    assert resolve_affected({"kind": "top_n", "n": 2}, replay) == {"A", "B"}


def test_resolve_random_fraction_is_seeded(replay):
    spec = {"kind": "random_fraction", "fraction": 0.66, "seed": 0}
    a = resolve_affected(spec, replay)
    b = resolve_affected(spec, replay)
    assert a == b  # determinism
    assert 1 <= len(a) <= 3


def test_resolve_random_fraction_validates_range(replay):
    with pytest.raises(ValueError):
        resolve_affected({"kind": "random_fraction", "fraction": 1.5}, replay)


def test_resolve_explicit_list(replay):
    assert resolve_affected({"kind": "explicit", "skus": ["A", "B"]}, replay) == {
        "A",
        "B",
    }


# --- Scenario builders -----------------------------------------------------
def test_build_abrupt_scenario(replay):
    cfg = [
        {
            "type": "abrupt",
            "start": 100,
            "duration": 30,
            "pct": 0.5,
            "affected": {"kind": "top_n", "n": 1},
        }
    ]
    scenarios = build_scenarios_from_config(cfg, replay)
    assert len(scenarios) == 1
    s = scenarios[0]
    assert isinstance(s, AbruptDrift)
    assert s.start == 100 and s.duration == 30 and s.pct == 0.5
    assert s.affected_skus == {"A"}
    # +50% applied only in [100, 130) and only on A.
    assert s.multiplier(99, "A") == 1.0
    assert s.multiplier(100, "A") == 1.5
    assert s.multiplier(130, "A") == 1.0
    assert s.multiplier(100, "B") == 1.0


def test_build_gradual_scenario(replay):
    cfg = [
        {
            "type": "gradual",
            "start": 50,
            "duration": 60,
            "per_day_pct": 0.01,
            "affected": {"kind": "all"},
        }
    ]
    scenarios = build_scenarios_from_config(cfg, replay)
    s = scenarios[0]
    assert isinstance(s, GradualDrift)
    # Day 0 of drift -> 1.0, day 50 of drift -> 1.5, beyond duration -> 1.0.
    assert s.multiplier(50, "A") == 1.0
    assert s.multiplier(75, "A") == 1.25
    assert s.multiplier(110, "A") == 1.0


def test_build_seasonal_scenario(replay):
    cfg = [
        {
            "type": "seasonal_pulse",
            "pulse_steps": [100, 107, 114],
            "pct": 2.0,
            "affected": {"kind": "top_n", "n": 2},
        }
    ]
    scenarios = build_scenarios_from_config(cfg, replay)
    s = scenarios[0]
    assert isinstance(s, SeasonalPulse)
    assert s.pulse_days == {100, 107, 114}
    assert s.multiplier(100, "A") == 3.0
    assert s.multiplier(101, "A") == 1.0
    assert s.multiplier(100, "C") == 1.0  # C is not in top-2


def test_seasonal_shorthand_uses_three_weekly_pulses(replay):
    cfg = [{"type": "seasonal_pulse", "start": 50, "pct": 2.0, "affected": {"kind": "all"}}]
    s = build_scenarios_from_config(cfg, replay)[0]
    assert isinstance(s, SeasonalPulse)
    assert s.pulse_days == {50, 57, 64}


def test_unknown_type_raises(replay):
    with pytest.raises(ValueError):
        build_scenarios_from_config([{"type": "wat"}], replay)


# --- Drift onset detection -------------------------------------------------
def test_primary_drift_start_picks_smallest_onset():
    cfg = [
        {"type": "abrupt", "start": 200, "duration": 30, "pct": 0.5},
        {"type": "seasonal_pulse", "pulse_steps": [150, 157]},
    ]
    assert primary_drift_start(cfg) == 150


def test_primary_drift_start_returns_none_when_empty():
    assert primary_drift_start([]) is None
    assert primary_drift_start(None) is None


# --- Integration: scenarios actually modify replay events ------------------
def test_injector_multiplies_demand(replay):
    cfg = [
        {
            "type": "abrupt",
            "start": 1,
            "duration": 1,
            "pct": 1.0,  # +100%
            "affected": {"kind": "explicit", "skus": ["A"]},
        }
    ]
    injector = DriftInjector(build_scenarios_from_config(cfg, replay))
    out = injector.apply(1, {"A": 10, "B": 5})
    assert out["A"] == 20
    assert out["B"] == 5
