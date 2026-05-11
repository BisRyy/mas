# Data

## Raw

Place the [Olist Brazilian E-Commerce Public Dataset](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce) CSVs under `data/raw/`. They are gitignored.

## Processed

`data/processed/orders.csv` is what the simulator consumes. Columns:

| column | description |
|---|---|
| `step` | simulation step (typically day index from earliest order) |
| `sku`  | product ID |
| `qty`  | units demanded that step |

A preprocessing notebook will live under `notebooks/` once we implement it.
