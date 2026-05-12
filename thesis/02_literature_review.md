# 2. Literature Review

This chapter reviews four bodies of work that frame the thesis: (1)
classical and modern e-commerce inventory management; (2) Multi-Agent
Systems in supply-chain and inventory coordination; (3) concept drift
and adaptive decision systems; (4) the constraints specific to e-commerce
in Ethiopia and other emerging markets. The chapter closes with the
research gap that motivates this work.

## 2.1 E-Commerce Inventory Challenges

E-commerce inventory management requires balancing two competing
objectives: maintaining high *service levels* (avoiding stockouts) and
minimizing *cost* (holding cost plus ordering cost plus stockout
penalty). The operations-research treatment of this trade-off has a
long history. The newsvendor model [@arrow1951newsvendor] gives the
optimal single-period order quantity under uncertain demand; multi-
period extensions yield the $(s, S)$ family of policies whose optimality
under fixed ordering cost was established by Scarf
[@scarf1959optimality] and refined for capacitated and lost-sales
settings by Federgruen and Zipkin [@federgruen1984optimal]. The
deterministic-demand limit produces the classical Economic Order
Quantity formula, and a fixed-Reorder-Point (ROP) rule is its
stochastic analogue at steady state. These approaches are reviewed
comprehensively in Silver, Pyke and Peterson [@silver2016inventory].

Their underlying assumption of stationary or well-characterized
stochastic demand routinely fails in online retail [@pawar2025drift],
where demand variability, promotions, seasonal effects, and rapid
shifts in consumer interest significantly degrade the effectiveness
of static inventory policies [@xiang2023concept]. Theoretical work on
non-stationary demand [@graves1999adaptive; @snyder2002forecasting]
generalizes the $(s, S)$ framework to time-varying parameters but
typically assumes the demand process is known up to its parameters —
an assumption violated by genuine *concept drift* (§2.3) where the
process *family* itself changes.

A separate strand of recent work approaches the problem from the
forecasting side. Ban and Rudin [@ban2019bigdata] propose a "big-data
newsvendor" that learns optimal order quantities directly from feature
data, bypassing the explicit-distribution assumption. Pawar et al.
[@pawar2025drift] show that integrating explicit drift detection with
forecasting reduces prediction error and improves responsiveness in
dynamic environments. Croston [@croston1972intermittent] addresses the
related but distinct *intermittent demand* problem (many zero-demand
periods), with the Syntetos-Boylan refinements [@syntetos2005accuracy]
providing the bias correction relevant to sparse per-SKU streams of
the kind encountered in this thesis.

Together, this literature argues for inventory optimization that moves
beyond fixed parameters toward systems capable of *monitoring* the
data-generating process and *adapting* to evolving demand.

A second strand of work focuses on the *cost structure* of online
retail. Where holding cost is low relative to ordering cost — as is
typical for light-goods, high-velocity e-commerce — the textbook EOQ
prescribes large, infrequent order quantities, and Periodic-refit
heuristics tend to hoard inventory between refits. This produces
policies that *appear* to maintain service level but at substantial
carrying cost, a phenomenon empirically reproduced in our results
(Chapter 4).

## 2.2 Multi-Agent Systems in Supply Chain and Inventory

Multi-Agent Systems (MAS) have been applied to supply-chain coordination
to decentralize decision-making and improve responsiveness and
robustness [@wooldridge2009intro]. In such systems, agents represent
roles such as retailers, warehouses, and suppliers, and coordinate via
message-passing and negotiation protocols [@shen2021agent].

Recent work has explored agent-based inventory optimization and
coordination mechanisms. Li et al. [@li2024multiagent] propose a
multi-agent framework integrating forecasting and replenishment agents
and demonstrate improved inventory turnover and cost reduction compared
to centralized approaches. Kim et al. [@kim2024marl] show that
multi-agent reinforcement learning improves resilience in inventory
systems under disruption. However, much of this work relies on
proprietary data or closed implementations, limiting reproducibility and
empirical comparison.

Moreover, many studies focus on *algorithmic* performance rather than
*architectural* design, leaving software-engineering concerns such as
modularity, extensibility, and operational robustness underexplored. The
present thesis explicitly addresses these concerns by treating the MAS
as a software artifact with documented agent interfaces, message
schemas, and audit logs.

## 2.3 Concept Drift and Adaptive Decision Systems

Concept drift occurs when the statistical properties of data streams
change over time, causing model performance degradation
[@gama2014survey]. In retail and inventory contexts, drift may be
*abrupt* (e.g., sudden demand surges), *gradual* (slow trend changes),
or *recurring* (seasonal effects) [@xiang2023concept].

Drift detection methods include statistical change-point detectors such
as ADWIN [@bifet2007adwin] and PELT, as well as error-monitoring
techniques (e.g., DDM, EDDM) that watch the prediction-error stream
rather than raw observations. After detection, forecasting models or
decision policies may be updated [@pawar2025drift]. A practical lesson
from this literature, which we adopt and extend, is that *raw-value*
detectors fail on sparse per-SKU streams (low signal-to-noise) and that
detection should be performed on the *forecast residual* — the population
mean of absolute residuals is a higher-SNR signal that aggregates across
the cohort.

Most existing adaptive systems are centralized. Few examine how drift
detection and adaptation can be *embedded* within a distributed
agent-based architecture, where the detector signal must be routed to
the agents that own the affected models and trigger lazy refits.

## 2.4 Ethiopia and Emerging-Market Constraints

E-commerce operations in Ethiopia and similar emerging markets face
additional constraints beyond demand uncertainty. Common challenges
include uneven internet connectivity, underdeveloped logistics
infrastructure, and persistent trust deficits in online transactions
[@nigatu2021ethiopia; @bao2025emerging]. These factors increase
lead-time uncertainty, amplify the impact of stockouts, and constrain
the feasibility of centralized, compute-intensive optimization systems.

Decentralized and modular architectures are therefore considered more
suitable for such contexts, as they can operate with partial
connectivity, scale incrementally, and provide auditable decision
processes that support trust and accountability [@bao2025emerging]. This
positioning influences several of our design decisions: per-agent
decision logs, locally executable forecasters (no cloud calls), and a
sweep infrastructure that runs offline.

## 2.5 Research Gap

Despite progress in agent-based supply-chain systems and concept-drift
research, there remains limited publicly reproducible work that combines:

1. A modular multi-agent inventory architecture with documented agent
   interfaces and communication schemas;
2. Explicit modeling and *injection* of concept-drift scenarios;
3. Error-monitoring drift detection embedded at the agent level;
4. Empirical evaluation using public e-commerce datasets with
   open-source implementations and statistically defensible (N ≥ 10
   seeds, hypothesis-tested) results;
5. Explicit consideration of architectural modularity, adaptability,
   and emerging-market constraints.

This thesis addresses the gap by delivering a reproducible simulation
framework and comparative evaluation against textbook-optimized
baselines, with attention to software-engineering qualities (modularity,
extensibility, reproducibility) and to the operational constraints
relevant to emerging markets.
