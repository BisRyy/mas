#!/usr/bin/env bash
# Reproduce every result in the thesis from a fresh checkout.
#
# Prerequisites:
#   1. Python 3.11+ available as `python3`.
#   2. Olist raw CSVs placed under data/raw/ (see data/README.md).
#
# Estimated wall time on a 2024 M2 MacBook Pro: ~4 hours.
#
#   bash scripts/reproduce_all.sh

set -euo pipefail

cd "$(dirname "$0")/.."

# ---------------------------------------------------------------------------
# 1. Environment
# ---------------------------------------------------------------------------
if [ ! -d .venv ]; then
  echo "[1/6] Creating virtualenv ..."
  python3 -m venv .venv
fi
# shellcheck source=/dev/null
source .venv/bin/activate
echo "[1/6] Installing dependencies ..."
pip install -q --upgrade pip
pip install -q -r requirements.txt

# ---------------------------------------------------------------------------
# 2. Preprocess Olist
# ---------------------------------------------------------------------------
echo "[2/6] Preprocessing Olist at 5 SKU cohorts ..."
for n in 50 100 200 500 1000; do
  python -m src.data.preprocess \
    --raw data/raw --out "data/processed/orders_${n}.csv" \
    --top-n "${n}" --min-date 2017-01-01 --max-date 2018-08-31
done
# The canonical 200-SKU cohort is what most experiments reference.
cp data/processed/orders_200.csv data/processed/orders.csv

# ---------------------------------------------------------------------------
# 3. Run the H1 sweep — 6 scenarios × 3 policies × 10 seeds = 180 runs
# ---------------------------------------------------------------------------
echo "[3/6] H1 sweep (180 runs) ..."
H1_CONFIGS=()
for pol in static_rop periodic_forecasting mas; do
  for scen in no_drift abrupt gradual seasonal severe_abrupt catastrophic; do
    H1_CONFIGS+=("experiments/configs/olist_${pol}_${scen}.yaml")
  done
done
python -m experiments.sweep -c "${H1_CONFIGS[@]}" --seeds 1..10 --jitter 0.2

python -m experiments.aggregate results/olist_*_no_drift \
  results/olist_*_abrupt results/olist_*_gradual results/olist_*_seasonal \
  results/olist_*_severe_abrupt results/olist_*_catastrophic
python -m experiments.h1_report > results/h1_report.md

# ---------------------------------------------------------------------------
# 4. Run the H3 scalability sweep — 5 sizes × 3 policies × 5 seeds = 75 runs
# ---------------------------------------------------------------------------
echo "[4/6] H3 scalability sweep (75 runs) ..."
H3_CONFIGS=()
for pol in static_rop periodic_forecasting mas; do
  for n in 50 100 200 500 1000; do
    H3_CONFIGS+=("experiments/configs/olist_scale_${pol}_n${n}.yaml")
  done
done
python -m experiments.sweep -c "${H3_CONFIGS[@]}" --seeds 1..5 --jitter 0.2

python -m experiments.aggregate results/olist_scale_*
python -m experiments.h3_report > results/h3_report.md

# ---------------------------------------------------------------------------
# 5. Run the ablation sweep — 4 variants × 10 seeds = 40 runs
# ---------------------------------------------------------------------------
echo "[5/6] Ablation sweep (40 runs) ..."
python -m experiments.sweep \
  -c experiments/configs/olist_ablation_full.yaml \
     experiments/configs/olist_ablation_no_adwin.yaml \
     experiments/configs/olist_ablation_ma_only.yaml \
     experiments/configs/olist_ablation_no_safety.yaml \
  --seeds 1..10 --jitter 0.2

python -m experiments.aggregate results/olist_ablation_*
python -m experiments.ablation_report > results/ablation_report.md

# ---------------------------------------------------------------------------
# 6. Generate figures
# ---------------------------------------------------------------------------
echo "[6/6] Generating figures ..."
python -m scripts.make_figures

echo ""
echo "Done. Outputs:"
echo "  results/h1_report.{json,csv,md}     — H1 hypothesis tests"
echo "  results/h3_report.{json,csv,md}     — H3 scalability analysis"
echo "  results/ablation_report.{json,csv,md} — Component ablation"
echo "  figures/*.pdf                       — Publication-quality figures"
echo "  results/olist_*/aggregate.json      — Per-cell aggregates (mean ± CI)"
echo ""
echo "To explore interactively:  streamlit run app.py"
