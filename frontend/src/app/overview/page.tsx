"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { api } from "@/lib/api";
import { pct, money, num, policyLabel } from "@/lib/format";
import { MetricCard } from "@/components/MetricCard";

export default function OverviewPage() {
  const families = useQuery({
    queryKey: ["family-breakdown"],
    queryFn: api.familyBreakdown,
  });
  const allExperiments = useQuery({
    queryKey: ["experiments-all"],
    queryFn: () => api.listExperiments({ limit: 100 }),
  });
  const h3 = useQuery({ queryKey: ["h3-report"], queryFn: api.h3Report });

  // Catastrophic-scenario MAS row for headline metrics.
  const cat = allExperiments.data?.find(
    (e) => e.config_name === "olist_mas_catastrophic",
  );

  return (
    <div className="space-y-8">
      <header className="space-y-1">
        <h1 className="text-3xl font-bold tracking-tight">Overview</h1>
        <p className="text-ink-muted">
          One-page dashboard of the thesis results. Top: the three hypothesis
          verdicts as the manuscript reports them, with one-click drill into
          the supporting reports. Middle: headline metrics for the worst-case
          scenario (catastrophic drift) under MAS. Bottom: a paginated slice
          of the experiment catalog.
          {families.data && (
            <span className="ml-2">
              Currently tracking{" "}
              {Object.values(families.data).reduce((a, b) => a + b, 0)}{" "}
              experiments.
            </span>
          )}
        </p>
      </header>

      {/* Hypothesis verdicts */}
      <section className="space-y-3">
        <h2 className="text-xl font-semibold">Hypothesis verdicts</h2>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
          <VerdictCard
            tag="H1"
            label="Performance"
            verdict="Confirmed and exceeded"
            tone="ok"
            detail="MAS reduces stockout 71.9–80.4% vs Static ROP; 17.3–33.5% vs Periodic. Mann–Whitney p ≤ 0.001 in every cell."
            link="/reports/h1"
          />
          <VerdictCard
            tag="H2"
            label="Adaptability"
            verdict="Reframed (cost-of-service)"
            tone="warn"
            detail="Both adaptive policies stay above 99% SL. Substantive finding: MAS achieves equivalent SL at 53–70% less inventory cost."
            link="/reports/h1"
          />
          <VerdictCard
            tag="H3"
            label="Scalability"
            verdict="Confirmed and exceeded"
            tone="ok"
            detail={
              h3.data
                ? `Power-law exponent b = ${
                    h3.data.fits.find((f) => f.policy === "mas")?.exponent_b.toFixed(3) ?? "—"
                  } (predicted ≈ 1.0 linear). Sublinear; near-constant.`
                : "Loading…"
            }
            link="/reports/h3"
          />
        </div>
      </section>

      {/* Catastrophic-scenario headline */}
      {cat && (
        <section className="space-y-3">
          <h2 className="text-xl font-semibold">
            Catastrophic-scenario headline (MAS)
          </h2>
          <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
            <MetricCard label="Stockout rate" value={pct(cat.mean_stockout_rate)} accent="mas" />
            <MetricCard label="Total cost" value={money(cat.mean_total_cost)} accent="mas" />
            <MetricCard label="Orders placed" value={num(cat.mean_n_orders)} accent="mas" />
            <MetricCard label="Forecast MAPE" value={pct(cat.mean_forecast_mape)} accent="mas" />
          </div>
        </section>
      )}

      {/* Catalog table */}
      <section className="space-y-3">
        <div className="flex items-end justify-between">
          <h2 className="text-xl font-semibold">Experiment catalog</h2>
          <Link href="/experiments" className="text-sm">
            Browse all →
          </Link>
        </div>
        <div className="card overflow-hidden p-0">
          <table>
            <thead>
              <tr>
                <th>Config</th>
                <th>Family</th>
                <th>Policy</th>
                <th>Scenario</th>
                <th>Seeds</th>
                <th className="text-right">Stockout</th>
                <th className="text-right">Cost</th>
              </tr>
            </thead>
            <tbody>
              {allExperiments.data?.slice(0, 12).map((e) => (
                <tr key={e.id}>
                  <td>
                    <Link href={`/experiments/${e.config_name}`} className="font-mono">
                      {e.config_name}
                    </Link>
                  </td>
                  <td className="uppercase text-xs text-ink-muted">{e.family}</td>
                  <td>
                    <span className={`policy-dot ${e.policy}`} />
                    {policyLabel(e.policy)}
                  </td>
                  <td className="text-xs text-ink-muted">{e.scenario}</td>
                  <td>{e.n_seeds}</td>
                  <td className="text-right">{pct(e.mean_stockout_rate)}</td>
                  <td className="text-right">{money(e.mean_total_cost)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}

function VerdictCard({
  tag,
  label,
  verdict,
  tone,
  detail,
  link,
}: {
  tag: string;
  label: string;
  verdict: string;
  tone: "ok" | "warn" | "bad";
  detail: string;
  link?: string;
}) {
  const toneColor =
    tone === "ok" ? "text-emerald-400" : tone === "warn" ? "text-amber-400" : "text-rose-400";
  return (
    <div className="card flex flex-col gap-2">
      <div className="flex items-center gap-2">
        <span className="rounded bg-bg-elevated px-2 py-0.5 text-xs font-semibold uppercase tracking-wider text-ink-muted">
          {tag}
        </span>
        <span className="text-sm text-ink-muted">{label}</span>
      </div>
      <div className={`text-lg font-semibold ${toneColor}`}>{verdict}</div>
      <p className="text-sm text-ink-muted">{detail}</p>
      {link && (
        <Link href={link} className="mt-auto text-sm">
          Open report →
        </Link>
      )}
    </div>
  );
}
