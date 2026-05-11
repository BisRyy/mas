"""The 5 agents specified in the thesis proposal."""
from .base import BaseInventoryAgent
from .forecasting import DemandForecastingAgent
from .monitoring import InventoryMonitoringAgent
from .replenishment import ReplenishmentAgent
from .supplier import SupplierAgent
from .analytics import AnalyticsAgent

__all__ = [
    "BaseInventoryAgent",
    "DemandForecastingAgent",
    "InventoryMonitoringAgent",
    "ReplenishmentAgent",
    "SupplierAgent",
    "AnalyticsAgent",
]
