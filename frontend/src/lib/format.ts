/** Small formatting helpers used across the UI. */

export function pct(v: number | null | undefined, digits = 2): string {
  if (v === null || v === undefined || Number.isNaN(v)) return "—";
  return `${(v * 100).toFixed(digits)}%`;
}

export function money(v: number | null | undefined): string {
  if (v === null || v === undefined || Number.isNaN(v)) return "—";
  return `$${Math.round(v).toLocaleString()}`;
}

export function num(v: number | null | undefined, digits = 0): string {
  if (v === null || v === undefined || Number.isNaN(v)) return "—";
  return Number(v).toLocaleString(undefined, {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}

export function policyLabel(p: string): string {
  return {
    mas: "MAS (proposed)",
    periodic_forecasting: "Periodic Forecasting",
    static_rop: "Static ROP",
    full: "Full MAS",
    no_adwin: "No ADWIN",
    ma_only: "MA only",
    no_safety: "No safety stock",
  }[p] ?? p;
}

export function policyColor(p: string): string {
  return {
    mas: "#2A9D8F",
    full: "#2A9D8F",
    periodic_forecasting: "#E69F00",
    no_adwin: "#CC79A7",
    static_rop: "#D55E00",
    no_safety: "#D55E00",
    ma_only: "#0072B2",
  }[p] ?? "#9ca3af";
}

export function timeAgo(iso: string): string {
  const d = new Date(iso);
  const sec = (Date.now() - d.getTime()) / 1000;
  if (sec < 60) return "just now";
  if (sec < 3600) return `${Math.floor(sec / 60)} min ago`;
  if (sec < 86400) return `${Math.floor(sec / 3600)} hr ago`;
  return `${Math.floor(sec / 86400)} day ago`;
}
