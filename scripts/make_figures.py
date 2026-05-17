"""Generate publication-quality figures from the aggregated results.

Outputs both PDF (preferred for thesis/papers) and PNG (preview) into
`figures/` at the repo root.

Run:
    python -m scripts.make_figures
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # headless
import matplotlib.pyplot as plt
import numpy as np

# ----------------------------------------------------------------------------
# Style — colorblind-safe palette + serif typography
# ----------------------------------------------------------------------------
plt.rcParams.update({
    "font.family": "serif",
    "font.size": 10,
    "axes.titlesize": 11,
    "axes.labelsize": 10,
    "xtick.labelsize": 9,
    "ytick.labelsize": 9,
    "legend.fontsize": 9,
    "figure.dpi": 120,
    "savefig.dpi": 300,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "grid.alpha": 0.25,
    "grid.linestyle": "-",
    "grid.linewidth": 0.5,
})

# Colorblind-safe palette (Wong / Okabe-Ito).
POLICY_COLORS = {
    "static_rop": "#D55E00",            # vermillion
    "periodic_forecasting": "#E69F00",  # orange
    "mas": "#009E73",                   # bluish green
}
POLICY_LABELS = {
    "static_rop": "Static ROP",
    "periodic_forecasting": "Periodic Forecasting",
    "mas": "MAS (proposed)",
}

POLICY_ORDER = ["static_rop", "periodic_forecasting", "mas"]
SCENARIO_ORDER = [
    "no_drift", "abrupt", "gradual", "seasonal", "severe_abrupt", "catastrophic",
]
SCENARIO_LABELS = {
    "no_drift": "No drift",
    "abrupt": "Abrupt",
    "gradual": "Gradual",
    "seasonal": "Seasonal",
    "severe_abrupt": "Severe abrupt",
    "catastrophic": "Catastrophic",
}

RESULTS = Path("results")
FIGURES = Path("figures")
FIGURES.mkdir(exist_ok=True)


def _load_agg(name: str) -> dict | None:
    p = RESULTS / name / "aggregate.json"
    if not p.exists():
        return None
    with open(p) as f:
        return json.load(f)


def _agg_metric(agg: dict | None, key: str) -> tuple[float, float] | None:
    if not agg:
        return None
    m = agg.get("metrics", {}).get(key)
    if not m:
        return None
    return float(m["mean"]), float(m["std"])


def _save(fig, name: str) -> None:
    pdf = FIGURES / f"{name}.pdf"
    png = FIGURES / f"{name}.png"
    fig.savefig(pdf, bbox_inches="tight")
    fig.savefig(png, bbox_inches="tight")
    print(f"  -> {pdf}")
    plt.close(fig)


# ============================================================================
# Figure 1: H1 stockout-rate comparison across scenarios
# ============================================================================
def fig_h1_stockout() -> None:
    print("Figure 1: H1 stockout-rate comparison")
    n_scen = len(SCENARIO_ORDER)
    n_pol = len(POLICY_ORDER)
    width = 0.26
    x = np.arange(n_scen)

    fig, ax = plt.subplots(figsize=(8.5, 4.2))
    for i, pol in enumerate(POLICY_ORDER):
        means, stds = [], []
        for scen in SCENARIO_ORDER:
            agg = _load_agg(f"olist_{pol}_{scen}")
            mt = _agg_metric(agg, "stockout_rate")
            if mt:
                means.append(mt[0] * 100)
                stds.append(mt[1] * 100)
            else:
                means.append(0); stds.append(0)
        offset = (i - 1) * width
        ax.bar(x + offset, means, width, yerr=stds,
               color=POLICY_COLORS[pol], label=POLICY_LABELS[pol],
               edgecolor="white", linewidth=0.6,
               error_kw=dict(ecolor="#333", lw=0.8, capsize=2.5))

    ax.set_xticks(x)
    ax.set_xticklabels([SCENARIO_LABELS[s] for s in SCENARIO_ORDER], rotation=15)
    ax.set_ylabel("Stockout rate (% of test-window steps)")
    ax.set_title("H1: Multi-agent system reduces stockouts vs both baselines\n"
                 "(N=10 seeds per cell; Mann–Whitney p ≤ 0.004 in every comparison)")
    ax.legend(loc="upper left", frameon=False)
    ax.set_ylim(0, 100)
    _save(fig, "h1_stockout_rate")


# ============================================================================
# Figure 2: H1 cost decomposition (stacked) per (scenario, policy)
# ============================================================================
def fig_h1_cost_decomposition() -> None:
    """Stacked cost decomposition per (scenario × policy).

    Design notes (post-review):
    - sharey=True is kept so bars are visually comparable across the six
      scenarios; the substantive H2-reframe finding is precisely that
      the totals are roughly the same except under catastrophic.
    - Total-cost value labels are added on top of every stacked column so
      small but real differences (e.g. MAS goes 185k -> 210k -> 304k
      across no_drift -> severe_abrupt -> catastrophic) are readable
      even though they're invisible at the bar-height level.
    - A footnote on the figure flags the stockout-cost sub-pixel issue:
      orange slices for MAS and Periodic are visually absent because
      their stockout cost is under $1.5k against a ~$650k axis, which
      could otherwise be misread as "no stockout penalty modeled."
    """
    print("Figure 2: cost decomposition (with value labels)")
    fig, axes = plt.subplots(2, 3, figsize=(11.5, 6.6), sharey=True)
    axes = axes.flatten()
    cost_keys = [("holding_cost", "Holding"),
                 ("ordering_cost", "Ordering"),
                 ("stockout_cost", "Stockout")]
    cost_colors = ["#0072B2", "#56B4E9", "#D55E00"]

    # Per-policy short labels reused across subplots.
    pol_labels = [
        POLICY_LABELS[p]
        .replace(" (proposed)", "")
        .replace("Periodic Forecasting", "Periodic")
        for p in POLICY_ORDER
    ]

    for ax, scen in zip(axes, SCENARIO_ORDER):
        x = np.arange(len(POLICY_ORDER))
        bottoms = np.zeros(len(POLICY_ORDER))
        # Track the per-policy total so we can label the top of each
        # stacked column with a single dollar figure.
        totals = np.zeros(len(POLICY_ORDER))

        for (key, label), color in zip(cost_keys, cost_colors):
            heights = []
            for pol in POLICY_ORDER:
                agg = _load_agg(f"olist_{pol}_{scen}")
                mt = _agg_metric(agg, key)
                heights.append(mt[0] if mt else 0.0)
            ax.bar(x, heights, bottom=bottoms, color=color, label=label,
                   edgecolor="white", linewidth=0.5, width=0.6)
            bottoms += np.array(heights)
            totals += np.array(heights)

        # Total-cost value label on top of each stacked column.
        for xi, total in zip(x, totals):
            if total <= 0:
                continue
            ax.text(
                xi, total + 12_000,  # ~2% of typical axis range above the bar
                f"${total/1000:.0f}k",
                ha="center", va="bottom",
                fontsize=8.2, fontweight="bold", color="#1F2933",
            )

        ax.set_xticks(x)
        ax.set_xticklabels(pol_labels, rotation=15)
        ax.set_title(SCENARIO_LABELS[scen], fontsize=10)
        ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(
            lambda v, _: f"${v/1000:.0f}k"))

    # Add headroom so the topmost value label doesn't get clipped by the
    # subplot frame. The catastrophic Periodic bar (~$648k) is the tallest.
    for ax in axes:
        ymin, ymax = ax.get_ylim()
        ax.set_ylim(ymin, max(ymax, 720_000))

    axes[0].set_ylabel("Total cost (USD over 504-day test window)")
    axes[3].set_ylabel("Total cost (USD over 504-day test window)")

    # Single legend at top.
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=3, frameon=False,
               bbox_to_anchor=(0.5, 1.01))
    fig.suptitle(
        "Cost decomposition: holding + ordering + stockout per scenario × policy",
        y=1.05, fontsize=11,
    )

    # Caption note flagging the sub-pixel stockout slices for MAS/Periodic.
    fig.text(
        0.5, -0.02,
        "Stockout cost for MAS and Periodic is < $1.5k in every scenario; "
        "the orange slice is therefore not visible at this y-scale "
        "(see Table 4.3 / dashboard /reports/h1 for the exact values).",
        ha="center", va="top",
        fontsize=8.4, style="italic", color="#4B5563",
    )

    plt.tight_layout()
    _save(fig, "h1_cost_decomposition")


# ============================================================================
# Figure 3: H3 scaling curves (runtime vs SKU count, log-log)
# ============================================================================
def fig_h3_scaling() -> None:
    print("Figure 3: H3 scaling")
    h3_path = RESULTS / "h3_report.json"
    if not h3_path.exists():
        print("  -> h3_report.json missing, skipping")
        return
    with open(h3_path) as f:
        h3 = json.load(f)
    rows = h3["rows"]
    fits = h3["fits"]

    fig, (ax_t, ax_m) = plt.subplots(1, 2, figsize=(11, 4.2))

    for pol in POLICY_ORDER:
        pol_rows = sorted([r for r in rows if r["policy"] == pol],
                          key=lambda r: r["n_skus"])
        if not pol_rows:
            continue
        ns = np.array([r["n_skus"] for r in pol_rows], dtype=float)
        rts = np.array([r["runtime_seconds_mean"] for r in pol_rows])
        stds = np.array([r["runtime_seconds_std"] for r in pol_rows])
        mems = np.array([r["peak_python_mem_mb_mean"] for r in pol_rows])

        ax_t.errorbar(ns, rts, yerr=stds, fmt="o", capsize=3, lw=1.3, ms=7,
                      color=POLICY_COLORS[pol], label=POLICY_LABELS[pol])
        # Power-law fit overlay.
        if pol in fits:
            a = fits[pol]["runtime_powerlaw"]["a"]
            b = fits[pol]["runtime_powerlaw"]["b"]
            xs_fit = np.linspace(ns.min(), ns.max(), 100)
            ys_fit = a * xs_fit ** b
            ax_t.plot(xs_fit, ys_fit, "--", color=POLICY_COLORS[pol], alpha=0.6,
                      lw=1.0, label=f"  fit: $t \\propto n^{{{b:.2f}}}$")

        ax_m.plot(ns, mems, "o-", lw=1.3, ms=7,
                  color=POLICY_COLORS[pol], label=POLICY_LABELS[pol])

    for ax, ylabel, title in [
        (ax_t, "Runtime per run (seconds)",
         "H3: Runtime scaling vs SKU count"),
        (ax_m, "Peak Python heap (MB)",
         "Peak memory scaling vs SKU count"),
    ]:
        ax.set_xscale("log")
        ax.set_yscale("log" if ax is ax_t else "linear")
        ax.set_xlabel("Number of SKUs (log scale)")
        ax.set_ylabel(ylabel)
        ax.set_title(title, fontsize=10.5)
        ax.legend(loc="upper left", frameon=False, fontsize=8.5)

    fig.suptitle(
        "H3: All three policies scale sublinearly; MAS runtime is "
        "effectively constant in N\n"
        f"(MAS power-law exponent b = {fits.get('mas', {}).get('runtime_powerlaw', {}).get('b', 0):.3f}, far below 1.0)",
        y=1.04, fontsize=11
    )
    plt.tight_layout()
    _save(fig, "h3_scaling")


# ============================================================================
# Figure 4: Ablation results on catastrophic
# ============================================================================
def fig_ablation() -> None:
    print("Figure 4: ablation")
    rep_path = RESULTS / "ablation_report.json"
    if not rep_path.exists():
        print("  -> ablation_report.json missing, skipping")
        return
    with open(rep_path) as f:
        rep = json.load(f)
    rows = rep["rows"]
    if not rows:
        return

    VARIANTS = ["full", "no_adwin", "ma_only", "no_safety"]
    VARIANT_LABELS = {
        "full": "Full MAS",
        "no_adwin": "No ADWIN",
        "ma_only": "MA only",
        "no_safety": "No safety stock",
    }
    VARIANT_COLORS = {
        "full": "#009E73",
        "no_adwin": "#CC79A7",
        "ma_only": "#0072B2",
        "no_safety": "#D55E00",
    }

    fig, (ax_so, ax_cost) = plt.subplots(1, 2, figsize=(10, 4.0))
    xs = np.arange(len(VARIANTS))

    so_means, so_stds, cost_means, cost_stds = [], [], [], []
    for v in VARIANTS:
        r = next((r for r in rows if r["variant"] == v), None)
        if not r:
            so_means.append(0); so_stds.append(0)
            cost_means.append(0); cost_stds.append(0)
            continue
        so_means.append(r.get("stockout_rate_mean", 0) * 100)
        so_stds.append(r.get("stockout_rate_std", 0) * 100)
        cost_means.append(r.get("total_cost_mean", 0) / 1000)
        cost_stds.append(r.get("total_cost_std", 0) / 1000)

    colors = [VARIANT_COLORS[v] for v in VARIANTS]
    ax_so.bar(xs, so_means, yerr=so_stds, color=colors, width=0.6,
              edgecolor="white", linewidth=0.6,
              error_kw=dict(ecolor="#333", lw=0.8, capsize=3))
    ax_so.set_xticks(xs)
    ax_so.set_xticklabels([VARIANT_LABELS[v] for v in VARIANTS], rotation=15)
    ax_so.set_ylabel("Stockout rate (%)")
    ax_so.set_title("Ablation: stockout rate (catastrophic scenario)")

    ax_cost.bar(xs, cost_means, yerr=cost_stds, color=colors, width=0.6,
                edgecolor="white", linewidth=0.6,
                error_kw=dict(ecolor="#333", lw=0.8, capsize=3))
    ax_cost.set_xticks(xs)
    ax_cost.set_xticklabels([VARIANT_LABELS[v] for v in VARIANTS], rotation=15)
    ax_cost.set_ylabel("Total cost (thousand $)")
    ax_cost.set_title("Ablation: total cost (catastrophic scenario)")

    fig.suptitle("Component contributions: which agent capability drives the win?",
                 y=1.02, fontsize=11)
    plt.tight_layout()
    _save(fig, "ablation")


# ============================================================================
# Figure 5: Forecast MAPE per scenario (MAS only)
# ============================================================================
def fig_mape() -> None:
    print("Figure 5: forecast MAPE per scenario")
    means, stds = [], []
    for scen in SCENARIO_ORDER:
        agg = _load_agg(f"olist_mas_{scen}")
        mt = _agg_metric(agg, "forecast_mape")
        if mt:
            means.append(mt[0] * 100); stds.append(mt[1] * 100)
        else:
            means.append(0); stds.append(0)

    fig, ax = plt.subplots(figsize=(8, 3.5))
    x = np.arange(len(SCENARIO_ORDER))
    ax.bar(x, means, yerr=stds, color=POLICY_COLORS["mas"], width=0.55,
           edgecolor="white", linewidth=0.6,
           error_kw=dict(ecolor="#333", lw=0.8, capsize=3))
    ax.set_xticks(x)
    ax.set_xticklabels([SCENARIO_LABELS[s] for s in SCENARIO_ORDER], rotation=15)
    ax.set_ylabel("Forecast MAPE (%)")
    ax.set_title("Forecast accuracy under each scenario (MAS, mean across seeds)")
    plt.tight_layout()
    _save(fig, "mas_mape_per_scenario")


# ============================================================================
# Figure 6: On-hand inventory time series (catastrophic, mean ± IQR)
# ============================================================================
def fig_timeseries_catastrophic() -> None:
    print("Figure 6: catastrophic time series")
    import pandas as pd

    fig, (ax_oh, ax_so) = plt.subplots(2, 1, figsize=(10, 5.5), sharex=True)
    drift_onset = None

    for pol in POLICY_ORDER:
        base = RESULTS / f"olist_{pol}_catastrophic"
        if not base.exists():
            continue
        frames = []
        for sd in sorted(base.glob("seed_*")):
            p = sd / "timeseries.csv"
            if p.exists():
                df = pd.read_csv(p)
                frames.append(df)
        if not frames:
            continue
        all_df = pd.concat(frames, ignore_index=True)
        agg = all_df.groupby("step").agg(
            on_hand_mean=("total_on_hand", "mean"),
            on_hand_q25=("total_on_hand", lambda s: s.quantile(0.25)),
            on_hand_q75=("total_on_hand", lambda s: s.quantile(0.75)),
            so_mean=("stockout_skus_step", "mean"),
            so_q25=("stockout_skus_step", lambda s: s.quantile(0.25)),
            so_q75=("stockout_skus_step", lambda s: s.quantile(0.75)),
        ).reset_index()

        c = POLICY_COLORS[pol]
        ax_oh.plot(agg["step"], agg["on_hand_mean"], color=c, lw=1.3,
                   label=POLICY_LABELS[pol])
        ax_oh.fill_between(agg["step"], agg["on_hand_q25"], agg["on_hand_q75"],
                           color=c, alpha=0.18, lw=0)
        ax_so.plot(agg["step"], agg["so_mean"], color=c, lw=1.3,
                   label=POLICY_LABELS[pol])
        ax_so.fill_between(agg["step"], agg["so_q25"], agg["so_q75"],
                           color=c, alpha=0.18, lw=0)

        # Try to extract drift onset from any summary in this cohort.
        if drift_onset is None:
            try:
                with open(next(base.glob("seed_*"))/"summary.json") as f:
                    s = json.load(f)
                drift_onset = s.get("drift_start_step")
            except Exception:
                pass

    for ax in (ax_oh, ax_so):
        if drift_onset is not None:
            ax.axvline(drift_onset, color="#444", linestyle="--", lw=1)
        ax.legend(loc="upper left", frameon=False, fontsize=8.5)

    ax_oh.set_ylabel("Total on-hand inventory (units)")
    ax_oh.set_title("Catastrophic scenario: on-hand inventory over time\n"
                    "(mean across N=10 seeds; shaded band = interquartile range)")
    ax_so.set_ylabel("SKUs in stockout (count)")
    ax_so.set_xlabel("Simulation step (days)")
    plt.tight_layout()
    _save(fig, "timeseries_catastrophic")


# ============================================================================
# Main
# ============================================================================
def main() -> None:
    print(f"Writing figures to {FIGURES}/ ...\n")
    fig_h1_stockout()
    fig_h1_cost_decomposition()
    fig_h3_scaling()
    fig_ablation()
    fig_mape()
    fig_timeseries_catastrophic()
    print(f"\nDone. {len(list(FIGURES.glob('*.pdf')))} PDF(s) + "
          f"{len(list(FIGURES.glob('*.png')))} PNG(s) in {FIGURES}/")


if __name__ == "__main__":
    main()
