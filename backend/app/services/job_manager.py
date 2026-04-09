"""In-process job queue for user-launched simulation sweeps.

Each job runs `python -m experiments.sweep -c <config> --seeds <seeds>`
under the project root, streaming progress to subscribers via an
asyncio.Queue. The job manager is intentionally simple: no external
broker, no persistence beyond the SQLite Job row. For production
scale, swap in Celery + Redis.
"""
from __future__ import annotations

import asyncio
import logging
import subprocess
import uuid
from collections import defaultdict, deque
from datetime import datetime
from pathlib import Path
from typing import Any, AsyncIterator

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_settings
from ..database import SessionLocal
from ..models import Job
from .ingestion import ingest_all

log = logging.getLogger(__name__)


class JobManager:
    def __init__(self, max_concurrent: int = 1, max_queue: int = 3):
        self._sem = asyncio.Semaphore(max_concurrent)
        self._max_queue = max_queue
        self._subscribers: dict[str, list[asyncio.Queue]] = defaultdict(list)
        self._tasks: dict[str, asyncio.Task] = {}
        self._tails: dict[str, deque[str]] = defaultdict(lambda: deque(maxlen=200))

    # --- Subscriber side --------------------------------------------------
    def subscribe(self, job_id: str) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue()
        self._subscribers[job_id].append(q)
        # Replay buffered tail so late subscribers see context.
        for line in list(self._tails[job_id]):
            q.put_nowait({"type": "log", "line": line})
        return q

    def unsubscribe(self, job_id: str, q: asyncio.Queue) -> None:
        try:
            self._subscribers[job_id].remove(q)
        except ValueError:
            pass

    async def _emit(self, job_id: str, event: dict[str, Any]) -> None:
        if event.get("type") == "log":
            self._tails[job_id].append(event.get("line", ""))
        for q in self._subscribers.get(job_id, []):
            await q.put(event)

    # --- Job lifecycle ----------------------------------------------------
    async def queue_count(self) -> int:
        return len(self._tasks)

    async def submit(
        self,
        db: AsyncSession,
        config_name: str,
        seeds: list[int],
        overrides: dict[str, Any] | None = None,
    ) -> Job:
        if len(self._tasks) >= self._max_queue:
            raise RuntimeError(
                f"queue full ({self._max_queue} jobs); try again later"
            )
        job = Job(
            id=str(uuid.uuid4()),
            config_name=config_name,
            seeds_csv=",".join(str(s) for s in seeds),
            status="queued",
            total_seeds=len(seeds),
            overrides_json=overrides or None,
        )
        db.add(job)
        await db.commit()

        task = asyncio.create_task(self._run_job(job.id, config_name, seeds, overrides or {}))
        self._tasks[job.id] = task
        task.add_done_callback(lambda _t: self._tasks.pop(job.id, None))
        return job

    async def _run_job(
        self, job_id: str, config_name: str, seeds: list[int], overrides: dict[str, Any]
    ) -> None:
        settings = get_settings()
        async with self._sem:  # cap concurrent simulations
            async with SessionLocal() as session:
                job = await session.get(Job, job_id)
                if job is None:
                    return
                job.status = "running"
                job.started_at = datetime.utcnow()
                await session.commit()
                await self._emit(job_id, {"type": "status", "status": "running"})

            base = settings.configs_dir / f"{config_name}.yaml"
            if not base.exists():
                await self._fail(job_id, f"Config not found: {base}")
                return

            # Apply overrides into a temp YAML if any provided.
            cfg_path = base
            if overrides:
                import yaml
                cfg_data = yaml.safe_load(base.read_text())
                cfg_data.update(overrides)
                cfg_data["name"] = f"{config_name}_user"
                tmp = settings.configs_dir / f"_user_{job_id}.yaml"
                tmp.write_text(yaml.safe_dump(cfg_data, sort_keys=False))
                cfg_path = tmp

            cmd = [
                "python", "-m", "experiments.sweep",
                "-c", str(cfg_path),
                "--seeds", *[str(s) for s in seeds],
                "--jitter", "0.2",
            ]
            try:
                await self._stream_subprocess(job_id, cmd, settings.project_root, total=len(seeds))
            except Exception as exc:
                await self._fail(job_id, repr(exc))
                return

            # Re-ingest results so the new seed rows show up in the catalog.
            async with SessionLocal() as session:
                await ingest_all(session)

            async with SessionLocal() as session:
                job = await session.get(Job, job_id)
                if job is None:
                    return
                if job.status != "failed":
                    job.status = "succeeded"
                    job.finished_at = datetime.utcnow()
                    job.progress_pct = 100.0
                    await session.commit()
                    await self._emit(job_id, {"type": "status", "status": "succeeded"})

    async def _stream_subprocess(
        self, job_id: str, cmd: list[str], cwd: Path, total: int
    ) -> None:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=str(cwd),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        completed = 0
        assert proc.stdout is not None
        async for raw in proc.stdout:
            line = raw.decode("utf-8", errors="replace").rstrip("\n")
            if not line:
                continue
            await self._emit(job_id, {"type": "log", "line": line})
            # Sweep prints "[K/N] olist_xxx seed=N stockout=…" — count completions.
            if line.startswith("[") and "/" in line[:8]:
                completed += 1
                pct = 100.0 * completed / max(total, 1)
                async with SessionLocal() as session:
                    job = await session.get(Job, job_id)
                    if job is not None:
                        job.completed_seeds = completed
                        job.progress_pct = pct
                        await session.commit()
                await self._emit(job_id, {
                    "type": "progress",
                    "completed": completed,
                    "total": total,
                    "pct": pct,
                })
        rc = await proc.wait()
        if rc != 0:
            await self._fail(job_id, f"sweep exited with code {rc}")

    async def _fail(self, job_id: str, error: str) -> None:
        async with SessionLocal() as session:
            job = await session.get(Job, job_id)
            if job is not None:
                job.status = "failed"
                job.error = error
                job.finished_at = datetime.utcnow()
                await session.commit()
        await self._emit(job_id, {"type": "status", "status": "failed", "error": error})


_manager: JobManager | None = None


def get_job_manager() -> JobManager:
    global _manager
    if _manager is None:
        s = get_settings()
        _manager = JobManager(
            max_concurrent=s.max_concurrent_runs,
            max_queue=s.max_queued_runs,
        )
    return _manager
