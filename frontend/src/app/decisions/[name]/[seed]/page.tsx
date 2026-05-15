"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { ChevronDown, ChevronRight, Download } from "lucide-react";
import { use, useMemo, useState } from "react";
import { api } from "@/lib/api";

/**
 * Decision-log viewer for one (experiment, seed).
 *
 * Shows everything the simulator emitted to `decisions.jsonl`:
 *   - per-row table with broken-out columns for the most common fields
 *     (qty, arrives, threshold, etc.) so frequent values are scannable
 *     at a glance
 *   - expandable details: click a row to see the full structured payload
 *     pretty-printed
 *   - aggregate distribution cards at the top of the page (events per
 *     agent, events per action) so you understand the shape of the log
 *     before drilling
 *   - filter by agent / action / SKU / step range
 *   - download the filtered page as JSON
 */

export default function DecisionViewerPage({
  params,
}: {
  params: Promise<{ name: string; seed: string }>;
}) {
  const { name, seed } = use(params);
  const seedNum = Number(seed);

  const [agent, setAgent] = useState<string>("");
  const [action, setAction] = useState<string>("");
  const [sku, setSku] = useState<string>("");
  const [stepMin, setStepMin] = useState<string>("");
  const [stepMax, setStepMax] = useState<string>("");
  const [page, setPage] = useState(1);
  const [expandedRows, setExpandedRows] = useState<Set<number>>(new Set());
  const pageSize = 50;

  const meta = useQuery({
    queryKey: ["seed-meta", name, seedNum],
    queryFn: () => api.getSeed(name, seedNum),
  });
  const agents = useQuery({
    queryKey: ["decision-agents", name, seedNum],
    queryFn: () => api.listDecisionAgents(name, seedNum),
  });
  const skus = useQuery({
    queryKey: ["decision-skus", name, seedNum],
    queryFn: () => api.listSkusWithDecisions(name, seedNum),
  });
  const decisions = useQuery({
    queryKey: ["decisions", name, seedNum, { agent, action, sku, stepMin, stepMax, page }],
    queryFn: () =>
      api.getDecisions(name, seedNum, {
        agent: agent || undefined,
        action: action || undefined,
        sku: sku || undefined,
        step_min: stepMin ? Number(stepMin) : undefined,
        step_max: stepMax ? Number(stepMax) : undefined,
        page,
        page_size: pageSize,
      }),
  });

  const noDecisions = decisions.data && decisions.data.total === 0;

  // Aggregate distribution across the *unfiltered* event population
  // (the agents endpoint already returns (agent, action, count) tuples
  // for the whole log) so the summary cards stay meaningful regardless
  // of the active filter.
  const dist = useMemo(() => {
    const rows = agents.data ?? [];
    const byAgent = new Map<string, number>();
    const byAction = new Map<string, number>();
    let total = 0;
    for (const { agent, action, count } of rows) {
      byAgent.set(agent, (byAgent.get(agent) ?? 0) + count);
      byAction.set(action, (byAction.get(action) ?? 0) + count);
      total += count;
    }
    return {
      total,
      byAgent: [...byAgent.entries()].sort((a, b) => b[1] - a[1]),
      byAction: [...byAction.entries()].sort((a, b) => b[1] - a[1]),
    };
  }, [agents.data]);

  function toggleRow(id: number) {
    setExpandedRows((cur) => {
      const next = new Set(cur);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function downloadJson() {
    if (!decisions.data) return;
    const blob = new Blob(
      [JSON.stringify(decisions.data.items, null, 2)],
      { type: "application/json" },
    );
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${name}_seed${seedNum}_decisions_p${page}.json`;
    a.click();
    URL.revokeObjectURL(url);
  }

  // What fields appear most often in details_json? Used to choose which
  // columns to surface at the top level.
  const detailKeys = useMemo(() => {
    const counts = new Map<string, number>();
    for (const d of decisions.data?.items ?? []) {
      if (!d.details_json) continue;
      for (const k of Object.keys(d.details_json)) {
        counts.set(k, (counts.get(k) ?? 0) + 1);
      }
    }
    return [...counts.entries()]
      .sort((a, b) => b[1] - a[1])
      .slice(0, 3)
      .map(([k]) => k);
  }, [decisions.data]);

  return (
    <div className="space-y-6">
      <header className="space-y-1">
        <Link href="/decisions" className="text-sm">← Decision audit</Link>
        <h1 className="mt-1 font-mono text-2xl font-bold">{name} · seed {seedNum}</h1>
        {meta.data && (
          <p className="text-ink-muted">
            {meta.data.n_skus} SKUs · {meta.data.n_refits} refits ·
            {" "}{meta.data.n_global_drift_events} global drift events
            {meta.data.n_decisions > 0 && (
              <> · {meta.data.n_decisions.toLocaleString()} decision events</>
            )}
          </p>
        )}
        <p className="text-xs text-ink-subtle">
          Step-by-step ledger for one seed. Filter by agent, action type, SKU,
          or step range. Click any row to expand the full structured payload.
          Use this view to answer per-decision &quot;why&quot; questions
          (which forecast informed an order, when ADWIN fired and what it
          observed, why safety stock changed).
        </p>
      </header>

      {/* Empty state — softened copy, with a direct path to remedy. */}
      {noDecisions && (
        <div className="card space-y-2 border-amber-700 bg-amber-950/20 text-sm">
          <div className="font-semibold text-amber-300">
            No decision-log data on file for this seed.
          </div>
          <p className="text-ink-muted">
            This sweep was run before <code className="rounded bg-bg-elevated px-1 py-0.5 font-mono text-xs">MAS_EMIT_DECISIONS</code> was
            on by default, so only the summary metrics and timeseries are
            ingested. Aggregate numbers on the{" "}
            <Link href={`/experiments/${name}`} className="underline hover:text-ink">
              experiment detail page
            </Link>{" "}
            are unaffected.
          </p>
          <p className="text-ink-muted">
            To populate the audit trail for this configuration, relaunch it
            from the dashboard &mdash; the deployment&apos;s runner has the
            emit flag set, so any new sweep will land here with a full event
            log.
          </p>
          <div>
            <Link
              href={`/runs/new?config=${encodeURIComponent(name)}`}
              className="inline-flex items-center gap-1 rounded-md bg-accent px-3 py-1.5 text-xs font-semibold text-white hover:bg-accent-muted"
            >
              Launch {name} →
            </Link>
          </div>
        </div>
      )}

      {/* Distribution summary — only meaningful when the seed has data. */}
      {!noDecisions && dist.total > 0 && (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <DistCard title="Events by agent" entries={dist.byAgent} total={dist.total} />
          <DistCard title="Events by action" entries={dist.byAction} total={dist.total} />
        </div>
      )}

      {/* Filters */}
      <div className="card flex flex-wrap items-end gap-3">
        <FilterSelect
          label="Agent"
          value={agent}
          onChange={(v) => { setAgent(v); setPage(1); }}
          options={["", ...Array.from(new Set((agents.data ?? []).map((a) => a.agent)))]}
        />
        <FilterSelect
          label="Action"
          value={action}
          onChange={(v) => { setAction(v); setPage(1); }}
          options={["", ...Array.from(new Set(
            (agents.data ?? [])
              .filter((a) => !agent || a.agent === agent)
              .map((a) => a.action),
          ))]}
        />
        <div className="flex flex-col">
          <label className="metric-label">SKU</label>
          <input
            list="sku-list"
            value={sku}
            onChange={(e) => { setSku(e.target.value); setPage(1); }}
            placeholder="any SKU"
            className="mt-1 w-64 rounded-md border border-border bg-bg-elevated px-3 py-1.5 font-mono text-xs text-ink"
          />
          <datalist id="sku-list">
            {(skus.data ?? []).slice(0, 200).map((s) => (
              <option key={s.sku} value={s.sku}>{s.decisions} decisions</option>
            ))}
          </datalist>
        </div>
        <div className="flex flex-col">
          <label className="metric-label">Step ≥</label>
          <input
            type="number"
            value={stepMin}
            onChange={(e) => { setStepMin(e.target.value); setPage(1); }}
            className="mt-1 w-24 rounded-md border border-border bg-bg-elevated px-2 py-1.5 text-sm text-ink"
          />
        </div>
        <div className="flex flex-col">
          <label className="metric-label">Step ≤</label>
          <input
            type="number"
            value={stepMax}
            onChange={(e) => { setStepMax(e.target.value); setPage(1); }}
            className="mt-1 w-24 rounded-md border border-border bg-bg-elevated px-2 py-1.5 text-sm text-ink"
          />
        </div>
        <div className="ml-auto flex flex-col">
          <span className="metric-label">Export</span>
          <button
            onClick={downloadJson}
            disabled={!decisions.data || decisions.data.items.length === 0}
            className="mt-1 inline-flex items-center gap-1 rounded-md border border-border bg-bg-elevated px-3 py-1.5 text-xs hover:bg-bg-surface disabled:opacity-50"
          >
            <Download size={12} /> JSON (this page)
          </button>
        </div>
      </div>

      {/* Decisions table */}
      <div className="card overflow-hidden p-0">
        <table>
          <thead>
            <tr>
              <th className="w-6" />
              <th>Step</th>
              <th>Agent</th>
              <th>Action</th>
              <th>SKU</th>
              {detailKeys.map((k) => (
                <th key={k} className="text-right font-mono text-[10px] uppercase">
                  {k}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {decisions.data?.items.map((d) => {
              const isOpen = expandedRows.has(d.id);
              const details = (d.details_json ?? {}) as Record<string, unknown>;
              return (
                <>
                  <tr
                    key={d.id}
                    onClick={() => toggleRow(d.id)}
                    className="cursor-pointer hover:bg-bg-elevated"
                  >
                    <td>
                      {d.details_json ? (
                        isOpen ? (
                          <ChevronDown size={14} className="text-ink-muted" />
                        ) : (
                          <ChevronRight size={14} className="text-ink-muted" />
                        )
                      ) : null}
                    </td>
                    <td className="tabular-nums">{d.step}</td>
                    <td>{d.agent}</td>
                    <td>
                      <span className="rounded bg-bg-elevated px-2 py-0.5 text-xs font-mono">
                        {d.action}
                      </span>
                    </td>
                    <td className="font-mono text-xs">
                      {d.sku ? truncateSku(d.sku) : "—"}
                    </td>
                    {detailKeys.map((k) => (
                      <td key={k} className="text-right font-mono text-xs">
                        {formatDetailValue(details[k])}
                      </td>
                    ))}
                  </tr>
                  {isOpen && d.details_json && (
                    <tr key={`${d.id}-details`} className="bg-bg-elevated/40">
                      <td colSpan={5 + detailKeys.length} className="px-4 py-3">
                        <div className="space-y-2">
                          {d.sku && (
                            <div className="text-xs text-ink-muted">
                              <span className="text-ink-subtle">SKU: </span>
                              <span className="font-mono">{d.sku}</span>
                            </div>
                          )}
                          <pre className="overflow-x-auto rounded bg-bg-base p-3 font-mono text-xs text-ink">
{JSON.stringify(d.details_json, null, 2)}
                          </pre>
                        </div>
                      </td>
                    </tr>
                  )}
                </>
              );
            })}
          </tbody>
        </table>
        {decisions.data && (
          <div className="flex items-center justify-between border-t border-border px-4 py-2 text-xs text-ink-muted">
            <div>
              {decisions.data.total.toLocaleString()} decisions ·
              {" "}page {decisions.data.page} of{" "}
              {Math.max(1, Math.ceil(decisions.data.total / pageSize))}
              {(agent || action || sku || stepMin || stepMax) && (
                <span className="ml-2 text-ink-subtle">(filtered)</span>
              )}
            </div>
            <div className="flex gap-2">
              <button
                className="rounded border border-border px-2 py-1 disabled:opacity-50"
                disabled={page === 1}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
              >
                ← Prev
              </button>
              <button
                className="rounded border border-border px-2 py-1 disabled:opacity-50"
                disabled={!decisions.data || page * pageSize >= decisions.data.total}
                onClick={() => setPage((p) => p + 1)}
              >
                Next →
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// ─── Helpers ─────────────────────────────────────────────────────────

function FilterSelect({
  label, value, onChange, options,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  options: string[];
}) {
  return (
    <div className="flex flex-col">
      <label className="metric-label">{label}</label>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="mt-1 min-w-32 rounded-md border border-border bg-bg-elevated px-3 py-1.5 text-sm text-ink"
      >
        {options.map((o) => (
          <option key={o} value={o}>{o || "any"}</option>
        ))}
      </select>
    </div>
  );
}

function DistCard({
  title,
  entries,
  total,
}: {
  title: string;
  entries: [string, number][];
  total: number;
}) {
  return (
    <div className="card space-y-2 p-3">
      <div className="metric-label">{title}</div>
      <div className="space-y-1.5">
        {entries.map(([k, n]) => {
          const frac = total > 0 ? n / total : 0;
          return (
            <div key={k} className="space-y-0.5">
              <div className="flex justify-between text-xs">
                <span className="font-mono text-ink">{k}</span>
                <span className="tabular-nums text-ink-muted">
                  {n.toLocaleString()} ({(frac * 100).toFixed(1)}%)
                </span>
              </div>
              <div className="h-1 overflow-hidden rounded-full bg-bg-elevated">
                <div
                  className="h-1 rounded-full bg-accent"
                  style={{ width: `${frac * 100}%` }}
                />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function truncateSku(sku: string): string {
  if (sku.length <= 12) return sku;
  return `${sku.slice(0, 8)}…`;
}

function formatDetailValue(v: unknown): string {
  if (v === undefined || v === null) return "—";
  if (typeof v === "number") {
    return Number.isInteger(v) ? v.toString() : v.toFixed(3);
  }
  if (typeof v === "boolean") return v ? "true" : "false";
  if (typeof v === "string") return v.length > 16 ? `${v.slice(0, 14)}…` : v;
  // Arrays / objects — show as compact JSON, truncate if huge.
  const s = JSON.stringify(v);
  return s.length > 24 ? `${s.slice(0, 22)}…` : s;
}
