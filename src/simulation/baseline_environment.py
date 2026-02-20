"""Plain-Python simulation loop for the baseline policies.

The proposal (Section 3.4) defines two baselines we must beat:

  1. Static ROP — fixed (s, Q) policy fit once from historical data, no
     adaptation during the run.
  2. Periodic centralized forecasting — refit on a fixed schedule (default
     every 30 days), no drift detection.

Both share the same environment as the MAS (Olist replay, lead times,
stockout accounting, drift injection); only the ordering decision logic
differs. We keep them in plain Python — no Mesa agents — to make the
contrast structural rather than algorithmic.
"""
from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Protocol

import pandas as pd

from src.baselines import StaticROPBaseline, PeriodicForecastingBaseline
from .replay import OrderReplay
from .drift_injector import DriftInjector


class _DecisionPolicy(Protocol):
    """What BaselineModel needs from a policy."""

    def decide(self, sku: str, on_hand: int) -> int: ...


@dataclass
class _PendingOrder:
    sku: str
    qty: int
    arrives_at_step: int


@dataclass
class BaselineRunResult:
    n_steps: int
    stockout_rate: float
    stockout_duration_per_sku: dict[str, int]
    final_total_on_hand: int
    n_orders: int
    total_units_ordered: int
    timeseries: list[dict] = field(default_factory=list)

    def to_summary(self) -> dict:
        return {
            "n_steps": self.n_steps,
            "stockout_rate": self.stockout_rate,
            "stockout_duration_per_sku": self.stockout_duration_per_sku,
            "final_total_on_hand": self.final_total_on_hand,
            "n_orders": self.n_orders,
            "total_units_ordered": self.total_units_ordered,
        }


class BaselineModel:
    """Run a baseline policy over the same replay/drift environment as the MAS.

    Lifecycle:
      1. `fit_warmup()` consumes steps [0, fit_window) to fit the policy.
      2. `run()` simulates steps [fit_window, fit_window + n_steps).

    For Static ROP the policy is frozen after warm-up. For Periodic
    Forecasting the policy observes demand during the run and refits on
    schedule (handled inside `PeriodicForecastingBaseline`).
    """

    def __init__(
        self,
        skus: list[str],
        replay: OrderReplay,
        policy_name: str,
        drift_injector: DriftInjector | None = None,
        initial_stock: dict[str, int] | None = None,
        lead_time: int = 7,
        fit_window: int = 90,
        service_level_z: float = 1.65,
        refit_interval: int = 30,
        recent_window: int = 90,
    ) -> None:
        self.skus = list(skus)
        self.replay = replay
        self.policy_name = policy_name
        self.drift_injector = drift_injector or DriftInjector(scenarios=[])
        self.lead_time = lead_time
        self.fit_window = fit_window
        self.service_level_z = service_level_z
        self.refit_interval = refit_interval
        self.recent_window = recent_window

        self.stock: dict[str, int] = dict(initial_stock or {})
        self.pending: deque[_PendingOrder] = deque()
        self.stockout_steps: dict[str, int] = defaultdict(int)
        self.n_orders = 0
        self.total_units_ordered = 0
        self.timeseries: list[dict] = []
        self.policy: _DecisionPolicy | None = None
        self.step_idx: int = 0

    # --- Warm-up ---------------------------------------------------------
    def fit_warmup(self) -> None:
        """Consume events from [0, fit_window) to fit the policy."""
        rows = []
        for step in range(self.fit_window):
            for sku, qty in self.replay.events_for_step(step).items():
                rows.append({"step": step, "sku": sku, "qty": qty})
        history = pd.DataFrame(rows) if rows else pd.DataFrame(
            columns=["step", "sku", "qty"]
        )
        if self.policy_name == "static_rop":
            self.policy = StaticROPBaseline.fit(
                history,
                lead_time=self.lead_time,
                service_level_z=self.service_level_z,
            )
        elif self.policy_name == "periodic_forecasting":
            self.policy = PeriodicForecastingBaseline(
                refit_interval=self.refit_interval,
                lead_time=self.lead_time,
                service_level_z=self.service_level_z,
                recent_window=self.recent_window,
                history=history if not history.empty else None,
            )
            self.policy.maybe_refit(step=self.fit_window - 1)
        else:
            raise ValueError(f"Unknown baseline policy: {self.policy_name!r}")

    # --- Simulation step --------------------------------------------------
    def _deliver_arrivals(self) -> None:
        remaining: deque[_PendingOrder] = deque()
        while self.pending:
            order = self.pending.popleft()
            if order.arrives_at_step <= self.step_idx:
                self.stock[order.sku] = self.stock.get(order.sku, 0) + order.qty
            else:
                remaining.append(order)
        self.pending = remaining

    def _fulfill(self, sku: str, qty: int) -> int:
        on_hand = self.stock.get(sku, 0)
        fulfilled = min(on_hand, qty)
        shorted = qty - fulfilled
        self.stock[sku] = on_hand - fulfilled
        if shorted > 0:
            self.stockout_steps[sku] += 1
        return shorted

    def _place_order(self, sku: str, qty: int) -> None:
        self.pending.append(
            _PendingOrder(
                sku=sku, qty=qty, arrives_at_step=self.step_idx + self.lead_time
            )
        )
        self.n_orders += 1
        self.total_units_ordered += qty

    # --- Run loop ---------------------------------------------------------
    def run(self, n_steps: int) -> BaselineRunResult:
        if self.policy is None:
            raise RuntimeError("Call fit_warmup() before run().")

        steps_with_stockout = 0
        for offset in range(n_steps):
            absolute_step = self.fit_window + offset
            self.step_idx = absolute_step

            # 1. Receive arriving shipments.
            self._deliver_arrivals()

            # 2. Pull demand and apply drift.
            events = self.replay.events_for_step(absolute_step)
            events = self.drift_injector.apply(absolute_step, events)

            # 3. Fulfill demand.
            had_stockout = False
            for sku, qty in events.items():
                shorted = self._fulfill(sku, qty)
                if shorted > 0:
                    had_stockout = True
                # Periodic forecasting observes raw demand for its next refit.
                if isinstance(self.policy, PeriodicForecastingBaseline):
                    self.policy.observe(absolute_step, sku, qty)
            if had_stockout:
                steps_with_stockout += 1

            # 4. Periodic refit (no-op for static ROP).
            if isinstance(self.policy, PeriodicForecastingBaseline):
                self.policy.maybe_refit(absolute_step)

            # 5. Decide replenishment.
            for sku in self.skus:
                qty = self.policy.decide(sku, self.stock.get(sku, 0))
                if qty > 0:
                    self._place_order(sku, qty)

            # 6. Record snapshot.
            self.timeseries.append(
                {
                    "step": absolute_step,
                    "total_on_hand": sum(self.stock.values()),
                    "stockout_skus_step": sum(
                        1 for s in self.skus if self.stock.get(s, 0) == 0
                    ),
                }
            )

        return BaselineRunResult(
            n_steps=n_steps,
            stockout_rate=steps_with_stockout / n_steps if n_steps else 0.0,
            stockout_duration_per_sku=dict(self.stockout_steps),
            final_total_on_hand=sum(self.stock.values()),
            n_orders=self.n_orders,
            total_units_ordered=self.total_units_ordered,
            timeseries=self.timeseries,
        )
