"""FastAPI application entry point."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .database import SessionLocal, init_db
from .routers import configs as configs_router
from .routers import experiments as experiments_router
from .routers import reports as reports_router
from .routers import runs as runs_router
from .routers import seeds as seeds_router
from .schemas import HealthCheck
from .services.ingestion import ingest_all


logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Bootstrap: create tables, ingest results/ at startup."""
    await init_db()
    async with SessionLocal() as session:
        counts = await ingest_all(session)
    log.info(
        "Startup ingest: %d experiments, %d seeds, %d decisions",
        counts["experiments"], counts["seeds"], counts["decisions"],
    )
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Inventory MAS — Tracking & Analytics API",
        version="1.0.0",
        description=(
            "REST + WebSocket API for the inventory-MAS simulator. Exposes "
            "experiment catalog, per-seed timeseries, decision-log audit "
            "trail, statistical reports, and a run launcher."
        ),
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(experiments_router.router)
    app.include_router(seeds_router.router)
    app.include_router(reports_router.router)
    app.include_router(runs_router.router)
    app.include_router(configs_router.router)

    @app.get("/api/health", response_model=HealthCheck, tags=["meta"])
    async def health() -> HealthCheck:
        return HealthCheck()

    return app


app = create_app()
