
## Ablation results on the catastrophic drift scenario

| Metric | full | no_adwin | ma_only | no_safety |
|---|---|---|---|---|
| Stockout rate | 23.85% | 7.96% (-66.6%) | 9.01% (-62.2%) | 8.69% (-63.6%) |
| Total cost | $296,578 | $233,508 (-21.3%) | $172,046 (-42.0%) | $211,608 (-28.7%) |
|   - holding | $179,376 | $160,947 (-10.3%) | $96,615 (-46.1%) | $142,798 (-20.4%) |
|   - ordering | $116,385 | $72,040 (-38.1%) | $74,750 (-35.8%) | $68,240 (-41.4%) |
|   - stockout | $817 | $520 (-36.3%) | $682 (-16.6%) | $570 (-30.3%) |
| Forecast MAPE | 86.5% | 84.5% (-2.2%) | 90.9% (+5.2%) | 86.8% (+0.4%) |
| Global drift events | 3.6 | 0.0 (-100.0%) | 2.0 (-44.4%) | 2.0 (-44.4%) |
| Refits | 2025 | 3192 (+57.6%) | 3104 (+53.3%) | 3239 (+59.9%) |

Deltas in parentheses are relative to `full` (control). Negative = ablation improves that metric (rare); positive = ablation hurts.

Wrote: results/ablation_report.{json,csv}
