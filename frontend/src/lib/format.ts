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

/**
 * Parse a backend timestamp into a Date.
 *
 * The backend stores naive UTC datetimes (SQLite has no tz support).
 * After the schema serializer change they go out as `+00:00`-suffixed
 * ISO strings, which `new Date(...)` handles correctly. For DB rows
 * written before the fix landed — or any path that bypasses the
 * serializer — the wire format may still be naive (no `Z`/`±HH:MM`),
 * which `new Date(...)` would otherwise interpret as *local* time and
 * shift every clock by the user's UTC offset. We append `Z`
 * defensively so the cutover is seamless and idempotent.
 */
export function parseBackendDate(iso: string): Date {
  // Already has a timezone marker (Z or ±HH:MM)? Use as-is.
  if (/(?:Z|[+-]\d{2}:?\d{2})$/.test(iso)) {
    return new Date(iso);
  }
  // Naive — assume UTC.
  return new Date(iso + "Z");
}

/**
 * Render a backend timestamp in the visitor's local timezone using the
 * browser's locale. Use everywhere a date/time is shown to a human.
 */
export function localDateTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  return parseBackendDate(iso).toLocaleString(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

export function timeAgo(iso: string): string {
  const d = parseBackendDate(iso);
  const sec = (Date.now() - d.getTime()) / 1000;
  if (sec < 60) return "just now";
  if (sec < 3600) return `${Math.floor(sec / 60)} min ago`;
  if (sec < 86400) return `${Math.floor(sec / 3600)} hr ago`;
  return `${Math.floor(sec / 86400)} day ago`;
}
