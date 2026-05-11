"""Run-level logger.

Each agent already keeps a per-action `decision_log`. The `RunLogger` is
the place to consolidate them at the end of a run for export to JSONL/CSV
under `results/logs/<run_id>/`.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class RunLogger:
    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []

    def add(self, **fields: Any) -> None:
        self.events.append(fields)

    def write_jsonl(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w") as f:
            for event in self.events:
                f.write(json.dumps(event) + "\n")
