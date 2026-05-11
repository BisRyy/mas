"""Mesa Model that ties the 5 agents together.

Mesa 3.x removed the `mesa.time` schedulers; agents register on the model
automatically and we step them in the deterministic order we instantiated
them. The model is the simulation environment. Each `step()`:
  1. Pulls the day's demand events from the order-replay engine
  2. Asks the drift injector to (optionally) modify those events
  3. Hands fulfillment to the Inventory Monitoring agent
  4. Lets every agent take its `step()` in deterministic order
"""
from __future__ import annotations

from typing import Any

from mesa import Model

from src.agents import (
    DemandForecastingAgent,
    InventoryMonitoringAgent,
    ReplenishmentAgent,
    SupplierAgent,
    AnalyticsAgent,
)
from .replay import OrderReplay
from .drift_injector import DriftInjector
from .logger import RunLogger


class InventoryModel(Model):
    """Top-level simulation model.

    Convenience attributes (`self.forecaster`, `self.monitor`, ...) are set
    so agents can address each other directly without scanning `self.agents`.
    """

    def __init__(
        self,
        skus: list[str],
        replay: OrderReplay,
        drift_injector: DriftInjector | None = None,
        initial_stock: dict[str, int] | None = None,
        seed: int = 42,
    ) -> None:
        super().__init__(seed=seed)
        self.skus = list(skus)
        self.replay = replay
        self.drift_injector = drift_injector or DriftInjector(scenarios=[])
        self.run_logger = RunLogger()

        # Instantiate agents in deterministic order:
        # supplier deliveries first (so today's stock includes arrivals),
        # then monitoring, forecasting, replenishment, analytics.
        # Mesa 3.x auto-registers each new Agent on its model.
        self.supplier = SupplierAgent(model=self)
        self.monitor = InventoryMonitoringAgent(
            model=self, initial_stock=initial_stock
        )
        self.forecaster = DemandForecastingAgent(model=self)
        self.replenisher = ReplenishmentAgent(model=self)
        self.analytics = AnalyticsAgent(model=self)

        # Explicit ordering matters for our pipeline; we don't rely on
        # `self.agents` iteration order.
        self._agent_order = [
            self.supplier,
            self.monitor,
            self.forecaster,
            self.replenisher,
            self.analytics,
        ]

    # --- One simulation tick ---------------------------------------------
    def step(self) -> None:
        # 1. Pull demand events for this step.
        events = self.replay.events_for_step(self.steps)
        # 2. Apply any active drift scenarios.
        events = self.drift_injector.apply(self.steps, events)
        # 3. Fulfill demand and broadcast observations to forecaster.
        for sku, qty in events.items():
            self.monitor.fulfill(sku, qty)
            self.forecaster.send(
                self.forecaster, {"type": "demand_observed", "sku": sku, "qty": qty}
            )
        # 4. Run agents in deterministic order.
        for agent in self._agent_order:
            agent.step()
        # Mesa 3.x: increment the step counter ourselves since we're not
        # using the (removed) scheduler.
        self.steps += 1

    # --- Run loop ---------------------------------------------------------
    def run(self, n_steps: int) -> dict[str, Any]:
        for _ in range(n_steps):
            self.step()
        return self.analytics.summary()
