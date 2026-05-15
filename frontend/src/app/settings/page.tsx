"use client";

/**
 * System diagnostics — there is no "settings" to mutate here. All knobs
 * are backend env vars; this page is read-only except for the
 * "Re-ingest now" action which surfaces the existing /api/_meta/reingest
 * endpoint (useful when sweep outputs land on the volume out-of-band).
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { api } from "@/lib/api";

export default function SettingsPage() {
  const qc = useQueryClient();
  const status = useQuery({
    queryKey: ["meta-status"],
    queryFn: api.systemStatus,
    refetchInterval: 10_000,
  });

  const [reingestMsg, setReingestMsg] = useState<string | null>(null);
  const reingest = useMutation({
    mutationFn: api.reingest,
    onSuccess: (r) => {
      setReingestMsg(
        `Ingested ${r.experiments} experiments · ${r.seeds} seeds · ${r.decisions} decisions`,
      );
      qc.invalidateQueries({ queryKey: ["meta-status"] });
      qc.invalidateQueries({ queryKey: ["experiments"] });
    },
    onError: (e: Error) => setReingestMsg(`Failed: ${e.message}`),
  });

  if (status.isLoading) {
    return <p className="text-ink-muted">Loading system status…</p>;
  }
  if (status.error || !status.data) {
    return (
      <div className="card border-rose-700 bg-rose-950/30 text-sm text-rose-300">
        Couldn&apos;t load system status. The backend may be unreachable.
        <div className="mt-2 font-mono text-xs">{String(status.error)}</div>
      </div>
    );
  }

  const s = status.data;
  const browserApi = process.env.NEXT_PUBLIC_API_URL ?? "(unset — relative)";

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-bold">System status</h1>
        <p className="text-ink-muted">
          Read-only diagnostics for the deployed stack. Configuration knobs
          are backend env vars; edit them in your deploy platform.
        </p>
      </header>

      {/* ─── API / Connection ──────────────────────────────────────────── */}
      <Section title="API">
        <Row label="Backend version" value={s.api.version} mono />
        <Row label="Uptime" value={formatDuration(s.api.uptime_seconds)} />
        <Row
          label="Started at"
          value={new Date(s.api.process_started_at_unix * 1000).toLocaleString()}
        />
        <Row label="Browser → API URL (WebSocket)" value={browserApi} mono />
      </Section>

      {/* ─── Database ──────────────────────────────────────────────────── */}
      <Section
        title="Database"
        actions={
          <button
            className="rounded-md bg-accent px-3 py-1.5 text-xs font-semibold text-white hover:bg-accent-muted disabled:opacity-60"
            onClick={() => reingest.mutate()}
            disabled={reingest.isPending}
          >
            {reingest.isPending ? "Re-ingesting…" : "Re-ingest results/"}
          </button>
        }
      >
        <Row label="URL" value={s.database.url_redacted} mono />
        <Row
          label="Last ingest"
          value={
            s.database.last_ingest_at
              ? `${new Date(s.database.last_ingest_at).toLocaleString()} (${
                  timeSince(s.database.last_ingest_at)
                } ago)`
              : "never"
          }
        />
        <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
          <Counter label="Experiments" value={s.database.counts.experiments} />
          <Counter label="Seeds" value={s.database.counts.seeds} />
          <Counter label="Decisions" value={s.database.counts.decisions} />
          <Counter label="Jobs" value={s.database.counts.jobs} />
        </div>
        {reingestMsg && (
          <div className="text-sm text-ink-muted">{reingestMsg}</div>
        )}
      </Section>

      {/* ─── Filesystem ────────────────────────────────────────────────── */}
      <Section title="Filesystem">
        <Row label="Project root" value={s.filesystem.project_root} mono />
        <Row label="Results dir" value={s.filesystem.results_dir} mono />
        <Row
          label="Results size on disk"
          value={formatBytes(s.filesystem.results_size_bytes)}
        />
        <Row label="Configs dir" value={s.filesystem.configs_dir} mono />
      </Section>

      {/* ─── Queue ─────────────────────────────────────────────────────── */}
      <Section title="Run queue">
        <div className="grid grid-cols-3 gap-3">
          <Counter label="Active jobs" value={s.queue.current_jobs} />
          <Counter label="Max queued" value={s.queue.max_queued} />
          <Counter label="Max concurrent" value={s.queue.max_concurrent} />
        </div>
      </Section>

      {/* ─── Policy ────────────────────────────────────────────────────── */}
      <Section title="Policy">
        <Row
          label="Allow run launch"
          value={
            <span
              className={
                s.policy.allow_run_launch ? "text-emerald-400" : "text-rose-400"
              }
            >
              {s.policy.allow_run_launch ? "enabled" : "disabled (read-only)"}
            </span>
          }
        />
        <Row
          label="CORS origins"
          value={
            <div className="space-y-0.5 font-mono text-xs">
              {s.policy.cors_origins.length === 0 ? (
                <span className="text-ink-muted">(none)</span>
              ) : (
                s.policy.cors_origins.map((o) => <div key={o}>{o}</div>)
              )}
            </div>
          }
        />
      </Section>
    </div>
  );
}

// ─── Layout helpers ────────────────────────────────────────────────────

function Section({
  title,
  children,
  actions,
}: {
  title: string;
  children: React.ReactNode;
  actions?: React.ReactNode;
}) {
  return (
    <section className="card space-y-3">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold">{title}</h2>
        {actions}
      </div>
      <div className="space-y-2">{children}</div>
    </section>
  );
}

function Row({
  label,
  value,
  mono = false,
}: {
  label: string;
  value: React.ReactNode;
  mono?: boolean;
}) {
  return (
    <div className="grid grid-cols-[180px_1fr] gap-3 text-sm">
      <div className="text-ink-muted">{label}</div>
      <div className={mono ? "font-mono text-xs break-all" : ""}>{value}</div>
    </div>
  );
}

function Counter({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-md bg-bg-elevated px-3 py-2">
      <div className="metric-label">{label}</div>
      <div className="text-xl font-semibold tabular-nums">
        {value.toLocaleString()}
      </div>
    </div>
  );
}

// ─── Formatters ────────────────────────────────────────────────────────

function formatBytes(n: number): string {
  if (n < 1024) return `${n} B`;
  if (n < 1024 ** 2) return `${(n / 1024).toFixed(1)} KB`;
  if (n < 1024 ** 3) return `${(n / 1024 ** 2).toFixed(1)} MB`;
  return `${(n / 1024 ** 3).toFixed(2)} GB`;
}

function formatDuration(seconds: number): string {
  const d = Math.floor(seconds / 86_400);
  const h = Math.floor((seconds % 86_400) / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = seconds % 60;
  const parts: string[] = [];
  if (d) parts.push(`${d}d`);
  if (h) parts.push(`${h}h`);
  if (m) parts.push(`${m}m`);
  parts.push(`${s}s`);
  return parts.join(" ");
}

function timeSince(iso: string): string {
  const delta = Math.floor((Date.now() - new Date(iso).getTime()) / 1000);
  if (delta < 60) return `${delta}s`;
  if (delta < 3600) return `${Math.floor(delta / 60)}m`;
  if (delta < 86_400) return `${Math.floor(delta / 3600)}h`;
  return `${Math.floor(delta / 86_400)}d`;
}
