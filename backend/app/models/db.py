"""SQLAlchemy models for the experiment catalog.

Schema:
  experiments   one row per (config_name, scenario, policy) cohort
  seeds         one row per (experiment, seed) — the leaves of a sweep
  decisions     one row per agent decision event (insert-heavy, indexed)
  jobs          one row per user-launched run, tracks status + progress

The schema is intentionally denormalised for read performance: a
queryable subset of summary metrics lives on `seeds` and `experiments`
so the dashboard can sort/filter without parsing JSON blobs at query
time. The full JSON summary is also stored for completeness.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    Column, DateTime, Float, ForeignKey, Index, Integer, JSON, String, Text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utcnow() -> datetime:
    """Timezone-aware UTC `now()`.

    Use this everywhere a timestamp is generated. `datetime.utcnow()` is
    naive (no tzinfo), which serializes to JSON without a `Z` suffix and
    is then misinterpreted as local time by JavaScript's `new Date(...)`.
    """
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------------------------
# Experiment cohorts (one per config × scenario × policy)
# ---------------------------------------------------------------------------
class Experiment(Base):
    __tablename__ = "experiments"

    id: Mapped[int] = mapped_column(primary_key=True)
    config_name: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    scenario: Mapped[str] = mapped_column(String(64), index=True)
    policy: Mapped[str] = mapped_column(String(32), index=True)
    n_seeds: Mapped[int] = mapped_column(Integer, default=0)
    family: Mapped[str] = mapped_column(String(32), index=True)  # h1, h3, ablation, custom

    # Aggregate metrics (mean across seeds) — surfaced for fast list views.
    mean_stockout_rate: Mapped[Optional[float]] = mapped_column(Float)
    mean_total_cost: Mapped[Optional[float]] = mapped_column(Float)
    mean_n_orders: Mapped[Optional[float]] = mapped_column(Float)
    mean_forecast_mape: Mapped[Optional[float]] = mapped_column(Float)
    mean_runtime_seconds: Mapped[Optional[float]] = mapped_column(Float)
    mean_n_drift_events: Mapped[Optional[float]] = mapped_column(Float)

    # Optional 95% CI bounds for the headline metric (stockout_rate).
    ci95_stockout_lo: Mapped[Optional[float]] = mapped_column(Float)
    ci95_stockout_hi: Mapped[Optional[float]] = mapped_column(Float)

    # Drift onset (for non-no_drift scenarios).
    drift_start_step: Mapped[Optional[int]] = mapped_column(Integer)

    # Full aggregate JSON for everything else.
    aggregate_json: Mapped[Optional[dict]] = mapped_column(JSON)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow,
    )

    seeds = relationship("Seed", back_populates="experiment", lazy="select",
                         cascade="all, delete-orphan")


# ---------------------------------------------------------------------------
# Individual seed runs
# ---------------------------------------------------------------------------
class Seed(Base):
    __tablename__ = "seeds"

    id: Mapped[int] = mapped_column(primary_key=True)
    experiment_id: Mapped[int] = mapped_column(
        ForeignKey("experiments.id", ondelete="CASCADE"), index=True
    )
    seed_num: Mapped[int] = mapped_column(Integer, index=True)
    n_skus: Mapped[Optional[int]] = mapped_column(Integer)

    # Headline metrics, indexed for filtering.
    stockout_rate: Mapped[Optional[float]] = mapped_column(Float, index=True)
    total_cost: Mapped[Optional[float]] = mapped_column(Float, index=True)
    n_orders: Mapped[Optional[int]] = mapped_column(Integer)
    forecast_mape: Mapped[Optional[float]] = mapped_column(Float)
    runtime_seconds: Mapped[Optional[float]] = mapped_column(Float)
    peak_memory_mb: Mapped[Optional[float]] = mapped_column(Float)
    n_drift_events: Mapped[Optional[int]] = mapped_column(Integer)
    n_global_drift_events: Mapped[Optional[int]] = mapped_column(Integer)
    n_refits: Mapped[Optional[int]] = mapped_column(Integer)

    # Full summary JSON.
    summary_json: Mapped[Optional[dict]] = mapped_column(JSON)
    # Path to the timeseries.csv on disk (relative to project root).
    timeseries_path: Mapped[Optional[str]] = mapped_column(String(500))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow,
    )

    experiment = relationship("Experiment", back_populates="seeds")
    decisions = relationship("Decision", back_populates="seed", lazy="select",
                             cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_seed_experiment_seednum", "experiment_id", "seed_num", unique=True),
    )


# ---------------------------------------------------------------------------
# Decision events from per-agent logs
# ---------------------------------------------------------------------------
class Decision(Base):
    """One row per logged action from any agent.

    Indexed by (seed_id, agent, action, step, sku) so per-SKU and
    per-action drill-downs return in O(log n).
    """
    __tablename__ = "decisions"

    id: Mapped[int] = mapped_column(primary_key=True)
    seed_id: Mapped[int] = mapped_column(
        ForeignKey("seeds.id", ondelete="CASCADE"), index=True
    )
    step: Mapped[int] = mapped_column(Integer, index=True)
    agent: Mapped[str] = mapped_column(String(32), index=True)
    action: Mapped[str] = mapped_column(String(64), index=True)
    sku: Mapped[Optional[str]] = mapped_column(String(64), index=True)
    # Full structured details (qty, residual, on_hand, etc.).
    details_json: Mapped[Optional[dict]] = mapped_column(JSON)

    seed = relationship("Seed", back_populates="decisions")

    __table_args__ = (
        Index("ix_decision_seed_agent_action", "seed_id", "agent", "action"),
        Index("ix_decision_seed_sku_step", "seed_id", "sku", "step"),
    )


# ---------------------------------------------------------------------------
# User-launched jobs (for the run-launcher UI)
# ---------------------------------------------------------------------------
class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)  # UUID
    config_name: Mapped[str] = mapped_column(String(255), index=True)
    seeds_csv: Mapped[str] = mapped_column(String(255))  # "1,2,3"
    status: Mapped[str] = mapped_column(String(32), index=True)
    # queued, running, succeeded, failed, cancelled
    progress_pct: Mapped[float] = mapped_column(Float, default=0.0)
    completed_seeds: Mapped[int] = mapped_column(Integer, default=0)
    total_seeds: Mapped[int] = mapped_column(Integer, default=0)
    log_tail: Mapped[Optional[str]] = mapped_column(Text)
    error: Mapped[Optional[str]] = mapped_column(Text)

    # Optional parameter overrides applied to the base config.
    overrides_json: Mapped[Optional[dict]] = mapped_column(JSON)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow,
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
