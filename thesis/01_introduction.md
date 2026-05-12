# 1. Introduction

## 1.1 Background of the Study

Inventory management sits at the core of e-commerce operations: it
directly determines whether a customer can complete a purchase, and what
it costs the platform to keep that promise. Traditional inventory
policies, including fixed reorder-point (ROP) rules and Economic Order
Quantity (EOQ) heuristics, assume that demand is either stationary or
follows a well-characterized stochastic process. Both assumptions are
routinely violated online, where promotions, viral product moments,
seasonal events, and shifts in consumer interest all combine to produce
*concept drift* — the statistical properties of the demand stream change
over time, and yesterday's optimal policy is no longer optimal today
[@gama2014survey; @pawar2025drift].

The dominant industrial response has been to retrain centralized
forecasting pipelines on a fixed schedule (e.g., weekly, monthly). This
mitigates slow drift but fails on three counts: (i) the schedule is
blind to data — it refits whether or not drift has occurred; (ii) refits
are computationally expensive, which keeps cadence coarse; and (iii) in
the gap between refits, a model fitted on stale data continues to drive
decisions [@xiang2023concept]. The problem is amplified in emerging
markets such as Ethiopia, where intermittent connectivity, limited
logistics, and a persistent trust deficit in digital transactions
[@nigatu2021ethiopia; @bao2025emerging] make centralized cloud-dependent
ERP systems both expensive and operationally fragile.

Multi-Agent Systems (MAS) offer a structurally different approach. In a
MAS architecture, autonomous software agents are responsible for narrow
slices of decision-making — monitoring inventory, forecasting demand,
deciding when and how much to reorder, simulating supplier behavior,
analyzing performance — and coordinate via message-passing rather than
through a centralized planner [@wooldridge2009intro]. The decentralization
makes the system more resilient to partial failures, easier to extend
with new agent roles, and amenable to per-agent decision auditing —
properties that are increasingly demanded in operations management
literature [@shen2021agent; @li2024multiagent].

This thesis designs, implements, and empirically evaluates such an
architecture, with three goals: (1) close the software-engineering gap
between agent-based supply-chain *theory* and reproducible, benchmarked
*systems*; (2) provide a publicly reproducible evaluation on an open
e-commerce dataset (Olist Brazilian E-Commerce); and (3) study how the
architecture's modular design and continuous-decision loop interact
with realistic demand drift. We use Ethiopian e-commerce as a
motivating context for the design choices (auditability, offline
operation, modest hardware footprint) rather than as an empirical test
bed — the evaluation in this thesis uses Brazilian data, and any claim
about Ethiopian operational fit is therefore architectural, not
empirical.

## 1.2 Statement of the Problem

Machine-learning-based demand forecasting can substantially reduce
stockout and overstock cost — but only if the forecasting model
*remains* a good description of demand. Three failure modes are well
documented in the literature and reproducible in practice:

1. **Silent model degradation under concept drift.** A model trained on
   one demand regime continues to make predictions even after the
   regime has changed, because the operational pipeline has no built-in
   way to notice [@gama2014survey].
2. **Coarse-cadence retraining.** Periodic centralized refitting is
   blind to *when* drift occurs; it under-reacts when drift is sudden
   and over-orders when demand normalizes after a transient shock
   [@xiang2023concept].
3. **Resource fragility.** Centralized retraining pipelines assume
   reliable compute and reliable connectivity. In intermittent
   environments these assumptions break, with cascading effects on
   downstream replenishment decisions [@bao2025emerging].

Existing agent-based inventory work has explored decentralized
coordination [@li2024multiagent; @kim2024marl], but the results are
overwhelmingly published with proprietary data and closed
implementations. The empirical literature lacks a reproducible
software-engineering treatment that (a) demonstrates an agent-based
inventory architecture beats traditional centralized policies on public
data, (b) measures the *cost* of that win, not just the service-level
gain, and (c) explicitly evaluates how drift detection at the agent
level changes the architecture's response curve. This thesis fills that
gap.

## 1.3 Objectives of the Study

### 1.3.1 General Objective

To design and empirically evaluate a multi-agent software architecture
for autonomous e-commerce inventory optimization that adapts to demand
variability and concept drift.

### 1.3.2 Specific Objectives

1. **Design a modular MAS architecture** comprising Demand Forecasting,
   Inventory Monitoring, Replenishment, Supplier, and Analytics agents,
   with explicit drift detection and adaptive forecasting tiers.
2. **Implement a reproducible simulation environment** that replays a
   public e-commerce dataset (Olist) under controllable concept-drift
   scenarios, with deterministic seeding and per-seed stochastic
   variation.
3. **Empirically compare the proposed system against textbook-optimized
   baselines** (Static ROP with EOQ-derived order quantity, and Periodic
   Centralized Forecasting with a recent-window refit), using a
   multi-seed evaluation that produces statistically defensible
   conclusions.
4. **Evaluate adaptability** under three families of injected drift
   (abrupt, gradual, seasonal pulse) plus two stress conditions (severe
   and catastrophic compound), measuring both service-level recovery
   and the inventory *cost* of maintaining that service level.
5. **Assess scalability** of the architecture as the number of managed
   SKUs increases, characterizing both runtime and peak memory as
   power-law fits across five cohorts (50, 100, 200, 500, 1000).

## 1.4 Research Questions

- **RQ1.** How can an autonomous multi-agent architecture be designed to
  manage e-commerce inventory in a way that adapts to changes in demand
  patterns (concept drift)?
- **RQ2.** To what extent does the proposed multi-agent system improve
  inventory performance — specifically stockout rates and total
  inventory cost — compared to textbook-optimized centralized baselines?
- **RQ3.** How quickly and effectively does the multi-agent system
  detect and respond to demand drift (abrupt, gradual, and seasonal
  shifts)?
- **RQ4.** How scalable is the architecture as the number of managed
  SKUs/agents grows, and what overhead does inter-agent coordination
  introduce?

## 1.5 Research Hypotheses

- **H1 (Performance).** The proposed MAS will reduce the average daily
  stockout rate by at least 10% compared to the Static ROP baseline,
  with statistical significance *p* < 0.05.
- **H2 (Adaptability).** Following a simulated abrupt demand increase of
  50%, the MAS will restore the target service level (95%) in fewer
  days on average than the Periodic Forecasting baseline.
- **H3 (Scalability).** The system's computational overhead will grow at
  most linearly with the number of agents, remaining feasible for
  standard commodity hardware.

(Chapter 4 reports the empirical verdict on each hypothesis. H2's
literal phrasing is reframed in Chapter 5 in light of the EOQ-driven
behavior of the Periodic baseline.)

## 1.6 Significance of the Study

This thesis contributes to software engineering by delivering a reusable,
modular architectural pattern for autonomous inventory decision-making
in e-commerce. It emphasizes reproducibility through (i) the use of a
public, immutable dataset; (ii) open-source dependencies pinned to
specific versions; (iii) version-controlled YAML experiment
configurations; (iv) seeded experiments with persistent per-step
timeseries; and (v) a one-command reproduce-all script. The resulting
framework can serve as a benchmark for future work at the intersection
of agent-based systems, adaptive analytics, and operations management.

For practitioners — particularly in emerging markets such as Ethiopia —
a decentralized agent-based approach reduces operational burden and
improves robustness in the presence of intermittent connectivity and
constrained compute. By logging decisions at the agent level, the system
also supports transparency that can increase trust among business
operators in environments where digital systems must earn trust before
adoption.

## 1.7 Scope and Limitations

### Scope

The work covers the *design* and *simulation-based evaluation* of agent
coordination for inventory decisions. The focus is on agent roles,
communication, drift detection, forecasting tiering, and empirical
evaluation under controllable drift scenarios using public data. The
software artifact is fully open-source and reproducible from a fresh
checkout in under four hours.

### Limitations

The research does not deploy the system in a live production
environment. Simulation-based findings may not capture all real-world
complexities — supplier negotiation, unpredictable lead-time
distributions, organizational and human-in-the-loop factors. Drift
scenarios are controlled approximations of real-world change; the
*natural* drift present in the underlying Olist dataset (platform
growth across 2017–2018) supplements but does not replace the injected
scenarios. The cost-weight defaults (holding $0.01/unit/day, ordering
$50/order, stockout $5/SKU/day) are typical of light-goods e-commerce
but would need recalibration for different domains.
