"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { use, useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";

interface Event {
  type: "snapshot" | "status" | "log" | "progress" | "ping" | "error";
  status?: string;
  line?: string;
  pct?: number;
  completed?: number;
  total?: number;
  log_tail?: string | null;
  progress_pct?: number;
  completed_seeds?: number;
  total_seeds?: number;
  error?: string;
  message?: string;
}

const STATUS_COLOR: Record<string, string> = {
  queued: "text-amber-400",
  running: "text-sky-400",
  succeeded: "text-emerald-400",
  failed: "text-rose-400",
};

export default function RunDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const [logs, setLogs] = useState<string[]>([]);
  const [pct, setPct] = useState(0);
  const [completed, setCompleted] = useState(0);
  const [total, setTotal] = useState(0);
  const [status, setStatus] = useState<string>("connecting");
  const [error, setError] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  const meta = useQuery({
    queryKey: ["run", id],
    queryFn: () => api.getRun(id),
    refetchInterval: status === "succeeded" || status === "failed" ? false : 5000,
  });

  useEffect(() => {
    const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
    const backendHost = process.env.NEXT_PUBLIC_API_URL
      ? new URL(process.env.NEXT_PUBLIC_API_URL).host
      : window.location.host;
    const ws = new WebSocket(`${proto}//${backendHost}/api/runs/${id}/stream`);
    wsRef.current = ws;

    ws.onmessage = (evt) => {
      const m = JSON.parse(evt.data) as Event;
      if (m.type === "snapshot") {
        setStatus(m.status ?? "unknown");
        setPct(m.progress_pct ?? 0);
        setCompleted(m.completed_seeds ?? 0);
        setTotal(m.total_seeds ?? 0);
        if (m.log_tail) setLogs(m.log_tail.split("\n"));
        if (m.error) setError(m.error);
      } else if (m.type === "status") {
        setStatus(m.status ?? status);
        if (m.error) setError(m.error);
      } else if (m.type === "progress") {
        setPct(m.pct ?? pct);
        setCompleted(m.completed ?? completed);
        setTotal(m.total ?? total);
      } else if (m.type === "log" && m.line) {
        setLogs((cur) => [...cur, m.line!].slice(-500));
      } else if (m.type === "error" && m.message) {
        setError(m.message);
      }
    };
    ws.onerror = () => setError("WebSocket connection error");

    return () => ws.close();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  return (
    <div className="space-y-6">
      <header>
        <Link href="/runs" className="text-sm">← All runs</Link>
        <h1 className="mt-1 font-mono text-2xl font-bold">Run {id.slice(0, 8)}…</h1>
        {meta.data && (
          <p className="text-ink-muted">
            <span className="font-mono">{meta.data.config_name}</span> · seeds {meta.data.seeds_csv}
          </p>
        )}
      </header>

      <div className="card grid grid-cols-2 gap-4 md:grid-cols-4">
        <div>
          <div className="metric-label">Status</div>
          <div className={`text-xl font-semibold ${STATUS_COLOR[status] ?? ""}`}>
            {status}
          </div>
        </div>
        <div>
          <div className="metric-label">Progress</div>
          <div className="text-xl font-semibold">{pct.toFixed(1)}%</div>
        </div>
        <div>
          <div className="metric-label">Completed</div>
          <div className="text-xl font-semibold">{completed} / {total}</div>
        </div>
        <div>
          <div className="metric-label">Job ID</div>
          <div className="font-mono text-xs">{id}</div>
        </div>
      </div>

      <div className="h-2 w-full overflow-hidden rounded-full bg-bg-elevated">
        <div
          className="h-2 rounded-full bg-accent transition-all"
          style={{ width: `${pct}%` }}
        />
      </div>

      {error && (
        <div className="card border-rose-700 bg-rose-950/30 text-sm text-rose-300">
          {error}
        </div>
      )}

      <section className="card">
        <h2 className="mb-3 text-sm font-semibold">Live log</h2>
        <pre className="max-h-96 overflow-auto whitespace-pre-wrap rounded-md bg-bg-elevated p-3 font-mono text-xs leading-relaxed text-ink-muted">
          {logs.length === 0 ? "(waiting for output…)" : logs.join("\n")}
        </pre>
      </section>
    </div>
  );
}
