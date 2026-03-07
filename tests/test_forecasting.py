"""Tests for the upgraded DemandForecastingAgent."""
from __future__ import annotations

import math
import random

import pytest

from src.simulation import InventoryModel, OrderReplay, DriftInjector
from src.simulation.drift_injector import AbruptDrift


def _noisy_series(steps: int, base: float, amplitude: float, period: int,
                  noise_sigma: float, seed: int = 0) -> dict[int, dict[str, int]]:
    """Build a step→{sku→qty} dict with a noisy seasonal pattern.

    Statsmodels' SimpleExpSmoothing / ExponentialSmoothing optimizers can
    refuse to fit perfectly cyclic integer data (zero residual variance
    confuses the BIC/log-likelihood). Adding small Gaussian noise produces
    series that fit reliably and still let us assert the chosen tier.
    """
    rng = random.Random(seed)
    out: dict[int, dict[str, int]] = {}
    for s in range(steps):
        seasonal = amplitude * math.sin(2 * math.pi * s / period)
        noise = rng.gauss(0, noise_sigma)
        val = max(int(round(base + seasonal + noise)), 0)
        out[s] = {"A": val}
    return out


def _build_model(events, initial_stock=None, drift_scenarios=None, seed=0):
    replay = OrderReplay(events_by_step=events)
    injector = DriftInjector(scenarios=drift_scenarios or [])
    return InventoryModel(
        skus=sorted({sku for day in events.values() for sku in day}),
        replay=replay,
        drift_injector=injector,
        initial_stock=initial_stock,
        seed=seed,
    )


def test_ma_tier_for_short_history():
    """A SKU with very few observations falls back to moving-average."""
    events = {step: {"A": 5} for step in range(5)}
    model = _build_model(events, initial_stock={"A": 100})
    model.run(n_steps=5)
    fitted = model.forecaster.models["A"]
    assert fitted.method == "ma"
    # MA mean equals the observed mean.
    assert fitted.mean == pytest.approx(5.0, abs=1e-6)


def test_ses_tier_for_medium_history():
    """At 14-34 observations we should be at SES (or MA fallback if SES fails)."""
    events = _noisy_series(steps=25, base=10, amplitude=2, period=3,
                            noise_sigma=1.5, seed=1)
    model = _build_model(events, initial_stock={"A": 1000})
    model.run(n_steps=25)
    fitted = model.forecaster.models["A"]
    # Tier should advance beyond MA. SES is preferred; MA fallback is the
    # documented graceful path when statsmodels can't fit.
    assert fitted.method in ("ses", "ma"), f"unexpected tier {fitted.method}"
    assert fitted.method == "ses", (
        "expected SES at this history length; only acceptable fallback is MA "
        "when statsmodels refuses to fit (this dataset is constructed to fit)"
    )
    assert fitted.mean >= 0


def test_hw_tier_for_long_history():
    """At >=35 observations we use Holt-Winters with weekly seasonality."""
    events = _noisy_series(steps=60, base=12, amplitude=3, period=7,
                            noise_sigma=1.0, seed=2)
    model = _build_model(events, initial_stock={"A": 5000})
    model.run(n_steps=60)
    fitted = model.forecaster.models["A"]
    assert fitted.method == "hw", (
        f"expected Holt-Winters at 60 obs of a weekly-seasonal series, got {fitted.method}"
    )
    # Residual std should be positive (noisy series).
    assert fitted.std > 0


def test_predict_std_drives_safety_stock():
    """High residual std should produce a larger predict_std than low std."""
    high_events = _noisy_series(steps=50, base=10, amplitude=8, period=4,
                                 noise_sigma=4.0, seed=3)
    f_high = _build_model(high_events, initial_stock={"A": 10000})
    f_high.run(n_steps=50)
    std_high = f_high.forecaster.predict_std("A")

    low_events = _noisy_series(steps=50, base=10, amplitude=0, period=4,
                                noise_sigma=0.3, seed=4)
    f_low = _build_model(low_events, initial_stock={"A": 10000})
    f_low.run(n_steps=50)
    std_low = f_low.forecaster.predict_std("A")

    assert std_high > std_low, (
        f"std_high ({std_high:.3f}) should exceed std_low ({std_low:.3f})"
    )


def test_no_drift_no_global_event():
    """Steady demand should not trigger the global drift detector."""
    events = {step: {"A": 5, "B": 3} for step in range(80)}
    model = _build_model(events, initial_stock={"A": 5000, "B": 5000})
    model.run(n_steps=80)
    assert model.forecaster.global_drift_steps == []


def test_drift_marks_models_stale_and_triggers_refit():
    """Manually flipping global drift should trigger refits on next predict."""
    events = {step: {"A": 5} for step in range(20)}
    model = _build_model(events, initial_stock={"A": 5000})
    model.run(n_steps=20)
    initial_refits = model.forecaster.refit_count

    # Simulate a global drift event: mark the SKU stale.
    model.forecaster.model_stale["A"] = True
    # Next predict should refit.
    model.forecaster.predict("A")
    assert model.forecaster.refit_count == initial_refits + 1


def test_summary_exposes_forecaster_metrics():
    """summary keys for forecaster diagnostics must be present."""
    events = {step: {"A": 5, "B": 2} for step in range(15)}
    model = _build_model(events, initial_stock={"A": 1000, "B": 1000})
    summary = model.run(n_steps=15)
    for key in (
        "forecast_mape",
        "n_drift_events",
        "n_global_drift_events",
        "n_refits",
        "active_model_methods",
    ):
        assert key in summary, f"missing key: {key}"
    assert isinstance(summary["active_model_methods"], dict)
    assert set(summary["active_model_methods"]) == {"ma", "ses", "hw"}
