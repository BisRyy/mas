# Inventory MAS

**Design, Implementation, and Empirical Evaluation of a Multi-Agent Architecture for E-Commerce Inventory Optimization**

MSc Thesis — Addis Ababa Science and Technology University, Department of Software Engineering.
Author: Bisrat Kebere Derebe · Advisor: Zeleke Abebaw, PhD.

## What this is

A reproducible simulation framework that compares an autonomous 5-agent inventory system against two traditional baselines (static ROP, periodic centralized forecasting) under three injected concept-drift scenarios, evaluated on the public Olist Brazilian E-Commerce dataset.

## Architecture (5 agents)

| Agent | Responsibility |
|---|---|
| Demand Forecasting | Predict future per-SKU demand |
| Inventory Monitoring | Track real-time stock levels |
| Replenishment | Decide when and how much to reorder |
| Supplier | Simulate external suppliers and lead times |
| Analytics | Evaluate system performance metrics |

## Drift scenarios (injected)

1. **Abrupt** — +50% demand on top SKUs, sustained 30 days
2. **Gradual** — +0.5%/day over 60 days on 30% of SKUs
3. **Seasonal pulse** — +200% weekly spikes for 3 consecutive weeks

## Baselines

- **B1**: Static ROP (fixed reorder points, no adaptation)
- **B2**: Periodic centralized forecasting (re-fits every 30 days)
- **Proposed**: Continuous agent-driven monitoring + drift detection + adaptive replenishment

## Metrics

- Stockout rate and stockout duration
- Inventory holding cost (and ordering cost where applicable)
- Adaptability — drift detection delay and time-to-recovery
- Scalability — runtime, memory, overhead vs. SKU/agent count
- Forecast accuracy — MAPE
- Qualitative — modularity, extensibility, reproducibility

## Hypotheses

- **H1** MAS reduces daily stockout rate by ≥10% vs static ROP (p < 0.05)
- **H2** After a 50% abrupt demand surge, MAS restores 95% service level faster than periodic baseline
- **H3** Computational overhead grows linearly with number of agents

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Or with Docker:

```bash
docker build -t inventory-mas .
docker run --rm -v $(pwd):/app inventory-mas python -m experiments.run --config experiments/configs/baseline_rop.yaml
```

## Running experiments

### Single run
```bash
python -m experiments.run --config experiments/configs/<name>.yaml
```

### Multi-seed sweep (the canonical way)
```bash
python -m experiments.sweep \
  -c experiments/configs/olist_mas_catastrophic.yaml \
     experiments/configs/olist_static_rop_catastrophic.yaml \
     experiments/configs/olist_periodic_forecasting_catastrophic.yaml \
  --seeds 1..10 --jitter 0.2
```

### Aggregate seeds → mean ± 95% CI
```bash
python -m experiments.aggregate results/olist_*_catastrophic
```

### Run hypothesis tests across the full design matrix
```bash
python -m experiments.h1_report          # H1: stockout & cost vs baselines
python -m experiments.h3_report          # H3: scaling complexity
python -m experiments.ablation_report    # ablation deltas
```

### Compare individual runs side-by-side
```bash
python -m experiments.compare results/run_a results/run_b results/run_c
```

### Reproduce everything from scratch
```bash
bash scripts/reproduce_all.sh   # ~4 hours; runs the full thesis evaluation
```

## Dashboard

A Streamlit dashboard renders the same results interactively (per-step plots,
cost breakdowns, drift event overlays, single-run drilldown).

```bash
streamlit run app.py
```

Then open http://localhost:8501. The sidebar lists every scenario found under
`results/`. The dashboard pulls from `summary.json` + `timeseries.csv`, so
re-run experiments and refresh the page to pick up new data.

## Layout

```
inventory-mas/
├── app.py                  # Streamlit dashboard (multi-seed CI bands + H1/H3 tabs)
├── RESULTS.md              # Headline numbers + hypothesis verdicts
├── scripts/
│   ├── reproduce_all.sh    # One-command end-to-end rerun
│   └── make_figures.py     # Generate publication-quality PDF/PNG figures
├── figures/                # Static figures (PDF + PNG)
├── data/                   # Raw + processed Olist data (gitignored)
├── src/
│   ├── agents/             # 5 agents (forecasting w/ MA→SES→Holt-Winters tiers)
│   ├── simulation/         # Environment, baseline env, replay, drift injector
│   ├── baselines/          # Static ROP, Periodic Forecasting (EOQ Q*)
│   ├── drift/              # ADWIN, PELT detectors
│   ├── metrics/            # Stockout, cost, MAPE, adaptability, summary
│   ├── data/               # Olist preprocessing pipeline
│   └── utils/              # Config, seeding (per-seed initial-stock jitter)
├── experiments/            # YAML configs + run / sweep / aggregate / stats
│   ├── run.py              # Single-run dispatcher
│   ├── sweep.py            # Multi-seed orchestrator
│   ├── aggregate.py        # Per-cell mean ± 95% CI
│   ├── stats.py            # Mann-Whitney U, Welch's t, Cohen's d
│   ├── h1_report.py        # H1 across (scenario × baseline × metric)
│   ├── h3_report.py        # H3 power-law + linear fits
│   ├── ablation_report.py  # Component-deletion deltas
│   ├── compare.py          # Terminal side-by-side comparison
│   └── configs/            # All experiment configs (YAML)
├── notebooks/              # Olist exploration + result analysis
├── results/                # Per-run summary.json, timeseries.csv, aggregates
└── tests/                  # pytest (23 tests, all passing)
```

## Dataset

[Olist Brazilian E-Commerce Public Dataset](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce). Place CSVs under `data/raw/`.

## License

For academic use. Citation details to be added after defense.
