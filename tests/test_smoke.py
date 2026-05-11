"""Smoke tests — confirm the scaffold imports and a tiny run completes."""
from __future__ import annotations


def test_imports():
    from src.agents import (
        DemandForecastingAgent,
        InventoryMonitoringAgent,
        ReplenishmentAgent,
        SupplierAgent,
        AnalyticsAgent,
    )
    from src.simulation import InventoryModel, OrderReplay, DriftInjector
    from src.baselines import StaticROPBaseline, PeriodicForecastingBaseline
    from src.metrics import stockout_rate, mape, detection_delay

    # Touch references so linters keep them.
    assert DemandForecastingAgent and InventoryMonitoringAgent
    assert ReplenishmentAgent and SupplierAgent and AnalyticsAgent
    assert InventoryModel and OrderReplay and DriftInjector
    assert StaticROPBaseline and PeriodicForecastingBaseline
    assert stockout_rate(1, 10) == 0.1
    assert mape([10, 20], [11, 18]) > 0
    assert detection_delay(100, 105) == 5


def test_tiny_simulation_runs():
    from src.simulation import InventoryModel, OrderReplay, DriftInjector

    # Two SKUs, 5 days of synthetic demand.
    events = {
        0: {"A": 5, "B": 2},
        1: {"A": 4, "B": 3},
        2: {"A": 6, "B": 1},
        3: {"A": 3, "B": 2},
        4: {"A": 5, "B": 2},
    }
    replay = OrderReplay(events_by_step=events)
    model = InventoryModel(
        skus=["A", "B"],
        replay=replay,
        drift_injector=DriftInjector(scenarios=[]),
        initial_stock={"A": 50, "B": 20},
        seed=0,
    )
    summary = model.run(n_steps=5)
    assert summary["n_steps"] == 5
    assert "stockout_rate" in summary
