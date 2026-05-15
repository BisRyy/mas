"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { policyColor, policyLabel } from "@/lib/format";
import { PlotlyChart } from "@/components/PlotlyChart";

export default function H3ReportPage() {
  const h3 = useQuery({ queryKey: ["h3-report"], queryFn: api.h3Report });

  const traces = (h3.data?.fits ?? []).flatMap((fit) => {
    const xs = (fit.raw_points as Array<Record<string, unknown>>)
      .map((p) => Number(p.n_skus))
      .sort((a, b) => a - b);
    const ys = (fit.raw_points as Array<Record<string, unknown>>)
      .sort((a, b) => Number(a.n_skus) - Number(b.n_skus))
      .map((p) => Number(p.runtime_seconds_mean));
    const xsFit = Array.from({ length: 50 }, (_, i) =>
      xs[0] + ((xs[xs.length - 1] - xs[0]) * i) / 49,
    );
    const ysFit = xsFit.map((x) => fit.a * Math.pow(x, fit.exponent_b));
    return [
      {
        x: xs,
        y: ys,
        mode: "markers" as const,
        marker: { color: policyColor(fit.policy), size: 9 },
        name: policyLabel(fit.policy),
        type: "scatter" as const,
      },
      {
        x: xsFit,
        y: ysFit,
        mode: "lines" as const,
        line: { color: policyColor(fit.policy), dash: "dash" as const, width: 1.2 },
        name: `  fit: n^${fit.exponent_b.toFixed(2)}`,
        type: "scatter" as const,
        showlegend: true,
      },
    ];
  });

  return (
    <div className="space-y-6">
      <header className="space-y-1">
        <h1 className="text-2xl font-bold">H3 &mdash; Scalability report</h1>
        <p className="text-ink-muted">
          Does per-step runtime grow faster than linear with the number of
          SKUs? We fit a power law <code>t = a · n<sup>b</sup></code> to
          per-step runtime measurements across cohort sizes (50, 100, 200,
          500, 1000 SKUs, 10 seeds each) for each policy, then classify the
          exponent <em>b</em>: <code>&lt; 1</code> sub-linear,{" "}
          <code>≈ 1</code> linear, <code>&gt; 1</code> super-linear. The
          per-policy table reports <em>b</em>, the coefficient <em>a</em>, the
          fit&apos;s R<sup>2</sup>, and the resulting classification; the
          scatter below overlays raw points with each fit line.
        </p>
      </header>

      <div className="card">
        <PlotlyChart
          height={420}
          data={traces as never}
          layout={{
            xaxis: { type: "log", title: { text: "n SKUs (log)" }, gridcolor: "#1f2937" },
            yaxis: { type: "log", title: { text: "runtime (s, log)" }, gridcolor: "#1f2937" },
            legend: { font: { color: "#d1d5db" } },
          } as never}
        />
      </div>

      <div className="card overflow-hidden p-0">
        <table>
          <thead>
            <tr>
              <th>Policy</th>
              <th className="text-right">Exponent b</th>
              <th className="text-right">R²</th>
              <th>Classification</th>
            </tr>
          </thead>
          <tbody>
            {h3.data?.fits.map((f) => (
              <tr key={f.policy}>
                <td>
                  <span className={`policy-dot ${f.policy}`} />
                  {policyLabel(f.policy)}
                </td>
                <td className="text-right">{f.exponent_b.toFixed(3)}</td>
                <td className="text-right">{f.r2.toFixed(3)}</td>
                <td>{f.classification || "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
