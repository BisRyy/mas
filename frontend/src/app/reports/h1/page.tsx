"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { pct, money } from "@/lib/format";

export default function H1ReportPage() {
  const h1 = useQuery({ queryKey: ["h1-report"], queryFn: api.h1Report });
  const stockoutTests = (h1.data?.tests ?? []).filter((t) => t.metric === "stockout_rate");
  const costTests = (h1.data?.tests ?? []).filter((t) => t.metric === "total_cost");

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-bold">H1 — Performance report</h1>
        <p className="text-ink-muted">
          MAS vs baselines across every drift scenario. Mann–Whitney U
          (primary), Welch&apos;s t, Cohen&apos;s d. N = 10 seeds per cell.
        </p>
      </header>

      <Section title="Stockout rate" tests={stockoutTests} formatter={pct} />
      <Section title="Total cost" tests={costTests} formatter={(v) => v == null ? "—" : money(v)} />
    </div>
  );
}

function Section({
  title,
  tests,
  formatter,
}: {
  title: string;
  tests: ReturnType<typeof useQuery<Awaited<ReturnType<typeof api.h1Report>>>>["data"] extends infer T
    ? T extends { tests: infer A } ? A : never
    : never;
  formatter: (v: number | null) => string;
}) {
  return (
    <section className="card overflow-hidden p-0">
      <div className="border-b border-border px-4 py-2 text-sm font-semibold">{title}</div>
      <table>
        <thead>
          <tr>
            <th>Scenario</th>
            <th>vs</th>
            <th className="text-right">MAS mean</th>
            <th className="text-right">Baseline mean</th>
            <th className="text-right">Δ</th>
            <th className="text-right">MW p</th>
            <th className="text-right">Welch p</th>
            <th className="text-right">Cohen&apos;s d</th>
          </tr>
        </thead>
        <tbody>
          {tests?.map((t, i) => {
            const sig = (t.mannwhitney_p ?? 1) < 0.05;
            return (
              <tr key={i}>
                <td>{t.scenario}</td>
                <td className="text-xs text-ink-muted">{t.baseline}</td>
                <td className="text-right">{formatter(t.treatment_mean)}</td>
                <td className="text-right">{formatter(t.baseline_mean)}</td>
                <td className="text-right font-semibold">
                  {t.rel_change != null ? `${(t.rel_change * 100).toFixed(1)}%` : "—"}
                </td>
                <td className={`text-right ${sig ? "text-emerald-400" : ""}`}>
                  {t.mannwhitney_p?.toFixed(4) ?? "—"}
                </td>
                <td className="text-right text-xs">
                  {t.welch_p != null ? t.welch_p.toExponential(2) : "—"}
                </td>
                <td className="text-right text-xs">
                  {t.cohens_d != null ? t.cohens_d.toFixed(2) : "—"}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </section>
  );
}
