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


/**
 * Build the WebSocket URL for /api/runs/{id}/stream.
 *
 * Avoids two failure modes:
 *   1. Local dev: Next.js's HTTP rewrites do NOT proxy WS upgrades, so
 *      we can't go through :3000. Use NEXT_PUBLIC_API_URL (set in
 *      .env.local) which points at the backend on :8000.
 *   2. Production behind HTTPS: if the page is https:// then the WS
 *      must be wss:// or the browser blocks it as mixed content.
 *
 * If NEXT_PUBLIC_API_URL is unset we fall back to a heuristic: when the
 * page is on :3000 the backend is probably on :8000 of the same host.
 */
function buildWebSocketUrl(jobId: string): string {
  const explicit = process.env.NEXT_PUBLIC_API_URL;
  if (explicit) {
    const url = new URL(explicit);
    const proto = url.protocol === "https:" ? "wss:" : "ws:";
    return `${proto}//${url.host}/api/runs/${jobId}/stream`;
  }
  const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
  let host = window.location.host;
  if (host.endsWith(":3000")) {
    host = host.replace(":3000", ":8000");
  }
  return `${proto}//${host}/api/runs/${jobId}/stream`;
}


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
  const [transport, setTransport] = useState<"ws" | "polling">("ws");
  const wsRef = useRef<WebSocket | null>(null);

  const isTerminal = status === "succeeded" || status === "failed";

  // HTTP polling — runs always at slow cadence, faster when we've fallen
  // back from WebSocket. Drives state updates either way so the UI keeps
  // working without WS.
  const poll = useQuery({
    queryKey: ["run", id, transport],
    queryFn: () => api.getRun(id),
    refetchInterval: isTerminal ? false : transport === "polling" ? 2000 : 5000,
  });

  useEffect(() => {
    if (!poll.data) return;
    setStatus(poll.data.status);
    setPct(poll.data.progress_pct);
    setCompleted(poll.data.completed_seeds);
    setTotal(poll.data.total_seeds);
    if (poll.data.error) setError(poll.data.error);
    if (poll.data.log_tail) setLogs(poll.data.log_tail.split("\n"));
  }, [poll.data]);

  useEffect(() => {
    if (transport !== "ws") return;

    const wsUrl = buildWebSocketUrl(id);
    let ws: WebSocket;
    try {
      ws = new WebSocket(wsUrl);
    } catch (e) {
      setTransport("polling");
      setError(
        `WebSocket construction failed (${(e as Error).message}); ` +
        `falling back to HTTP polling.`,
      );
      return;
    }
    wsRef.current = ws;

    let opened = false;

    ws.onopen = () => {
      opened = true;
      setError(null);
    };

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
        if (m.status) setStatus(m.status);
        if (m.error) setError(m.error);
      } else if (m.type === "progress") {
        if (m.pct !== undefined) setPct(m.pct);
        if (m.completed !== undefined) setCompleted(m.completed);
        if (m.total !== undefined) setTotal(m.total);
      } else if (m.type === "log" && m.line) {
        setLogs((cur) => [...cur, m.line!].slice(-500));
      } else if (m.type === "error" && m.message) {
        setError(m.message);
      }
    };

    ws.onerror = () => {
      if (!opened) {
        setTransport("polling");
        setError(
          `Live WebSocket unavailable on ${wsUrl}. Falling back to HTTP polling.\n` +
          `Hint: ensure NEXT_PUBLIC_API_URL points at the backend host:port. ` +
          `Current: ${process.env.NEXT_PUBLIC_API_URL ?? "<unset>"}`,
        );
      }
    };

    ws.onclose = () => {
      if (!opened) {
        setTransport("polling");
      } else if (!isTerminal) {
        setTransport("polling");
        setError("Live connection dropped — switched to HTTP polling.");
      }
    };

    return () => {
      try { ws.close(); } catch {}
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id, transport]);

  return (
    <div className="space-y-6">
      <header className="space-y-1">
        <Link href="/runs" className="text-sm">← All runs</Link>
        <h1 className="mt-1 font-mono text-2xl font-bold">Run {id.slice(0, 8)}…</h1>
        {poll.data && (
          <p className="text-ink-muted">
            <span className="font-mono">{poll.data.config_name}</span> · seeds {poll.data.seeds_csv}
            {" · "}
            <span className="text-xs uppercase tracking-wider">
              transport: {transport}
              {transport === "polling" && " (2 s)"}
            </span>
          </p>
        )}
        <p className="text-xs text-ink-subtle">
          Live progress for one sweep job. Status, completed-seeds counter,
          and the worker&apos;s stdout/stderr stream in real time over
          WebSocket when available; if the WS upgrade fails (e.g. behind a
          proxy that strips it) the page falls back to 2&nbsp;s HTTP polling
          automatically. When the job lands in <em>succeeded</em>, its results
          ingest into the catalog and the experiment becomes browsable on
          every other page.
        </p>
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
        <div className="card border-amber-700 bg-amber-950/30 text-sm text-amber-300 whitespace-pre-line">
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
