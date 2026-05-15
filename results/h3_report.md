
## H3 — Runtime scaling: power-law fit `t = a * n^b`

| Policy | b (exponent) | R² | Classification | Linear R² |
|---|---:|---:|---|---:|
| static_rop | 0.713 | 0.9843 | sublinear | 0.9999 |
| periodic_forecasting | 0.535 | 0.9994 | sublinear | 0.9663 |
| mas | 0.372 | 0.8701 | near-constant | 0.6467 |

## Memory scaling: power-law fit on peak Python heap

| Policy | b (exponent) | R² | Classification |
|---|---:|---:|---|
| static_rop | 0.349 | 0.8720 | near-constant |
| periodic_forecasting | 0.419 | 0.9991 | near-constant |
| mas | 0.149 | 0.2323 | near-constant |

## Raw data

| Policy | N SKUs | Runtime (s) | t/step (ms) | Peak heap (MB) | Stockout |
|---|---:|---:|---:|---:|---:|
| mas | 50 | 33.38 | 66.63 | 10.6 | 8.66% |
| mas | 100 | 53.54 | 106.24 | 5.0 | 11.94% |
| mas | 200 | 84.52 | 167.70 | 7.3 | 17.14% |
| mas | 500 | 98.84 | 194.56 | 9.8 | 10.47% |
| mas | 1,000 | 102.64 | 201.26 | 13.0 | 4.27% |
| periodic_forecasting | 50 | 2.35 | 4.70 | 0.5 | 13.01% |
| periodic_forecasting | 100 | 3.51 | 6.96 | 0.6 | 16.19% |
| periodic_forecasting | 200 | 5.07 | 10.06 | 0.8 | 26.35% |
| periodic_forecasting | 500 | 8.31 | 16.36 | 1.2 | 34.25% |
| periodic_forecasting | 1,000 | 11.66 | 22.87 | 1.6 | 39.53% |
| static_rop | 50 | 0.01 | 0.03 | 0.1 | 87.74% |
| static_rop | 100 | 0.02 | 0.04 | 0.1 | 89.40% |
| static_rop | 200 | 0.03 | 0.06 | 0.1 | 90.56% |
| static_rop | 500 | 0.06 | 0.12 | 0.2 | 92.09% |
| static_rop | 1,000 | 0.12 | 0.23 | 0.4 | 92.27% |

Wrote: results/h3_report.json, results/h3_report.csv
