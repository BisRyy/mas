"""Baselines specified in the proposal (Section 3.4)."""
from .static_rop import StaticROPBaseline
from .periodic_forecasting import PeriodicForecastingBaseline

__all__ = ["StaticROPBaseline", "PeriodicForecastingBaseline"]
