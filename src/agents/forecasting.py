"""Demand Forecasting Agent.

Tiered per-SKU forecaster (model selected by history length) with per-SKU
ADWIN drift detection. The detector marks a SKU's model stale on signal;
the next `predict()` call lazily refits.

Tier ladder (per SKU):
  -  < `min_obs_ses`  : moving-average level
  -  < `min_obs_hw`   : SimpleExpSmoothing (level only)
  -  >=`min_obs_hw`   : Holt-Winters additive (level + trend + seasonal_periods)

The agent exposes:
  - `predict(sku) -> float`       : expected per-day demand for `sku`
  - `predict_std(sku) -> float`   : residual std (used for safety stock)
  - `drift_events`                : list of (step, sku) tuples
  - `refit_count`                 : total refits across SKUs
  - `actuals[sku]` / `predictions[sku]` : for end-of-run MAPE
"""
from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any
import math
import warnings

from .base import BaseInventoryAgent


# Silence the noisy "ConvergenceWarning" stream from statsmodels — we already
# have an explicit MA fallback when fits fail, and the warnings are not
# actionable on per-SKU short series.
warnings.filterwarnings("ignore", category=Warning, module=r"statsmodels.*")


@dataclass
class _FittedModel:
    """Cached forecast for a SKU.

    We store the *one-step-ahead* mean and a residual std rather than the
    full statsmodels result so memory stays bounded across 200+ SKUs.
    """
    mean: float
    std: float
    fitted_at_step: int
    method: str  # "ma" | "ses" | "hw"
    n_obs: int


class DemandForecastingAgent(BaseInventoryAgent):
    def __init__(
        self,
        model: Any,
        history_window: int = 180,
        forecast_horizon: int = 7,
        min_obs_ses: int = 14,
        min_obs_hw: int = 35,
        seasonal_periods: int = 7,
        safety_refit_interval: int = 60,
        # ADWIN's default delta (0.002) is tuned for noisy streams; on
        # per-SKU forecast residuals it's too conservative. We use 0.01 by
        # default, which still controls false positives but actually detects
        # the kind of regime shifts the proposal targets. Tunable per run.
        adwin_delta: float = 0.01,
    ) -> None:
        super().__init__(model)
        self.history_window = history_window
        self.forecast_horizon = forecast_horizon
        self.min_obs_ses = min_obs_ses
        self.min_obs_hw = min_obs_hw
        self.seasonal_periods = seasonal_periods
        self.safety_refit_interval = safety_refit_interval
        self.adwin_delta = adwin_delta

        # Per-SKU rolling history, models, detectors.
        self.history: dict[str, deque[float]] = defaultdict(
            lambda: deque(maxlen=self.history_window)
        )
        self.models: dict[str, _FittedModel] = {}
        self.detectors: dict[str, Any] = {}  # per-SKU ADWIN, lazily created
        self.model_stale: dict[str, bool] = defaultdict(lambda: True)

        # Global ADWIN on the system-wide mean absolute residual. Per-SKU
        # residuals are too noisy to drive detection on their own; the
        # population mean averages out individual variance and reveals
        # regime shifts that affect the cohort. This is the primary refit
        # trigger; per-SKU detectors stay as diagnostics for which SKU drifted.
        self._global_detector: Any = None  # lazily created on first residual

        # Diagnostics.
        self.drift_events: list[tuple[int, str]] = []  # per-SKU detections
        self.global_drift_steps: list[int] = []         # global detections
        self.refit_count: int = 0
        self.actuals: dict[str, list[float]] = defaultdict(list)
        self.predictions: dict[str, list[float]] = defaultdict(list)

    # --- Drift detection --------------------------------------------------
    def _get_detector(self, sku: str):
        from src.drift import ADWINDetector

        if sku not in self.detectors:
            self.detectors[sku] = ADWINDetector(delta=self.adwin_delta)
        return self.detectors[sku]

    def _get_global_detector(self):
        from src.drift import ADWINDetector

        if self._global_detector is None:
            self._global_detector = ADWINDetector(delta=self.adwin_delta)
        return self._global_detector

    # --- Fitting ----------------------------------------------------------
    def _fit_ma(self, hist: list[float]) -> _FittedModel:
        n = len(hist)
        mean = sum(hist) / n if n else 0.0
        if n > 1:
            var = sum((x - mean) ** 2 for x in hist) / (n - 1)
            std = math.sqrt(var)
        else:
            std = 0.0
        return _FittedModel(
            mean=mean,
            std=std,
            fitted_at_step=self.model.steps,
            method="ma",
            n_obs=n,
        )

    def _fit_ses(self, hist: list[float]) -> _FittedModel:
        from statsmodels.tsa.holtwinters import SimpleExpSmoothing
        import numpy as np

        try:
            res = SimpleExpSmoothing(np.array(hist, dtype=float)).fit(
                optimized=True
            )
            forecast = float(res.forecast(1)[0])
            resid = np.array(hist, dtype=float) - res.fittedvalues
            std = float(np.std(resid, ddof=1)) if len(resid) > 1 else 0.0
            return _FittedModel(
                mean=max(forecast, 0.0),
                std=std,
                fitted_at_step=self.model.steps,
                method="ses",
                n_obs=len(hist),
            )
        except Exception:
            return self._fit_ma(hist)

    def _fit_hw(self, hist: list[float]) -> _FittedModel:
        from statsmodels.tsa.holtwinters import ExponentialSmoothing
        import numpy as np

        try:
            res = ExponentialSmoothing(
                np.array(hist, dtype=float),
                trend="add",
                seasonal="add",
                seasonal_periods=self.seasonal_periods,
                initialization_method="estimated",
            ).fit(optimized=True)
            forecast = float(res.forecast(1)[0])
            resid = np.array(hist, dtype=float) - res.fittedvalues
            std = float(np.std(resid, ddof=1)) if len(resid) > 1 else 0.0
            return _FittedModel(
                mean=max(forecast, 0.0),
                std=std,
                fitted_at_step=self.model.steps,
                method="hw",
                n_obs=len(hist),
            )
        except Exception:
            return self._fit_ses(hist)

    def _refit(self, sku: str) -> None:
        hist_list = list(self.history.get(sku, []))
        n = len(hist_list)
        if n < self.min_obs_ses:
            model = self._fit_ma(hist_list)
        elif n < self.min_obs_hw:
            model = self._fit_ses(hist_list)
        else:
            model = self._fit_hw(hist_list)
        self.models[sku] = model
        self.model_stale[sku] = False
        self.refit_count += 1
        self.log("refit", sku=sku, method=model.method, n_obs=model.n_obs)

    # --- Public API used by ReplenishmentAgent ---------------------------
    def _ensure_fresh(self, sku: str) -> _FittedModel | None:
        if sku not in self.history or len(self.history[sku]) == 0:
            return None
        fitted = self.models.get(sku)
        n_obs = len(self.history[sku])
        # Refit when stale, missing, time-stale, or when history has grown
        # past a tier threshold so we can promote MA -> SES -> HW.
        tier_promotion = (
            fitted is not None
            and (
                (fitted.method == "ma" and n_obs >= self.min_obs_ses)
                or (fitted.method == "ses" and n_obs >= self.min_obs_hw)
            )
        )
        needs_refit = (
            self.model_stale.get(sku, True)
            or fitted is None
            or tier_promotion
            or (self.model.steps - fitted.fitted_at_step) >= self.safety_refit_interval
        )
        if needs_refit:
            self._refit(sku)
        return self.models.get(sku)

    def predict(self, sku: str) -> float:
        """Expected per-day demand for `sku`."""
        fitted = self._ensure_fresh(sku)
        return fitted.mean if fitted else 0.0

    def predict_std(self, sku: str) -> float:
        """Residual std of per-day demand (used to compute safety stock)."""
        fitted = self._ensure_fresh(sku)
        return fitted.std if fitted else 0.0

    # --- Mesa hook --------------------------------------------------------
    def step(self) -> None:
        step_idx = self.model.steps
        # Collect residuals across all SKUs that observed demand this step,
        # for the global drift detector.
        step_residuals: list[float] = []
        step_skus_with_residual: list[str] = []

        for msg in self.drain_inbox():
            if msg.get("type") != "demand_observed":
                continue
            sku, qty = msg["sku"], float(msg["qty"])
            # Observation -> history.
            self.history[sku].append(qty)
            self.actuals[sku].append(qty)
            # Capture the prediction that was current going into this step.
            fitted = self.models.get(sku)
            if fitted is None:
                # No model yet -> cannot compute a residual; skip ADWIN.
                continue
            predicted = fitted.mean
            self.predictions[sku].append(predicted)

            # Drift detection on absolute forecast residual. §2.3 of the
            # proposal: error-monitoring techniques.
            residual = abs(qty - predicted)
            step_residuals.append(residual)
            step_skus_with_residual.append(sku)

            # Per-SKU detector (diagnostic, narrow signal).
            signal = self._get_detector(sku).update(residual, step=step_idx)
            if signal.detected:
                self.drift_events.append((step_idx, sku))
                self.model_stale[sku] = True
                self.log("drift_detected", sku=sku, step=step_idx, residual=residual)

        # Global detector on the step's mean absolute residual. This is the
        # primary trigger because per-SKU streams are too noisy on sparse data.
        if step_residuals:
            mean_residual = sum(step_residuals) / len(step_residuals)
            global_signal = self._get_global_detector().update(
                mean_residual, step=step_idx
            )
            if global_signal.detected:
                self.global_drift_steps.append(step_idx)
                # Mark every SKU that contributed to today's residual stale;
                # next predict() refits them. Other SKUs keep their current
                # models (no fresh evidence they've drifted).
                for sku in step_skus_with_residual:
                    self.model_stale[sku] = True
                self.log(
                    "global_drift_detected",
                    step=step_idx,
                    mean_residual=mean_residual,
                    n_skus_affected=len(step_skus_with_residual),
                )
