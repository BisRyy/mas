"use client";

import dynamic from "next/dynamic";
import type { Data, Layout, Config } from "plotly.js-dist-min";

// Lazy-load Plotly so the ~3 MB lib stays out of the initial bundle.
const Plot = dynamic(() => import("react-plotly.js").then((m) => m.default), {
  ssr: false,
  loading: () => (
    <div className="flex h-72 items-center justify-center text-ink-muted">
      Loading chart…
    </div>
  ),
});

const DARK_LAYOUT: Partial<Layout> = {
  template: "plotly_dark" as unknown as Layout["template"],
  plot_bgcolor: "#0e1117",
  paper_bgcolor: "#0e1117",
  font: { color: "#d1d5db", family: "ui-sans-serif" },
  margin: { t: 30, l: 50, r: 20, b: 50 },
  hovermode: "x unified",
  xaxis: { gridcolor: "#1f2937", zerolinecolor: "#1f2937", color: "#9ca3af" },
  yaxis: { gridcolor: "#1f2937", zerolinecolor: "#1f2937", color: "#9ca3af" },
  legend: { bgcolor: "rgba(0,0,0,0)", font: { color: "#d1d5db" } },
};

export function PlotlyChart({
  data,
  layout,
  height = 320,
  config,
}: {
  data: Data[];
  layout?: Partial<Layout>;
  height?: number;
  config?: Partial<Config>;
}) {
  return (
    <div style={{ width: "100%", height }}>
      <Plot
        data={data}
        layout={{ ...DARK_LAYOUT, ...layout, autosize: true } as Layout}
        config={{ displayModeBar: false, responsive: true, ...config }}
        style={{ width: "100%", height: "100%" }}
        useResizeHandler
      />
    </div>
  );
}
