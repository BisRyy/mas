"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { api } from "@/lib/api";
import { timeAgo } from "@/lib/format";

const STATUS_COLOR: Record<string, string> = {
  queued: "text-amber-400",
  running: "text-sky-400",
  succeeded: "text-emerald-400",
  failed: "text-rose-400",
  cancelled: "text-ink-muted",
};

export default function RunsPage() {
  const runs = useQuery({
    queryKey: ["runs"],
    queryFn: api.listRuns,
    refetchInterval: 3000,
  });

  return (
    <div className="space-y-6">
      <header className="flex items-end justify-between">
        <div>
          <h1 className="text-2xl font-bold">Runs</h1>
          <p className="text-ink-muted">
            History of user-launched sweeps. Auto-refreshes every 3 s.
          </p>
        </div>
        <Link href="/runs/new" className="rounded-md bg-accent px-4 py-2 text-sm font-semibold text-white hover:bg-accent-muted">
          + Launch new run
        </Link>
      </header>

      <div className="card overflow-hidden p-0">
        <table>
          <thead>
            <tr>
              <th>Status</th>
              <th>Config</th>
              <th>Seeds</th>
              <th>Progress</th>
              <th>Started</th>
              <th>Open</th>
            </tr>
          </thead>
          <tbody>
            {runs.data?.length === 0 && (
              <tr>
                <td colSpan={6} className="py-6 text-center text-ink-muted">
                  No runs yet. Click <em>Launch new run</em> to start one.
                </td>
              </tr>
            )}
            {runs.data?.map((r) => (
              <tr key={r.id}>
                <td>
                  <span className={STATUS_COLOR[r.status] ?? ""}>{r.status}</span>
                </td>
                <td className="font-mono text-xs">{r.config_name}</td>
                <td>{r.seeds_csv}</td>
                <td>
                  <div className="flex items-center gap-2">
                    <div className="h-1.5 w-32 rounded-full bg-bg-elevated">
                      <div
                        className="h-1.5 rounded-full bg-accent"
                        style={{ width: `${r.progress_pct}%` }}
                      />
                    </div>
                    <span className="text-xs text-ink-muted">
                      {r.completed_seeds}/{r.total_seeds}
                    </span>
                  </div>
                </td>
                <td className="text-xs text-ink-muted">
                  {r.started_at ? timeAgo(r.started_at) : "—"}
                </td>
                <td>
                  <Link href={`/runs/${r.id}`} className="text-sm">
                    View →
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
