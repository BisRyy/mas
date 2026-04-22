export function MetricCard({
  label,
  value,
  sub,
  accent,
}: {
  label: string;
  value: string;
  sub?: string;
  accent?: "mas" | "periodic_forecasting" | "static_rop";
}) {
  return (
    <div className="card">
      <div className="metric-label flex items-center gap-2">
        {accent && <span className={`policy-dot ${accent}`} />}
        {label}
      </div>
      <div className="metric-value mt-1">{value}</div>
      {sub && <div className="mt-1 text-xs text-ink-muted">{sub}</div>}
    </div>
  );
}
