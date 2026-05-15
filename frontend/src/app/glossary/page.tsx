/**
 * Glossary — definitions for every abbreviation, scenario code, metric,
 * and statistical term that shows up elsewhere in the dashboard. Linked
 * from the About page and the sidebar.
 *
 * Server-rendered; pure static HTML.
 */

import Link from "next/link";
import { Info } from "lucide-react";

interface Term {
  term: string;
  short?: string; // shown as a code-style chip
  body: React.ReactNode;
}

const POLICIES: Term[] = [
  {
    term: "MAS",
    short: "mas",
    body: (
      <>
        Multi-Agent System — the architecture under study. Five
        cooperating agents (forecasting, drift detection, replenishment,
        inventory state, coordinator) share the inventory loop.
      </>
    ),
  },
  {
    term: "Static ROP",
    short: "static_rop",
    body: (
      <>
        Baseline policy. Reorder Point and order quantity are fixed at
        the start of the simulation from historical mean demand and never
        adapt. Stand-in for the simplest textbook approach used widely in
        small-to-mid retailers.
      </>
    ),
  },
  {
    term: "Periodic Forecasting",
    short: "periodic_forecasting",
    body: (
      <>
        Baseline policy. Re-fits the demand forecast on a fixed schedule
        (every N steps) regardless of whether demand has changed.
        Stronger than Static ROP — adapts to slow trends — but blind to
        abrupt shifts between refit cycles.
      </>
    ),
  },
];

const FORECASTING: Term[] = [
  {
    term: "Tiered forecasting",
    body: (
      <>
        Forecaster selection per SKU based on data sufficiency:{" "}
        <Chip>MA</Chip> → <Chip>SES</Chip> → <Chip>Holt-Winters</Chip>.
        New / sparse SKUs get a simple moving average; rich-history SKUs
        graduate to seasonally-decomposed models.
      </>
    ),
  },
  {
    term: "MA",
    short: "moving_average",
    body: <>Moving Average. Mean of demand over the last <em>w</em> observations.</>,
  },
  {
    term: "SES",
    short: "simple_exp_smoothing",
    body: (
      <>
        Simple Exponential Smoothing. Forecast is an exponentially-weighted
        average of past demand. Handles slow trends; no seasonality.
      </>
    ),
  },
  {
    term: "Holt-Winters",
    body: (
      <>
        Triple Exponential Smoothing — level + trend + seasonal
        components. Used for SKUs with enough history to identify a
        seasonal cycle.
      </>
    ),
  },
  {
    term: "MAPE",
    short: "mean_abs_pct_error",
    body: (
      <>
        Mean Absolute Percentage Error. Forecast quality metric: average
        of <code>|actual − forecast| / actual</code>. Lower is better; 0%
        is perfect.
      </>
    ),
  },
];

const DRIFT: Term[] = [
  {
    term: "Concept drift",
    body: (
      <>
        Change in the distribution that is generating the data over time.
        In inventory: yesterday&apos;s demand model no longer predicts
        today&apos;s demand.
      </>
    ),
  },
  {
    term: "ADWIN",
    short: "adaptive_windowing",
    body: (
      <>
        ADaptive WINdowing (Bifet & Gavaldà, 2007). Streaming change
        detector that maintains a variable-size window of recent
        observations and signals when its two halves differ
        statistically. Triggers a forecaster refit when it fires.
      </>
    ),
  },
  {
    term: "Per-SKU vs global drift",
    body: (
      <>
        We run one ADWIN per SKU on forecast residuals (catches
        SKU-specific shifts) and a second ADWIN on the population-mean
        residual (catches market-wide shifts that sparse per-SKU streams
        miss).
      </>
    ),
  },
  {
    term: "Refit",
    body: (
      <>
        Re-training the forecasting model on the most recent window of
        data. Triggered either by ADWIN (MAS) or on a fixed schedule
        (Periodic Forecasting).
      </>
    ),
  },
];

const INVENTORY: Term[] = [
  {
    term: "(s, S) policy",
    body: (
      <>
        Continuous-review inventory rule (Scarf, 1959). When position
        falls below <em>s</em> (reorder point), order up to <em>S</em>{" "}
        (order-up-to level). Provably optimal under a class of
        single-item assumptions.
      </>
    ),
  },
  {
    term: "EOQ",
    short: "economic_order_qty",
    body: (
      <>
        Economic Order Quantity — the order size that minimizes the sum
        of holding + ordering costs. Used to derive the default{" "}
        <em>S − s</em> gap.
      </>
    ),
  },
  {
    term: "Reorder Point",
    short: "rop",
    body: (
      <>
        Inventory level at which a replenishment order is placed.
        Computed as <em>lead-time demand + safety stock</em>.
      </>
    ),
  },
  {
    term: "Safety stock",
    body: (
      <>
        Buffer above forecast demand sized to cover demand-during-lead-time
        variability at a target service level. The MAS version of this is
        dynamic — it scales with recent forecast uncertainty.
      </>
    ),
  },
  {
    term: "Lead time",
    body: (
      <>
        Number of simulation steps between placing an order and the order
        landing on-hand.
      </>
    ),
  },
  {
    term: "On-hand / On-order",
    body: (
      <>
        On-hand = units physically in stock right now. On-order = units
        already ordered but still in transit. Inventory position =
        on-hand + on-order − backorders.
      </>
    ),
  },
  {
    term: "SKU",
    short: "stock_keeping_unit",
    body: <>An individual product variant tracked separately in inventory.</>,
  },
];

const SCENARIOS: Term[] = [
  {
    term: "no_drift",
    body: <>Stationary demand throughout the horizon. Sanity-check baseline.</>,
  },
  {
    term: "gradual",
    body: (
      <>
        Demand mean drifts slowly and continuously over the horizon
        (e.g. monotonic trend). Tests the &quot;slow shift&quot; case.
      </>
    ),
  },
  {
    term: "seasonal",
    body: (
      <>
        Demand follows a repeating cyclical pattern. Tests whether
        forecasters pick up the seasonality and the policy doesn&apos;t
        over- or under-react at cycle boundaries.
      </>
    ),
  },
  {
    term: "abrupt",
    body: (
      <>
        Single sharp change in demand level at a known step. Tests how
        quickly the system detects and adapts.
      </>
    ),
  },
  {
    term: "severe_abrupt",
    body: <>Larger-magnitude version of <code>abrupt</code>.</>,
  },
  {
    term: "catastrophic",
    body: (
      <>
        Multiple compounding shifts (e.g. abrupt level change + variance
        spike). Worst-case stress test.
      </>
    ),
  },
];

const METRICS: Term[] = [
  {
    term: "Stockout rate",
    body: (
      <>
        Fraction of SKU × time-step cells where demand could not be
        satisfied from on-hand inventory. Primary loss metric for{" "}
        <Link className="underline" href="/reports/h1">H1</Link>.
      </>
    ),
  },
  {
    term: "Total cost",
    body: (
      <>
        Sum of holding cost (per unit-step on-hand) + ordering cost (per
        order placed) + stockout penalty (per unmet unit). Reported as a
        single dollar figure across the horizon.
      </>
    ),
  },
  {
    term: "n_orders",
    body: <>Total number of replenishment orders placed during the run.</>,
  },
  {
    term: "n_drift_events",
    body: (
      <>
        Count of times the per-SKU ADWIN signaled a drift and triggered
        a forecaster refit during the run.
      </>
    ),
  },
  {
    term: "n_global_drift_events",
    body: (
      <>
        Count of times the global (population-mean) ADWIN signaled. Often
        much smaller than per-SKU count; correlates with regime shifts.
      </>
    ),
  },
  {
    term: "n_refits",
    body: (
      <>
        Number of forecaster refit operations performed. Equals{" "}
        <code>n_drift_events</code> for MAS, equals{" "}
        <code>n_steps / refit_period</code> for Periodic.
      </>
    ),
  },
];

const STATS: Term[] = [
  {
    term: "Seed",
    body: (
      <>
        RNG seed for one independent replication of an experiment.
        Reported as <code>seed_001</code> through <code>seed_010</code>{" "}
        — every cell is N = 10.
      </>
    ),
  },
  {
    term: "Mann-Whitney U",
    short: "mw_p",
    body: (
      <>
        Non-parametric two-sample test of whether one distribution is
        stochastically greater than another. Our primary significance
        test because sweep distributions aren&apos;t normal.
      </>
    ),
  },
  {
    term: "Welch's t",
    short: "welch_p",
    body: (
      <>
        Two-sample t-test that does NOT assume equal variances. Reported
        alongside Mann-Whitney as a parametric cross-check.
      </>
    ),
  },
  {
    term: "Cohen's d",
    body: (
      <>
        Standardized effect size. <code>|d| ≥ 0.8</code> = large effect,{" "}
        <code>0.5</code> = medium, <code>0.2</code> = small. A p-value
        tells you whether an effect is real; <em>d</em> tells you how big
        it is.
      </>
    ),
  },
  {
    term: "CI95",
    body: (
      <>
        95% confidence interval. Bootstrap-style bounds on the per-cell
        mean; non-overlapping CIs across policies indicate practical
        separation.
      </>
    ),
  },
  {
    term: "p ≤ 0.05",
    body: (
      <>
        Statistical significance threshold used throughout. Sub-0.001
        values are reported as <code>≤ 0.001</code> for compactness.
      </>
    ),
  },
];

const EXPERIMENT: Term[] = [
  {
    term: "Sweep",
    body: (
      <>
        A batch of seed runs for a single configuration. Output of one
        sweep is one row under <code>results/&lt;config_name&gt;/</code>.
      </>
    ),
  },
  {
    term: "Ablation",
    body: (
      <>
        Variant of the MAS with one component disabled (e.g. no ADWIN,
        no safety stock, MA-only forecaster). Used to attribute
        performance contributions to specific design choices. See{" "}
        <Link className="underline" href="/reports/ablation">/reports/ablation</Link>.
      </>
    ),
  },
  {
    term: "Family",
    body: (
      <>
        Experiments are grouped into families: <code>h1</code> (six
        scenarios × three policies), <code>h3</code> (scale sweep, 50 →
        1000 SKUs), <code>ablation</code> (component removal), and{" "}
        <code>custom</code> (everything else).
      </>
    ),
  },
  {
    term: "Tier promotion",
    body: (
      <>
        When a SKU accumulates enough observations to support a more
        expressive forecaster, it is &quot;promoted&quot; from MA to SES
        or SES to Holt-Winters mid-simulation.
      </>
    ),
  },
];

export default function GlossaryPage() {
  return (
    <div className="space-y-8">
      <header className="space-y-2">
        <h1 className="text-3xl font-bold tracking-tight">Glossary</h1>
        <p className="text-ink-muted">
          Every abbreviation, scenario code, metric, and statistical term
          that appears elsewhere in the dashboard, defined in one place.
        </p>
        <div className="card flex items-start gap-2 border-accent/40 bg-accent/5 text-xs text-ink-muted">
          <Info size={14} className="mt-0.5 shrink-0 text-accent" />
          <p>
            Looking for the conceptual <em>why</em> instead of the literal{" "}
            <em>what</em>? See the{" "}
            <Link href="/about" className="underline hover:text-ink">
              About page
            </Link>
            .
          </p>
        </div>
      </header>

      <GlossarySection title="Policies under test" terms={POLICIES} />
      <GlossarySection title="Forecasting" terms={FORECASTING} />
      <GlossarySection title="Drift detection" terms={DRIFT} />
      <GlossarySection title="Inventory math" terms={INVENTORY} />
      <GlossarySection title="Drift scenarios" terms={SCENARIOS} />
      <GlossarySection title="Metrics" terms={METRICS} />
      <GlossarySection title="Statistics" terms={STATS} />
      <GlossarySection title="Experiment organization" terms={EXPERIMENT} />
    </div>
  );
}

function GlossarySection({
  title,
  terms,
}: {
  title: string;
  terms: Term[];
}) {
  return (
    <section className="space-y-3">
      <h2 className="text-xl font-semibold">{title}</h2>
      <dl className="card space-y-4 divide-y divide-border [&>*:not(:first-child)]:pt-4">
        {terms.map((t) => (
          <div key={t.term} className="grid grid-cols-1 gap-1 md:grid-cols-[220px_1fr] md:gap-4">
            <dt className="space-y-1">
              <div className="font-semibold text-ink">{t.term}</div>
              {t.short && <Chip>{t.short}</Chip>}
            </dt>
            <dd className="text-sm leading-relaxed text-ink-muted [&_code]:rounded [&_code]:bg-bg-elevated [&_code]:px-1 [&_code]:py-0.5 [&_code]:font-mono [&_code]:text-xs [&_em]:text-ink">
              {t.body}
            </dd>
          </div>
        ))}
      </dl>
    </section>
  );
}

function Chip({ children }: { children: React.ReactNode }) {
  return (
    <span className="inline-block rounded bg-bg-elevated px-1.5 py-0.5 font-mono text-xs text-ink-muted">
      {children}
    </span>
  );
}
