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

## Running an experiment

```bash
python -m experiments.run --config experiments/configs/<name>.yaml
```

## Layout

```
inventory-mas/
├── data/                 # raw + processed Olist data (gitignored)
├── src/
│   ├── agents/           # 5 agents
│   ├── simulation/       # environment, scheduler, replay, drift injector, logger
│   ├── baselines/        # static ROP, periodic forecasting
│   ├── drift/            # ADWIN, PELT detectors
│   ├── metrics/          # stockout, holding cost, MAPE
│   └── utils/            # config, seeding, IO
├── experiments/          # YAML configs + run entrypoint
├── notebooks/            # exploration & result analysis
├── results/              # logs + figures (gitignored)
└── tests/
```

## Dataset

[Olist Brazilian E-Commerce Public Dataset](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce). Place CSVs under `data/raw/`.

## License

For academic use. Citation details to be added after defense.
