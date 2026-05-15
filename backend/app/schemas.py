"""Pydantic DTOs exposed by the REST API.

Kept separate from the SQLAlchemy ORM models so the wire format can
evolve independently from the database schema.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, field_serializer


def _serialize_dt(v: Optional[datetime]) -> Optional[str]:
    """Serialize datetimes as RFC 3339 with a TZ marker.

    Why: SQLite doesn't preserve tzinfo, so datetimes read back from the
    DB are naive. JavaScript's `new Date(iso)` interprets naive ISO
    strings as *local* time, which corrupted every clock in the UI.
    Coerce naive datetimes to UTC and always emit a `+00:00` suffix so
    the browser parses them correctly and `.toLocaleString()` renders
    them in the user's zone.
    """
    if v is None:
        return None
    if v.tzinfo is None:
        v = v.replace(tzinfo=timezone.utc)
    return v.isoformat()


class TimedModel(BaseModel):
    """Base for any schema that contains datetime fields.

    The `field_serializer` runs against the listed field names if they
    exist on the subclass (check_fields=False suppresses the error when
    a subclass has none of them). The covered names — created_at,
    updated_at, started_at, finished_at, generated_at — are all the
    datetime fields currently in the API surface. New names should be
    added here.
    """

    @field_serializer(
        "created_at", "updated_at", "started_at", "finished_at",
        "generated_at", check_fields=False,
    )
    def _ser_dt(self, v: Optional[datetime]) -> Optional[str]:
        return _serialize_dt(v)


class ORMModel(TimedModel):
    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Experiments
# ---------------------------------------------------------------------------
class ExperimentSummary(ORMModel):
    id: int
    config_name: str
    scenario: str
    policy: str
    family: str
    n_seeds: int
    mean_stockout_rate: Optional[float]
    mean_total_cost: Optional[float]
    mean_n_orders: Optional[float]
    mean_forecast_mape: Optional[float]
    mean_runtime_seconds: Optional[float]
    mean_n_drift_events: Optional[float]
    ci95_stockout_lo: Optional[float]
    ci95_stockout_hi: Optional[float]
    drift_start_step: Optional[int]
    updated_at: datetime


class ExperimentDetail(ExperimentSummary):
    aggregate_json: Optional[dict[str, Any]] = None
    created_at: datetime


# ---------------------------------------------------------------------------
# Seeds
# ---------------------------------------------------------------------------
class SeedSummary(ORMModel):
    id: int
    experiment_id: int
    seed_num: int
    n_skus: Optional[int]
    stockout_rate: Optional[float]
    total_cost: Optional[float]
    n_orders: Optional[int]
    forecast_mape: Optional[float]
    runtime_seconds: Optional[float]
    n_drift_events: Optional[int]
    n_global_drift_events: Optional[int]
    n_refits: Optional[int]


class SeedDetail(SeedSummary):
    summary_json: Optional[dict[str, Any]] = None
    timeseries_path: Optional[str] = None
    peak_memory_mb: Optional[float] = None


class TimeseriesPoint(BaseModel):
    step: int
    total_on_hand: int
    stockout_skus_step: int


class SeedTimeseries(BaseModel):
    seed_id: int
    steps: list[TimeseriesPoint]


# ---------------------------------------------------------------------------
# Decisions
# ---------------------------------------------------------------------------
class DecisionEntry(ORMModel):
    id: int
    step: int
    agent: str
    action: str
    sku: Optional[str]
    details_json: Optional[dict[str, Any]]


class DecisionPage(BaseModel):
    items: list[DecisionEntry]
    total: int
    page: int
    page_size: int


# ---------------------------------------------------------------------------
# Reports
# ---------------------------------------------------------------------------
class StatTest(BaseModel):
    scenario: str
    baseline: str
    metric: str
    treatment_mean: Optional[float] = None
    baseline_mean: Optional[float] = None
    rel_change: Optional[float] = None
    mannwhitney_p: Optional[float] = None
    welch_p: Optional[float] = None
    cohens_d: Optional[float] = None


class H1Report(TimedModel):
    generated_at: datetime
    tests: list[StatTest]


class H3Fit(BaseModel):
    policy: str
    exponent_b: float
    a: float
    r2: float
    classification: str
    linear_r2: Optional[float] = None
    raw_points: list[dict[str, Any]] = Field(default_factory=list)


class H3Report(TimedModel):
    generated_at: datetime
    fits: list[H3Fit]


class AblationRow(BaseModel):
    variant: str
    n_seeds: int
    stockout_rate_mean: Optional[float] = None
    total_cost_mean: Optional[float] = None
    forecast_mape_mean: Optional[float] = None
    n_global_drift_events_mean: Optional[float] = None
    rel_to_full_stockout: Optional[float] = None
    rel_to_full_cost: Optional[float] = None


class AblationReport(TimedModel):
    generated_at: datetime
    rows: list[AblationRow]


# ---------------------------------------------------------------------------
# Jobs (run launcher)
# ---------------------------------------------------------------------------
class JobStatus(ORMModel):
    id: str
    config_name: str
    seeds_csv: str
    status: str
    progress_pct: float
    completed_seeds: int
    total_seeds: int
    log_tail: Optional[str] = None
    error: Optional[str] = None
    overrides_json: Optional[dict[str, Any]] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None


class JobCreate(BaseModel):
    config_name: str = Field(..., description="Name of YAML config under experiments/configs/")
    seeds: list[int] = Field(..., min_length=1, max_length=30)
    overrides: dict[str, Any] = Field(
        default_factory=dict,
        description="Top-level config keys to override (e.g. {lead_time: 14})",
    )


# ---------------------------------------------------------------------------
# Misc
# ---------------------------------------------------------------------------
class IngestionResult(BaseModel):
    experiments: int
    seeds: int
    decisions: int


class HealthCheck(BaseModel):
    status: str = "ok"
    version: str = "1.0.0"
