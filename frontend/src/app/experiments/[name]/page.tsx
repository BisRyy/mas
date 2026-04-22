"use client";

import { useQuery, useQueries } from "@tanstack/react-query";
import Link from "next/link";
import { use, useMemo, useState } from "react";
import { api } from "@/lib/api";
import { pct, money, num, policyLabel, policyColor } from "@/lib/format";
import { MetricCard } from "@/components/MetricCard";
import { PlotlyChart } from "@/components/PlotlyChart";

export default function ExperimentDetailPage({
  params,
}: {
  params: Promise<{ name: string }>;
}) {
  const { name } = use(params);
  const [selectedSeed, setSelectedSeed] = useState<number | null>(null);

  const detail = useQuery({
    queryKey: ["experiment", name],
    queryFn: () => api.getExperiment(name),
  });
  const seeds = useQuery({
    queryKey: ["seeds", name],
    queryFn: () => api.listSeeds(name),
  });

  // Fetch each seed's timeseries in parallel.
  const tsQueries = useQueries({
    queries: (seeds.data ?? []).map((s) => ({
      queryKey: ["timeseries", name, s.seed_num],
      queryFn: () => api.getSeedTimeseries(name, s.seed_num),
      staleTime: 5 * 60_000,
    })),
  });

  const policy = detail.data?.policy ?? "mas";
  const color = policyColor(policy);

  const allLoaded = tsQueries.every((q) => q.data);
  const meanBand = useMemo(() => {
    if (!allLoaded || tsQueries.length === 0) return null;
    // Build per-step arrays across all seeds
    const byStep = new Map<number, { on_hand: number[]; stockouts: number[] }>();
    for (const q of tsQueries) {
      for (const p of q.data!.steps) {
        const cur = byStep.get(p.step) ?? { on_hand: [], stockouts: [] };
        cur.on_hand.push(p.total_on_hand);
        cur.stockouts.push(p.stockout_skus_step);
        byStep.set(p.step, cur);
      }
    }
    const steps = [...byStep.keys()].sort((a, b) => a - b);
    const mean = (xs: number[]) => xs.reduce((s, x) => s + x, 0) / xs.length;
    const q = (xs: number[], qq: number) => {
      const s = [...xs].sort((a, b) => a - b);
      const idx = Math.floor((s.length - 1) * qq);
      return s[idx];
    };
    return {
      steps,
      on_hand_mean: steps.map((s) => mean(byStep.get(s)!.on_hand)),
      on_hand_q25: steps.map((s) => q(byStep.get(s)!.on_hand, 0.25)),
      on_hand_q75: steps.map((s) => q(byStep.get(s)!.on_hand, 0.75)),
      stockouts_mean: steps.map((s) => mean(byStep.get(s)!.stockouts)),
      stockouts_q25: steps.map((s) => q(byStep.get(s)!.stockouts, 0.25)),
      stockouts_q75: steps.map((s) => q(byStep.get(s)!.stockouts, 0.75)),
    };
  }, [allLoaded, tsQueries]);

  if (detail.isLoading) return <div>Loading…</div>;
  if (detail.error || !detail.data)
    return <div className="text-rose-400">Experiment not found: {name}</div>;

  return (
    <div className="space-y-6">
      <header>
        <Link href="/experiments" className="text-sm">
          ← All experiments
        </Link>
        <h1 className="mt-1 font-mono text-2xl font-bold">{name}</h1>
        <p className="text-ink-muted">
          <span className={`policy-dot ${policy}`} />
          {policyLabel(policy)} · scenario <span className="font-medium">{detail.data.scenario}</span> ·
          {" "}{detail.data.n_seeds} seeds · family {detail.data.family.toUpperCase()}
        </p>
      </header>

      <section className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <MetricCard label="Stockout rate" value={pct(detail.data.mean_stockout_rate)}
                    sub={detail.data.ci95_stockout_lo && detail.data.ci95_stockout_hi
                      ? `95% CI [${pct(detail.data.ci95_stockout_lo)}, ${pct(detail.data.ci95_stockout_hi)}]`
                      : undefined} />
        <MetricCard label="Total cost" value={money(detail.data.mean_total_cost)} />
        <MetricCard label="Orders placed" value={num(detail.data.mean_n_orders)} />
        <MetricCard label="Forecast MAPE" value={pct(detail.data.mean_forecast_mape)} />
      </section>

      {/* Time series with CI band */}
      <section className="card">
        <h2 className="mb-3 text-lg font-semibold">
          Time series — mean across seeds, IQR shaded
        </h2>
        {!allLoaded ? (
          <div className="py-10 text-center text-ink-muted">Loading time series…</div>
        ) : meanBand ? (
          <>
            <PlotlyChart
              height={320}
              data={[
                {
                  x: [...meanBand.steps, ...meanBand.steps.slice().reverse()],
                  y: [...meanBand.on_hand_q75, ...meanBand.on_hand_q25.slice().reverse()],
                  fill: "toself",
                  fillcolor: hexA(color, 0.18),
                  line: { width: 0 },
                  hoverinfo: "skip",
                  showlegend: false,
                  type: "scatter",
                },
                {
                  x: meanBand.steps,
                  y: meanBand.on_hand_mean,
                  mode: "lines",
                  line: { color, width: 2 },
                  name: "On-hand inventory",
                  type: "scatter",
                },
              ]}
              layout={{
                title: { text: "Total on-hand inventory", font: { color: "#d1d5db" } },
                yaxis: { title: { text: "units" }, gridcolor: "#1f2937" },
                xaxis: { title: { text: "simulation step (day)" }, gridcolor: "#1f2937" },
              } as never}
            />
            <PlotlyChart
              height={280}
              data={[
                {
                  x: [...meanBand.steps, ...meanBand.steps.slice().reverse()],
                  y: [...meanBand.stockouts_q75, ...meanBand.stockouts_q25.slice().reverse()],
                  fill: "toself",
                  fillcolor: hexA(color, 0.18),
                  line: { width: 0 },
                  hoverinfo: "skip",
                  showlegend: false,
                  type: "scatter",
                },
                {
                  x: meanBand.steps,
                  y: meanBand.stockouts_mean,
                  mode: "lines",
                  line: { color, width: 2 },
                  name: "Stockout SKUs / step",
                  type: "scatter",
                },
              ]}
              layout={{
                title: { text: "SKUs in stockout per step", font: { color: "#d1d5db" } },
                yaxis: { title: { text: "count" }, gridcolor: "#1f2937" },
                xaxis: { title: { text: "simulation step (day)" }, gridcolor: "#1f2937" },
              } as never}
            />
          </>
        ) : null}
      </section>

      {/* Per-seed table */}
      <section className="card overflow-hidden p-0">
        <table>
          <thead>
            <tr>
              <th>Seed</th>
              <th className="text-right">Stockout</th>
              <th className="text-right">Cost</th>
              <th className="text-right">Orders</th>
              <th className="text-right">MAPE</th>
              <th className="text-right">Refits</th>
              <th className="text-right">Drift</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {seeds.data?.map((s) => (
              <tr key={s.id}>
                <td>{s.seed_num}</td>
                <td className="text-right">{pct(s.stockout_rate)}</td>
                <td className="text-right">{money(s.total_cost)}</td>
                <td className="text-right">{num(s.n_orders)}</td>
                <td className="text-right">{pct(s.forecast_mape)}</td>
                <td className="text-right">{num(s.n_refits)}</td>
                <td className="text-right">{num(s.n_global_drift_events)}</td>
                <td>
                  <Link
                    href={`/decisions/${name}/${s.seed_num}`}
                    className="text-sm"
                  >
                    Decisions →
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  );
}

function hexA(hex: string, alpha: number): string {
  const h = hex.replace("#", "");
  const r = parseInt(h.slice(0, 2), 16);
  const g = parseInt(h.slice(2, 4), 16);
  const b = parseInt(h.slice(4, 6), 16);
  return `rgba(${r},${g},${b},${alpha})`;
}
