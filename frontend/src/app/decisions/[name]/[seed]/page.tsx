"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { use, useState } from "react";
import { api } from "@/lib/api";

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

  return (
    <div className="space-y-6">
      <header>
        <Link href="/decisions" className="text-sm">← Decision audit</Link>
        <h1 className="mt-1 font-mono text-2xl font-bold">{name} · seed {seedNum}</h1>
        {meta.data && (
          <p className="text-ink-muted">
            {meta.data.n_skus} SKUs · {meta.data.n_refits} refits ·
            {" "}{meta.data.n_global_drift_events} global drift events
          </p>
        )}
      </header>

      {noDecisions && (
        <div className="card border-amber-700 text-sm">
          <strong className="text-amber-400">No decision-log data on file for this seed.</strong>
          {" "}Re-run the sweep with
          <code className="mx-1 font-mono">MAS_EMIT_DECISIONS=1</code>
          to populate the audit trail. The summary metrics on the experiment detail
          page are unaffected.
        </div>
      )}

      <div className="card flex flex-wrap gap-3">
        <FilterSelect label="Agent" value={agent} onChange={(v) => { setAgent(v); setPage(1); }}
                      options={["", ...new Set((agents.data ?? []).map((a) => a.agent))]} />
        <FilterSelect label="Action" value={action} onChange={(v) => { setAction(v); setPage(1); }}
                      options={["", ...new Set((agents.data ?? []).filter((a) => !agent || a.agent === agent).map((a) => a.action))]} />
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
      </div>

      <div className="card overflow-hidden p-0">
        <table>
          <thead>
            <tr>
              <th>Step</th>
              <th>Agent</th>
              <th>Action</th>
              <th>SKU</th>
              <th>Details</th>
            </tr>
          </thead>
          <tbody>
            {decisions.data?.items.map((d) => (
              <tr key={d.id}>
                <td>{d.step}</td>
                <td>{d.agent}</td>
                <td>
                  <span className="rounded bg-bg-elevated px-2 py-0.5 text-xs font-mono">
                    {d.action}
                  </span>
                </td>
                <td className="font-mono text-xs">{d.sku ?? "—"}</td>
                <td className="font-mono text-xs text-ink-muted">
                  {d.details_json
                    ? JSON.stringify(d.details_json).slice(0, 120)
                    : "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {decisions.data && (
          <div className="flex items-center justify-between border-t border-border px-4 py-2 text-xs text-ink-muted">
            <div>
              {decisions.data.total.toLocaleString()} decisions ·
              {" "}page {decisions.data.page} of{" "}
              {Math.max(1, Math.ceil(decisions.data.total / pageSize))}
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

function FilterSelect({
  label, value, onChange, options,
}: { label: string; value: string; onChange: (v: string) => void; options: string[] }) {
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
