"use client";

import { useMemo } from "react";
import type { DecisionEntry } from "@/lib/api";

/**
 * Visual diagram of the 5-agent MAS for a single simulation step.
 *
 * Layout (mirrors the architecture figure in §3.1 of the thesis):
 *
 *      ┌────────────────────┐
 *      │  Forecasting       │
 *      │  Agent             │
 *      └─────────┬──────────┘
 *                │ forecasts μ, σ
 *                ▼
 *      ┌──────────────────┐         ┌──────────────────┐
 *      │  Inventory       │ stock   │  Replenishment   │
 *      │  Monitor         │────────►│  Agent           │
 *      └──────────────────┘         └─────────┬────────┘
 *                ▲                            │ reorder qty
 *                │ deliveries                 ▼
 *      ┌──────────────────┐         ┌──────────────────┐
 *      │  Supplier        │◄────────│  (places PO)     │
 *      │  Agent           │  po     │                  │
 *      └──────────────────┘         └──────────────────┘
 *                                            │
 *                                            ▼
 *                                  ┌──────────────────┐
 *                                  │  Analytics       │
 *                                  │  Agent           │
 *                                  └──────────────────┘
 *
 * Each agent box shows: the agent name, the most recent action it
 * took this step (e.g. "refit ses · 18 SKUs"), and any drift /
 * stockout indicator. Edges between agents highlight (animate) when a
 * message of that type was emitted on the current step.
 */

interface Props {
  decisions: DecisionEntry[];
  loading?: boolean;
  snapshotMetrics?: Record<string, number> | null;
}

interface AgentStat {
  count: number;
  actions: Record<string, number>;
  latestSummary: string;
}

function summarize(agentDecisions: DecisionEntry[]): AgentStat {
  const actions: Record<string, number> = {};
  for (const d of agentDecisions) {
    actions[d.action] = (actions[d.action] ?? 0) + 1;
  }
  // Pick a one-line summary of what this agent did this step.
  let summary = "idle";
  if (agentDecisions.length > 0) {
    const dominant = Object.entries(actions).sort((a, b) => b[1] - a[1])[0];
    summary = `${dominant[0]} × ${dominant[1]}`;
  }
  return {
    count: agentDecisions.length,
    actions,
    latestSummary: summary,
  };
}

export function AgentDiagram({ decisions, loading, snapshotMetrics }: Props) {
  const byAgent = useMemo(() => {
    const map: Record<string, DecisionEntry[]> = {
      forecaster: [],
      monitor: [],
      replenisher: [],
      supplier: [],
      analytics: [],
    };
    for (const d of decisions) {
      if (map[d.agent]) map[d.agent].push(d);
    }
    return {
      forecaster: summarize(map.forecaster),
      monitor: summarize(map.monitor),
      replenisher: summarize(map.replenisher),
      supplier: summarize(map.supplier),
      analytics: summarize(map.analytics),
    };
  }, [decisions]);

  // Edge activity: did any reorder fire this step? Any PO placed? Any drift?
  const edgeActive = useMemo(() => {
    return {
      forecastToReplenisher: byAgent.forecaster.count > 0,
      monitorToReplenisher: byAgent.monitor.actions.fulfill > 0,
      replenisherToSupplier: byAgent.replenisher.actions.reorder > 0,
      supplierToMonitor: byAgent.supplier.actions.po_delivered > 0,
      allToAnalytics: byAgent.analytics.count > 0,
      analyticsDrift:
        (byAgent.analytics.actions.drift_detected ?? 0) +
          (byAgent.analytics.actions.global_drift_detected ?? 0) >
        0,
    };
  }, [byAgent]);

  return (
    <div className="card space-y-4">
      <div className="flex items-baseline justify-between">
        <h2 className="text-sm font-semibold">Multi-Agent System</h2>
        <div className="text-xs text-ink-muted">
          {loading
            ? "loading…"
            : `${decisions.length} agent action${decisions.length === 1 ? "" : "s"} this step`}
        </div>
      </div>

      {/* Diagram grid -- inline 5-agent layout */}
      <div className="relative">
        <div className="grid grid-cols-3 gap-4">
          {/* Row 1: Forecasting */}
          <div className="col-span-3 flex justify-center">
            <AgentCard
              name="Forecasting"
              agentKey="forecaster"
              stat={byAgent.forecaster}
              hint="Tier ladder + ADWIN"
            />
          </div>

          {/* Connectors row 1 -> row 2 */}
          <div className="col-span-3 flex justify-center text-ink-muted text-xs">
            <Arrow active={edgeActive.forecastToReplenisher} label="μ, σ" direction="down" />
          </div>

          {/* Row 2: Monitor – Replenisher – Supplier */}
          <AgentCard
            name="Inventory Monitor"
            agentKey="monitor"
            stat={byAgent.monitor}
            hint="Stock fulfilment"
          />
          <div className="flex flex-col items-center">
            <Arrow
              active={edgeActive.monitorToReplenisher}
              label="on_hand"
              direction="right"
            />
            <AgentCard
              name="Replenishment"
              agentKey="replenisher"
              stat={byAgent.replenisher}
              hint="(s, S) decisions"
            />
            <Arrow
              active={edgeActive.replenisherToSupplier}
              label="reorder qty"
              direction="right"
            />
          </div>
          <AgentCard
            name="Supplier"
            agentKey="supplier"
            stat={byAgent.supplier}
            hint="PO + lead time"
          />

          {/* Connector row 2 -> row 3 (supplier delivers back to monitor) */}
          <div className="col-span-3 flex justify-between items-center px-12 text-ink-muted text-xs">
            <Arrow
              active={edgeActive.supplierToMonitor}
              label="deliveries (return path)"
              direction="up-left"
            />
            <Arrow active={edgeActive.allToAnalytics} label="snapshot" direction="down" />
          </div>

          {/* Row 3: Analytics (right-side) */}
          <div className="col-span-3 flex justify-center">
            <AgentCard
              name="Analytics"
              agentKey="analytics"
              stat={byAgent.analytics}
              hint="Metrics + drift detection"
              alarm={edgeActive.analyticsDrift}
            />
          </div>
        </div>
      </div>

      {/* Snapshot strip — system-level KPIs at this step */}
      {snapshotMetrics && (
        <div className="border-t border-border pt-3 grid grid-cols-4 gap-3 text-xs">
          <Kpi
            label="Total on-hand"
            value={snapshotMetrics.total_on_hand?.toLocaleString() ?? "—"}
            unit="units"
          />
          <Kpi
            label="Stockout SKUs"
            value={snapshotMetrics.stockout_skus_step?.toString() ?? "0"}
            unit="this step"
            danger={(snapshotMetrics.stockout_skus_step ?? 0) > 0}
          />
          <Kpi
            label="Reorders"
            value={byAgent.replenisher.actions.reorder?.toString() ?? "0"}
            unit="issued"
          />
          <Kpi
            label="POs delivered"
            value={byAgent.supplier.actions.po_delivered?.toString() ?? "0"}
            unit="received"
          />
        </div>
      )}
    </div>
  );
}

// ----------------------------------------------------------------------------
const AGENT_STYLE: Record<
  string,
  { ring: string; tag: string; iconText: string }
> = {
  forecaster: {
    ring: "border-purple-500/40 shadow-purple-500/20",
    tag: "bg-purple-500/10 text-purple-300",
    iconText: "F",
  },
  monitor: {
    ring: "border-sky-500/40 shadow-sky-500/20",
    tag: "bg-sky-500/10 text-sky-300",
    iconText: "M",
  },
  replenisher: {
    ring: "border-amber-500/40 shadow-amber-500/20",
    tag: "bg-amber-500/10 text-amber-300",
    iconText: "R",
  },
  supplier: {
    ring: "border-emerald-500/40 shadow-emerald-500/20",
    tag: "bg-emerald-500/10 text-emerald-300",
    iconText: "S",
  },
  analytics: {
    ring: "border-rose-500/40 shadow-rose-500/20",
    tag: "bg-rose-500/10 text-rose-300",
    iconText: "A",
  },
};

interface AgentCardProps {
  name: string;
  agentKey: string;
  stat: AgentStat;
  hint?: string;
  alarm?: boolean;
}

function AgentCard({ name, agentKey, stat, hint, alarm }: AgentCardProps) {
  const style = AGENT_STYLE[agentKey] ?? AGENT_STYLE.forecaster;
  const active = stat.count > 0;
  return (
    <div
      className={[
        "relative rounded-lg border-2 p-3 transition-all w-full max-w-[230px]",
        style.ring,
        active
          ? "shadow-lg bg-bg-elevated"
          : "opacity-60 bg-bg-surface",
        alarm && "animate-pulse ring-2 ring-rose-500/60",
      ]
        .filter(Boolean)
        .join(" ")}
    >
      <div className="flex items-center gap-2 mb-2">
        <div
          className={`flex items-center justify-center w-6 h-6 rounded-full text-xs font-bold ${style.tag}`}
        >
          {style.iconText}
        </div>
        <div className="font-semibold text-sm">{name}</div>
        {active && (
          <span className="ml-auto text-[10px] text-emerald-400">●</span>
        )}
      </div>
      <div className="text-xs text-ink-muted leading-tight">
        {hint}
      </div>
      <div className="text-xs mt-2 font-mono text-ink">
        {stat.latestSummary}
      </div>
      {stat.count > 0 && (
        <div className="mt-1 flex flex-wrap gap-1">
          {Object.entries(stat.actions).map(([action, n]) => (
            <span
              key={action}
              className={`px-1.5 py-0.5 rounded text-[10px] ${style.tag}`}
            >
              {action}:{n}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

// ----------------------------------------------------------------------------
function Arrow({
  active,
  label,
  direction = "down",
}: {
  active: boolean;
  label: string;
  direction?: "down" | "right" | "up-left";
}) {
  const arrow =
    direction === "down" ? "↓" : direction === "right" ? "→" : "↖";
  return (
    <div
      className={[
        "flex items-center gap-1 text-xs px-2 py-1 rounded transition-colors",
        active ? "text-emerald-400 font-semibold" : "text-ink-subtle",
      ].join(" ")}
    >
      <span className="text-base leading-none">{arrow}</span>
      <span>{label}</span>
    </div>
  );
}

// ----------------------------------------------------------------------------
function Kpi({
  label,
  value,
  unit,
  danger,
}: {
  label: string;
  value: string;
  unit?: string;
  danger?: boolean;
}) {
  return (
    <div>
      <div className="text-[10px] uppercase tracking-wider text-ink-subtle">
        {label}
      </div>
      <div
        className={[
          "font-mono text-lg",
          danger ? "text-rose-400" : "text-ink",
        ].join(" ")}
      >
        {value}
      </div>
      {unit && <div className="text-[10px] text-ink-subtle">{unit}</div>}
    </div>
  );
}
