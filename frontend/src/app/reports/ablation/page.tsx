"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { pct, money } from "@/lib/format";

export default function AblationReportPage() {
  const abl = useQuery({ queryKey: ["ablation-report"], queryFn: api.ablationReport });

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-bold">Ablation report</h1>
        <p className="text-ink-muted">
          Component-removal study on the catastrophic scenario (N = 10 seeds
          per variant). Δ columns are relative to the <em>full</em> MAS.
        </p>
      </header>

      <div className="card overflow-hidden p-0">
        <table>
          <thead>
            <tr>
              <th>Variant</th>
              <th>N</th>
              <th className="text-right">Stockout</th>
              <th className="text-right">Δ vs full</th>
              <th className="text-right">Total cost</th>
              <th className="text-right">Δ vs full</th>
              <th className="text-right">MAPE</th>
              <th className="text-right">Global drift</th>
            </tr>
          </thead>
          <tbody>
            {abl.data?.rows.map((r) => (
              <tr key={r.variant}>
                <td>
                  <span className={`policy-dot ${r.variant}`} />
                  <strong>{r.variant}</strong>
                </td>
                <td>{r.n_seeds}</td>
                <td className="text-right">{pct(r.stockout_rate_mean)}</td>
                <td className="text-right">
                  {r.rel_to_full_stockout != null
                    ? `${(r.rel_to_full_stockout * 100).toFixed(1)}%`
                    : "—"}
                </td>
                <td className="text-right">{money(r.total_cost_mean)}</td>
                <td className="text-right">
                  {r.rel_to_full_cost != null
                    ? `${(r.rel_to_full_cost * 100).toFixed(1)}%`
                    : "—"}
                </td>
                <td className="text-right">{pct(r.forecast_mape_mean)}</td>
                <td className="text-right">
                  {r.n_global_drift_events_mean?.toFixed(1) ?? "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <section className="card text-sm text-ink-muted">
        <p>
          <strong className="text-ink">Reading the table:</strong> under the
          adversarial catastrophic scenario every individual ablation
          <em> improves</em> both stockout rate and total cost relative to
          the full MAS. The mechanism is documented in thesis §5.3 —
          the Holt–Winters forecaster captures the genuine transient
          volatility, inflating <code>z·σ·√LT</code> and driving
          over-provisioning. Bounded safety stock (capping the buffer at a
          multiple of mean lead-time demand) is the fix queued as future
          work.
        </p>
      </section>
    </div>
  );
}
