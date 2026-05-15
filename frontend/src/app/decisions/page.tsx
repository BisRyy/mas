"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useMemo, useState } from "react";
import { api } from "@/lib/api";
import { policyLabel } from "@/lib/format";

type CoverageEntry = {
  n_seeds: number;
  n_seeds_with_decisions: number;
  first_populated_seed: number | null;
};

export default function DecisionsIndexPage() {
  const [scope, setScope] = useState<"populated" | "all">("populated");

  const exps = useQuery({
    queryKey: ["experiments-for-decisions"],
    queryFn: () => api.listExperiments({ limit: 500 }),
  });
  const coverage = useQuery({
    queryKey: ["decision-coverage"],
    queryFn: api.decisionCoverage,
  });

  // Merge experiments with their coverage and sort so populated ones surface
  // first, then alphabetical within tiers.
  const rows = useMemo(() => {
    const data = exps.data ?? [];
    const cov = coverage.data ?? {};
    const merged = data.map((e) => {
      const c: CoverageEntry =
        cov[e.config_name] ?? {
          n_seeds: e.n_seeds,
          n_seeds_with_decisions: 0,
          first_populated_seed: null,
        };
      return { ...e, coverage: c };
    });
    const filtered = scope === "populated"
      ? merged.filter((r) => r.coverage.n_seeds_with_decisions > 0)
      : merged;
    return [...filtered].sort((a, b) => {
      // Primary: higher coverage first
      const ac = a.coverage.n_seeds_with_decisions;
      const bc = b.coverage.n_seeds_with_decisions;
      if (ac !== bc) return bc - ac;
      // Tie-break: alphabetical
      return a.config_name.localeCompare(b.config_name);
    });
  }, [exps.data, coverage.data, scope]);

  const totals = useMemo(() => {
    const cov = coverage.data ?? {};
    let withLogs = 0;
    let totalExps = 0;
    let totalSeeds = 0;
    let seedsWithLogs = 0;
    for (const [, c] of Object.entries(cov)) {
      totalExps += 1;
      totalSeeds += c.n_seeds;
      seedsWithLogs += c.n_seeds_with_decisions;
      if (c.n_seeds_with_decisions > 0) withLogs += 1;
    }
    return { withLogs, totalExps, totalSeeds, seedsWithLogs };
  }, [coverage.data]);

  return (
    <div className="space-y-6">
      <header className="space-y-1">
        <h1 className="text-2xl font-bold">Decision audit</h1>
        <p className="text-ink-muted">
          Full audit trail of every agent action in a simulation. When MAS is
          run with{" "}
          <code className="rounded bg-bg-elevated px-1 py-0.5 text-xs font-mono">
            MAS_EMIT_DECISIONS=1
          </code>{" "}
          (the deployment default), each step, each agent, each SKU produces a
          structured event with its inputs and outputs &mdash; the inventory
          equivalent of an event-sourced ledger. Use this view to answer
          questions like &quot;why did the supplier agent order 18 units of SKU
          X at step 90?&quot; with the literal log line that decided it.
        </p>
        <p className="text-xs text-ink-subtle">
          Pick an experiment below to open one of its seeds. The{" "}
          <em>Audit log</em> column shows how many of the experiment&apos;s
          seeds have decision data on file. Empty cells mean the sweep was run
          before <code>MAS_EMIT_DECISIONS</code> was on &mdash; relaunch from{" "}
          <Link href="/runs/new" className="underline">/runs/new</Link> to
          populate them. New runs land in the same volume and become browsable
          here automatically.
        </p>
      </header>

      {/* Coverage summary cards */}
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <StatCard label="Experiments with logs" value={`${totals.withLogs} / ${totals.totalExps}`} />
        <StatCard label="Seeds with logs" value={`${totals.seedsWithLogs} / ${totals.totalSeeds}`} />
        <StatCard label="Showing" value={`${rows.length} experiment${rows.length === 1 ? "" : "s"}`} />
        <div className="card flex flex-col gap-1">
          <div className="metric-label">Filter</div>
          <div className="flex gap-1 rounded bg-bg-elevated p-0.5">
            <button
              onClick={() => setScope("populated")}
              className={`flex-1 rounded px-2 py-1 text-xs ${
                scope === "populated"
                  ? "bg-bg-surface font-semibold text-ink"
                  : "text-ink-muted hover:text-ink"
              }`}
            >
              Has logs
            </button>
            <button
              onClick={() => setScope("all")}
              className={`flex-1 rounded px-2 py-1 text-xs ${
                scope === "all"
                  ? "bg-bg-surface font-semibold text-ink"
                  : "text-ink-muted hover:text-ink"
              }`}
            >
              All
            </button>
          </div>
        </div>
      </div>

      <div className="card overflow-hidden p-0">
        <table>
          <thead>
            <tr>
              <th>Experiment</th>
              <th>Policy</th>
              <th>Scenario</th>
              <th>Seeds</th>
              <th>Audit log</th>
              <th>Open</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((e) => {
              const c = e.coverage;
              const hasAny = c.n_seeds_with_decisions > 0;
              const full = c.n_seeds > 0 && c.n_seeds_with_decisions === c.n_seeds;
              const targetSeed = c.first_populated_seed ?? 1;
              return (
                <tr key={e.id}>
                  <td>
                    <Link
                      href={`/decisions/${e.config_name}/${targetSeed}`}
                      className="font-mono"
                    >
                      {e.config_name}
                    </Link>
                  </td>
                  <td>
                    <span className={`policy-dot ${e.policy}`} />
                    {policyLabel(e.policy)}
                  </td>
                  <td className="text-xs text-ink-muted">{e.scenario}</td>
                  <td>{e.n_seeds}</td>
                  <td>
                    <CoverageBadge
                      withLogs={c.n_seeds_with_decisions}
                      total={c.n_seeds}
                      tone={full ? "ok" : hasAny ? "partial" : "none"}
                    />
                  </td>
                  <td>
                    {hasAny ? (
                      <Link
                        href={`/decisions/${e.config_name}/${targetSeed}`}
                        className="text-sm"
                      >
                        Open seed {targetSeed} →
                      </Link>
                    ) : (
                      <span className="text-xs text-ink-subtle">
                        no logs &mdash;{" "}
                        <Link
                          href={`/runs/new?config=${encodeURIComponent(e.config_name)}`}
                          className="underline hover:text-ink"
                        >
                          relaunch
                        </Link>
                      </span>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
        {rows.length === 0 && (
          <div className="px-4 py-6 text-center text-sm text-ink-muted">
            {exps.isLoading || coverage.isLoading
              ? "Loading…"
              : scope === "populated"
                ? 'No experiments currently have audit logs. Switch to "All" to see every experiment, or launch a new run with MAS_EMIT_DECISIONS=1 (the deployment default).'
                : "No experiments in the catalog yet."}
          </div>
        )}
      </div>
    </div>
  );
}

function StatCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="card">
      <div className="metric-label">{label}</div>
      <div className="text-xl font-semibold tabular-nums">{value}</div>
    </div>
  );
}

function CoverageBadge({
  withLogs,
  total,
  tone,
}: {
  withLogs: number;
  total: number;
  tone: "ok" | "partial" | "none";
}) {
  const color =
    tone === "ok"
      ? "bg-emerald-950/40 text-emerald-300 border-emerald-700/60"
      : tone === "partial"
        ? "bg-amber-950/40 text-amber-300 border-amber-700/60"
        : "bg-bg-elevated text-ink-subtle border-border";
  const dot =
    tone === "ok"
      ? "bg-emerald-400"
      : tone === "partial"
        ? "bg-amber-400"
        : "bg-ink-subtle";
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5 text-xs ${color}`}
    >
      <span className={`h-1.5 w-1.5 rounded-full ${dot}`} />
      {withLogs} / {total}
    </span>
  );
}
