"""Backend configuration.

All knobs that need to vary by environment (dev / docker / production)
live here. Pydantic-Settings reads from environment variables prefixed
with `MAS_` plus an optional `.env` file at the repo root.
"""
from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="MAS_",
        env_file=(".env",),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Filesystem layout --------------------------------------------------
    # Project root — the directory that contains src/, results/, experiments/,
    # thesis/, etc. Set MAS_PROJECT_ROOT to point to a different checkout if
    # running the backend out-of-tree.
    project_root: Path = Field(
        default_factory=lambda: Path(__file__).resolve().parents[2]
    )

    # SQLite database file for the experiment catalog. Held in the project
    # root by default so it's discoverable alongside the simulation outputs.
    database_url: str = "sqlite+aiosqlite:///./backend/inventory_mas.db"
    sync_database_url: str = "sqlite:///./backend/inventory_mas.db"

    # --- API ----------------------------------------------------------------
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    # Comma-separated list of allowed CORS origins. Wildcard is fine in dev
    # but the Docker Compose / production deploys should set this to the
    # actual frontend origin.
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    # --- Run-launch policy --------------------------------------------------
    # When False the POST /api/runs endpoint always 403s. Set to False to
    # ship a read-only public demo.
    allow_run_launch: bool = True
    # Cap how many sweeps can be queued at once to keep a small VM
    # responsive. The N-th request returns 429.
    max_queued_runs: int = 3
    # Cap on parallel workers actually executing simulations. Each sim is
    # single-threaded but heavy on CPU.
    max_concurrent_runs: int = 1

    # --- Misc ---------------------------------------------------------------
    log_level: str = "INFO"

    # Helpers
    @property
    def results_dir(self) -> Path:
        return self.project_root / "results"

    @property
    def configs_dir(self) -> Path:
        return self.project_root / "experiments" / "configs"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
