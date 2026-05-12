# 3. Methodology

This chapter describes how the work is carried out. It is organized in
three parts. **§3.1** presents the system architecture and design of the
proposed multi-agent inventory system. **§3.2** documents the
implementation — technology stack, project layout, key algorithms, the
reproducibility infrastructure, and one specific bug whose discovery
and resolution materially affected the empirical results. **§3.3**
specifies the experimental methodology: the dataset and its
preprocessing, the simulation protocol, the injected drift scenarios,
the baselines, the evaluation metrics, the multi-seed statistical
procedure, and the hardware environment.

## 3.1 System Architecture and Design

This part describes the architectural design of the proposed multi-agent
system. It begins with the high-level architecture, then describes each
agent's responsibilities and interfaces, the inter-agent communication
model, the drift-detection mechanism, the tiered forecasting design,
and the simulation environment that hosts the agents.

### 3.1.1 Design Goals

The architecture is designed around five concrete goals derived from
Chapter 1:

1. **Modularity.** Each agent owns a single responsibility and exposes
   a narrow interface. New agents (e.g., a Pricing Agent) can be added
   without modifying existing ones.
2. **Auditability.** Every decision is logged with its inputs at the
   per-agent level, supporting post-hoc inspection and the
   trust-building required in emerging-market deployment.
3. **Adaptability.** The system must respond to demand drift without
   relying on a fixed retraining schedule.
4. **Reproducibility.** Given a configuration and a seed, the system
   must produce identical results across runs and machines.
5. **Scalability.** Per-step computational cost must grow at most
   linearly with the number of SKUs.

### 3.1.2 High-Level Architecture

The system comprises five autonomous agents coordinated through a
shared simulation environment (the Mesa `Model`). Each agent processes
its own inbox of messages, maintains its own state, writes its own
decision log, and is stepped in a fixed deterministic order each
simulation tick.

![Figure 3.1. High-level architecture: five autonomous agents coordinated through a shared simulation environment. Solid arrows denote data flow at each simulation step; the dashed feedback arrow shows the analytics agent's read-only observation of the post-decision state.](figures/architecture.png)

The agents execute in the deterministic order: **Supplier**, **Inventory
Monitoring**, **Demand Forecasting**, **Replenishment**, **Analytics**.
This ordering ensures that (i) deliveries from in-flight purchase orders
arrive before today's demand is fulfilled; (ii) the forecaster sees
today's observation before any replenishment decision is made on it;
(iii) analytics observes the post-decision state of the system.

### 3.1.3 Agent Responsibilities

#### 3.1.3.1 Demand Forecasting Agent

The Demand Forecasting Agent owns the model that predicts per-day
demand for each SKU. It maintains three pieces of state per SKU:

- a rolling observation history (deque, default 180-day window),
- a fitted forecasting model selected from a *tier ladder* (see §3.1.5),
- per-SKU ADWIN detectors (diagnostic) plus a global ADWIN detector on
  the population mean of absolute forecast residuals (the primary
  drift signal, §3.1.4).

It exposes two methods to the Replenishment Agent:

- `predict(sku) -> float` — expected per-day demand;
- `predict_std(sku) -> float` — residual standard deviation, used by
  the Replenishment Agent to compute safety stock.

Refitting is **lazy**: the agent marks a SKU model stale on drift
detection or on time elapsed since the last fit (`safety_refit_interval`,
default 60 days), and the next `predict` call triggers the actual fit.
This bounds the worst-case latency of incorporating new information
without paying refit cost on every step.

#### 3.1.3.2 Inventory Monitoring Agent

The Inventory Monitoring Agent tracks the on-hand stock for every SKU.
Its public interface is three methods:

- `fulfill(sku, qty) -> (fulfilled, shorted)` — decrements stock,
  records stockouts when `shorted > 0`.
- `receive(sku, qty)` — adds inventory from arriving shipments.
- `level(sku) -> int` — read-only stock query for the replenisher.

Stockouts are counted at the SKU-step granularity, supporting both the
overall *stockout rate* metric and per-SKU *stockout duration*.

#### 3.1.3.3 Replenishment Agent

The Replenishment Agent decides when to reorder and how much. It
implements a continuous-review (s, S) policy:

$$
s = \mu_{\text{LT}} + z \cdot \sigma \cdot \sqrt{LT}
\qquad
S = s + LT \cdot \mu
$$

where $\mu$ is the forecaster's per-day mean prediction, $\sigma$ is the
residual standard deviation, $LT$ is the supplier lead time, and $z$ is
the service-level quantile (default 1.65 ≈ 95%). When on-hand drops at
or below $s$, the agent issues a purchase order for $S - \text{on\_hand}$
units to the Supplier Agent.

#### 3.1.3.4 Supplier Agent

The Supplier Agent simulates external suppliers. It maintains a queue
of pending orders, each annotated with an arrival step computed at order
time as `current_step + lead_time(sku)`. On every model step, orders
whose arrival step has been reached are delivered to the Inventory
Monitoring Agent. Per-SKU lead times can be configured; the default is
seven days uniformly.

#### 3.1.3.5 Analytics Agent

The Analytics Agent observes the post-decision state of the system on
every step and records a per-step snapshot. At the end of a run, it
produces a summary including stockout rate, stockout duration per SKU,
final on-hand inventory, order count, total units ordered, forecast
MAPE, drift event count, and active model methods by tier. The summary
is serialized to JSON; the per-step timeseries to CSV.

### 3.1.4 Drift Detection

Drift detection is a first-class concern of the architecture. The
implementation uses ADWIN [@bifet2007adwin], adapted to e-commerce
constraints.

**Per-SKU detectors (diagnostic).** Each SKU has its own ADWIN instance
updated with absolute forecast residuals $|y_t - \hat y_t|$. These
detectors provide *which* SKU drifted when a fire occurs, which supports
auditability.

**Global detector (primary).** Because per-SKU streams on a long-tail
e-commerce cohort are sparse and noisy, a per-SKU detector's
signal-to-noise ratio is low and the detector fires unreliably. We
therefore add a **global ADWIN detector** on the *population mean* of
step-level absolute residuals:

$$
r_t = \frac{1}{|S_t|} \sum_{s \in S_t} |y_{s,t} - \hat y_{s,t}|
$$

where $S_t$ is the set of SKUs that had observable demand at step $t$.
This aggregation lifts the SNR and reveals regime shifts that affect
the cohort. When the global detector fires, the agent marks all
contributing SKUs' models stale; the next `predict` call refits them.

ADWIN's $\delta$ parameter (false-positive rate bound) defaults to
0.01 in this implementation; lower values produced silent detection on
Olist's sparse per-SKU streams in early tests, and higher values
produced unacceptable false positives in the no-drift control scenario.

### 3.1.5 Tiered Forecasting

A single forecasting algorithm is unsuitable across the head and tail
of an e-commerce SKU cohort. Top-volume SKUs have enough observations
to fit a Holt–Winters model with weekly seasonality; long-tail SKUs do
not. We therefore use a **tier ladder** that selects the algorithm
based on the available history length:

| Observations available | Tier | Method |
|:-:|:-:|:-:|
| < 14 | 1 | Moving average |
| 14 – 34 | 2 | Simple Exponential Smoothing |
| ≥ 35 | 3 | Holt–Winters additive (seasonal period 7) |

Each tier has a **graceful fallback**: if statsmodels fails to fit at a
tier (rare but possible for short pathological series), the agent falls
back to the next-lower tier. This ensures the forecaster always returns
a usable prediction.

The tier is selected at fit time, not at predict time. When a SKU
accumulates enough history to warrant a higher tier, the next refit
(on drift, on safety-interval expiry, or on tier-promotion check
inside `_ensure_fresh`) advances the model.

### 3.1.6 Inter-Agent Communication

Agents exchange information via two mechanisms:

1. **Direct method calls on shared state.** When the Replenishment
   Agent needs the latest stock level for SKU $s$, it calls
   `self.model.monitor.level(s)`. This is appropriate because all five
   agents live in the same process and share a common simulation clock.
2. **Inbox messages.** When the simulation environment broadcasts a
   demand event to the forecaster, it sends a structured message
   (`{type: "demand_observed", sku, qty}`) into the forecaster's inbox.
   The forecaster drains its inbox at the top of its `step()`. This
   model is extensible: new event types can be added without breaking
   existing agents.

Every agent maintains a `decision_log` — a list of structured records,
one per action — that is serialized at the end of a run. This is the
audit trail required by the proposal's transparency goal.

### 3.1.7 Simulation Environment

The simulation environment is the top-level `InventoryModel` (a Mesa
`Model` subclass). On each step it:

1. Reads the day's demand events from the Order Replay engine, which
   serves pre-processed Olist data in (step, sku, qty) form.
2. Optionally transforms the events via the Drift Injector, which
   composes multiplicative drift scenarios per the configuration.
3. Fulfills demand via the Inventory Monitoring Agent and broadcasts
   observations to the Demand Forecasting Agent.
4. Steps each agent in the canonical order described in §3.1.2.

The model bypasses Mesa 3.5's wrapped step counter and owns its own
`steps` attribute (Mesa 3.5 wraps user-defined `step()` with an
event-driven scheduler that auto-increments `steps`; when combined
with a manual increment in user code, this produces a double-step
bug, documented in §3.2.5).

### 3.1.8 Baseline Comparators

Two baselines are implemented for comparison, with care taken to ensure
they represent *textbook-optimized* practice rather than strawmen:

1. **Static Reorder Point** computes $(s, Q^*)$ where $Q^*$ is the
   classical Economic Order Quantity $Q^* = \sqrt{2DK/h}$ using the
   project's cost defaults (holding $h$, ordering $K$). Both $s$ and
   $Q^*$ are fit once on a warm-up window and frozen for the run.
2. **Periodic Centralized Forecasting** also uses the EOQ-derived $Q^*$
   but refits every 30 days on a *recent window* (default 90 days) of
   observed demand. This is materially more responsive than refitting
   on the entire history.

Both baselines share the same simulation environment, the same drift
injector, the same lead-time queue, and the same metrics. They differ
from the proposed MAS only in *decision logic* — making the comparison
structurally fair.

**Role of Static ROP as a control.** A reasonable objection is that a
truly frozen policy is unrealistic — real operators recalibrate
quarterly or semi-annually. We agree, but we deliberately model Static
ROP as the *zero-recalibration limit* because (i) it isolates the
contribution of *any* adaptation, however slow, from the contribution
of the architectural changes the MAS introduces; (ii) a quarterly-
recalibrated Static ROP would essentially be the Periodic baseline
with a longer refit interval, collapsing the three-way comparison into
a two-way; and (iii) the Static ROP's catastrophic stockout rate
documents what happens to *any* deployment that fails to recalibrate
during a period of demand growth — a failure mode operators describe
in interviews. We therefore retain it as an informative control, not
as a strawman, and report all metrics for both baselines side by side
so the reader can judge each on its merits.

## 3.2 Implementation

This part documents the implementation: the technology stack, the
project layout, key algorithmic choices, the reproducibility
infrastructure, and one specific bug whose discovery and resolution
materially affected the empirical results.

### 3.2.1 Technology Stack

The implementation is in pure Python 3.11+ and uses only open-source
dependencies. The complete dependency manifest is in `requirements.txt`;
the principal libraries are listed in Table 3.1.

**Table 3.1.** Principal dependencies.

| Library | Version | Role |
|:-:|:-:|:-:|
| Mesa | ≥ 3.5 | Agent-based modeling framework (Agent / Model base classes) |
| statsmodels | ≥ 0.14 | Simple Exponential Smoothing, Holt–Winters |
| scikit-learn | ≥ 1.4 | Auxiliary fitting utilities |
| river | ≥ 0.21 | ADWIN drift detector |
| ruptures | ≥ 1.1 | PELT change-point detector (available, not used in headline runs) |
| pandas | ≥ 2.2 | Data manipulation, replay |
| numpy / scipy | ≥ 1.26 / ≥ 1.13 | Numerics, hypothesis tests |
| psutil | ≥ 5.9 | Per-run memory and resource profiling |
| matplotlib + plotly + streamlit | various | Figures + interactive dashboard |
| pytest | ≥ 8.0 | Test suite (23 tests, all passing) |

All experiments run on commodity hardware. The headline 180-run sweep
completes in approximately 50 minutes on an Apple M-series MacBook
Pro.

### 3.2.2 Project Layout

```
inventory-mas/
├── app.py                  Streamlit dashboard
├── RESULTS.md              Headline numbers + hypothesis verdicts
├── scripts/
│   ├── reproduce_all.sh    One-command end-to-end rerun
│   └── make_figures.py     Static figure generator (PDF + PNG)
├── figures/                Publication-quality figures
├── data/
│   ├── raw/                Olist CSVs (gitignored)
│   └── processed/          Replay-ready CSVs at 5 SKU cohorts
├── src/
│   ├── agents/             The five agents
│   ├── simulation/         Environment, baseline env, replay, drift, logger
│   ├── baselines/          Static ROP, Periodic Forecasting (EOQ Q*)
│   ├── drift/              ADWIN, PELT detector wrappers
│   ├── metrics/            Stockout, cost, MAPE, adaptability, summary
│   ├── data/               Olist preprocessing pipeline
│   └── utils/              Config loading, seeding, jitter
├── experiments/
│   ├── run.py              Single-run entrypoint
│   ├── sweep.py            Multi-seed orchestrator
│   ├── aggregate.py        Per-cell mean ± 95% CI
│   ├── stats.py            Mann–Whitney U, Welch's t, Cohen's d
│   ├── h1_report.py        H1 report across (scenario × baseline × metric)
│   ├── h3_report.py        H3 power-law and linear fits
│   ├── ablation_report.py  Component ablation deltas
│   ├── compare.py          Terminal side-by-side comparison
│   └── configs/            All experiment configs (YAML)
├── notebooks/              Olist exploration
├── results/                Per-run summary.json + timeseries.csv + aggregate.json
├── tests/                  pytest suite
└── thesis/                 This manuscript
```

### 3.2.3 Key Algorithms

#### 3.2.3.1 Demand Forecasting Tier Selection

The tier ladder (§3.1.5) is implemented in `src/agents/forecasting.py`.
The relevant logic is reproduced below in edited form for clarity.

```python
def _refit(self, sku: str) -> None:
    hist = list(self.history[sku])
    n = len(hist)
    if n < self.min_obs_ses:
        model = self._fit_ma(hist)
    elif n < self.min_obs_hw:
        model = self._fit_ses(hist)
    else:
        model = self._fit_hw(hist)
    self.models[sku] = model
    self.model_stale[sku] = False
    self.refit_count += 1
```

The actual `_fit_*` methods wrap statsmodels calls in `try/except`
blocks. When the underlying optimization fails (rare, but possible on
pathological short series), the method returns the next-lower tier as
a graceful fallback. This guarantees `predict` always returns a usable
value.

#### 3.2.3.2 Lazy Refitting with Tier Promotion

A naive implementation would refit on every step a model is stale.
Profile-wise, the dominant cost in a MAS run is statsmodels fitting,
so we use **lazy refitting**: a model is only refit when `predict()`
is called *and* one of the following holds:

- The model is marked stale (drift detected or never fit);
- More than `safety_refit_interval` steps have elapsed since the last
  fit (default 60 days);
- The available history has grown past a tier boundary (e.g., from 13
  to 14 observations, promoting MA → SES).

This bounds per-step CPU cost by the number of *new* predict calls
multiplied by the average refit cost — a much smaller quantity than
`#SKUs × refit_cost / step`.

#### 3.2.3.3 Residual-Based Global ADWIN

The drift detection uses ADWIN on the *forecast residual* stream, not
on raw observed quantities. The motivation, in code form:

```python
# In DemandForecastingAgent.step()
residual = abs(qty - predicted)            # absolute forecast error
step_residuals.append(residual)            # per-SKU contribution
# ...
mean_residual = sum(step_residuals) / len(step_residuals)
global_signal = self._get_global_detector().update(mean_residual, step=step_idx)
if global_signal.detected:
    self.global_drift_steps.append(step_idx)
    for sku in step_skus_with_residual:
        self.model_stale[sku] = True
    self.log("global_drift_detected", ...)
```

This is the *error-monitoring* approach in the drift-detection
literature [@pawar2025drift], implemented at agent granularity. The
empirical justification is in Chapter 4 (the global detector reliably
fires on the catastrophic scenario; per-SKU detectors alone do not).

#### 3.2.3.4 Continuous (s, S) Replenishment

The replenishment policy is implemented in `src/agents/replenishment.py`:

```python
mean_per_day = max(forecaster.predict(sku), 0.0)
std_per_day = max(forecaster.predict_std(sku), 0.0)
mean_lt_demand = mean_per_day * lead_time
safety_stock = self.service_level_z * std_per_day * math.sqrt(lead_time)
reorder_point = mean_lt_demand + safety_stock
order_up_to = reorder_point + lead_time * mean_per_day
if on_hand <= reorder_point:
    qty = max(int(order_up_to - on_hand), 0)
    supplier.place_order(sku, qty)
```

Note that *both* the per-day mean and its standard deviation come from
the forecaster — the replenishment agent does not maintain its own
estimate. This factoring keeps the safety-stock buffer responsive to
the forecaster's residual variance: when forecasting is uncertain, the
buffer is automatically wider.

#### 3.2.3.5 EOQ Baseline Order Quantity

The Static ROP baseline computes the textbook EOQ:

```python
denom = max(holding_cost, 1e-9)
eoq = (2.0 * agg["mean"] * ordering_cost / denom).pow(0.5)
lt_floor = agg["mean"] * lead_time
oq = eoq.combine(lt_floor, max).round().astype(int).clip(lower=1)
```

The `lt_floor` term enforces a minimum of one lead-time of demand per
order; this is necessary because for very low-volume SKUs the EOQ can
round to zero. Without it, the baseline would never reorder those
SKUs.

### 3.2.4 Reproducibility Infrastructure

**Configuration.** Every experiment is described by a YAML
configuration in `experiments/configs/`. A typical config:

```yaml
name: olist_mas_catastrophic
seed: 42
n_steps: 594
fit_window: 90
lead_time: 7
service_level_z: 1.65
refit_interval: 30
recovery_target: 0.95
data:
  processed_path: data/processed/orders.csv
policy: mas
drift:
  scenarios:
    - type: abrupt
      start: 270
      duration: 29
      pct: 3.0
      affected: {kind: top_n, n: 100}
    - type: abrupt
      start: 300
      duration: 29
      pct: 5.0
      affected: {kind: top_n, n: 100}
    - type: abrupt
      start: 330
      duration: 29
      pct: 7.0
      affected: {kind: top_n, n: 100}
initial_stock: { ... }   # per-SKU integer dictionary
results_dir: results
```

**Seeded Stochasticity.** Pure replay of Olist orders is deterministic.
To introduce realistic seed-to-seed variance, the runner applies ±20%
multiplicative jitter to each SKU's initial stock, keyed on the run
seed. The jitter is applied identically to all policies within a seed
(so the seed effectively chooses a starting condition that all three
policies must handle), and varies across seeds (so different seeds
give different starting conditions). This produces enough variance for
Mann–Whitney U to have power at N = 10 per condition.

**Sweep Orchestration.** `experiments/sweep.py` runs N seeds × M
configs sequentially, writing each result to
`results/<config_name>/seed_NNN/{summary.json,timeseries.csv}`. It
also records wall-clock runtime, peak Python heap (via `tracemalloc`),
and delta resident-set-size (via `psutil`) per run, supporting the
scalability analysis in Chapter 4.

**Aggregation.** `experiments/aggregate.py` reads all seed-level
summaries for a config and produces `aggregate.json` containing, for
every numeric metric, the mean, std, min/max, quartiles, and 95%
confidence interval via the Student-t small-sample formula.

**One-Command Rerun.** `scripts/reproduce_all.sh` runs the entire
evaluation from a fresh checkout: preprocesses Olist at five SKU
cohorts, runs the H1 sweep (180 runs), the H3 sweep (75 runs), the
ablation sweep (40 runs), aggregates every cell, generates the three
reports, and writes the publication figures. Estimated wall time
≈ 4 hours on a 2024 M2 MacBook Pro.

### 3.2.5 The Mesa Double-Step Bug

During implementation, a subtle correctness bug was discovered late in
the evaluation phase. The bug originated in our handling of the Mesa
3.5 step interface:

- Our `InventoryModel.step()` method explicitly performs `self.steps
  += 1` at the end of each tick.
- Mesa 3.5, however, wraps a user-defined `step()` method with an
  internal `_wrapped_step` that delegates to `_do_step`, which itself
  performs `self.steps += 1` *before* invoking the user step.

The result was that `self.steps` advanced by **two** every iteration:
once inside Mesa's wrapper, once inside our code. The simulation
processed every *other* day of Olist demand and ignored the rest.
This under-loaded the MAS path by 50%, artificially flattering its
stockout numbers in early experiments.

The bug was diagnosed by adding instrumentation to a smoke test, then
fixed in two lines:

```python
# In InventoryModel.__init__, after super().__init__(seed=seed):
self.step = self._user_step   # bypass Mesa's wrapper
self.steps = start_step
```

The fix bypasses Mesa's wrapping by reassigning `self.step` to the
unwrapped user step method and owning the step counter directly.

This discovery is reported here in full because (i) it is a real
software-engineering finding of independent interest to other Mesa-3
users, (ii) the bug was caught by the test suite we developed (the
tier-promotion tests would not converge to the right tier when only
half the observations arrived), and (iii) every empirical number
reported in Chapter 4 is computed on the post-fix code.

### 3.2.6 Test Suite

The test suite uses `pytest` and lives in `tests/`. The 23 tests
cover:

- Smoke tests for end-to-end run completion;
- Each forecaster tier (MA, SES, Holt–Winters) on synthetic data with
  the expected pattern;
- Tier-promotion when history grows past a threshold;
- Drift-event triggering and the stale-flag → refit pipeline;
- Summary surface (every expected key present, correct types);
- Replay correctness on the processed Olist CSV;
- The drift injector's three scenario types.

All 23 tests pass on the post-fix code. The three tier-promotion tests
in particular were vital — they were the harness that surfaced the
Mesa-3 double-step bug.

Statement-level coverage is **68% across `src/`** (measured by
`pytest-cov`). The uncovered code lives mostly in (i) the data-pipeline
CLI front-ends (`src/data/preprocess.py`, `src/utils/config.py`),
which are exercised end-to-end by the reproduce-all script rather than
by unit tests, and (ii) the `BaselineModel.run` loop and per-step
methods (which are exercised by integration tests under `tests/` that
do not import them directly enough for pytest-cov's static analysis to
register the lines as hit). Core decision logic — agents, forecasters,
drift injector, drift detectors, metrics — is at 85–100% coverage.

## 3.3 Experimental Methodology

This part specifies how the empirical evaluation is conducted: the
research design, the dataset and its preprocessing, the simulation
protocol, the injected drift scenarios, the baselines, the evaluation
metrics, the multi-seed statistical procedure, and the hardware
environment.

### 3.3.1 Research Design

The study follows an *experimental software engineering* approach with
three phases:

1. **Architecture design** (§3.1).
2. **Implementation** of the simulation and agent framework (§3.2).
3. **Controlled experiments** that compare the proposed system against
   the baselines across a 3 × 6 design (3 policies × 6 drift scenarios)
   plus a 3 × 5 scalability design (3 policies × 5 SKU cohorts) plus a
   4-cell ablation. Each cell is run with N = 10 seeds (N = 5 for the
   scalability sweep).

Experiments are reproducible: fixed seeds with documented stochastic
sources, version-controlled YAML configurations, persistent per-step
timeseries, and a single shell script that re-runs the entire
evaluation.

### 3.3.2 Dataset and Preprocessing

The primary dataset is the **Olist Brazilian E-Commerce Public Dataset**
(orders, items, products, sellers, dates from 2016-09-04 to
2018-10-17). Five tables are joined to produce a `(step, sku, qty)`
demand stream:

1. `orders` is filtered to non-cancelled, non-unavailable statuses.
2. Order items are joined to their orders and to product information.
3. The order purchase timestamp is bucketed by day to produce the
   simulation step.
4. The top-N SKUs by total demand are retained; lower-volume SKUs are
   dropped to focus the evaluation on the cohort where forecasting
   models have a chance to fit.
5. The date window is constrained to **2017-01-01 → 2018-08-31** to
   avoid an early sparse-data period and a late ramp-down. This
   produces ≈ 504–600 steps depending on the cohort size.

The five processed cohorts used in the scalability study are saved to
`data/processed/orders_{50,100,200,500,1000}.csv`. The 200-SKU cohort
is the canonical one used by the H1, H2, and ablation experiments.

### 3.3.3 Simulation Protocol

A single experimental run proceeds as follows. Let the processed
dataset contain $T$ steps, and let the configuration specify a
`fit_window` $W$ (default 90) and `n_steps` $N$ (default $T$).

1. **Warm-up.** Days $0, 1, \ldots, W-1$ are used to fit the baseline
   policies. The MAS forecaster is *pre-filled* with the same warm-up
   data so all three policies enter the test window with identical
   information.
2. **Test window.** Days $W, W+1, \ldots, N-1$ are the test window.
   Every reported metric is computed only on the test window. This
   gives N − W = 504 days of test data with the default parameters.
3. **Per-step pipeline.** On each step the simulator (i) reads the
   day's events from the Order Replay engine, (ii) applies any
   configured drift scenarios to the events, (iii) fulfills demand via
   the Inventory Monitoring Agent and broadcasts to the Demand
   Forecasting Agent, and (iv) steps each agent in the canonical order
   described in §3.1.2.

Both BaselineModel and InventoryModel share the same protocol; they
differ only in the decision logic invoked in step (iv).

### 3.3.4 Drift Scenarios

Six scenarios are evaluated. The first three correspond to the
proposal's three drift families; the last two are stress conditions
designed to distinguish the policies' tail behavior; the *no-drift*
baseline is the control.

**Table 3.2.** Drift scenarios used in the evaluation.

| Scenario | Type | Onset | Duration | Magnitude | Affected SKUs |
|:-:|:-:|:-:|:-:|:-:|:-:|
| no_drift | — | — | — | — | — |
| abrupt | Abrupt | step 280 | 30 days | +50% | top-50 |
| gradual | Gradual | step 280 | 60 days | +0.5%/day | random 30% |
| seasonal | Seasonal pulse | steps 280, 287, 294 | 1 day each | +200% | all |
| severe_abrupt | Abrupt | step 270 | 29 days | +200% | top-200 |
| catastrophic | Compound (3 abrupt) | steps 270, 300, 330 | 29 days each | +300%, +500%, +700% | top-100 |

All drift onsets are placed *after* the warm-up window so that all
three policies enter the test on identical state.

### 3.3.5 Baselines

Two centralized baselines are implemented as described in §3.1.8:

- **Static ROP.** Fits $(s, Q^*)$ where $s$ uses the textbook
  service-level formula and $Q^*$ is the Economic Order Quantity
  $Q^* = \sqrt{2DK/h}$ with project default costs. Frozen for the run.
- **Periodic Forecasting.** Same $(s, Q^*)$ but refit every 30 days on
  a 90-day rolling window of recent observed demand.

Both baselines use the same lead time, service-level $z$, and cost
parameters as the MAS, ensuring the comparison isolates the decision
*architecture*, not parameter tuning.

### 3.3.6 Evaluation Metrics

The metrics fall into three groups: service, cost, and adaptability.

**Service:**

- *Stockout rate* — fraction of test-window steps in which any SKU
  experienced shorted demand.
- *Stockout duration per SKU* — count of steps each SKU spent in
  stockout. Sums for total SKU-step stockouts.

**Cost:**

- *Holding cost* — $h$ × ∑ on-hand-per-step (project default $h$ =
  \$0.01/unit/day).
- *Ordering cost* — $K$ × number of orders ($K$ = \$50/order).
- *Stockout cost* — $p$ × total SKU-step stockouts ($p$ = \$5/SKU/day).
- *Total cost* — sum of the three.

**Adaptability and forecasting:**

- *Forecast MAPE* — mean absolute percentage error of one-step-ahead
  per-SKU predictions on the test window.
- *Number of drift events* (per-SKU and global).
- *Number of refits*.
- *Active model methods* — count of SKUs whose current model is at
  each tier (MA / SES / Holt–Winters).
- *Time-to-recovery* — first step after drift onset at which service
  level ≥ 0.95 is sustained for ≥ 7 consecutive steps (only meaningful
  when a policy actually drops below 0.95).
- *Mean service level post-drift* — averaged across the post-drift
  portion of the test window.

**Resource use (scalability study):**

- *Wall-clock runtime per run* — total seconds for the test window.
- *Per-step time* — runtime / N test steps, in milliseconds.
- *Peak Python heap* — sampled via `tracemalloc`.
- *Δ Resident-set-size* — sampled via `psutil` at run start and end.

### 3.3.7 Multi-Seed Procedure and Statistical Tests

Each (scenario, policy) cell is run with N = 10 seeds. Within a seed,
all three policies see the same starting condition (the same ±20%
jittered initial stock per SKU), so the comparison is paired in the
seed dimension; across seeds, conditions vary.

For each pair of conditions to be tested (e.g., MAS vs Static ROP on
`stockout_rate` in scenario `no_drift`), we compute:

- **Mann–Whitney U** — two-sided, non-parametric, no distributional
  assumption. Used as the primary test.
- **Welch's t-test** — two-sided, handles unequal variance. Reported
  for completeness.
- **Cohen's d** with pooled standard deviation — effect size.

With N = 10 per group, the Mann–Whitney U has a two-sided p-value
floor of 0.0002; reporting p = 0.0002 indicates that the rank
distributions are perfectly separated, which is the strongest evidence
the test can produce at this sample size.

A reader skeptical of consistently hitting the test's floor may ask
whether the simulation contains enough stochasticity for seeds to
vary meaningfully. The answer is yes — and the reason the rank
distributions separate cleanly is *not* low within-condition variance
but *high* across-condition variance. Within a single (policy,
scenario) cell, the ±20% initial-stock jitter produces measurable
seed-to-seed variation in stockout rate (typical std ≈ 0.5–1.0 pp).
But the *gap* between policies is on the order of 10–70 pp, two orders
of magnitude larger than the within-cell std. Mann–Whitney's rank
mechanic exploits this geometry: when the gap between samples is much
larger than the spread within samples, all ranks of one group fall
entirely above all ranks of the other, and the test bottoms out at
its sample-size-dependent floor. The result is robust evidence of
separation, not a numerical artifact of underpowered tests.

### 3.3.8 Hyperparameters and Defaults

**Table 3.3.** Default parameters used unless stated otherwise.

| Parameter | Value |
|:-:|:-:|
| `seed` | 1 … 10 (sweep) |
| `n_steps` | 594 (or as per cohort) |
| `fit_window` | 90 |
| `lead_time` | 7 days |
| `service_level_z` | 1.65 (≈ 95%) |
| `refit_interval` (Periodic) | 30 days |
| `recent_window` (Periodic) | 90 days |
| `safety_refit_interval` (MAS) | 60 days |
| `adwin_delta` | 0.01 |
| `min_obs_ses` | 14 |
| `min_obs_hw` | 35 |
| `seasonal_periods` (HW) | 7 |
| `history_window` (forecaster) | 180 days |
| holding cost $h$ | \$0.01/unit/day |
| ordering cost $K$ | \$50/order |
| stockout cost $p$ | \$5/SKU/day |
| stochastic.initial_stock_jitter | 0.20 |

**On the cost weights.** Our defaults reflect mid-range values from
the inventory-management literature for light-goods e-commerce.
Silver, Pyke, and Peterson [@silver2016inventory, Ch. 4] place annual
holding cost at 20–40% of unit value for typical retail; at a \$10
unit value, $h \approx \$2$–\$4/unit/year ≈ \$0.005$–$\$0.011/unit/day$.
Fixed ordering cost per purchase order is dominated by administrative
overhead and is reported at \$25–\$100/order across industries; we use
the median. Stockout cost is the hardest parameter to anchor —
operators' explicit stockout-cost estimates vary by two orders of
magnitude — so we use \$5/SKU/day as a deliberately moderate default.
Chapter 5 §5.6 discusses cost-weight sensitivity, and a sweep over
$(h, K, p)$ is listed as a journal-submission future-work item.

### 3.3.9 Hardware Environment

All experiments run on a single 2024 Apple M-series MacBook Pro
(Mac, Python 3.14, macOS 25). The Mesa simulator is single-threaded;
the sweep orchestrator runs experiments sequentially. No GPU is used.

### 3.3.10 Threats to Validity

Chapter 5 §5.6 expands on these.

- **Construct validity.** The cost weights are typical of light-goods
  e-commerce; results for high-value, slow-moving inventory may shift
  the trade-off curve materially.
- **Internal validity.** Earlier results were affected by a Mesa-3.5
  step-counter bug (§3.2.5). All reported numbers are computed on the
  post-fix code.
- **External validity.** Olist is one platform in one country. The
  paper would benefit from a second dataset (e.g., M5) for
  generalization; the framework is designed to accept arbitrary
  `(step, sku, qty)` CSVs.
- **Statistical validity.** N = 10 seeds is the practical floor for
  Mann–Whitney U to potentially yield p < 0.05; the obtained p-values
  hit the test's lower bound, indicating the rank distributions are
  cleanly separated. N = 30 would be preferred for a journal
  resubmission.
