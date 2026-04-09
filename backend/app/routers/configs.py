"""Endpoints exposing the on-disk YAML config catalog."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from fastapi import APIRouter, HTTPException

from ..config import get_settings


router = APIRouter(prefix="/api/configs", tags=["configs"])


@router.get("")
async def list_configs() -> list[dict[str, Any]]:
    settings = get_settings()
    out: list[dict[str, Any]] = []
    for p in sorted(settings.configs_dir.glob("*.yaml")):
        try:
            data = yaml.safe_load(p.read_text()) or {}
        except Exception:
            continue
        out.append({
            "name": p.stem,
            "scenario": data.get("name"),
            "policy": data.get("policy"),
            "n_steps": data.get("n_steps"),
            "fit_window": data.get("fit_window"),
            "lead_time": data.get("lead_time"),
            "has_drift": bool((data.get("drift") or {}).get("scenarios")),
            "size_bytes": p.stat().st_size,
        })
    return out


@router.get("/{name}")
async def get_config(name: str) -> dict[str, Any]:
    settings = get_settings()
    p = settings.configs_dir / f"{name}.yaml"
    if not p.exists():
        raise HTTPException(404, f"Config {name!r} not found")
    try:
        data = yaml.safe_load(p.read_text()) or {}
    except Exception as exc:
        raise HTTPException(500, f"Failed to parse: {exc}")
    # initial_stock can be huge — replace with a summary.
    init = data.get("initial_stock")
    if isinstance(init, dict):
        data["initial_stock"] = {
            "_kind": "dict",
            "n_skus": len(init),
            "min": min(init.values()) if init else None,
            "max": max(init.values()) if init else None,
            "mean": sum(init.values()) / len(init) if init else None,
        }
    return data
