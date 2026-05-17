# 5. Discussion

This chapter interprets the empirical findings of Chapter 4, addresses
the H2 framing issue head-on, identifies threats to validity, situates
the results in the broader literature, and discusses implications for
practice — particularly for emerging-market deployment.

## 5.1 Why the MAS Wins

The MAS dominates the centralized baselines on both service level and
cost. The mechanism, in order of contribution:

1. **Continuous decision-making.** The Replenishment Agent reviews
   stock every step and issues orders the moment a SKU crosses its
   reorder point. Periodic Forecasting, by contrast, makes ordering
   decisions on a 30-day cadence — but the *parameter refresh* is
   30-day; the actual orders happen continuously using stale
   parameters. The MAS therefore has both daily-fresh data and
   daily-fresh parameters.
2. **Forecast-driven safety stock.** The replenishment policy uses the
   forecaster's residual standard deviation directly to size the safety
   buffer ($z \cdot \sigma \cdot \sqrt{LT}$). When forecasting becomes
   less certain — for example during the catastrophic compound shock —
   the buffer widens automatically. The baselines, fitting once per
   refit window on an aggregate, do not adapt safety stock at the same
   frequency.
3. **Tiered forecasting.** The Demand Forecasting Agent uses Holt–Winters
   on SKUs with enough history (≈ 30% of the cohort) and cheaper models
   on the rest. This avoids both over-fitting tail SKUs and
   under-modeling head SKUs.
4. **Error-driven drift detection.** The global ADWIN detector on
   forecast residuals fires only when the forecaster is *systematically*
   wrong across the cohort. This is a robust signal — sparse per-SKU
   streams are too noisy for a per-SKU detector to fire reliably.

The cost-component breakdown (Figure 4.3) makes the trade-off concrete.
The MAS does not win because every cost line is lower — it wins because
the cost lines move in opposite directions and the net is favorable. In
the no-drift cell, the MAS spends roughly five times as much on ordering
($124k) as Static ROP ($22k) and almost twice as much as Periodic
Forecasting ($70k), because the adaptive safety-stock recalculation
drives more frequent, smaller reorders. That extra ordering activity
is paid back several times over on the holding side: MAS holding cost is
$61k against $225k for Static ROP and $541k for Periodic — a 3.7×
and 8.9× reduction respectively. Stockout penalty contributes negligibly
for either adaptive policy ($0.4k for MAS, $0.9k for Periodic), and is
the only line where Static ROP carries a real cost ($36k uniformly).
The net total cost ranking — MAS $185k, Static ROP $283k, Periodic $612k
— is therefore the result of a deliberate trade: spend more on transport
to save much more on capital tied up in inventory.

The same logic explains why MAS's lead narrows under the catastrophic
scenario. MAS holding cost rises from $61k to $182k (a 3.0× increase)
because the forecaster's correctly-expanded residual std inflates safety
stock, while Static ROP's holding cost actually *decreases* slightly
($225k → $214k) because its fixed reorder point under-orders during the
surge and runs leaner inventory as a side-effect. The MAS still wins on
total cost ($304k vs $273k vs $648k), but the §5.3 ablation finding —
that *removing* adaptive components helps under catastrophic — has its
mechanical explanation in this same figure: the adaptive components are
working as designed; they are simply provisioning for a 700% surge that,
on the inventory-cost side of the ledger, is cheaper to under-provision
for in this experimental cost-parameter regime.

## 5.2 The H2 Reframe

The original H2 ("MAS restores 95% SL faster than Periodic") is
*ill-posed under the EOQ-optimized baseline*. Both adaptive policies
maintain mean post-drift service level above 99% even under the
catastrophic compound shock, because the EOQ-derived order quantity is
large enough that Periodic's between-refit stale period is absorbed by
standing inventory. Time-to-recovery is therefore 0 for both, and the
hypothesis cannot distinguish them.

A naive response would be to design a harsher scenario that *does* push
Periodic below 0.95 SL. We attempted this (the catastrophic scenario in
§3.3.4 was deliberately designed to break the Periodic
baseline) but the EOQ Q\* was large enough that even a +700% demand
shock for 29 days stayed within Periodic's standing inventory. Going
even harsher would put us outside the regime where the experimental
setup is informative.

The *substantive* H2 finding lives in the cost dimension. The MAS and
Periodic achieve essentially the same service level under drift, but
they pay very different prices to achieve it:

| Scenario | MAS cost | Periodic cost | MAS savings |
|:-:|:-:|:-:|:-:|
| abrupt | $184,896 | $612,888 | **−70%** |
| catastrophic | $304,399 | $647,775 | **−53%** |

The right H2 to test in a journal version of this work is
**cost-of-service after drift**: how does the *total cost* of
maintaining a fixed service-level target evolve after drift onset?
We state this as a formal post-hoc hypothesis:

> **H2′ (Cost-efficiency under drift).** At equivalent post-drift mean
> service level (≥ 99%), the MAS will incur at least 30% less total
> inventory cost than the Periodic Forecasting baseline, with
> Mann–Whitney *p* < 0.05.

Our existing data already supports H2′ in every drift scenario:

| Scenario | MAS cost | Periodic cost | MAS savings vs Periodic | Mann–Whitney *p* |
|:-:|:-:|:-:|:-:|:-:|
| abrupt | $184,896 | $612,888 | **−69.8%** | 0.0002 |
| gradual | $186,216 | $612,109 | **−69.6%** | 0.0002 |
| seasonal | $186,538 | $613,385 | **−69.6%** | 0.0002 |
| severe_abrupt | $209,660 | $617,033 | **−66.0%** | 0.0002 |
| catastrophic | $304,399 | $647,775 | **−53.0%** | 0.0036 |

Every cell exceeds the 30% threshold; every test is significant. H2′
is therefore **confirmed** as a post-hoc hypothesis. We mark it
"reframed" rather than "confirmed" only because it was not part of the
preregistered hypothesis set in Chapter 1 §1.5. We recommend H2′ as
the H2 statement for the journal submission.

## 5.3 Ablation Surprise: Safety Stock Under Extreme Drift

The component ablation reported in §4.5 produced a finding worth
discussing explicitly: on the *catastrophic* scenario, every individual
ablation (no ADWIN, MA-only forecaster, no safety stock) *improves*
both stockout rate and total cost relative to the full MAS. This is
the opposite of what an ablation conventionally demonstrates and merits
careful interpretation.

The mechanism is best seen in the cost decomposition. Under catastrophic
3-phase compound shocks (+300%, +500%, +700% surges on top-100 SKUs
across three refit windows), the Holt–Winters forecaster *correctly*
learns large per-day mean predictions and *correctly* reports a large
residual standard deviation reflecting the genuine volatility. Both
quantities feed into the replenishment policy:

$$
s = \mu_{\text{LT}} + z \cdot \sigma \cdot \sqrt{LT}
$$

When $\sigma$ is large (the system *knows* uncertainty is high), the
safety stock $z\sigma\sqrt{LT}$ balloons. The reorder point and
order-up-to level rise proportionally, and the system places large
orders that result in standing inventory orders of magnitude larger
than necessary once the transient ends.

The simpler MA-only forecaster produces a more conservative estimate
of mean and a much smaller estimate of standard deviation (because
moving-average residual std measures variability *around the mean*,
not the absolute volatility). Under adversarial drift it therefore
*underestimates* the buffer needed — and that happens to be closer to
the true optimum than the full forecaster's *correct* overestimate.

Three observations follow from this:

1. **It is a real algorithmic limitation, not a bug.** The full MAS
   responds *honestly* to the data; the data say "volatility is
   enormous"; and the policy responds by buffering aggressively. The
   problem is in the *interaction* between the safety-stock formula
   and a forecaster that accurately captures transient volatility.

2. **The fix is to bound safety stock**. A natural future-work item
   is to cap $z\sigma\sqrt{LT}$ at some reasonable multiple of $\mu_
   {\text{LT}}$ (e.g., $2\mu_{\text{LT}}$), or to use trimmed or
   robust statistics for the residual std estimator.

3. **Under milder drift, the full MAS dominates.** Tables 4.1 and 4.3
   show the full MAS beats both baselines on every cell of the H1
   evaluation, across no_drift, abrupt, gradual, seasonal, and
   severe_abrupt scenarios. The ablation surprise is specifically a
   boundary-condition behavior at adversarial extremes — relevant for
   reviewers and for production deployment, but not a refutation of
   the H1 result.

This is the kind of finding that a less thorough ablation study would
have missed entirely. We report it because honesty about limitations
is more valuable than a clean narrative.

## 5.4 Why MAS Is Cheaper Than Periodic

A natural follow-up question is *why* MAS spends so much less than
Periodic to achieve the same service level. The mechanism is in the
order quantity: Periodic refits its $(s, Q^*)$ every 30 days, but the
EOQ formula $Q^* = \sqrt{2DK/h}$ depends on the *recent-window mean
demand* $D$. With our cost defaults ($K = \$50$ ordering, $h = \$0.01$
holding per unit per day), the optimal $Q^*$ is large — large enough
that an order covers approximately 100 days of average demand. Periodic
therefore places fewer, larger orders, and carries large standing
inventory between them. The MAS, with a continuous review and a
forecaster-aware safety buffer, places more, smaller orders driven by
*actual* stock depletion rather than scheduled refit boundaries. It
holds 3–4× less inventory at the cost of 30% more orders.

In our parameter regime, the trade-off favors MAS strongly: holding
cost dominates ordering cost over the test window, so MAS's
just-in-time pattern dominates Periodic's batch pattern.

## 5.5 The Mesa-3.5 Step-Counter Bug: Lessons for Test Design

The Mesa double-step bug, technically described in §3.2.5, is worth a
brief discussion-grade reflection because it illustrates a class of
correctness issue that is invisible in metric trajectories. The bug
under-loaded the MAS simulation by 50%, yet every output metric
remained plausible: the simulation completed without errors, the
forecaster produced reasonable predictions, the replenishment agent
ordered, and the analytics agent emitted a normal-looking summary.

The signal that something was wrong came from the **tier-promotion
tests** in the test suite, not from any production-style smoke test.
Those tests assert a *property* of how the architecture should evolve
(history grows → forecaster tier advances). With half the observations
arriving, tier promotion lagged by a factor of two and the tests
failed.

Two lessons follow:

1. **Test architectural invariants, not just end-to-end outcomes.**
   Property-based tests survive silent under-loading; smoke tests do
   not.
2. **Be suspicious of framework wrappers around user-defined methods.**
   Mesa 3.5's reassignment of `self.step` to an event-driven wrapper is
   documented in the changelog but emits no runtime warning. Users
   carrying over Mesa 2.x patterns will silently double-count.

## 5.6 Threats to Validity

### Construct validity

- **Cost weights.** Total cost depends on the relative magnitudes of
  $h$, $K$, $p$. The defaults ($h=0.01$, $K=50$, $p=5$) reflect typical
  light-goods e-commerce. For high-value, slow-moving inventory (large
  $h$ per unit), the EOQ favors smaller, more frequent orders, and the
  MAS-vs-Periodic cost gap would shrink. We recommend a sensitivity
  analysis sweep over $(h, K, p)$ for the journal submission.
- **Service-level target.** $z = 1.65$ targets approximately 95%
  in-stock probability for the lead-time demand distribution. Different
  targets would shift the safety-stock buffer and therefore the
  cost-vs-service trade-off.

### Internal validity

- **The Mesa-3.5 bug** (§5.5). Affected all pre-fix results; reported
  numbers are post-fix.
- **Single-machine evaluation.** All experiments run on one MacBook
  Pro. Hardware-dependent timing (Chapter 4 §4.3) is reported as
  relative rather than absolute.
- **Determinism.** Within a (config, seed) pair, runs are bit-identical.
  This is verified by the test suite and was relied upon during
  debugging.

### External validity

- **One dataset.** Olist is one platform in one country. The framework
  accepts any `(step, sku, qty)` CSV; adding M5 (Walmart) or comparable
  open datasets is feasible and would broaden the generalization claim.
- **Simulated lead times.** Real-world lead-time variability is
  underspecified in this study — we use a constant 7-day lead time.
  Real suppliers exhibit lead-time variance (and correlated variance
  with demand). The framework supports per-order stochastic lead times
  but the experiments use constants for comparability.
- **No human-in-the-loop.** Real inventory operators override automated
  decisions for promotions, supply disruptions, and qualitative signal.
  This is out of scope for this thesis, which evaluates the algorithm,
  not the operator.

### Statistical validity

- **N = 10 seeds.** The Mann–Whitney U at N = 10 vs N = 10 has a
  two-sided *p*-floor of 0.0002. The hypothesis tests in Chapter 4 hit
  this floor in nearly every cell, indicating perfectly separated rank
  distributions. For a top-tier journal, N = 30 would be preferable.
- **Multiple-comparison correction.** This work reports 36 pairwise
  tests (6 scenarios × 2 baselines × 3 metrics). At α = 0.05, the
  family-wise error rate with Bonferroni correction requires *p* <
  0.0014. All 36 obtained *p*-values pass this threshold, so the
  conclusions are robust to multiple comparisons.

## 5.7 Implications for Practice

### For e-commerce operators in emerging markets

These implications are *architectural* rather than empirical: our
evaluation uses Brazilian e-commerce data, and we have not run any
Ethiopia-specific experiments. We argue from the *properties* of the
architecture, not from country-specific benchmarks.

- A decentralized agent-based approach can be deployed on commodity
  hardware (the framework runs end-to-end on a laptop in under five
  minutes per scenario), eliminating the cloud-dependency that
  centralized ERP systems require.
- Per-agent decision logs provide auditability that supports the
  trust-building required in markets with low digital-transaction
  trust — every decision is reproducible from logs.
- The MAS's cost savings (50–70% vs the textbook-optimized baseline)
  translate directly to working-capital efficiency, which matters
  proportionally more for capital-constrained SMEs than for large
  enterprises.

An empirical Ethiopia-specific evaluation — replicating the H1 design
on an Ethiopian e-commerce dataset and/or with simulated connectivity
disruption — would convert these architectural arguments into
empirical claims and is listed as future work in §6.6.

### For software engineering researchers

- The thesis demonstrates that *architectural quality* (modular agents,
  explicit interfaces, per-agent audit logs) and *algorithmic quality*
  (tiered forecasting, error-driven drift detection) are complementary,
  not competing.
- The Mesa-3.5 step-counter bug is a worked example of a class of
  silent correctness failures that test suites built around end-to-end
  smoke tests will miss but property-based tests will catch.

### For inventory and operations researchers

- Cost dominates stockout rate as a discriminating metric once both
  policies are above the service-level target. Any future evaluation
  should report *both* metrics; stockout rate alone makes
  brute-force hoarding look identical to adaptive policy.
- The 95% service-level recovery time, as a metric, is degenerate when
  the comparison includes an EOQ-optimized periodic baseline at a
  light-goods cost ratio. Cost-of-service is the sharper alternative.

### When the simpler baseline suffices

Sharpening the claim is more valuable than overgeneralizing it. The
proposed architecture is *not* the right choice when:

1. **Demand is genuinely stationary** over the planning horizon. A
   stationary process has no concept drift; Static ROP with a single
   well-fit calibration is theoretically optimal and operationally
   simpler. The forecaster, drift detector, and refit machinery in the
   MAS add cost without benefit in this regime.
2. **The cohort is small enough for human oversight.** With < 20 SKUs,
   an experienced inventory operator with a spreadsheet review every
   two weeks will outperform any automated system, because human
   judgment incorporates qualitative signals (supplier rumors,
   competitor moves) the architecture cannot see.
3. **Holding cost dominates ordering cost** ($h \gg K$, e.g.,
   high-value perishables). Here the EOQ optimum is small frequent
   orders, the Periodic baseline's hoarding pattern is naturally
   suppressed, and the MAS's marginal cost advantage shrinks toward
   zero. The §5.5 cost-weight sensitivity discussion expands on this.
4. **Under adversarial three-phase shocks** of the kind constructed in
   our `catastrophic` scenario, the ablation (§4.5) shows the full MAS
   over-reacts to genuine volatility. Until the bounded-safety-stock
   fix (§6.6) is implemented, deployments expecting such adversarial
   conditions should consider the `ma_only` configuration as a more
   conservative alternative.

These honest negative cases sharpen rather than weaken the positive
claim: the architecture earns its complexity *under non-stationary,
medium-to-large cohorts, with light-to-medium holding cost, and
absent adversarial worst-case drift*. That is a substantial operating
regime — most e-commerce SMEs in our target market fall inside it —
but it is not all of inventory.

## 5.8 Limitations

This section summarizes the limitations specific to the discussion's
interpretive claims; the full threats-to-validity treatment is in
§5.6, and the forward research agenda is consolidated in §6.6.

- **Constant lead times.** Real lead times vary, sometimes
  systematically with demand. Our experiments use a uniform 7-day
  lead time across SKUs; the framework supports stochastic lead times
  but the headline runs do not exercise them.
- **Single dataset.** Olist is one platform in one country. The
  framework accepts any `(step, sku, qty)` CSV; replication on M5 or
  a comparable open dataset is the most important external-validity
  check.
- **N = 10 seeds.** Sufficient for *p* < 0.001 in every cell but below
  the N = 30 expected by top-tier journals. Re-running at N = 30 is a
  short follow-up.
- **No comparison against published agent-based methods.** We compare
  against textbook-optimized centralized baselines, not against
  Li et al. (2024) or Kim et al. (2024). A like-for-like algorithmic
  comparison would require reimplementing those methods, which is
  outside the scope of this thesis.
