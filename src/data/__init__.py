"""Olist preprocessing — turn raw Kaggle CSVs into the simulator's input format.

Importing this package eagerly was triggering a `runpy` warning when running
`python -m src.data.preprocess`, so submodules are imported lazily on demand.
Use `from src.data.preprocess import ...` directly.
"""
