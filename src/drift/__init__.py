"""Drift detectors used by the Demand Forecasting Agent.

The proposal cites ADWIN (Bifet & Gavaldà, 2007) and change-point methods
such as PELT. We expose a uniform `BaseDriftDetector` interface so the
forecasting agent can swap between them.
"""
from .base import BaseDriftDetector, DriftSignal
from .adwin_detector import ADWINDetector
from .pelt_detector import PELTDetector

__all__ = ["BaseDriftDetector", "DriftSignal", "ADWINDetector", "PELTDetector"]
