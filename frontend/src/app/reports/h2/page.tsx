"use client";

/**
 * H2 — Adaptability / Cost-efficiency report.
 *
 * The original H2 ("MAS restores 95% SL faster than Periodic") is
 * empirically vacuous in our setup: both adaptive policies maintain
 * post-drift SL > 99% in every scenario because EOQ-derived order
 * quantities absorb the between-refit stale window. This page tells
 * that story explicitly, then renders the manuscript's reframed
 * H2' (cost-of-service under drift) from the data the H1 report
 * already returns.
 */

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useMemo } from "react";
import { api } from "@/lib/api";
import { pct, money } from "@/lib/format";

const SL_FLOOR = 0.99;          // The 99% claim from §5.2
const H2_PRIME_THRESHOLD = -0.3; // "≥30% less cost" → rel_change ≤ −0.30

export default function H2ReportPage() {
  const h1 = useQuery({ queryKey: ["h1-report"], queryFn: api.h1Report });
  const exps = useQuery({
    queryKey: ["experiments-h1-for-h2"],
    queryFn: () => api.listExperiments({ family: "h1", limit: 200 }),
  });

  // H2' rows: cost tests against periodic_forecasting baseline only.
  const costRows = useMemo(
    () =>
      (h1.data?.tests ?? [])
        .filter((t) => t.metric === "total_cost" && t.baseline === "periodic_forecasting")
        .sort((a, b) => a.scenario.localeCompare(b.scenario)),
    [h1.data],
  );

  // Service-level matrix: scenario → policy → mean SL = 1 - mean_stockout_rate.
  const slMatrix = useMemo(() => {
    const out: Record<string, Record<string, number | null>> = {};
    for (const e of exps.data ?? []) {
      out[e.scenario] = out[e.scenario] ?? {};
      out[e.scenario][e.policy] =
        e.mean_stockout_rate == null ? null : 1 - e.mean_stockout_rate;
    }
    return out;
  }, [exps.data]);

  const scenarios = useMemo(
    () => Object.keys(slMatrix).sort(),
    [slMatrix],
  );

  // Pass/fail check for H2'.
  const verdict = useMemo(() => {
    if (costRows.length === 0) return null;
    const allBeatThreshold = costRows.every(
      (t) => t.rel_change != null && t.rel_change <= H2_PRIME_THRESHOLD,
    );
    const allSignificant = costRows.every(
      (t) => t.mannwhitney_p != null && t.mannwhitney_p < 0.05,
    );
    return { allBeatThreshold, allSignificant };
  }, [costRows]);

  return (
    <div className="space-y-6">
      <header className="space-y-1">
        <h1 className="text-2xl font-bold">H2 &mdash; Adaptability report</h1>
        <p className="text-ink-muted">
          The original H2 was: <em>after an abrupt demand shock, MAS will
          restore the 95% service level faster than Periodic Forecasting</em>.
          Empirically, the hypothesis is vacuous in this experimental setup —
          both adaptive policies maintain post-drift service level above 99%
          in every scenario (the EOQ-derived order quantity absorbs Periodic&apos;s
          between-refit stale window). Time-to-recovery is 0 for both, so the
          original H2 cannot distinguish the policies.
        </p>
        <p className="text-xs text-ink-subtle">
          The substantive finding has moved to the cost dimension &mdash; both
          policies achieve the same service level, but at very different
          prices. The manuscript&apos;s Discussion §5.2 reframes H2 as{" "}
          <strong className="text-ink">H2′ (Cost-efficiency under drift)</strong>:
          at equivalent post-drift SL (≥ 99%), MAS will incur at least 30% less
          total cost than Periodic Forecasting, with Mann&ndash;Whitney{" "}
          <em>p</em> &lt; 0.05.
        </p>
      </header>

      {/* ─── Why the original H2 is vacuous ─────────────────────────── */}
      <section className="space-y-3">
        <h2 className="text-xl font-semibold">
          Why the original H2 is empirically vacuous
        </h2>
        <p className="text-sm text-ink-muted">
          Post-drift mean service level for every (policy × scenario) cell.
          Both <em>mas</em> and <em>periodic_forecasting</em> sit above the
          99% line in every column, so a 95% target is never breached and
          time-to-recovery is identically zero.
        </p>
        <div className="card overflow-hidden p-0">
          <table>
            <thead>
              <tr>
                <th>Scenario</th>
                <th className="text-right">MAS</th>
                <th className="text-right">Periodic</th>
                <th className="text-right">Static ROP</th>
                <th>Verdict</th>
              </tr>
            </thead>
            <tbody>
              {scenarios.map((s) => {
                const mas = slMatrix[s]?.mas ?? null;
                const per = slMatrix[s]?.periodic_forecasting ?? null;
                const stat = slMatrix[s]?.static_rop ?? null;
                const adaptiveSafe =
                  mas != null && per != null && mas >= SL_FLOOR && per >= SL_FLOOR;
                return (
                  <tr key={s}>
                    <td className="text-xs text-ink-muted">{s}</td>
                    <td className="text-right tabular-nums">
                      <SLValue v={mas} />
                    </td>
                    <td className="text-right tabular-nums">
                      <SLValue v={per} />
                    </td>
                    <td className="text-right tabular-nums">
                      <SLValue v={stat} />
                    </td>
                    <td className="text-xs">
                      {adaptiveSafe ? (
                        <span className="text-emerald-400">
                          both adaptive policies ≥ 99%
                        </span>
                      ) : (
                        <span className="text-amber-400">SL gap present</span>
                      )}
                    </td>
                  </tr>
                );
              })}
              {scenarios.length === 0 && (
                <tr>
                  <td colSpan={5} className="text-center text-ink-muted">
                    Loading…
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>

      {/* ─── H2' verdict callout ───────────────────────────────────── */}
      {verdict && (
        <section
          className={`card border ${
            verdict.allBeatThreshold && verdict.allSignificant
              ? "border-emerald-700 bg-emerald-950/20"
              : "border-amber-700 bg-amber-950/20"
          }`}
        >
          <div className="flex items-center gap-2">
            <span className="rounded bg-bg-elevated px-2 py-0.5 text-xs font-semibold uppercase tracking-wider text-ink-muted">
              H2′
            </span>
            <span className="text-sm text-ink-muted">
              Cost-efficiency under drift
            </span>
          </div>
          <div
            className={`mt-1 text-lg font-semibold ${
              verdict.allBeatThreshold && verdict.allSignificant
                ? "text-emerald-400"
                : "text-amber-400"
            }`}
          >
            {verdict.allBeatThreshold && verdict.allSignificant
              ? "Confirmed (post-hoc)"
              : "Partially supported"}
          </div>
          <p className="mt-2 text-sm text-ink-muted">
            MAS beats the −30% threshold in {costRows.filter((t) => (t.rel_change ?? 0) <= H2_PRIME_THRESHOLD).length} of {costRows.length} scenarios
            {" "}with Mann&ndash;Whitney <em>p</em> &lt; 0.05 in{" "}
            {costRows.filter((t) => (t.mannwhitney_p ?? 1) < 0.05).length} of {costRows.length}.
            We label this <em>confirmed (post-hoc)</em> rather than
            simply <em>confirmed</em> because H2′ was formulated after seeing
            the data; the preregistered version was the vacuous SL-recovery
            statement above.
          </p>
        </section>
      )}

      {/* ─── H2' supporting table ──────────────────────────────────── */}
      <section className="space-y-3">
        <h2 className="text-xl font-semibold">
          H2′ supporting data &mdash; total cost: MAS vs Periodic
        </h2>
        <p className="text-sm text-ink-muted">
          Per-scenario mean total cost across N = 10 seeds. <em>Δ vs Periodic</em>{" "}
          is the relative change ((MAS − Periodic) / Periodic). Mann&ndash;Whitney{" "}
          <em>p</em> is the primary significance test;{" "}
          a value &lt; 0.05 means the cost reduction is statistically
          distinguishable from chance under the null of equal medians.
        </p>
        <div className="card overflow-hidden p-0">
          <table>
            <thead>
              <tr>
                <th>Scenario</th>
                <th className="text-right">MAS cost</th>
                <th className="text-right">Periodic cost</th>
                <th className="text-right">Δ vs Periodic</th>
                <th className="text-right">MW <em>p</em></th>
                <th className="text-right">Welch <em>p</em></th>
                <th className="text-right">
                  Cohen&apos;s <em>d</em>
                </th>
                <th>Threshold (−30%)</th>
              </tr>
            </thead>
            <tbody>
              {costRows.map((t, i) => {
                const passThreshold =
                  t.rel_change != null && t.rel_change <= H2_PRIME_THRESHOLD;
                const significant =
                  t.mannwhitney_p != null && t.mannwhitney_p < 0.05;
                return (
                  <tr key={i} className={significant ? "font-medium" : ""}>
                    <td className="text-xs text-ink-muted">{t.scenario}</td>
                    <td className="text-right tabular-nums">
                      {money(t.treatment_mean)}
                    </td>
                    <td className="text-right tabular-nums">
                      {money(t.baseline_mean)}
                    </td>
                    <td
                      className={`text-right tabular-nums ${
                        passThreshold ? "text-emerald-400" : ""
                      }`}
                    >
                      {t.rel_change == null
                        ? "—"
                        : `${(t.rel_change * 100).toFixed(1)}%`}
                    </td>
                    <td className="text-right tabular-nums">
                      {fmtP(t.mannwhitney_p)}
                    </td>
                    <td className="text-right tabular-nums">
                      {fmtP(t.welch_p)}
                    </td>
                    <td className="text-right tabular-nums">
                      {t.cohens_d == null ? "—" : t.cohens_d.toFixed(2)}
                    </td>
                    <td>
                      {passThreshold ? (
                        <span className="text-xs text-emerald-400">
                          pass (≤ −30%)
                        </span>
                      ) : (
                        <span className="text-xs text-ink-muted">below</span>
                      )}
                    </td>
                  </tr>
                );
              })}
              {costRows.length === 0 && (
                <tr>
                  <td colSpan={8} className="text-center text-ink-muted">
                    Loading…
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>

      {/* ─── Read-on links ─────────────────────────────────────────── */}
      <section className="card text-sm text-ink-muted">
        Related views:{" "}
        <Link href="/reports/h1" className="underline hover:text-ink">
          /reports/h1
        </Link>{" "}
        carries the full stockout and cost comparison against both baselines.{" "}
        <Link href="/compare" className="underline hover:text-ink">
          /compare
        </Link>{" "}
        overlays the per-seed inventory trajectories side-by-side. The
        Discussion §5.2 in the thesis manuscript discusses the reframe in
        more depth.
      </section>
    </div>
  );
}

// ─── Helpers ────────────────────────────────────────────────────────

function SLValue({ v }: { v: number | null }) {
  if (v == null) return <span className="text-ink-subtle">—</span>;
  const good = v >= SL_FLOOR;
  return (
    <span className={good ? "text-emerald-400" : "text-amber-400"}>
      {pct(v)}
    </span>
  );
}

function fmtP(p: number | null | undefined): string {
  if (p == null) return "—";
  if (p < 0.001) return "≤ 0.001";
  return p.toFixed(4);
}
