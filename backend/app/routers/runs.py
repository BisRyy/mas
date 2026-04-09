"""Run-launcher endpoints + live progress WebSocket."""
from __future__ import annotations

import asyncio
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_settings
from ..database import get_db, SessionLocal
from ..models import Job
from ..schemas import JobCreate, JobStatus
from ..services.job_manager import get_job_manager

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api/runs", tags=["runs"])


@router.post("", response_model=JobStatus, status_code=202)
async def create_run(payload: JobCreate, db: AsyncSession = Depends(get_db)):
    settings = get_settings()
    if not settings.allow_run_launch:
        raise HTTPException(403, "Run launching is disabled in this deployment")

    cfg_path = settings.configs_dir / f"{payload.config_name}.yaml"
    if not cfg_path.exists():
        raise HTTPException(404, f"Config {payload.config_name!r} not found")

    mgr = get_job_manager()
    try:
        job = await mgr.submit(
            db,
            payload.config_name,
            payload.seeds,
            payload.overrides,
        )
    except RuntimeError as exc:
        raise HTTPException(429, str(exc))
    return job


@router.get("", response_model=list[JobStatus])
async def list_runs(
    status: Optional[str] = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Job).order_by(Job.created_at.desc()).limit(limit)
    if status:
        stmt = stmt.where(Job.status == status)
    res = await db.execute(stmt)
    return res.scalars().all()


@router.get("/{job_id}", response_model=JobStatus)
async def get_run(job_id: str, db: AsyncSession = Depends(get_db)):
    job = await db.get(Job, job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    return job


# ---------------------------------------------------------------------------
# WebSocket for live progress
# ---------------------------------------------------------------------------
@router.websocket("/{job_id}/stream")
async def stream_progress(ws: WebSocket, job_id: str):
    await ws.accept()

    # Replay current state once, then stream new events.
    async with SessionLocal() as session:
        job = await session.get(Job, job_id)
        if job is None:
            await ws.send_json({"type": "error", "message": "Job not found"})
            await ws.close(code=1008)
            return
        await ws.send_json({
            "type": "snapshot",
            "status": job.status,
            "completed_seeds": job.completed_seeds,
            "total_seeds": job.total_seeds,
            "progress_pct": job.progress_pct,
            "log_tail": job.log_tail,
            "error": job.error,
        })

    mgr = get_job_manager()
    q = mgr.subscribe(job_id)
    try:
        while True:
            try:
                event = await asyncio.wait_for(q.get(), timeout=30)
            except asyncio.TimeoutError:
                # heartbeat to keep the connection alive on proxies
                await ws.send_json({"type": "ping"})
                continue
            await ws.send_json(event)
            if event.get("type") == "status" and event.get("status") in (
                "succeeded", "failed", "cancelled"
            ):
                break
    except WebSocketDisconnect:
        pass
    finally:
        mgr.unsubscribe(job_id, q)
