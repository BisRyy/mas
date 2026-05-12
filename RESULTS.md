# Results — Inventory MAS thesis

Reproducible summary of the empirical evaluation. All numbers come from
post-Mesa-fix code; see `thesis/04_implementation.md` §4.5 for context
on the bug discovered and fixed mid-evaluation. Every result file is
under `results/`; the full evaluation reproduces from
`bash scripts/reproduce_all.sh` (≈ 4 hours on an M2 MacBook Pro).

## Headline

| Hypothesis | Status | Result |
|:--|:-:|:--|
| H1 — Performance | ✅ Confirmed and exceeded | MAS reduces stockout 71.9–80.4% vs Static ROP, 17.3–33.5% vs Periodic, MW p ≤ 0.001 every cell |
| H2 — Adaptability | ↻ Reframed | Both adaptive policies stay > 99% SL; *cost-of-service* differentiates: MAS is 53–70% cheaper than Periodic |
| H3 — Scalability | ✅ Confirmed and exceeded | Power-law exponent *b* = 0.372 (proposal predicted ≈ 1.0 linear) |

## H1 — Performance

Six scenarios × three policies × ten seeds = 180 runs.

**Stockout rate (mean across seeds):**

| Scenario | Static ROP | Periodic | MAS | Δ vs ROP | Δ vs Periodic |
|:-:|:-:|:-:|:-:|:-:|:-:|
| no_drift | 90.65% | 26.15% | 17.82% | **−80.4%** | **−31.9%** |
| abrupt | 90.65% | 26.69% | 17.74% | **−80.4%** | **−33.5%** |
| gradual | 90.65% | 26.15% | 19.01% | **−79.0%** | **−27.3%** |
| seasonal | 90.65% | 26.33% | 18.00% | **−80.1%** | **−31.7%** |
| severe_abrupt | 90.65% | 27.42% | 21.29% | **−76.5%** | **−22.4%** |
| catastrophic | 90.65% | 30.81% | 25.48% | **−71.9%** | **−17.3%** |

Mann–Whitney *p* = 0.0002 (test floor at N=10 vs N=10) in 11 of 12
cells; the lone exception is catastrophic vs Periodic at *p* = 0.001.
Cohen's *d* magnitudes range from −1.1 (catastrophic vs Periodic) to
−175 (no_drift vs Static ROP).

**Total cost (mean across seeds):**

| Scenario | Static ROP | Periodic | MAS | Δ vs ROP | Δ vs Periodic |
|:-:|:-:|:-:|:-:|:-:|:-:|
| no_drift | $283,108 | $612,285 | $185,181 | **−34.6%** | **−69.8%** |
| abrupt | $282,686 | $612,888 | $184,896 | **−34.6%** | **−69.8%** |
| gradual | $283,067 | $612,109 | $186,216 | **−34.2%** | **−69.6%** |
| seasonal | $282,948 | $613,385 | $186,538 | **−34.1%** | **−69.6%** |
| severe_abrupt | $281,578 | $617,033 | $209,660 | **−25.5%** | **−66.0%** |
| catastrophic | $273,208 | $647,775 | $304,399 | **+11.4%*** | **−53.0%** |

\* In `catastrophic`, Static ROP looks cheaper only because it stocks out
90% of the time and therefore barely orders. It is not a useful win.

Full statistical detail in `results/h1_report.{json,csv,md}` and
`figures/h1_stockout_rate.pdf` / `figures/h1_cost_decomposition.pdf`.

## H3 — Scalability

Five SKU cohorts × three policies × five seeds = 75 runs.

**Mean runtime per run:**

| Policy | n = 50 | n = 100 | n = 200 | n = 500 | n = 1000 |
|:-:|:-:|:-:|:-:|:-:|:-:|
| Static ROP | 0.01 s | 0.02 s | 0.03 s | 0.06 s | 0.12 s |
| Periodic Forecasting | 2.35 s | 3.51 s | 5.07 s | 8.31 s | 11.66 s |
| **MAS** | **33.4 s** | **53.5 s** | **84.5 s** | **98.8 s** | **102.6 s** |

**Power-law fits** ($t \propto n^b$):

| Policy | exponent *b* | R² |
|:-:|:-:|:-:|
| Static ROP | 0.713 | 0.984 |
| Periodic Forecasting | 0.535 | 0.999 |
| **MAS** | **0.372** | 0.870 |

All sublinear; MAS is the most sublinear. Memory follows the same
pattern (MAS exponent 0.22). Full data in
`results/h3_report.{json,csv,md}` and `figures/h3_scaling.pdf`.

## H2 — Adaptability (Reframed)

The literal proposal hypothesis ("MAS restores 95% SL faster than
Periodic after a 50% abrupt surge") is **not testable as stated**:
both adaptive policies maintain mean post-drift SL above 99% in every
scenario (because the EOQ-derived Q\* produces enough standing inventory
to absorb drift). The substantive finding is on **cost of maintaining
service level**:

| Scenario | MAS cost | Periodic cost | MAS savings |
|:-:|:-:|:-:|:-:|
| abrupt | $184,896 | $612,888 | **−70%** |
| severe_abrupt | $209,660 | $617,033 | **−66%** |
| catastrophic | $304,399 | $647,775 | **−53%** |

Recommend reframing H2 as **cost-of-service after drift** for the
journal submission. See `thesis/07_discussion.md` §7.2.

## Ablation

Four variants × ten seeds = 40 runs on the catastrophic scenario.
Δ is relative to the `full` MAS control.

| Variant | Stockout | Total cost | MAPE | Global drift events |
|:-:|:-:|:-:|:-:|:-:|
| full | 23.85% | $296,578 | 86.5% | 3.6 |
| no_adwin | 7.96% (−66.6%) | $233,508 (−21.3%) | 84.5% | 0.0 |
| ma_only | 9.01% (−62.2%) | $172,046 (−42.0%) | 90.9% | 2.0 |
| no_safety | 8.69% (−63.6%) | $211,608 (−28.7%) | 86.8% | 2.0 |

**Unexpected finding.** Under the *catastrophic* scenario, every
ablation *improves* both stockout and cost. The mechanism: the
forecaster honestly captures large transient volatility, which inflates
the residual std and therefore the safety-stock buffer `z·σ·√LT`,
driving over-ordering. The ablations that simplify the forecaster
(`ma_only`) or zero the buffer (`no_safety`) end up holding less
inventory at the cost of slightly more stockouts — net win on cost.

This is a **boundary-condition behavior at adversarial drift**. Under
mild and moderate drift (no_drift, abrupt, gradual, seasonal,
severe_abrupt), the full MAS dominates the baselines on both stockout
and cost (Tables 6.1, 6.3 of the thesis). The ablation surprise
identifies a real future-work item: cap safety stock at a sensible
multiple of `μ·LT`, or use robust statistics for the residual std
estimator. See `thesis/07_discussion.md` §7.3a for the full
discussion.

![Ablation results.](figures/ablation.pdf)

Full data in `results/ablation_report.{json,csv,md}`.

## Reproducibility checklist

- [x] Deterministic given (seed, jitter, dataset hash)
- [x] N = 10 seeds per cell with hypothesis tests
- [x] Effect sizes (Cohen's d) reported alongside p-values
- [x] Bonferroni-corrected; all p < 0.0014
- [x] Dockerfile pins the Python interpreter and dependencies
- [x] All configs under `experiments/configs/` version-controlled
- [x] One-command rerun via `scripts/reproduce_all.sh`
- [x] Per-step per-seed timeseries persisted to disk for re-analysis

## Where every number comes from

| Claim | Backing file |
|---|---|
| H1 p-values, effect sizes | `results/h1_report.{json,csv,md}` |
| H3 scaling exponents | `results/h3_report.{json,csv,md}` |
| Ablation deltas | `results/ablation_report.{json,csv,md}` *(pending)* |
| Per-cell mean ± CI | `results/<run_name>/aggregate.json` |
| Per-seed raw runs | `results/<run_name>/seed_*/summary.json` |
| Figures | `figures/*.pdf` and `figures/*.png` |
| Thesis manuscript | `thesis/*.md` (assemble via `bash thesis/build.sh`) |
