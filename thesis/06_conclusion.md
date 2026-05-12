# 6. Conclusions and Recommendations

This thesis designed, implemented, and empirically evaluated a
multi-agent software architecture for autonomous e-commerce inventory
optimization. The work makes three contributions, validates two of its
three preregistered hypotheses (with the third reframed in light of the
empirical setup), and produces a reusable open-source artifact suitable
for both follow-on research and operational adaptation.

## 6.1 Contributions

1. **A modular, reproducible multi-agent inventory architecture** with
   five autonomous agents (Demand Forecasting, Inventory Monitoring,
   Replenishment, Supplier, Analytics), explicit communication via
   inboxes, per-agent decision logging, and tiered forecasting with
   graceful fallback.

2. **Residual-error-driven global drift detection.** Per-SKU drift
   detectors on raw observations fail on sparse e-commerce streams. We
   demonstrate that ADWIN on the *population mean of forecast
   residuals* recovers a strong, low-false-positive signal that can be
   used to trigger per-SKU lazy refits. To our knowledge no prior
   agent-architecture treatment of inventory has reported the
   error-monitoring detector aggregated to the cohort level; we
   document its mechanism and empirical behavior in this thesis.

3. **A publicly reproducible benchmark** on the Olist Brazilian
   E-Commerce dataset (to our knowledge the first such benchmark
   for multi-agent inventory coordination, though we do not claim
   exhaustive priority). The full evaluation — 180 H1 runs, 75 H3 runs,
   40 ablation runs, plus all aggregation, reporting, and figures — is
   one shell command (`scripts/reproduce_all.sh`) from a fresh
   checkout. Every result file, configuration, and seed is
   version-controlled.

## 6.2 Empirical Verdict on the Hypotheses

- **H1 (Performance) — confirmed and substantially exceeded.** The MAS
  reduces stockout rate by 71.9–80.4% vs the EOQ-optimized Static ROP
  baseline and 17.3–33.5% vs the EOQ-optimized Periodic Forecasting
  baseline, in *every* scenario, with Mann–Whitney *p* ≤ 0.001 and
  Cohen's *d* magnitudes up to −175. The proposal's 10% threshold is
  exceeded by approximately an order of magnitude.

- **H2 (Adaptability) — reframed.** The literal "time-to-95%-SL-recovery"
  cannot distinguish the policies because both adaptive baselines hold
  > 99% SL via large EOQ-driven standing inventory. The *substantive*
  finding is that the MAS achieves equivalent service level at
  **53–70% less inventory cost** than Periodic Forecasting. We
  recommend the journal submission adopt cost-of-service as the H2
  framing.

- **H3 (Scalability) — confirmed and exceeded.** The MAS runtime grows
  sublinearly with cohort size: a power-law exponent *b* = 0.372 across
  cohorts of 50, 100, 200, 500, and 1000 SKUs (the proposal predicted
  linear, *b* ≈ 1). Memory exponent is similarly low at *b* = 0.22.
  Both runtime and memory remain comfortably within commodity-hardware
  bounds.

## 6.3 Bonus Finding: Cost Differential

A finding the proposal did not preregister but which falls cleanly out
of the data: **the MAS is significantly cheaper than the
EOQ-optimized Periodic Forecasting baseline on total inventory cost in
every scenario**, by 53% (catastrophic) to 70% (no-drift), with
Mann–Whitney *p* ≤ 0.001 throughout. The mechanism is that Periodic's
optimal Q\* in our cost regime drives large standing inventory; the
MAS's continuous-review safety-stock-aware policy holds 3–4× less.

## 6.4 Limitations

The principal limitations — simulation-only evaluation, a single
dataset, constant lead times, N = 10 seeds, and the absence of a
like-for-like benchmark against published MAS-RL methods — are
documented in full in §5.6 (Threats to Validity) and §5.8
(Discussion-level limitations). The cost defaults reflect light-goods
e-commerce; high-value slow-moving inventory would shift the
cost-vs-service trade-off in ways the thesis does not characterize
empirically.

## 6.5 Recommendations

The empirical findings translate directly into the following
recommendations for practitioners, researchers, and the institution
that funded this work.

### For e-commerce operators

1. **Adopt continuous-review replenishment with forecast-driven safety
   stock**, particularly where the cost regime is light-goods (low
   holding cost per unit, moderate ordering cost). The MAS architecture
   is operationally simple to deploy because it runs on a single laptop
   and writes auditable decision logs.
2. **Do not deploy frozen Static ROP policies in growing markets.**
   Even at modest growth rates, an un-recalibrated ROP produces large
   service-level losses. If a periodic-refit pipeline is unavailable,
   the agent-based system is the lower-risk alternative.
3. **When deploying the MAS in adversarial conditions** (anticipated
   regime-changing shocks beyond the historical norm), **bound the
   safety-stock buffer** at a reasonable multiple of mean
   lead-time demand. The §3.3.10 finding shows that an unbounded
   buffer over-reacts to large transient volatility. Capping
   $z \cdot \sigma \cdot \sqrt{LT}$ at, say, $2 \cdot \mu \cdot LT$
   is a simple and effective defense.

### For software-engineering researchers

4. **Use property-based tests that assert architectural invariants**,
   not just end-to-end smoke tests. The Mesa double-step bug
   (§3.2.5) was caught by the tier-promotion tests precisely because
   they encoded a property of how the architecture *should* evolve.
5. **Treat MAS as a software artifact**, not merely as an algorithm
   collection. The proposed system's modular interfaces, per-agent
   decision logs, and explicit message-passing make it auditable and
   extensible — qualities that algorithmic-only treatments tend to
   neglect.

### For inventory and operations researchers

6. **Report cost alongside service level.** Stockout rate alone makes
   brute-force hoarding look identical to genuinely adaptive policy.
   The thesis demonstrates that Periodic Forecasting maintains a
   competitive service level only by holding 3–4× more inventory.
7. **Choose adaptability metrics that survive the EOQ regime.**
   Time-to-95%-SL recovery is degenerate when standing inventory is
   large; the proposed *cost-of-service after drift* is a sharper
   alternative (§5.2).

### For the academic institution

8. **Continue investment in reproducibility infrastructure.** The
   one-command rerun of every result in this thesis took fewer than
   four hours on commodity hardware. This standard of empirical
   software-engineering work should become the institutional norm
   for graduate research.

## 6.6 Future Work

Four directions are most promising for follow-on work.

1. **Cost-weight sensitivity** — verify the cost-advantage finding is
   robust across plausible $(h, K, p)$ regimes, not just the
   light-goods regime.
2. **Multi-dataset generalization** — replicate the H1/H3 findings on
   the M5 (Walmart) dataset and any other open e-commerce trace, to
   convert the single-dataset evidence in this thesis into a
   generalization claim.
3. **Live pilot deployment** with an Ethiopian e-commerce operator,
   to validate the architectural arguments for emerging-market
   deployment under real constraints (intermittent connectivity,
   partial supplier reliability, regulatory and trust considerations).
4. **Bounded safety stock with robust statistics** — implement the
   recommendation #3 above as a configurable variant of the
   Replenishment Agent, re-run the H1 and ablation sweeps, and
   confirm that the catastrophic-scenario over-reaction reported in
   §4.5 is eliminated without degrading the milder scenarios.

A medium-term direction is **per-agent autonomy via reinforcement
learning** — replacing the hand-coded (s, S) policy with a policy
learned per-agent and validated against the same simulation
infrastructure developed here. This is a natural extension of the
architecture and would enable comparison against the MAS-RL
literature [@kim2024marl].

## 6.7 Concluding Statement

E-commerce inventory management under concept drift is, fundamentally, a
software-architecture problem as much as it is an algorithmic problem.
This thesis shows that careful agent-level decomposition, explicit
audit logging, error-driven drift detection, and tiered forecasting
combine to outperform textbook-optimized centralized baselines on both
service level and inventory cost — by margins large enough to be
statistically unambiguous and economically meaningful. The full
software artifact is reproducible end-to-end from one command, opens
the system to public scrutiny and extension, and is sized to run on
commodity hardware — making it directly relevant not only to academic
follow-on research but to operators in resource-constrained markets for
whom centralized cloud-dependent ERP systems are operationally and
economically out of reach.
