"""Inventory MAS — thesis dashboard.

Streamlit app for exploring experiment results: pick runs, view summary
metrics, compare policies side-by-side, visualize time series with drift
overlays, and inspect cost breakdowns.

Launch:
    streamlit run app.py
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
import yaml

# ----------------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------------
RESULTS_DIR = Path("results")
CONFIGS_DIR = Path("experiments/configs")

POLICY_LABELS = {
    "static_rop": "Static ROP",
    "periodic_forecasting": "Periodic Forecasting",
    "mas": "MAS (proposed)",
}

POLICY_COLORS = {
    "static_rop": "#E63946",          # red — weakest baseline
    "periodic_forecasting": "#F4A261",  # amber — mid baseline
    "mas": "#2A9D8F",                 # teal — the proposed system
}

# ----------------------------------------------------------------------------
# Page setup + style
# ----------------------------------------------------------------------------
st.set_page_config(
    page_title="Inventory MAS — Thesis Dashboard",
    layout="wide",
    page_icon="📦",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    /* Tighten default padding */
    .block-container { padding-top: 2rem; padding-bottom: 3rem; max-width: 1400px; }

    /* Typography */
    h1 { font-weight: 700; letter-spacing: -0.02em; color: #f9fafb; }
    h2 { font-weight: 600; margin-top: 1.5rem; color: #f3f4f6; }
    h3 { font-weight: 600; color: #e5e7eb; }
    p, .stMarkdown { color: #d1d5db; }

    /* Custom metric cards — dark surfaces with subtle borders */
    div[data-testid="stMetric"] {
        background: #161b22;
        border: 1px solid #30363d;
        border-radius: 12px;
        padding: 1rem 1.25rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.4);
    }
    div[data-testid="stMetric"] > label {
        color: #9ca3af;
        font-size: 0.85rem;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.04em;
    }
    div[data-testid="stMetricValue"] { font-size: 1.7rem; font-weight: 700; color: #f9fafb; }
    div[data-testid="stMetricDelta"] { font-size: 0.85rem; }

    /* Sidebar */
    section[data-testid="stSidebar"] { background: #0b0f14; border-right: 1px solid #1f2937; }
    section[data-testid="stSidebar"] .stMarkdown { color: #d1d5db; }
    section[data-testid="stSidebar"] hr { border-color: #1f2937; }

    /* Tabs */
    button[role="tab"] { font-weight: 500; color: #d1d5db; }
    button[role="tab"][aria-selected="true"] { color: #2A9D8F; }

    /* DataFrames */
    div[data-testid="stDataFrame"] { border-radius: 8px; overflow: hidden; }

    /* Captions */
    .stCaption, [data-testid="stCaptionContainer"] { color: #9ca3af !important; }

    /* Selectbox / multiselect */
    div[data-baseweb="select"] > div { background-color: #161b22; border-color: #30363d; }

    /* Code blocks (used by st.json) */
    pre, code { background: #161b22 !important; color: #e5e7eb !important; }
    </style>
    """,
    unsafe_allow_html=True,
)

# Plotly template tuned for the dark theme.
PLOT_TEMPLATE = "plotly_dark"
PLOT_BG = "#0e1117"
PLOT_GRID = "#1f2937"
PLOT_AXIS = "#9ca3af"

# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------
@st.cache_data(show_spinner=False)
def list_runs() -> list[str]:
    if not RESULTS_DIR.exists():
        return []
    out = []
    for p in RESULTS_DIR.iterdir():
        if not p.is_dir():
            continue
        # A run is anything that has aggregate.json (multi-seed) or summary.json (single).
        if (p / "aggregate.json").exists() or (p / "summary.json").exists():
            out.append(p.name)
    return sorted(out)


@st.cache_data(show_spinner=False)
def load_aggregate(name: str) -> dict | None:
    p = RESULTS_DIR / name / "aggregate.json"
    if not p.exists():
        return None
    with open(p) as f:
        return json.load(f)


@st.cache_data(show_spinner=False)
def load_run(name: str) -> tuple[dict, pd.DataFrame | None]:
    """Load a run's top-level summary + a representative seed timeseries.

    If only seed-level outputs exist (no top-level summary.json), falls back
    to seed_001.
    """
    base = RESULTS_DIR / name
    summary_path = base / "summary.json"
    if not summary_path.exists():
        seed_path = base / "seed_001" / "summary.json"
        summary_path = seed_path if seed_path.exists() else summary_path
    with open(summary_path) as f:
        summary = json.load(f)
    ts_path = base / "timeseries.csv"
    if not ts_path.exists():
        ts_path = base / "seed_001" / "timeseries.csv"
    ts = pd.read_csv(ts_path) if ts_path.exists() else None
    return summary, ts


@st.cache_data(show_spinner=False)
def load_seed_timeseries(name: str) -> pd.DataFrame | None:
    """Return a long DataFrame [seed, step, total_on_hand, stockout_skus_step] for all seeds."""
    base = RESULTS_DIR / name
    frames = []
    for sd in sorted(base.glob("seed_*")):
        p = sd / "timeseries.csv"
        if p.exists():
            df = pd.read_csv(p)
            df["seed"] = sd.name
            frames.append(df)
    if not frames:
        return None
    return pd.concat(frames, ignore_index=True)


@st.cache_data(show_spinner=False)
def load_h1_report() -> pd.DataFrame | None:
    p = RESULTS_DIR / "h1_report.csv"
    if not p.exists():
        return None
    return pd.read_csv(p)


@st.cache_data(show_spinner=False)
def load_h3_report() -> dict | None:
    p = RESULTS_DIR / "h3_report.json"
    if not p.exists():
        return None
    with open(p) as f:
        return json.load(f)


def agg_metric(agg: dict | None, key: str) -> dict | None:
    """Return the {mean, std, ci95_lo, ci95_hi, n} dict for a metric or None."""
    if not agg:
        return None
    return agg.get("metrics", {}).get(key)


@st.cache_data(show_spinner=False)
def load_run_config(summary: dict) -> dict | None:
    cfg_path = summary.get("config")
    if not cfg_path or not Path(cfg_path).exists():
        return None
    with open(cfg_path) as f:
        return yaml.safe_load(f)


def parse_run_name(name: str) -> tuple[str, str]:
    """Return (policy, scenario) from a run name like 'olist_mas_catastrophic'."""
    parts = name.split("_")
    # Walk from the end: scenario suffix could be 1-3 words.
    for split_idx in range(2, len(parts)):
        prefix = "_".join(parts[:split_idx])
        suffix = "_".join(parts[split_idx:])
        if any(prefix.endswith(p) for p in POLICY_LABELS):
            policy = next(p for p in POLICY_LABELS if prefix.endswith(p))
            return policy, suffix
    return "unknown", name


def group_runs(names: list[str]) -> dict[str, list[str]]:
    """Group runs by scenario suffix."""
    groups: dict[str, list[str]] = {}
    for n in names:
        _, scen = parse_run_name(n)
        groups.setdefault(scen, []).append(n)
    return groups


def policy_of(summary: dict, name: str) -> str:
    return summary.get("policy") or parse_run_name(name)[0]


def policy_label(p: str) -> str:
    return POLICY_LABELS.get(p, p)


def policy_color(p: str) -> str:
    return POLICY_COLORS.get(p, "#6b7280")


def fmt_int(x) -> str:
    if x is None:
        return "—"
    try:
        return f"{int(x):,}"
    except (TypeError, ValueError):
        return str(x)


def fmt_pct(x) -> str:
    if x is None:
        return "—"
    try:
        return f"{float(x):.2%}"
    except (TypeError, ValueError):
        return str(x)


def fmt_money(x) -> str:
    if x is None:
        return "—"
    try:
        return f"${float(x):,.0f}"
    except (TypeError, ValueError):
        return str(x)

# ----------------------------------------------------------------------------
# Sidebar — run picker
# ----------------------------------------------------------------------------
runs = list_runs()
if not runs:
    st.error("No runs found. Generate some with `python -m experiments.run --config ...` first.")
    st.stop()

with st.sidebar:
    st.markdown("### 📦 Inventory MAS")
    st.caption("Thesis evaluation dashboard")
    st.markdown("---")
    view = st.radio(
        "View",
        ["Scenario comparison", "Scalability (H3)"],
        index=0,
    )
    st.markdown("---")
    st.markdown("**Compare runs**")

    grouped = group_runs(runs)
    # Filter out the `scale_<policy>_n<N>` runs from the scenario picker —
    # they live in their own view.
    grouped = {k: v for k, v in grouped.items() if not k.startswith("n")
               and not any(r.startswith("olist_scale") for r in v)}
    scenarios = sorted(grouped.keys())
    default_scenario = "catastrophic" if "catastrophic" in scenarios else scenarios[0]

    scenario = st.selectbox(
        "Scenario",
        scenarios,
        index=scenarios.index(default_scenario),
        help="Pick a drift scenario to compare across policies.",
        disabled=(view != "Scenario comparison"),
    )
    candidate_runs = grouped[scenario]
    selected = st.multiselect(
        "Runs",
        candidate_runs,
        default=candidate_runs,
        help="Two or more runs to compare side by side.",
    )

    st.markdown("---")
    st.markdown("**Single-run drilldown**")
    detail_run = st.selectbox(
        "Inspect",
        selected if selected else candidate_runs,
        index=0 if (selected or candidate_runs) else None,
    )

    st.markdown("---")
    st.caption(
        f"📁 {len(runs)} total run(s) under `{RESULTS_DIR}/`. "
        "Refresh the page after new runs."
    )

# ----------------------------------------------------------------------------
# Header
# ----------------------------------------------------------------------------
st.markdown("# Inventory MAS — Evaluation Dashboard")
st.markdown(
    "Comparing a 5-agent inventory system against two traditional baselines on the "
    "Olist Brazilian E-Commerce dataset, with optional injected concept drift."
)

# -- Scalability view (H3) ---------------------------------------------------
if view == "Scalability (H3)":
    st.markdown("## H3 — Computational scalability")
    st.caption(
        "Power-law fit `t = a · n^b` to runtime vs SKU count. "
        "**b ≈ 1.0 → linear (H3 supported); b < 1.0 → sublinear (better than H3); "
        "b > 1.2 → super-linear (H3 rejected).**"
    )
    h3 = load_h3_report()
    if h3 is None:
        st.warning(
            "No H3 report on disk yet. Run "
            "`python -m experiments.sweep -c experiments/configs/olist_scale_*.yaml --seeds 1..5` "
            "then `python -m experiments.aggregate results/olist_scale_*` "
            "then `python -m experiments.h3_report`."
        )
    else:
        rows = h3["rows"]
        fits = h3["fits"]

        # Headline cards: one per policy with b + classification.
        st.markdown("### Complexity classification")
        if fits:
            cols = st.columns(len(fits))
            for col, (pol, fit) in zip(cols, fits.items()):
                rp = fit["runtime_powerlaw"]
                b = rp["b"]
                classification = rp["complexity"]
                color = (
                    "#22c55e" if classification in ("near-constant", "sublinear", "linear")
                    else "#f59e0b" if classification == "near-linear"
                    else "#ef4444"
                )
                with col:
                    st.markdown(
                        f"<div style='border:1px solid #30363d;border-radius:12px;"
                        f"padding:1.2rem;background:#161b22;'>"
                        f"<div style='display:flex;align-items:center;gap:0.5rem;margin-bottom:0.5rem;'>"
                        f"<span style='width:10px;height:10px;border-radius:50%;background:{policy_color(pol)};display:inline-block;'></span>"
                        f"<span style='font-weight:600;color:#e5e7eb;font-size:0.95rem;'>{policy_label(pol)}</span>"
                        f"</div>"
                        f"<div style='color:#9ca3af;font-size:0.75rem;letter-spacing:0.05em;text-transform:uppercase;'>exponent b</div>"
                        f"<div style='font-size:2.2rem;font-weight:700;color:#f9fafb;margin-bottom:0.3rem;'>"
                        f"{b:.3f}</div>"
                        f"<div style='color:{color};font-weight:600;text-transform:capitalize;'>"
                        f"{classification}</div>"
                        f"<div style='color:#d1d5db;font-size:0.85rem;margin-top:0.5rem;'>"
                        f"R² (log-log) = {rp['r2']:.3f}<br>"
                        f"Linear R² = {fit['runtime_linear']['r2']:.3f}<br>"
                        f"Memory exponent = {fit['memory_powerlaw']['b']:.3f}"
                        f"</div></div>",
                        unsafe_allow_html=True,
                    )

        # Runtime plot — log-log with fitted lines.
        st.markdown("### Runtime vs SKU count")
        fig = go.Figure()
        for pol in POLICY_LABELS:
            pol_rows = sorted([r for r in rows if r["policy"] == pol],
                              key=lambda r: r["n_skus"])
            if not pol_rows:
                continue
            xs = [r["n_skus"] for r in pol_rows]
            ys = [r.get("runtime_seconds_mean", 0) for r in pol_rows]
            stds = [r.get("runtime_seconds_std", 0) for r in pol_rows]
            fig.add_trace(go.Scatter(
                x=xs, y=ys, mode="lines+markers", name=policy_label(pol),
                line=dict(color=policy_color(pol), width=2),
                marker=dict(size=10),
                error_y=dict(type="data", array=stds, color=policy_color(pol),
                             thickness=1.2, width=4),
                hovertemplate="N=%{x}<br>runtime=%{y:.2f}s<extra></extra>",
            ))
            # Power-law fit overlay.
            fit = fits.get(pol)
            if fit:
                a, b = fit["runtime_powerlaw"]["a"], fit["runtime_powerlaw"]["b"]
                xs_fit = list(range(min(xs), max(xs) + 1, max((max(xs) - min(xs)) // 50, 1)))
                ys_fit = [a * (x ** b) for x in xs_fit]
                fig.add_trace(go.Scatter(
                    x=xs_fit, y=ys_fit, mode="lines",
                    line=dict(color=policy_color(pol), width=1, dash="dot"),
                    name=f"{policy_label(pol)} fit (b={b:.2f})",
                    hoverinfo="skip", showlegend=False,
                ))
        fig.update_layout(
            template=PLOT_TEMPLATE,
            height=460,
            plot_bgcolor=PLOT_BG, paper_bgcolor=PLOT_BG,
            font=dict(color="#d1d5db"),
            xaxis=dict(title="SKU count (log)", type="log",
                       gridcolor=PLOT_GRID, zerolinecolor=PLOT_GRID, color=PLOT_AXIS),
            yaxis=dict(title="Runtime (s, log)", type="log",
                       gridcolor=PLOT_GRID, zerolinecolor=PLOT_GRID, color=PLOT_AXIS),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0.5, xanchor="center"),
            margin=dict(t=30, l=20, r=20, b=20),
        )
        st.plotly_chart(fig, use_container_width=True)

        # Memory plot.
        st.markdown("### Peak Python heap vs SKU count")
        fig_mem = go.Figure()
        for pol in POLICY_LABELS:
            pol_rows = sorted([r for r in rows if r["policy"] == pol],
                              key=lambda r: r["n_skus"])
            if not pol_rows:
                continue
            xs = [r["n_skus"] for r in pol_rows]
            ys = [r.get("peak_python_mem_mb_mean", 0) for r in pol_rows]
            fig_mem.add_trace(go.Scatter(
                x=xs, y=ys, mode="lines+markers", name=policy_label(pol),
                line=dict(color=policy_color(pol), width=2),
                marker=dict(size=10),
                hovertemplate="N=%{x}<br>peak heap=%{y:.1f} MB<extra></extra>",
            ))
        fig_mem.update_layout(
            template=PLOT_TEMPLATE,
            height=380,
            plot_bgcolor=PLOT_BG, paper_bgcolor=PLOT_BG,
            font=dict(color="#d1d5db"),
            xaxis=dict(title="SKU count", gridcolor=PLOT_GRID, zerolinecolor=PLOT_GRID, color=PLOT_AXIS),
            yaxis=dict(title="peak heap (MB)", gridcolor=PLOT_GRID, zerolinecolor=PLOT_GRID, color=PLOT_AXIS),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0.5, xanchor="center"),
            margin=dict(t=30, l=20, r=20, b=20),
        )
        st.plotly_chart(fig_mem, use_container_width=True)

        # Raw table.
        st.markdown("### Raw measurements")
        st.caption("Means across seeds; std is the per-cell standard deviation.")
        df = pd.DataFrame([
            {
                "Policy": policy_label(r["policy"]),
                "SKUs": r["n_skus"],
                "Seeds": r.get("n_seeds"),
                "Runtime (s)": f"{r.get('runtime_seconds_mean', 0):.2f} ± {r.get('runtime_seconds_std', 0):.2f}",
                "Time/step (ms)": f"{r.get('time_per_step_ms_mean', 0):.2f}",
                "Peak heap (MB)": f"{r.get('peak_python_mem_mb_mean', 0):.1f}",
                "Stockout": f"{r.get('stockout_rate_mean', 0):.2%}",
                "Refits": f"{r.get('n_refits_mean', 0):.0f}",
            }
            for r in sorted(rows, key=lambda r: (list(POLICY_LABELS).index(r['policy']) if r['policy'] in POLICY_LABELS else 99, r["n_skus"]))
        ])
        st.dataframe(df, hide_index=True, use_container_width=True)
    st.stop()  # don't render the scenario-comparison body below

# Load selected runs
loaded = []
for name in selected:
    summary, ts = load_run(name)
    agg = load_aggregate(name)
    loaded.append((name, summary, ts, agg))

if not loaded:
    st.warning("Select at least one run from the sidebar.")
    st.stop()

# Sort: static_rop, periodic_forecasting, mas
loaded.sort(key=lambda x: list(POLICY_LABELS).index(policy_of(x[1], x[0]))
            if policy_of(x[1], x[0]) in POLICY_LABELS else 99)

# Total-seed count across selected runs (for the banner)
n_seeds_total = sum(
    (agg or {}).get("n_seeds", 0) for _, _, _, agg in loaded
)
if n_seeds_total > 0:
    st.success(
        f"Multi-seed evaluation: **{n_seeds_total} runs across {len(loaded)} conditions** "
        f"(N={loaded[0][3]['n_seeds']} seeds each)."
    )

# ----------------------------------------------------------------------------
# Section 1 — Summary cards (the headline)
# ----------------------------------------------------------------------------
st.markdown("## Headline metrics")
st.caption(f"Scenario: **{scenario}**")

def _val_and_ci(agg: dict | None, summary: dict, key: str, formatter):
    """Return (display_str, ci_str_or_None). Prefers aggregate mean+CI when available."""
    m = agg_metric(agg, key)
    if m is not None:
        return formatter(m["mean"]), f"95% CI [{formatter(m['ci95_lo'])}, {formatter(m['ci95_hi'])}]"
    return formatter(summary.get(key)), None


cols = st.columns(len(loaded))
for col, (name, summary, _, agg) in zip(cols, loaded):
    pol = policy_of(summary, name)
    with col:
        st.markdown(
            f"<div style='display:flex;align-items:center;gap:0.5rem;'>"
            f"<span style='width:10px;height:10px;border-radius:50%;background:{policy_color(pol)};display:inline-block;'></span>"
            f"<span style='font-weight:600;color:#e5e7eb;font-size:0.95rem;'>{policy_label(pol)}</span>"
            f"</div>",
            unsafe_allow_html=True,
        )
        for label, key, fmt in [
            ("Stockout rate", "stockout_rate", fmt_pct),
            ("Total cost", "total_cost", fmt_money),
            ("Orders placed", "n_orders", fmt_int),
            ("Forecast MAPE", "forecast_mape", fmt_pct),
        ]:
            v, ci = _val_and_ci(agg, summary, key, fmt)
            st.metric(label, v, delta=ci, delta_color="off")

# ----------------------------------------------------------------------------
# Section 2 — Tabs: time series / cost / drift / details
# ----------------------------------------------------------------------------
tab_ts, tab_cost, tab_drift, tab_stats, tab_table = st.tabs(
    ["📈 Time series", "💰 Cost breakdown", "⚠️ Drift detection",
     "🧪 Statistical tests (H1)", "📋 Full metrics"]
)

# --- Time series tab ---
with tab_ts:
    st.markdown("### Per-step behavior across the test window")
    st.caption(
        "Mean across seeds with shaded interquartile range (Q25–Q75). "
        "Drift onset shown as a vertical dashed line."
    )

    drift_onset = None
    for name, summary, _, _ in loaded:
        ds = summary.get("drift_start_step")
        if ds is not None:
            drift_onset = ds
            break

    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True,
        subplot_titles=("Total on-hand inventory", "SKUs in stockout per step"),
        vertical_spacing=0.12,
    )

    def _hex_to_rgba(hex_color: str, alpha: float) -> str:
        h = hex_color.lstrip("#")
        r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
        return f"rgba({r},{g},{b},{alpha})"

    for name, summary, ts_seed1, agg in loaded:
        pol = policy_of(summary, name)
        color = policy_color(pol)

        all_seeds = load_seed_timeseries(name)
        for col_idx, (metric, row_num) in enumerate(
            [("total_on_hand", 1), ("stockout_skus_step", 2)]
        ):
            if all_seeds is not None:
                grouped = all_seeds.groupby("step")[metric]
                mean = grouped.mean().sort_index()
                q25 = grouped.quantile(0.25).sort_index()
                q75 = grouped.quantile(0.75).sort_index()
                xs = mean.index.tolist()
                # Shaded band (upper, then lower, filled to next y).
                fig.add_trace(
                    go.Scatter(
                        x=xs + xs[::-1],
                        y=q75.tolist() + q25.tolist()[::-1],
                        fill="toself", fillcolor=_hex_to_rgba(color, 0.18),
                        line=dict(width=0), hoverinfo="skip",
                        showlegend=False, legendgroup=pol,
                    ),
                    row=row_num, col=1,
                )
                # Mean line on top.
                fig.add_trace(
                    go.Scatter(
                        x=xs, y=mean.tolist(),
                        mode="lines", name=policy_label(pol),
                        line=dict(color=color, width=2),
                        legendgroup=pol, showlegend=(row_num == 1),
                        hovertemplate=f"step=%{{x}}<br>{metric}=%{{y:,.0f}} (mean of N seeds)<extra></extra>",
                    ),
                    row=row_num, col=1,
                )
            elif ts_seed1 is not None and not ts_seed1.empty:
                ts_seed1 = ts_seed1.sort_values("step")
                fig.add_trace(
                    go.Scatter(
                        x=ts_seed1["step"], y=ts_seed1[metric],
                        mode="lines", name=policy_label(pol),
                        line=dict(color=color, width=2),
                        legendgroup=pol, showlegend=(row_num == 1),
                    ),
                    row=row_num, col=1,
                )

    # Drift onset overlay
    if drift_onset is not None:
        for row in (1, 2):
            fig.add_vline(
                x=drift_onset, line_dash="dash", line_color="#6b7280",
                annotation_text="drift onset" if row == 1 else None,
                annotation_position="top right",
                row=row, col=1,
            )

    fig.update_layout(
        template=PLOT_TEMPLATE,
        height=620, hovermode="x unified", margin=dict(t=50, l=20, r=20, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.06, x=0.5, xanchor="center"),
        plot_bgcolor=PLOT_BG, paper_bgcolor=PLOT_BG,
        font=dict(color="#d1d5db"),
    )
    fig.update_xaxes(title_text="simulation step (days)", row=2, col=1,
                     gridcolor=PLOT_GRID, zerolinecolor=PLOT_GRID, color=PLOT_AXIS)
    fig.update_xaxes(gridcolor=PLOT_GRID, zerolinecolor=PLOT_GRID, color=PLOT_AXIS, row=1, col=1)
    fig.update_yaxes(gridcolor=PLOT_GRID, zerolinecolor=PLOT_GRID, color=PLOT_AXIS)
    st.plotly_chart(fig, use_container_width=True)

# --- Cost breakdown tab ---
with tab_cost:
    st.markdown("### Cost decomposition")
    st.caption(
        "Total cost = holding + ordering + stockout. Weights are configurable "
        "per run (defaults: holding=0.01/unit/day, ordering=$50/order, stockout=$5/SKU-day)."
    )

    cost_rows = []
    for name, summary, _, agg in loaded:
        pol = policy_of(summary, name)
        # Use aggregate means when available; fall back to single-run summary.
        def get(k, default=0):
            m = agg_metric(agg, k)
            return m["mean"] if m else summary.get(k, default)
        cost_rows.append({
            "policy": policy_label(pol),
            "color": policy_color(pol),
            "Holding": get("holding_cost"),
            "Ordering": get("ordering_cost"),
            "Stockout": get("stockout_cost"),
            "Total": get("total_cost"),
        })

    fig = go.Figure()
    for component, comp_color in [
        ("Holding", "#1f3a5f"),
        ("Ordering", "#4a90c2"),
        ("Stockout", "#c0392b"),
    ]:
        fig.add_trace(
            go.Bar(
                x=[r["policy"] for r in cost_rows],
                y=[r[component] for r in cost_rows],
                name=component,
                marker_color=comp_color,
                hovertemplate=f"{component}: $%{{y:,.0f}}<extra></extra>",
            )
        )
    fig.update_layout(
        template=PLOT_TEMPLATE,
        barmode="stack",
        height=430,
        margin=dict(t=10, l=20, r=20, b=20),
        plot_bgcolor=PLOT_BG, paper_bgcolor=PLOT_BG,
        font=dict(color="#d1d5db"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0.5, xanchor="center"),
        yaxis=dict(title="cost ($)", tickformat=",", gridcolor=PLOT_GRID,
                   zerolinecolor=PLOT_GRID, color=PLOT_AXIS),
        xaxis=dict(gridcolor=PLOT_GRID, zerolinecolor=PLOT_GRID, color=PLOT_AXIS),
    )
    st.plotly_chart(fig, use_container_width=True)

    # Per-component table
    df = pd.DataFrame([
        {
            "Policy": r["policy"],
            "Holding": fmt_money(r["Holding"]),
            "Ordering": fmt_money(r["Ordering"]),
            "Stockout": fmt_money(r["Stockout"]),
            "Total": fmt_money(r["Total"]),
        }
        for r in cost_rows
    ])
    st.dataframe(df, hide_index=True, use_container_width=True)

# --- Drift tab ---
with tab_drift:
    st.markdown("### Drift detection events (MAS only)")
    st.caption(
        "ADWIN watches the population mean of forecast residuals. A global event "
        "triggers refits across the SKUs that contributed to that step's signal."
    )

    drift_rows = []
    for name, summary, _, agg in loaded:
        pol = policy_of(summary, name)
        if pol != "mas":
            continue
        def get(k, default=0):
            m = agg_metric(agg, k)
            return m["mean"] if m else summary.get(k, default)
        drift_rows.append({
            "Run": name,
            "Global drift events": get("n_global_drift_events"),
            "Per-SKU drift events": get("n_drift_events"),
            "Total refits": get("n_refits"),
            "Forecast MAPE": fmt_pct(get("forecast_mape")),
            "Active models": summary.get("active_model_methods", {}),
        })

    if not drift_rows:
        st.info("No MAS runs in the current selection.")
    else:
        for r in drift_rows:
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Global drift events", fmt_int(r["Global drift events"]))
            c2.metric("Per-SKU drift events", fmt_int(r["Per-SKU drift events"]))
            c3.metric("Refits triggered", fmt_int(r["Total refits"]))
            c4.metric("MAPE", r["Forecast MAPE"])
            am = r["Active models"]
            if isinstance(am, dict) and am:
                model_chips = " &nbsp;|&nbsp; ".join(
                    f"<b>{k.upper()}</b> {v}" for k, v in am.items()
                )
                st.markdown(
                    f"<div style='color:#6b7280;font-size:0.85rem;margin-top:-0.5rem;'>Active model methods: {model_chips}</div>",
                    unsafe_allow_html=True,
                )
            st.markdown("")

# --- Statistical tests tab ---
with tab_stats:
    st.markdown("### Hypothesis H1: MAS reduces stockout rate vs baselines")
    st.caption(
        "Mann-Whitney U is the primary test (non-parametric, no normality "
        "assumption). Welch's t and Cohen's d are reported for completeness. "
        "**Significance threshold: p < 0.05.** Note: MW p-floor with N=10 vs 10 "
        "is 0.0002 (two-sided)."
    )

    h1 = load_h1_report()
    if h1 is None or h1.empty:
        st.info("Run `python -m experiments.h1_report` to generate H1 tests.")
    else:
        # Filter to current scenario
        scen_rows = h1[h1["scenario"] == scenario].copy()
        if scen_rows.empty:
            st.info(f"No H1 tests on file for scenario '{scenario}'.")
        else:
            for metric in ["stockout_rate", "total_cost"]:
                m_rows = scen_rows[scen_rows["metric"] == metric]
                if m_rows.empty:
                    continue
                st.markdown(f"#### {metric}")
                cols = st.columns(len(m_rows))
                for (_, row), col in zip(m_rows.iterrows(), cols):
                    p_value = float(row["mannwhitney_p"])
                    sig_color = "#22c55e" if p_value < 0.05 else "#9ca3af"
                    sig_label = "✅ significant" if p_value < 0.05 else "n.s."
                    with col:
                        st.markdown(
                            f"<div style='border:1px solid #30363d;border-radius:10px;"
                            f"padding:1rem;background:#161b22;'>"
                            f"<div style='color:#9ca3af;font-size:0.8rem;letter-spacing:0.05em;"
                            f"text-transform:uppercase;margin-bottom:0.3rem;'>"
                            f"MAS vs {row['baseline']}</div>"
                            f"<div style='color:#f9fafb;font-size:1.5rem;font-weight:700;"
                            f"margin-bottom:0.4rem;'>"
                            f"{float(row['rel_change']):+.1%} relative</div>"
                            f"<div style='color:{sig_color};font-size:0.9rem;font-weight:600;'>"
                            f"{sig_label}</div>"
                            f"<div style='color:#d1d5db;font-size:0.85rem;margin-top:0.5rem;'>"
                            f"Mann-Whitney p = <b>{p_value:.4f}</b><br>"
                            f"Welch's t p = {float(row['welch_p']):.2e}<br>"
                            f"Cohen's d = {float(row['cohens_d']):+.2f}"
                            f"</div></div>",
                            unsafe_allow_html=True,
                        )

        st.markdown("---")
        st.markdown("#### Full H1 report (all scenarios × baselines × metrics)")
        st.caption("From `results/h1_report.csv`")
        # Light formatting for display.
        display_h1 = h1.copy()
        display_h1["mannwhitney_p"] = display_h1["mannwhitney_p"].apply(lambda x: f"{x:.4f}")
        display_h1["welch_p"] = display_h1["welch_p"].apply(lambda x: f"{x:.2e}")
        display_h1["cohens_d"] = display_h1["cohens_d"].apply(lambda x: f"{x:+.1f}")
        display_h1["rel_change"] = display_h1["rel_change"].apply(lambda x: f"{x:+.1%}")
        display_h1["abs_diff"] = display_h1["abs_diff"].apply(lambda x: f"{x:+.4f}")
        st.dataframe(
            display_h1[[
                "scenario", "baseline", "metric", "n_treatment", "n_baseline",
                "rel_change", "mannwhitney_p", "welch_p", "cohens_d",
            ]],
            hide_index=True, use_container_width=True,
        )

# --- Full metrics table tab ---
with tab_table:
    st.markdown("### All summary fields")
    rows = []
    for name, summary, _, agg in loaded:
        flat = {k: v for k, v in summary.items() if not isinstance(v, (dict, list))}
        if agg:
            flat["n_seeds"] = agg.get("n_seeds")
        flat["__run"] = name
        rows.append(flat)
    df = pd.DataFrame(rows).set_index("__run").T
    st.dataframe(df, use_container_width=True)

# ----------------------------------------------------------------------------
# Section 3 — Single-run drilldown
# ----------------------------------------------------------------------------
if detail_run and detail_run in [n for n, _, _, _ in loaded]:
    st.markdown("---")
    st.markdown(f"## Drilldown — `{detail_run}`")
    summary, ts = next((s, t) for n, s, t, _ in loaded if n == detail_run)
    cfg = load_run_config(summary)
    pol = policy_of(summary, detail_run)

    c1, c2 = st.columns([2, 1])
    with c1:
        if ts is not None and not ts.empty:
            n_total_skus = None
            if cfg and "initial_stock" in cfg:
                n_total_skus = len(cfg["initial_stock"])
            elif "stockout_duration_per_sku" in summary:
                n_total_skus = max(
                    len(summary["stockout_duration_per_sku"]),
                    ts["stockout_skus_step"].max(),
                    1,
                )
            service_level = (
                1 - ts["stockout_skus_step"] / max(n_total_skus or 1, 1)
            )
            fig = go.Figure()
            fig.add_trace(
                go.Scatter(
                    x=ts["step"], y=service_level, mode="lines",
                    line=dict(color=policy_color(pol), width=2),
                    name="service level",
                    hovertemplate="step=%{x}<br>SL=%{y:.2%}<extra></extra>",
                )
            )
            fig.add_hline(
                y=0.95, line_dash="dot", line_color="#9ca3af",
                annotation_text="95% target", annotation_position="top right",
            )
            drift_onset = summary.get("drift_start_step")
            if drift_onset is not None:
                fig.add_vline(x=drift_onset, line_dash="dash", line_color="#6b7280",
                              annotation_text="drift onset", annotation_position="top left")
            fig.update_layout(
                template=PLOT_TEMPLATE,
                title=f"Service level across the test window — {policy_label(pol)}",
                height=380,
                plot_bgcolor=PLOT_BG, paper_bgcolor=PLOT_BG,
                font=dict(color="#d1d5db"),
                margin=dict(t=50, l=20, r=20, b=20),
                yaxis=dict(tickformat=".0%", gridcolor=PLOT_GRID,
                           zerolinecolor=PLOT_GRID, color=PLOT_AXIS, range=[0, 1.02]),
                xaxis=dict(title="simulation step (days)", gridcolor=PLOT_GRID,
                           zerolinecolor=PLOT_GRID, color=PLOT_AXIS),
            )
            st.plotly_chart(fig, use_container_width=True)

    with c2:
        st.markdown("**Configuration**")
        if cfg:
            display_cfg = {
                k: v for k, v in cfg.items()
                if k not in ("initial_stock",)  # too big to show inline
            }
            st.json(display_cfg, expanded=False)
        else:
            st.info("No config file found for this run.")
