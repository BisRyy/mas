"""Olist Brazilian E-Commerce -> simulator input.

Turns the raw Kaggle CSVs into `data/processed/orders.csv` with the columns
the `OrderReplay` engine consumes:

    step, sku, qty

Defaults follow the choices we agreed on for the first end-to-end run:
- Daily granularity (`step` = whole days from `min_date`)
- Top-N SKUs by total units sold (default 200)
- Purchase timestamp drives the demand signal
- Cancelled and unavailable orders excluded; everything else counts as demand

Run from the CLI:

    python -m src.data.preprocess --raw data/raw --out data/processed/orders.csv
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import argparse

import pandas as pd


# Statuses we treat as real demand. The proposal frames demand as "what the
# customer asked for", so anything that wasn't actively cancelled by us or
# never made it into our system counts.
DEFAULT_INCLUDED_STATUSES: frozenset[str] = frozenset(
    {"delivered", "shipped", "invoiced", "processing", "approved", "created"}
)


@dataclass
class PreprocessConfig:
    raw_dir: Path
    out_path: Path
    top_n_skus: int | None = 200          # None to keep every SKU
    granularity: str = "D"                # pandas offset alias: D=day, W=week
    min_date: str | None = None           # e.g. "2017-01-01" to skip warm-up
    max_date: str | None = None           # e.g. "2018-08-31" to skip ramp-down
    included_statuses: frozenset[str] = DEFAULT_INCLUDED_STATUSES


# ---------------------------------------------------------------------------
# Loading & cleaning
# ---------------------------------------------------------------------------
def load_raw(raw_dir: Path) -> dict[str, pd.DataFrame]:
    """Load just the tables we need and parse the relevant timestamps."""
    raw_dir = Path(raw_dir)
    orders = pd.read_csv(
        raw_dir / "olist_orders_dataset.csv",
        parse_dates=[
            "order_purchase_timestamp",
            "order_approved_at",
            "order_delivered_carrier_date",
            "order_delivered_customer_date",
            "order_estimated_delivery_date",
        ],
    )
    items = pd.read_csv(raw_dir / "olist_order_items_dataset.csv")
    products = pd.read_csv(raw_dir / "olist_products_dataset.csv")
    sellers = pd.read_csv(raw_dir / "olist_sellers_dataset.csv")
    return {
        "orders": orders,
        "items": items,
        "products": products,
        "sellers": sellers,
    }


# ---------------------------------------------------------------------------
# Core pipeline
# ---------------------------------------------------------------------------
def build_demand_table(
    tables: dict[str, pd.DataFrame], cfg: PreprocessConfig
) -> pd.DataFrame:
    """Return a (step, sku, qty) DataFrame ready for the simulator.

    `step` is an integer offset from the first observed day (or `cfg.min_date`),
    measured in `cfg.granularity` periods.
    """
    orders = tables["orders"]
    items = tables["items"]

    # 1. Filter orders by status.
    orders = orders[orders["order_status"].isin(cfg.included_statuses)].copy()

    # 2. Join items to their order so we know when the demand happened.
    df = items.merge(
        orders[["order_id", "order_purchase_timestamp", "order_status"]],
        on="order_id",
        how="inner",
    )

    # 3. Drop rows missing a timestamp (rare) and sort.
    df = df.dropna(subset=["order_purchase_timestamp"])
    df = df.sort_values("order_purchase_timestamp")

    # 4. Apply optional date window.
    if cfg.min_date is not None:
        df = df[df["order_purchase_timestamp"] >= pd.Timestamp(cfg.min_date)]
    if cfg.max_date is not None:
        df = df[df["order_purchase_timestamp"] <= pd.Timestamp(cfg.max_date)]
    if df.empty:
        raise ValueError("No rows left after filtering. Check date window / statuses.")

    # 5. Optional top-N SKU restriction.
    if cfg.top_n_skus is not None:
        top = (
            df["product_id"].value_counts().nlargest(cfg.top_n_skus).index
        )
        df = df[df["product_id"].isin(top)]

    # 6. Bucket timestamps into the chosen granularity and turn into int step
    #    relative to the first bucket.
    df["bucket"] = df["order_purchase_timestamp"].dt.to_period(cfg.granularity)
    first_bucket = df["bucket"].min()
    df["step"] = (df["bucket"] - first_bucket).apply(lambda x: x.n).astype(int)

    # 7. Aggregate to (step, sku, qty). Each row in `items` is one unit ordered.
    out = (
        df.groupby(["step", "product_id"], as_index=False)
        .size()
        .rename(columns={"product_id": "sku", "size": "qty"})
        .sort_values(["step", "sku"])
        .reset_index(drop=True)
    )
    return out


def write_processed(df: pd.DataFrame, out_path: Path) -> None:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path, index=False)


def run(cfg: PreprocessConfig) -> pd.DataFrame:
    tables = load_raw(cfg.raw_dir)
    demand = build_demand_table(tables, cfg)
    write_processed(demand, cfg.out_path)
    return demand


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python -m src.data.preprocess",
        description="Build (step, sku, qty) demand table from Olist raw CSVs.",
    )
    p.add_argument("--raw", type=Path, default=Path("data/raw"))
    p.add_argument("--out", type=Path, default=Path("data/processed/orders.csv"))
    p.add_argument(
        "--top-n", type=int, default=200,
        help="Keep only the top-N SKUs by total units. Use 0 to keep all.",
    )
    p.add_argument(
        "--granularity", default="D", choices=["D", "W"],
        help="D = daily, W = weekly.",
    )
    p.add_argument("--min-date", default=None, help="ISO date, e.g. 2017-01-01.")
    p.add_argument("--max-date", default=None, help="ISO date, e.g. 2018-08-31.")
    return p


def main(argv: list[str] | None = None) -> None:
    args = _build_parser().parse_args(argv)
    cfg = PreprocessConfig(
        raw_dir=args.raw,
        out_path=args.out,
        top_n_skus=args.top_n if args.top_n > 0 else None,
        granularity=args.granularity,
        min_date=args.min_date,
        max_date=args.max_date,
    )
    df = run(cfg)
    n_skus = df["sku"].nunique()
    n_steps = df["step"].max() + 1
    print(
        f"Wrote {len(df):,} rows -> {cfg.out_path} "
        f"({n_skus:,} SKUs, {n_steps:,} steps, total qty={int(df['qty'].sum()):,})"
    )


if __name__ == "__main__":
    main()
