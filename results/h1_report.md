
## H1 — stockout_rate: MAS vs baselines

| Scenario | Baseline | MAS mean | Baseline mean | Rel Δ | MW p | Welch p | Cohen d |
|---|---|---:|---:|---:|---:|---:|---:|
| no_drift | static_rop | 17.82% | 90.65% | -80.3% | 0.0002 **<0.05** | 1.97e-24 | -111.1 |
| no_drift | periodic_forecasting | 17.82% | 26.15% | -31.9% | 0.0002 **<0.05** | 1.24e-14 | -10.1 |
| abrupt | static_rop | 17.74% | 90.65% | -80.4% | 0.0002 **<0.05** | 1.46e-22 | -99.1 |
| abrupt | periodic_forecasting | 17.74% | 26.69% | -33.5% | 0.0002 **<0.05** | 2.63e-14 | -10.1 |
| gradual | static_rop | 19.01% | 90.65% | -79.0% | 0.0002 **<0.05** | 1.68e-20 | -83.5 |
| gradual | periodic_forecasting | 19.01% | 26.15% | -27.3% | 0.0002 **<0.05** | 2.49e-11 | -7.2 |
| seasonal | static_rop | 18.00% | 90.65% | -80.1% | 0.0002 **<0.05** | 8.88e-25 | -113.0 |
| seasonal | periodic_forecasting | 18.00% | 26.33% | -31.7% | 0.0002 **<0.05** | 1.27e-14 | -10.1 |
| severe_abrupt | static_rop | 21.29% | 90.65% | -76.5% | 0.0002 **<0.05** | 5.02e-23 | -98.9 |
| severe_abrupt | periodic_forecasting | 21.29% | 27.42% | -22.4% | 0.0002 **<0.05** | 1.53e-11 | -6.6 |
| catastrophic | static_rop | 25.48% | 90.65% | -71.9% | 0.0002 **<0.05** | 1.56e-10 | -14.0 |
| catastrophic | periodic_forecasting | 25.48% | 30.81% | -17.3% | 0.0010 **<0.05** | 3.09e-02 | -1.1 |

## Cost differential: MAS vs baselines

| Scenario | Baseline | MAS mean | Baseline mean | Rel Δ | MW p | Welch p | Cohen d |
|---|---|---:|---:|---:|---:|---:|---:|
| no_drift | static_rop | $185,181 | $283,108 | -34.6% | 0.0002 **<0.05** | 2.17e-28 | -100.9 |
| no_drift | periodic_forecasting | $185,181 | $612,285 | -69.8% | 0.0002 **<0.05** | 1.08e-38 | -313.1 |
| abrupt | static_rop | $184,896 | $282,686 | -34.6% | 0.0002 **<0.05** | 5.62e-27 | -95.5 |
| abrupt | periodic_forecasting | $184,896 | $612,888 | -69.8% | 0.0002 **<0.05** | 4.95e-39 | -299.2 |
| gradual | static_rop | $186,216 | $283,067 | -34.2% | 0.0002 **<0.05** | 2.39e-28 | -100.0 |
| gradual | periodic_forecasting | $186,216 | $612,109 | -69.6% | 0.0002 **<0.05** | 1.78e-38 | -310.8 |
| seasonal | static_rop | $186,538 | $282,948 | -34.1% | 0.0002 **<0.05** | 1.32e-27 | -96.7 |
| seasonal | periodic_forecasting | $186,538 | $613,385 | -69.6% | 0.0002 **<0.05** | 1.97e-39 | -311.3 |
| severe_abrupt | static_rop | $209,660 | $281,578 | -25.5% | 0.0002 **<0.05** | 9.28e-16 | -36.1 |
| severe_abrupt | periodic_forecasting | $209,660 | $617,033 | -66.0% | 0.0002 **<0.05** | 2.29e-29 | -187.7 |
| catastrophic | static_rop | $304,399 | $273,208 | +11.4% | 0.0028 **<0.05** | 3.81e-03 | +1.7 |
| catastrophic | periodic_forecasting | $304,399 | $647,775 | -53.0% | 0.0002 **<0.05** | 9.58e-12 | -19.0 |

Wrote: results/h1_report.json, results/h1_report.csv
