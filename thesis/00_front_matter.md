---
title: "Design, Implementation, and Empirical Evaluation of a Multi-Agent Architecture for E-Commerce Inventory Optimization"
author: "Bisrat Kebere Derebe"
date: "2026"
---

\thispagestyle{empty}

# ADDIS ABABA SCIENCE AND TECHNOLOGY UNIVERSITY {.unnumbered}

::: {style="text-align:center"}
**DESIGN, IMPLEMENTATION, AND EMPIRICAL EVALUATION OF A
MULTI-AGENT ARCHITECTURE FOR E-COMMERCE INVENTORY OPTIMIZATION**

**By**

**BISRAT KEBERE DEREBE**

A Thesis Submitted as a Partial Fulfillment to the Requirements for
the Award of the Degree of Master of Science in Software Engineering

to

**DEPARTMENT OF SOFTWARE ENGINEERING**

**SCHOOL OF POST GRADUATE STUDIES**

**MAY 2026**
:::

\newpage

# Approval Page {.unnumbered}

This is to certify that the thesis prepared by **Bisrat Kebere
Derebe** entitled "**Design, Implementation, and Empirical Evaluation
of a Multi-Agent Architecture for E-Commerce Inventory
Optimization**" and submitted as a partial fulfillment for the award
of the Degree of Master of Science in Software Engineering complies
with the regulations of the university and meets the accepted
standards with respect to originality, content and quality.

**Signed by Examining Board:**

| Role | Name | Signature | Date |
|:---|:---|:---|:---|
| Advisor | Zeleke Abebaw, PhD |  |  |
| External Examiner |  |  |  |
| Internal Examiner |  |  |  |
| Chairperson |  |  |  |
| DGC Chairperson |  |  |  |
| SPGS Dean / Vice Dean |  |  |  |

\newpage

# Declaration {.unnumbered}

I hereby declare that this thesis entitled "**Design, Implementation,
and Empirical Evaluation of a Multi-Agent Architecture for E-Commerce
Inventory Optimization**" was prepared by me, with the guidance of my
advisor. The work contained herein is my own except where explicitly
stated otherwise in the text, and that this work has not been
submitted, in whole or in part, for any other degree or professional
qualification.

\

| | |
|:---|:---|
| Author: Bisrat Kebere Derebe | Signature and Date: ___________________________ |

\

**Witnessed by:**

| | |
|:---|:---|
| Name of advisor: Zeleke Abebaw, PhD | Signature and Date: ___________________________ |

\newpage

# Abstract {.unnumbered}

E-commerce inventory management must balance customer service against
carrying cost under non-stationary demand. Traditional centralized
policies — fixed reorder points, periodic forecast refits — degrade
silently when the demand distribution shifts. This thesis designs,
implements, and empirically evaluates an autonomous multi-agent
software architecture for inventory optimization that adapts to
concept drift via residual-error-driven detection and tiered demand
forecasting. Five autonomous agents (Demand Forecasting, Inventory
Monitoring, Replenishment, Supplier, and Analytics) coordinate via
message-passing on shared state, with the Demand Forecasting Agent
hosting both a model-tiering policy (moving average → Simple
Exponential Smoothing → Holt–Winters) and a global ADWIN drift
detector on the population mean of absolute forecast residuals. We
evaluate the system against two textbook-optimized baselines (Static
Reorder Point with EOQ-derived order quantity; Periodic Centralized
Forecasting with a 90-day recent window) on the Olist Brazilian
E-Commerce Public Dataset (200 SKUs, 504 simulated days), under six
demand-drift conditions: no drift, abrupt, gradual, seasonal pulse,
severe abrupt, and a catastrophic three-phase compound shock. Across
180 multi-seed runs (N = 10 seeds per cell, ±20% initial-stock jitter
for realistic variance), the proposed system reduces the daily
stockout rate by 17–80% versus both baselines (Mann–Whitney *p* ≤
0.001 in every cell; Cohen's *d* up to −313) and is 53–70% cheaper
than the Periodic Forecasting baseline on total inventory cost. A
scalability study at five SKU cohorts (50, 100, 200, 500, 1000) finds
the multi-agent system's wall-clock runtime grows with exponent *b* =
0.37 in a power-law fit — sublinear and substantially below the
linear bound hypothesized in the proposal. The work contributes (i) a
reusable, open-source simulation framework with seeded
reproducibility, (ii) a publicly reproducible benchmark of
multi-agent inventory coordination on the Olist dataset, and (iii)
empirical evidence that agent-level decision logging plus
error-driven drift detection outperform centralized periodic
refitting both on service level and on total operating cost.

**Keywords:** multi-agent systems, inventory optimization, concept
drift, ADWIN, Holt–Winters forecasting.

\newpage

# Acknowledgments {.unnumbered}

I am grateful to my advisor **Dr. Zeleke Abebaw** for guidance
throughout the design and evaluation phases of this work, and to the
Department of Software Engineering at Addis Ababa Science and
Technology University for institutional support. I thank the
maintainers of the Olist Brazilian E-Commerce dataset, the Mesa
agent-based modeling project, and the broader open-source scientific
Python community whose tools made this work reproducible.

\newpage

# List of Abbreviations and Acronyms {.unnumbered}

| Abbreviation | Meaning |
|:-:|:-:|
| ABM | Agent-Based Modeling |
| ADWIN | Adaptive Windowing (drift detection algorithm) |
| AI | Artificial Intelligence |
| ARIMA | AutoRegressive Integrated Moving Average |
| CI | Confidence Interval |
| DDM | Drift Detection Method |
| EOQ | Economic Order Quantity |
| ETS | Exponential Smoothing State Space (Error / Trend / Seasonal) |
| HW | Holt–Winters (forecasting method) |
| LT | Lead Time |
| MA | Moving Average |
| MAPE | Mean Absolute Percentage Error |
| MAS | Multi-Agent System |
| MSE | Mean Squared Error |
| MW | Mann–Whitney (statistical test) |
| Olist | Brazilian E-Commerce Public Dataset (curated by Olist) |
| PELT | Pruned Exact Linear Time (change-point detection) |
| ROP | Reorder Point |
| SES | Simple Exponential Smoothing |
| SE | Software Engineering |
| SKU | Stock Keeping Unit |
| SL | Service Level |
| (s, S) | Continuous-review reorder point / order-up-to-level policy |

\newpage

# List of Tables {.unnumbered}

| Table | Description |
|:-:|:-:|
| 3.1 | Principal dependencies |
| 3.2 | Drift scenarios used in the evaluation |
| 3.3 | Default parameters used unless stated otherwise |
| 4.1 | Stockout rate (mean) and relative reduction vs each baseline |
| 4.2 | Effect size (Cohen's *d*) for stockout rate |
| 4.3 | Total inventory cost (mean) and relative change vs baseline |
| 4.4 | Mean runtime per run by policy and cohort size |
| 4.5 | Mean service level post-drift onset |
| 4.6 | Mean final on-hand inventory by policy across scenarios |
| 4.7 | Ablation results on the catastrophic scenario |
| 4.8 | Mean forecast MAPE by scenario |

\newpage

# List of Figures {.unnumbered}

| Figure | Description |
|:-:|:-:|
| 4.1 | H1 — Stockout rate by policy and scenario |
| 4.2 | Cost decomposition across scenarios and policies (stacked, shared y-axis) |
| 4.3 | Cost components broken out per panel with per-panel y-scales |
| 4.4 | H3 — Runtime and memory scaling (log–log axes) |
| 4.5 | Ablation — stockout rate and total cost by variant |
| 4.6 | Forecast MAPE per scenario (MAS only) |
| 4.7 | Catastrophic scenario time series (on-hand and stockouts) |
