"""Seed-sweep orchestrator for multi-seed evaluation.

For each base config and each seed in `seeds`, runs the experiment and
writes results under `results/<base_name>/seed_<seed>/`. Adds a small
`stochastic.initial_stock_jitter` so seeds actually produce different
realizations (otherwise the simulator is deterministic given the replay).

Usage:
    python -m experiments.sweep -c experiments/configs/olist_mas_catastrophic.yaml \
        --seeds 1 2 3 4 5 6 7 8 9 10 --jitter 0.2

    # Or sweep multiple base configs at once:
    python -m experiments.sweep -c experiments/configs/olist_*_catastrophic.yaml \
        --seeds 1..10 --jitter 0.2
"""
from __future__ import annotations

import argparse
import copy
import json
import os
import sys
import time
import tracemalloc
from pathlib import Path

import psutil
import yaml

# Re-use the same run logic the single-experiment CLI uses.
from experiments.run import POLICY_HANDLERS, _augment_with_costs, _augment_with_recovery
from src.simulation import OrderReplay
from src.utils import load_config, set_global_seed


def _parse_seeds(arg: list[str]) -> list[int]:
    """Accept either explicit ints or a `a..b` range form."""
    seeds: list[int] = []
    for token in arg:
        if ".." in token:
            a, b = token.split("..", 1)
            seeds.extend(range(int(a), int(b) + 1))
        else:
            seeds.append(int(token))
    return seeds


def _write_timeseries_csv(timeseries, path: Path) -> None:
    if not timeseries:
        return
    import csv
    fields = sorted({k for row in timeseries for k in row.keys()})
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(timeseries)


def run_one(base_cfg: dict, seed: int, jitter: float, base_name: str,
            base_results_dir: Path) -> dict:
    """Run a single (config, seed) cell and return its summary."""
    cfg = copy.deepcopy(base_cfg)
    cfg["seed"] = seed
    stochastic = cfg.setdefault("stochastic", {})
    stochastic["initial_stock_jitter"] = float(jitter)
    # Output dir for this seed.
    out_dir = base_results_dir / base_name / f"seed_{seed:03d}"
    cfg["results_dir"] = str(base_results_dir)
    cfg["name"] = f"{base_name}/seed_{seed:03d}"

    set_global_seed(seed)
    replay = OrderReplay.from_csv(cfg["data"]["processed_path"])
    policy = cfg.get("policy", "mas")
    if policy not in POLICY_HANDLERS:
        raise ValueError(f"Unknown policy: {policy!r}")

    # Resource profiling: wall time + peak RSS + Python heap peak.
    proc = psutil.Process(os.getpid())
    rss_before = proc.memory_info().rss
    tracemalloc.start()
    t0 = time.perf_counter()
    summary, timeseries, model = POLICY_HANDLERS[policy](cfg, replay)
    elapsed = time.perf_counter() - t0
    rss_after = proc.memory_info().rss
    _, py_peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    summary["policy"] = policy
    summary["seed"] = seed
    summary["fit_window"] = int(cfg.get("fit_window", 90))
    summary["n_skus_used"] = len(replay.skus)
    summary["runtime_seconds"] = elapsed
    summary["time_per_step_ms"] = (
        1000.0 * elapsed / max(int(cfg["n_steps"]) - int(cfg.get("fit_window", 90)), 1)
    )
    summary["peak_python_mem_mb"] = py_peak / (1024 * 1024)
    summary["delta_rss_mb"] = (rss_after - rss_before) / (1024 * 1024)
    _augment_with_costs(summary, timeseries, cfg)
    _augment_with_recovery(summary, timeseries, cfg, n_total_skus=len(replay.skus))

    out_dir.mkdir(parents=True, exist_ok=True)
    with open(out_dir / "summary.json", "w") as f:
        json.dump(summary, f, indent=2, default=str)
    _write_timeseries_csv(timeseries, out_dir / "timeseries.csv")
    # Optional decision-log dump (only when MAS_EMIT_DECISIONS=1).
    from src.utils.decision_export import write_decisions_jsonl
    write_decisions_jsonl(model, out_dir)
    return summary


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="python -m experiments.sweep")
    p.add_argument("-c", "--config", required=True, nargs="+",
                   help="One or more base config paths (globs allowed at shell level).")
    p.add_argument("--seeds", required=True, nargs="+",
                   help="Seeds to run. Accepts integers and `a..b` ranges.")
    p.add_argument("--jitter", type=float, default=0.2,
                   help="Initial-stock multiplicative jitter (per-SKU ±jitter).")
    p.add_argument("--results-dir", type=Path, default=Path("results"))
    args = p.parse_args(argv)

    seeds = _parse_seeds(args.seeds)
    configs = [Path(c) for c in args.config]
    print(f"Sweeping {len(configs)} config(s) × {len(seeds)} seed(s) = "
          f"{len(configs) * len(seeds)} runs. jitter={args.jitter}.")

    overall_start = time.perf_counter()
    n_total = len(configs) * len(seeds)
    n_done = 0
    failures: list[tuple[str, int, str]] = []
    for cfg_path in configs:
        base_cfg = load_config(cfg_path)
        base_name = base_cfg.get("name") or cfg_path.stem
        for seed in seeds:
            n_done += 1
            label = f"[{n_done}/{n_total}] {base_name} seed={seed}"
            try:
                t0 = time.perf_counter()
                summary = run_one(base_cfg, seed, args.jitter, base_name, args.results_dir)
                elapsed = time.perf_counter() - t0
                so = summary.get("stockout_rate", 0.0)
                tc = summary.get("total_cost", 0.0)
                print(f"{label}  stockout={so:.2%}  cost=${tc:>10,.0f}  ({elapsed:.1f}s)")
            except Exception as exc:
                failures.append((base_name, seed, repr(exc)))
                print(f"{label}  FAILED: {exc}", file=sys.stderr)

    total_elapsed = time.perf_counter() - overall_start
    print(f"\nSweep finished in {total_elapsed:.1f}s "
          f"({total_elapsed/n_total:.1f}s/run avg). "
          f"{len(failures)} failure(s).")
    if failures:
        for name, seed, err in failures[:5]:
            print(f"  failure: {name} seed={seed} -> {err}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
