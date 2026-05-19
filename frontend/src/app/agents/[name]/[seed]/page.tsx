"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { use, useEffect, useMemo, useState, useRef } from "react";
import { ChevronLeft, Pause, Play, SkipBack, SkipForward, RotateCcw } from "lucide-react";
import { api, type DecisionEntry } from "@/lib/api";
import { AgentDiagram } from "@/components/AgentDiagram";

/**
 * Live Agent Activity — step-by-step playback of a seed run.
 *
 * Reuses the persisted `decisions.jsonl` log for an (experiment, seed)
 * pair. The play-back UI lets the reader scrub through simulation steps
 * and see, on each step, which agents acted, what messages flowed
 * between them, and the resulting state (current on-hand inventory,
 * pending POs, drift events).
 *
 * Three concerns are separated:
 *   1. Step counter + playback controls (this file)
 *   2. The 5-agent diagram with animated message arrows (AgentDiagram)
 *   3. The recent-activity feed at the bottom (this file)
 */
export default function AgentLivePage({
  params,
}: {
  params: Promise<{ name: string; seed: string }>;
}) {
  const { name, seed } = use(params);
  const seedNum = Number(seed);

  // Step playback state -----------------------------------------------------
  const [step, setStep] = useState<number | null>(null);
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState(1); // 1x = 500ms/step; 2/5/10x scale that
  const playTimer = useRef<ReturnType<typeof setInterval> | null>(null);

  // Seed metadata to know step range
  const seedMeta = useQuery({
    queryKey: ["agents-seed", name, seedNum],
    queryFn: () => api.getSeed(name, seedNum),
  });

  // First page of decisions to find the min step (warm-up window end)
  const firstPage = useQuery({
    queryKey: ["agents-first", name, seedNum],
    queryFn: () =>
      api.getDecisions(name, seedNum, { page: 1, page_size: 1 }),
  });

  // Total decision count
  const stats = useQuery({
    queryKey: ["agents-stats", name, seedNum],
    queryFn: () => api.listDecisionAgents(name, seedNum),
  });

  const minStep = firstPage.data?.items[0]?.step ?? 90;
  // n_steps is on the seed summary; we don't fetch it directly here,
  // instead infer max from seed metadata if available.
  const maxStep = useMemo(() => {
    const ns = seedMeta.data?.summary_json as { n_steps?: number } | null | undefined;
    return minStep + (ns?.n_steps ?? 504) - 1;
  }, [seedMeta.data, minStep]);

  // Initialise step at the first available step
  useEffect(() => {
    if (step === null && firstPage.data?.items[0]) {
      setStep(firstPage.data.items[0].step);
    }
  }, [firstPage.data, step]);

  // Decisions for the current step (and a small look-back for context)
  const currentDecisions = useQuery({
    queryKey: ["agents-step", name, seedNum, step],
    queryFn: () =>
      step !== null
        ? api.getDecisions(name, seedNum, {
            step_min: step,
            step_max: step,
            page_size: 500,
          })
        : Promise.resolve(null),
    enabled: step !== null,
  });

  // Playback loop -----------------------------------------------------------
  useEffect(() => {
    if (!playing) {
      if (playTimer.current) {
        clearInterval(playTimer.current);
        playTimer.current = null;
      }
      return;
    }
    const intervalMs = Math.max(80, 600 / speed);
    playTimer.current = setInterval(() => {
      setStep((s) => {
        if (s === null) return s;
        if (s >= maxStep) {
          setPlaying(false);
          return s;
        }
        return s + 1;
      });
    }, intervalMs);
    return () => {
      if (playTimer.current) {
        clearInterval(playTimer.current);
        playTimer.current = null;
      }
    };
  }, [playing, speed, maxStep]);

  // Derived: agent counts + most-recent action per agent
  const agentSnapshots = useMemo(() => {
    const items = currentDecisions.data?.items ?? [];
    const map: Record<string, DecisionEntry[]> = {
      forecaster: [],
      monitor: [],
      replenisher: [],
      supplier: [],
      analytics: [],
    };
    for (const d of items) {
      if (map[d.agent]) map[d.agent].push(d);
    }
    return map;
  }, [currentDecisions.data]);

  // Cumulative metrics for the current step
  const snapshotMetrics = useMemo(() => {
    const a = agentSnapshots.analytics.find((d) => d.action === "metrics_snapshot");
    if (!a || !a.details_json) return null;
    return a.details_json as Record<string, number>;
  }, [agentSnapshots]);

  // Loading / error guards --------------------------------------------------
  if (firstPage.isError || seedMeta.isError) {
    return (
      <div className="card p-8 text-rose-400">
        Could not load decision data for seed {seedNum} of{" "}
        <code className="font-mono">{name}</code>. The run may not have been
        captured with decision logging.
      </div>
    );
  }
  if (firstPage.isLoading || step === null) {
    return (
      <div className="space-y-4">
        <header className="space-y-1">
          <h1 className="text-2xl font-bold">Live Agent Activity</h1>
          <p className="text-ink-muted text-sm">Loading decision log…</p>
        </header>
      </div>
    );
  }

  const total_decisions = stats.data?.reduce((s, x) => s + x.count, 0) ?? 0;

  return (
    <div className="space-y-6">
      <header className="space-y-1">
        <Link
          href="/agents"
          className="inline-flex items-center gap-1 text-xs text-ink-muted hover:text-ink"
        >
          <ChevronLeft size={14} /> Back to seed picker
        </Link>
        <h1 className="text-2xl font-bold">
          Live Agent Activity
        </h1>
        <p className="text-ink-muted text-sm">
          Replaying the 5-agent MAS for{" "}
          <code className="font-mono text-xs">{name}</code> / seed{" "}
          <span className="font-mono">{seedNum}</span>{" "}
          ({total_decisions.toLocaleString()} decisions logged across steps{" "}
          {minStep} – {maxStep}).
        </p>
      </header>

      {/* Playback controls --------------------------------------------- */}
      <div className="card space-y-3">
        <div className="flex flex-wrap items-center gap-3">
          <div className="text-sm text-ink-muted">
            Step{" "}
            <span className="font-mono text-base text-ink">{step}</span> /{" "}
            <span className="font-mono">{maxStep}</span>
          </div>

          <div className="flex-1" />

          <div className="flex items-center gap-1">
            <button
              onClick={() => setStep(minStep)}
              className="p-2 rounded hover:bg-bg-elevated text-ink-muted hover:text-ink"
              title="Reset to start"
            >
              <RotateCcw size={16} />
            </button>
            <button
              onClick={() => setStep((s) => Math.max(minStep, (s ?? minStep) - 1))}
              className="p-2 rounded hover:bg-bg-elevated text-ink-muted hover:text-ink"
              title="Step back"
            >
              <SkipBack size={16} />
            </button>
            <button
              onClick={() => setPlaying((p) => !p)}
              className="p-2 rounded bg-accent text-white hover:bg-accent-muted"
              title={playing ? "Pause" : "Play"}
            >
              {playing ? <Pause size={16} /> : <Play size={16} />}
            </button>
            <button
              onClick={() => setStep((s) => Math.min(maxStep, (s ?? minStep) + 1))}
              className="p-2 rounded hover:bg-bg-elevated text-ink-muted hover:text-ink"
              title="Step forward"
            >
              <SkipForward size={16} />
            </button>
          </div>

          <div className="flex items-center gap-1 text-xs">
            {[1, 2, 5, 10].map((x) => (
              <button
                key={x}
                onClick={() => setSpeed(x)}
                className={`px-2 py-1 rounded ${
                  speed === x
                    ? "bg-accent text-white"
                    : "bg-bg-elevated text-ink-muted hover:text-ink"
                }`}
              >
                {x}×
              </button>
            ))}
          </div>
        </div>

        <input
          type="range"
          min={minStep}
          max={maxStep}
          value={step}
          onChange={(e) => setStep(Number(e.target.value))}
          className="w-full accent-accent"
        />
      </div>

      {/* Agent diagram ---------------------------------------------------- */}
      <AgentDiagram
        decisions={currentDecisions.data?.items ?? []}
        loading={currentDecisions.isLoading}
        snapshotMetrics={snapshotMetrics}
      />

      {/* Recent activity feed -------------------------------------------- */}
      <div className="card space-y-2 p-0 overflow-hidden">
        <div className="border-b border-border px-4 py-2 text-sm font-semibold">
          Step {step} activity ({currentDecisions.data?.items.length ?? 0} events)
        </div>
        {currentDecisions.isLoading && (
          <div className="px-4 py-3 text-sm text-ink-muted">Loading…</div>
        )}
        <div className="max-h-[400px] overflow-y-auto">
          <table>
            <thead>
              <tr>
                <th>Agent</th>
                <th>Action</th>
                <th>SKU</th>
                <th>Details</th>
              </tr>
            </thead>
            <tbody>
              {(currentDecisions.data?.items ?? []).map((d) => (
                <tr key={d.id}>
                  <td>
                    <AgentBadge name={d.agent} />
                  </td>
                  <td className="font-mono text-xs">{d.action}</td>
                  <td className="font-mono text-xs text-ink-muted">
                    {d.sku ? d.sku.slice(0, 10) + "…" : "—"}
                  </td>
                  <td className="font-mono text-xs text-ink-muted truncate max-w-md">
                    {formatDetails(d.details_json)}
                  </td>
                </tr>
              ))}
              {(currentDecisions.data?.items ?? []).length === 0 &&
                !currentDecisions.isLoading && (
                  <tr>
                    <td colSpan={4} className="text-center text-ink-muted py-6">
                      No agent activity on step {step}.
                    </td>
                  </tr>
                )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

// ----------------------------------------------------------------------------
const AGENT_COLORS: Record<string, string> = {
  forecaster: "bg-purple-500/20 text-purple-300 border-purple-500/40",
  monitor: "bg-sky-500/20 text-sky-300 border-sky-500/40",
  replenisher: "bg-amber-500/20 text-amber-300 border-amber-500/40",
  supplier: "bg-emerald-500/20 text-emerald-300 border-emerald-500/40",
  analytics: "bg-rose-500/20 text-rose-300 border-rose-500/40",
};

function AgentBadge({ name }: { name: string }) {
  const cls = AGENT_COLORS[name] ?? "bg-bg-elevated text-ink";
  return (
    <span
      className={`inline-block px-2 py-0.5 rounded text-[10px] uppercase tracking-wider border ${cls}`}
    >
      {name}
    </span>
  );
}

function formatDetails(d: unknown): string {
  if (!d || typeof d !== "object") return "";
  const obj = d as Record<string, unknown>;
  return Object.entries(obj)
    .filter(([k]) => k !== "step" && k !== "agent" && k !== "action" && k !== "sku")
    .map(([k, v]) => `${k}=${typeof v === "number" ? +Number(v).toFixed(2) : v}`)
    .join(" · ");
}
