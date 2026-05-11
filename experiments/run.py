"""Experiment runner.

Usage:
    python -m experiments.run --config experiments/configs/<name>.yaml
"""
from __future__ import annotations

from pathlib import Path
import json
import click

from src.utils import load_config, set_global_seed
from src.simulation import InventoryModel, OrderReplay, DriftInjector


@click.command()
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    required=True,
    help="Path to a YAML experiment config.",
)
def main(config: Path) -> None:
    cfg = load_config(config)
    set_global_seed(cfg.get("seed", 42))

    replay = OrderReplay.from_csv(cfg["data"]["processed_path"])
    skus = replay.skus

    # TODO: build drift scenarios from cfg["drift"] when implementing experiments.
    injector = DriftInjector(scenarios=[])

    model = InventoryModel(
        skus=skus,
        replay=replay,
        drift_injector=injector,
        initial_stock=cfg.get("initial_stock"),
        seed=cfg.get("seed", 42),
    )

    summary = model.run(n_steps=cfg.get("n_steps", replay.n_steps))

    out_dir = Path(cfg.get("results_dir", "results")) / cfg.get("name", "default")
    out_dir.mkdir(parents=True, exist_ok=True)
    with open(out_dir / "summary.json", "w") as f:
        json.dump(summary, f, indent=2, default=str)
    click.echo(f"Wrote {out_dir / 'summary.json'}")


if __name__ == "__main__":
    main()
