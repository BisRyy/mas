"use client";

import { useQueries, useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { api } from "@/lib/api";
import { pct, money, num, policyColor, policyLabel } from "@/lib/format";
import { PlotlyChart } from "@/components/PlotlyChart";

export default function ComparePage() {
  const [selected, setSelected] = useState<string[]>([
    "olist_static_rop_catastrophic",
    "olist_periodic_forecasting_catastrophic",
    "olist_mas_catastrophic",
  ]);

  const all = useQuery({
    queryKey: ["experiments-all-for-compare"],
    queryFn: () => api.listExperiments({ limit: 500 }),
  });

  const details = useQueries({
    queries: selected.map((name) => ({
      queryKey: ["experiment", name],
      queryFn: () => api.getExperiment(name),
    })),
  });

  // Fetch first-seed timeseries for each selected run for the comparison plot.
  const tsQueries = useQueries({
    queries: selected.map((name) => ({
      queryKey: ["timeseries", name, 1],
      queryFn: () => api.getSeedTimeseries(name, 1),
      staleTime: 5 * 60_000,
    })),
  });

  function toggle(name: string) {
    setSelected((cur) =>
      cur.includes(name) ? cur.filter((c) => c !== name) : [...cur, name],
    );
  }

  return (
    <div className="space-y-6">
      <header className="space-y-1">
        <h1 className="text-2xl font-bold">Comparison</h1>
        <p className="text-ink-muted">
          Side-by-side view of multiple experiments. Pick any combination of
          configurations &mdash; usually one MAS run plus one or more baselines
          for the same scenario &mdash; and the dashboard overlays their
          seed-1 inventory and stockout trajectories on a shared time axis,
          then lists their aggregate metrics in a single table.
        </p>
        <p className="text-xs text-ink-subtle">
          Defaults to the three catastrophic-scenario policies. Use this view
          to visually verify the H1 claims in <em>/reports/h1</em>.
        </p>
      </header>

      <details className="card" open>
        <summary className="cursor-pointer text-sm font-semibold">
          Select experiments ({selected.length} selected)
        </summary>
        <div className="mt-3 grid grid-cols-1 gap-1 md:grid-cols-2 lg:grid-cols-3">
          {all.data?.map((e) => (
            <label key={e.id} className="flex cursor-pointer items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={selected.includes(e.config_name)}
                onChange={() => toggle(e.config_name)}
              />
              <span className={`policy-dot ${e.policy}`} />
              <span className="font-mono text-xs">{e.config_name}</span>
            </label>
          ))}
        </div>
      </details>

      {/* Summary table */}
      <div className="card overflow-hidden p-0">
        <table>
          <thead>
            <tr>
              <th>Experiment</th>
              <th className="text-right">Stockout</th>
              <th className="text-right">Cost</th>
              <th className="text-right">Orders</th>
              <th className="text-right">MAPE</th>
              <th className="text-right">Runtime</th>
            </tr>
          </thead>
          <tbody>
            {details.map((d, i) => {
              if (!d.data) return null;
              return (
                <tr key={d.data.id}>
                  <td>
                    <span className={`policy-dot ${d.data.policy}`} />
                    <span className="font-mono">{d.data.config_name}</span>
                  </td>
                  <td className="text-right">{pct(d.data.mean_stockout_rate)}</td>
                  <td className="text-right">{money(d.data.mean_total_cost)}</td>
                  <td className="text-right">{num(d.data.mean_n_orders)}</td>
                  <td className="text-right">{pct(d.data.mean_forecast_mape)}</td>
                  <td className="text-right">{num(d.data.mean_runtime_seconds, 1)}s</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Overlaid time series */}
      <section className="card">
        <h2 className="mb-3 text-lg font-semibold">Overlay — seed 1 of each</h2>
        <PlotlyChart
          height={420}
          data={tsQueries
            .map((q, i) => {
              if (!q.data) return null;
              const name = selected[i];
              const policy = details[i]?.data?.policy ?? "mas";
              return {
                x: q.data.steps.map((s) => s.step),
                y: q.data.steps.map((s) => s.total_on_hand),
                mode: "lines" as const,
                line: { color: policyColor(policy), width: 2 },
                name,
                type: "scatter" as const,
              };
            })
            .filter(Boolean) as never[]}
          layout={{
            title: { text: "Total on-hand inventory (seed 1)", font: { color: "#d1d5db" } },
            yaxis: { gridcolor: "#1f2937" },
            xaxis: { title: { text: "simulation step (day)" }, gridcolor: "#1f2937" },
          } as never}
        />
      </section>
    </div>
  );
}
