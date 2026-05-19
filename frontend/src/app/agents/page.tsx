"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useMemo, useState } from "react";
import { api } from "@/lib/api";
import { policyLabel } from "@/lib/format";

/**
 * Live Agent Activity — landing page.
 *
 * Lets the user pick an (experiment, seed) pair to "play back" the per-step
 * decision log as a live agent-system visualisation. Only experiments
 * whose seed runs were captured with decision logs (MAS_EMIT_DECISIONS=1)
 * have anything to show — we surface those first.
 */
export default function AgentsIndexPage() {
  const [scope, setScope] = useState<"populated" | "all">("populated");

  const exps = useQuery({
    queryKey: ["experiments-for-agents"],
    queryFn: () => api.listExperiments({ limit: 500 }),
  });
  const coverage = useQuery({
    queryKey: ["decision-coverage-agents"],
    queryFn: api.decisionCoverage,
  });

  const rows = useMemo(() => {
    const data = exps.data ?? [];
    const cov = coverage.data ?? {};
    const merged = data.map((e) => {
      const c = cov[e.config_name] ?? {
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
      const ac = a.coverage.n_seeds_with_decisions;
      const bc = b.coverage.n_seeds_with_decisions;
      if (ac !== bc) return bc - ac;
      return a.config_name.localeCompare(b.config_name);
    });
  }, [exps.data, coverage.data, scope]);

  return (
    <div className="space-y-6">
      <header className="space-y-2">
        <h1 className="text-2xl font-bold">Live Agent Activity</h1>
        <p className="text-ink-muted max-w-3xl">
          Watch the 5-agent MAS run in playback mode. Pick a captured seed
          below to see, step-by-step, what each agent decided — the
          Forecasting Agent refitting models, the Inventory Monitor
          fulfilling orders, the Replenishment Agent issuing reorders, the
          Supplier shipping POs, and the Analytics Agent recording metrics
          — and the messages flowing between them. Only seeds run with
          decision logging (<code className="font-mono text-xs">MAS_EMIT_DECISIONS=1</code>)
          are available; launch a fresh run from{" "}
          <Link href="/runs/new" className="text-accent hover:underline">
            Launch run
          </Link>{" "}
          with the toggle enabled to add more.
        </p>
      </header>

      <div className="flex items-center gap-2">
        <button
          onClick={() => setScope("populated")}
          className={`px-3 py-1 rounded text-sm ${
            scope === "populated"
              ? "bg-accent text-white"
              : "bg-bg-elevated text-ink-muted hover:text-ink"
          }`}
        >
          With decisions
        </button>
        <button
          onClick={() => setScope("all")}
          className={`px-3 py-1 rounded text-sm ${
            scope === "all"
              ? "bg-accent text-white"
              : "bg-bg-elevated text-ink-muted hover:text-ink"
          }`}
        >
          All experiments
        </button>
      </div>

      <div className="card overflow-hidden p-0">
        <table>
          <thead>
            <tr>
              <th>Config</th>
              <th>Scenario</th>
              <th>Policy</th>
              <th>Seeds (with logs)</th>
              <th>Open</th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 && (
              <tr>
                <td colSpan={5} className="py-6 text-center text-ink-muted">
                  {scope === "populated"
                    ? "No experiments with decision logs yet. Launch a run with MAS_EMIT_DECISIONS=1."
                    : "No experiments at all."}
                </td>
              </tr>
            )}
            {rows.map((r) => {
              const seed = r.coverage.first_populated_seed ?? 1;
              const hasLogs = r.coverage.n_seeds_with_decisions > 0;
              return (
                <tr key={r.config_name}>
                  <td className="font-mono text-xs">{r.config_name}</td>
                  <td>{r.scenario}</td>
                  <td>{policyLabel(r.policy)}</td>
                  <td>
                    <span className={hasLogs ? "" : "text-ink-subtle"}>
                      {r.coverage.n_seeds_with_decisions} / {r.coverage.n_seeds}
                    </span>
                  </td>
                  <td>
                    {hasLogs ? (
                      <Link
                        href={`/agents/${encodeURIComponent(r.config_name)}/${seed}`}
                        className="text-accent hover:underline"
                      >
                        Watch →
                      </Link>
                    ) : (
                      <span className="text-ink-subtle">no logs</span>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
