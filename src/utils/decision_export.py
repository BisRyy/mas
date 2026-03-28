"""Optional decision-log export for the dashboard's audit trail.

When the environment variable ``MAS_EMIT_DECISIONS=1`` is set, the
experiment runner will dump every agent's ``decision_log`` into a
``decisions.jsonl`` file alongside ``summary.json`` for the run. Each
line is one decision event:

    {"step": 281, "agent": "replenisher", "action": "reorder",
     "sku": "abc123", "qty": 12, "rop": 8.4, ...}

The simulator already maintains these logs in-process; this module is
just the IO sink.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Iterable


# Agent attribute names on InventoryModel and BaselineModel that carry
# decision logs. Only agents that exist on the given model are dumped.
_KNOWN_AGENT_ATTRS = (
    ("supplier", "supplier"),
    ("monitor", "monitor"),
    ("forecaster", "forecaster"),
    ("replenisher", "replenisher"),
    ("analytics", "analytics"),
)


def emission_enabled() -> bool:
    """True when decisions should be persisted for this run."""
    return os.environ.get("MAS_EMIT_DECISIONS", "0").lower() in {"1", "true", "yes"}


def _iter_agent_logs(model: Any) -> Iterable[tuple[str, list[dict]]]:
    for attr, label in _KNOWN_AGENT_ATTRS:
        agent = getattr(model, attr, None)
        if agent is None:
            continue
        log = getattr(agent, "decision_log", None)
        if not log:
            continue
        yield label, log


def write_decisions_jsonl(model: Any, out_dir: Path) -> int:
    """Write `<out_dir>/decisions.jsonl` from the model's agent logs.

    Returns the number of events written. No-op when emission is disabled.
    """
    if not emission_enabled():
        return 0

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "decisions.jsonl"

    n = 0
    with path.open("w") as f:
        for agent_name, log in _iter_agent_logs(model):
            for entry in log:
                # entry already has 'step' and 'action'; we ensure 'agent' is set.
                record = {"agent": agent_name, **entry}
                f.write(json.dumps(record, default=str) + "\n")
                n += 1
    return n
