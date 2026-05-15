"""System status + diagnostics — powers the frontend /settings page.

Read-only. Aggregates information that would otherwise require shelling
into the container (DB row counts, disk usage, queue state, effective
config). Also exposes a single mutation: a one-shot re-ingestion of the
results/ tree, useful when sweep outputs have been added to the volume
out-of-band (e.g. SCP'd in) and we don't want to bounce the container.
"""
from __future__ import annotations

import os
import time
from pathlib import Path

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_settings
from ..database import get_db
from ..models import Decision, Experiment, Job, Seed
from ..services.ingestion import ingest_all
from ..services.job_manager import get_job_manager


router = APIRouter(prefix="/api/_meta", tags=["meta"])


# Process start time — captured at module import so /status can report
# how long uvicorn has been up.
_PROCESS_STARTED_AT = time.time()


def _dir_size_bytes(path: Path) -> int:
    """Recursive on-disk size of a directory tree, ignoring symlinks."""
    if not path.exists():
        return 0
    total = 0
    for root, _dirs, files in os.walk(path, followlinks=False):
        for f in files:
            try:
                total += os.path.getsize(os.path.join(root, f))
            except OSError:
                # File vanished mid-walk or permission denied — skip.
                continue
    return total


@router.get("/status")
async def system_status(db: AsyncSession = Depends(get_db)) -> dict:
    """One-shot snapshot of API + DB + queue + disk state."""
    settings = get_settings()
    jm = get_job_manager()

    # DB row counts — cheap on SQLite even for the 23k-row decisions table.
    counts = {}
    for name, model in [
        ("experiments", Experiment),
        ("seeds", Seed),
        ("decisions", Decision),
        ("jobs", Job),
    ]:
        n = await db.scalar(select(func.count()).select_from(model))
        counts[name] = int(n or 0)

    # Last ingest = most-recent Experiment.updated_at.
    last_updated = await db.scalar(select(func.max(Experiment.updated_at)))

    # Queue state.
    queue_count = await jm.queue_count()

    # Disk usage of the results-data volume mount.
    results_bytes = _dir_size_bytes(settings.results_dir)

    return {
        "api": {
            "version": "1.0.0",
            "uptime_seconds": int(time.time() - _PROCESS_STARTED_AT),
            "process_started_at_unix": int(_PROCESS_STARTED_AT),
        },
        "database": {
            "url_redacted": _redact_db_url(settings.database_url),
            "counts": counts,
            "last_ingest_at": last_updated.isoformat() if last_updated else None,
        },
        "filesystem": {
            "project_root": str(settings.project_root),
            "results_dir": str(settings.results_dir),
            "results_size_bytes": results_bytes,
            "configs_dir": str(settings.configs_dir),
        },
        "queue": {
            "current_jobs": queue_count,
            "max_queued": settings.max_queued_runs,
            "max_concurrent": settings.max_concurrent_runs,
        },
        "policy": {
            "allow_run_launch": settings.allow_run_launch,
            "cors_origins": settings.cors_origin_list,
        },
    }


@router.post("/reingest")
async def trigger_reingest(db: AsyncSession = Depends(get_db)) -> dict:
    """Re-walk results/ and upsert into the DB. Idempotent."""
    counts = await ingest_all(db)
    return {"ok": True, **counts}


def _redact_db_url(url: str) -> str:
    """SQLite URLs don't carry credentials, but redact defensively in case
    the deployment is ever swapped for Postgres/MySQL."""
    if "@" not in url:
        return url
    scheme, rest = url.split("://", 1)
    if "@" in rest:
        _creds, host = rest.split("@", 1)
        return f"{scheme}://***@{host}"
    return url
