/**
 * About the research — read-only marketing/context page for visitors
 * who arrive at the dashboard without prior context (advisors,
 * collaborators, reviewers, the author's future self).
 *
 * Server-rendered (no "use client"): all content is static so it ships
 * as plain HTML, fast TTFB, no JS hydration cost.
 */

import Link from "next/link";
import { Github, ExternalLink, BookOpen } from "lucide-react";

const GITHUB_URL = "https://github.com/BisRyy/mas";

export default function AboutPage() {
  return (
    <div className="space-y-10">
      {/* ─── Hero ────────────────────────────────────────────────────── */}
      <header className="space-y-3">
        <div className="text-xs uppercase tracking-wider text-ink-muted">
          MSc Thesis · Addis Ababa Science and Technology University
        </div>
        <h1 className="text-3xl font-bold leading-tight md:text-4xl">
          Design, Implementation, and Empirical Evaluation of a
          Multi-Agent Architecture for E-Commerce Inventory Optimization
        </h1>
        <p className="text-ink-muted">
          A reproducible study on whether a small society of cooperating
          agents — forecasting, drift detection, replenishment, inventory
          state, and coordination — can outperform classical inventory
          policies under non-stationary demand on real e-commerce data.
        </p>
        <div className="flex flex-wrap gap-3 pt-2">
          <a
            href={GITHUB_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 rounded-md border border-border bg-bg-elevated px-3 py-2 text-sm font-medium hover:bg-bg-surface"
          >
            <Github size={16} /> Source on GitHub
            <ExternalLink size={12} className="text-ink-muted" />
          </a>
          <Link
            href="/reports/h1"
            className="inline-flex items-center gap-2 rounded-md bg-accent px-3 py-2 text-sm font-medium text-white hover:bg-accent-muted"
          >
            <BookOpen size={16} /> See the results
          </Link>
        </div>
      </header>

      {/* ─── Problem ─────────────────────────────────────────────────── */}
      <Section title="The problem">
        <p>
          Inventory decisions in e-commerce live on a knife&apos;s edge.
          Hold too much and capital is locked in slow-moving SKUs; hold too
          little and a single stockout drives lost margin, customer churn,
          and platform penalties. The classical literature — Arrow-style
          newsvendor, Scarf&apos;s <em>(s, S)</em> policies, periodic
          forecasting — assumes a relatively stable demand distribution
          and adapts slowly when that assumption breaks.
        </p>
        <p>
          Real e-commerce demand does not behave that way. Promotions,
          virality, supply disruptions, and seasonality cause{" "}
          <em>concept drift</em>: the distribution generating today&apos;s
          orders is meaningfully different from last week&apos;s. A
          forecasting model that re-fits on a fixed schedule will trail
          the change; a policy with static safety stock will either
          stock out during the shift or sit on excess inventory after it
          settles.
        </p>
      </Section>

      {/* ─── Approach ────────────────────────────────────────────────── */}
      <Section title="The approach">
        <p>
          We design a five-agent system that splits the inventory loop
          along its natural seams. Each agent owns a narrow concern and
          publishes results the next agent consumes, with a coordinator
          that arbitrates when their recommendations conflict.
        </p>
        <ul className="ml-5 list-disc space-y-1">
          <li>
            <strong>Forecasting agent</strong> — tiered MA →
            SimpleExpSmoothing → Holt-Winters, promoted per-SKU based on
            data sufficiency.
          </li>
          <li>
            <strong>Drift-detection agent</strong> — ADWIN windowing on
            per-SKU residuals plus a global ADWIN on the population mean,
            triggers refits when the data distribution shifts.
          </li>
          <li>
            <strong>Replenishment agent</strong> — EOQ-derived{" "}
            <em>(s, S)</em> policy with dynamic safety stock as a function
            of forecast uncertainty and recent volatility.
          </li>
          <li>
            <strong>Inventory-state agent</strong> — single source of
            truth for on-hand, on-order, and pipeline positions.
          </li>
          <li>
            <strong>Coordinator</strong> — orchestrates the per-tick
            interaction, handles tie-breaking, and emits the decision log
            used for the audit trail you see in this dashboard.
          </li>
        </ul>
      </Section>

      {/* ─── Method ──────────────────────────────────────────────────── */}
      <Section title="Evaluation">
        <p>
          Demand is replayed from the Olist Brazilian E-Commerce public
          dataset across cohorts of 50 / 100 / 200 / 500 / 1000 SKUs. Each
          configuration runs N = 10 seeds. The MAS architecture is
          compared against two baselines (Static ROP and Periodic
          Forecasting) under six demand regimes — stationary, gradual
          drift, seasonal, abrupt, severe abrupt, and catastrophic.
        </p>
        <p>Three hypotheses, all pre-registered before the sweep ran:</p>
        <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
          <HCard
            tag="H1"
            label="Performance"
            claim="MAS reduces stockouts vs both baselines under drift."
          />
          <HCard
            tag="H2"
            label="Adaptability"
            claim="MAS recovers service level faster after distribution shifts."
          />
          <HCard
            tag="H3"
            label="Scalability"
            claim="Per-step runtime grows sub-linearly with SKU count."
          />
        </div>
        <p>
          Statistical tests: Mann-Whitney U as the primary, Welch&apos;s
          t for parametric comparison, and Cohen&apos;s d for effect
          size. Results, raw seed-level data, and the 23k-event decision
          log are all browsable from this dashboard.
        </p>
      </Section>

      {/* ─── What's in this dashboard ────────────────────────────────── */}
      <Section title="What this dashboard shows">
        <p>
          Everything is read from the same SQLite catalog that the thesis
          manuscript pulls from. No numbers diverge between paper and UI.
        </p>
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
          <LinkCard
            href="/experiments"
            title="Experiment catalog"
            body="All 36 sweep configurations with per-seed aggregates."
          />
          <LinkCard
            href="/reports/h1"
            title="H1 report"
            body="Stockout-rate + total-cost comparisons, every scenario, every baseline."
          />
          <LinkCard
            href="/reports/h3"
            title="H3 scalability"
            body="Power-law fits on per-step runtime vs SKU count."
          />
          <LinkCard
            href="/reports/ablation"
            title="Ablation"
            body="Contribution of each component (drift detector, safety stock, forecast tier)."
          />
          <LinkCard
            href="/decisions"
            title="Decision audit"
            body="Per-tick agent log — every action with the inputs that produced it."
          />
          <LinkCard
            href="/runs/new"
            title="Launch a run"
            body="Re-run any configuration; results stream live into the catalog."
          />
        </div>
      </Section>

      {/* ─── Reproducibility ─────────────────────────────────────────── */}
      <Section title="Reproducing the results">
        <p>
          The full source — simulator, backend, frontend, thesis sources,
          and the canonical sweep outputs — is on GitHub. A typical
          end-to-end reproduction:
        </p>
        <pre className="overflow-auto rounded-md bg-bg-elevated p-3 font-mono text-xs leading-relaxed text-ink">
{`git clone ${GITHUB_URL}.git
cd mas
make download-data           # fetch Olist CSVs
make sweep CONFIG=olist_mas_catastrophic SEEDS=001..010
make reports                 # regenerate H1/H3/ablation tables`}
        </pre>
        <p>
          The deployed instance you are looking at was built from{" "}
          <a
            href={GITHUB_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="underline hover:text-ink"
          >
            this exact repository
          </a>
          . Hit <em>Settings</em> in the sidebar to see what version is
          running and to trigger a fresh ingestion.
        </p>
      </Section>

      {/* ─── Author / citation ───────────────────────────────────────── */}
      <Section title="Author">
        <p>
          <strong>Bisrat Kebere Derebe</strong> — MSc candidate,
          Software Engineering, Addis Ababa Science and Technology
          University (AASTU).
        </p>
        <p className="text-xs text-ink-subtle">
          If you cite this work, please link to{" "}
          <a
            href={GITHUB_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="underline hover:text-ink"
          >
            the repository
          </a>{" "}
          and reference the manuscript in <code>thesis/</code>.
        </p>
      </Section>
    </div>
  );
}

// ─── Layout helpers ──────────────────────────────────────────────────

function Section({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section className="space-y-3">
      <h2 className="text-xl font-semibold">{title}</h2>
      <div className="space-y-3 text-sm leading-relaxed text-ink-muted [&_strong]:text-ink [&_em]:text-ink">
        {children}
      </div>
    </section>
  );
}

function HCard({
  tag,
  label,
  claim,
}: {
  tag: string;
  label: string;
  claim: string;
}) {
  return (
    <div className="card space-y-1">
      <div className="flex items-center gap-2">
        <span className="rounded bg-bg-elevated px-2 py-0.5 text-xs font-semibold uppercase tracking-wider text-ink-muted">
          {tag}
        </span>
        <span className="text-sm text-ink-muted">{label}</span>
      </div>
      <p className="text-sm text-ink">{claim}</p>
    </div>
  );
}

function LinkCard({
  href,
  title,
  body,
}: {
  href: string;
  title: string;
  body: string;
}) {
  return (
    <Link
      href={href}
      className="card block transition hover:border-accent hover:bg-bg-surface"
    >
      <div className="text-sm font-semibold text-ink">{title}</div>
      <p className="mt-1 text-xs text-ink-muted">{body}</p>
    </Link>
  );
}
