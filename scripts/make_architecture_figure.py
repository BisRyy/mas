"""Generate the system-architecture diagram for thesis §3.1.2.

Outputs:
  figures/architecture.png
  figures/architecture.pdf

Layout (top → bottom):
  ┌────────────────────────────────────────────────────────────────┐
  │                 SIMULATION ENVIRONMENT (Mesa)                   │
  └────┬────────┬────────┬────────┬────────┬───────────────────────┘
       │        │        │        │        │   demand events / tick
       ▼        ▼        ▼        ▼        ▼
   ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐
   │ ① SUP  │ │ ② MON  │ │ ③ FCST │ │ ④ REPL │ │ ⑤ ANAL │
   │        │ │        │ │        │ │        │ │        │
   └───┬────┘ └───┬────┘ └───┬────┘ └───┬────┘ └───┬────┘
       │          │          │          │          │
       └─deliver──┴─demand───┴──μ,σ─────┴──orders──┴─snapshot
                                                   (curved back to ①)

Design choices:
  - Inter-agent flow lives in a dedicated lane BELOW the agent boxes
    so labels never overlap box content.
  - Numbered execution badges (1-5) make the deterministic step order
    immediately legible — this is a non-obvious property the manuscript
    spends a paragraph explaining.
  - Analytics' dashed "read-only" line is routed underneath the flow
    lane so it can't crash into the operational arrows.
  - Colorblind-safe Wong / Okabe-Ito palette throughout.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

FIG = Path("figures")
FIG.mkdir(exist_ok=True)


# Palette — colorblind-safe.
COLOR_ENV         = "#264653"  # slate (environment + headings)
COLOR_AGENT_FILL  = "#2A9D8F"  # MAS teal (agent boxes)
COLOR_AGENT_DEEP  = "#1F7A70"  # deeper teal (agent number badge)
COLOR_TEXT_LIGHT  = "#FFFFFF"
COLOR_TEXT_DARK   = "#1F2933"
COLOR_INK         = "#374151"  # primary flow arrows
COLOR_INK_MUTED   = "#6B7280"  # broadcast + observation arrows
COLOR_BG          = "#FAFAF9"  # canvas (off-white, easier on print)


# --------------------------------------------------------------------- helpers


def rounded_box(ax, x, y, w, h, *, facecolor, edgecolor=None, linewidth=1.2,
                rounding=0.10, zorder=2):
    """Filled rounded rectangle. Caller draws text on top."""
    rect = FancyBboxPatch(
        (x, y), w, h,
        boxstyle=f"round,pad=0.0,rounding_size={rounding}",
        linewidth=linewidth,
        edgecolor=edgecolor or facecolor,
        facecolor=facecolor,
        zorder=zorder,
    )
    ax.add_patch(rect)


def agent_box(ax, x, y, w, h, *, number, title, line2, line3):
    """One agent: filled card + numbered badge + title + two label lines."""
    # Card
    rounded_box(ax, x, y, w, h, facecolor=COLOR_AGENT_FILL,
                edgecolor=COLOR_AGENT_DEEP, linewidth=1.4)

    # Numbered execution badge in the top-left corner
    badge_r = 0.22
    bx, by = x + 0.32, y + h - 0.32
    circ = plt.Circle((bx, by), badge_r,
                      facecolor=COLOR_AGENT_DEEP,
                      edgecolor=COLOR_TEXT_LIGHT, linewidth=1.2, zorder=3)
    ax.add_patch(circ)
    ax.text(bx, by, str(number), ha="center", va="center",
            color=COLOR_TEXT_LIGHT, fontsize=10, fontweight="bold", zorder=4)

    # Title (two lines if it contains a newline)
    ax.text(x + w / 2, y + h - 0.55, title,
            ha="center", va="top",
            color=COLOR_TEXT_LIGHT, fontsize=11, fontweight="bold", zorder=4)

    # Subtitle lines
    ax.text(x + w / 2, y + 0.42, line2,
            ha="center", va="center",
            color=COLOR_TEXT_LIGHT, fontsize=8.6, zorder=4)
    ax.text(x + w / 2, y + 0.20, line3,
            ha="center", va="center",
            color=COLOR_TEXT_LIGHT, fontsize=8.0, alpha=0.88, style="italic",
            zorder=4)


def arrow(ax, x1, y1, x2, y2, *, color=COLOR_INK, lw=1.2, style="-|>",
          rad=0.0, dashed=False, zorder=1, shrink_a=2, shrink_b=2):
    a = FancyArrowPatch(
        (x1, y1), (x2, y2),
        arrowstyle=style,
        mutation_scale=14,
        linewidth=lw,
        color=color,
        shrinkA=shrink_a, shrinkB=shrink_b,
        connectionstyle=f"arc3,rad={rad}",
        linestyle=(0, (4, 3)) if dashed else "-",
        zorder=zorder,
    )
    ax.add_patch(a)


def label(ax, x, y, text, *, color=COLOR_INK_MUTED, fontsize=8.2,
          ha="center", va="center", style="italic", weight="normal",
          bg=False):
    """Text label. If bg=True draws a small white background to keep the
    label readable when it crosses other lines."""
    kw = dict(ha=ha, va=va, color=color, fontsize=fontsize, style=style,
              fontweight=weight, zorder=5)
    if bg:
        kw["bbox"] = dict(boxstyle="round,pad=0.18",
                          facecolor=COLOR_BG, edgecolor="none")
    ax.text(x, y, text, **kw)


# --------------------------------------------------------------------- main


def main() -> None:
    fig, ax = plt.subplots(figsize=(13.0, 7.6))
    fig.patch.set_facecolor(COLOR_BG)
    ax.set_facecolor(COLOR_BG)
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 8)
    ax.set_aspect("equal")
    ax.axis("off")

    # ─── (1) Top: Simulation Environment header ──────────────────────────
    env_x, env_y, env_w, env_h = 0.5, 6.4, 13.0, 1.1
    rounded_box(ax, env_x, env_y, env_w, env_h,
                facecolor=COLOR_ENV, edgecolor=COLOR_ENV, rounding=0.14)
    ax.text(env_x + env_w / 2, env_y + env_h - 0.32,
            "S I M U L A T I O N   E N V I R O N M E N T",
            ha="center", va="top",
            color=COLOR_TEXT_LIGHT, fontsize=12.5, fontweight="bold")
    ax.text(env_x + env_w / 2, env_y + 0.25,
            "Mesa Model    ·    Order Replay    ·    Drift Injector    ·    Decision Logger",
            ha="center", va="center",
            color="#CFD8DC", fontsize=9.8, style="italic")

    # ─── (2) Five agent cards in a row ───────────────────────────────────
    # Each agent: (number, two-line title, primary fn, key state)
    agents = [
        (1, "Supplier",            "Order fulfilment",    "Pending PO queue · lead time"),
        (2, "Inventory Monitoring","Per-SKU stock book",  "Stockouts · fulfilment"),
        (3, "Demand Forecasting",  "Predict μ, σ per SKU","Tier ladder · Global ADWIN"),
        (4, "Replenishment",       "(s, S) policy",       "Reorder when ≤ s, up to S"),
        (5, "Analytics",           "Run-level snapshot",  "Timeseries · summary JSON"),
    ]
    agent_w, agent_h = 2.20, 1.85
    n = len(agents)
    inner_w = env_w
    gap = (inner_w - n * agent_w) / (n - 1)
    agent_y = 3.55

    centers: list[tuple[float, float, float]] = []  # (center_x, top_y, bottom_y)
    for i, (num, title, sub, state) in enumerate(agents):
        x = env_x + i * (agent_w + gap)
        agent_box(ax, x, agent_y, agent_w, agent_h,
                  number=num, title=title, line2=sub, line3=state)
        cx = x + agent_w / 2
        centers.append((cx, agent_y + agent_h, agent_y))

    # ─── (3) Broadcast arrows: env → each agent (top edge) ───────────────
    for cx, top_y, _ in centers:
        arrow(ax, cx, env_y, cx, top_y + 0.02,
              color=COLOR_INK_MUTED, lw=1.0, style="-|>",
              shrink_a=2, shrink_b=2, zorder=1)

    # Single label on the broadcast (centered, above the middle agent).
    label(ax, env_x + env_w / 2, (env_y + agent_y + agent_h) / 2 + 0.05,
          "demand events per tick",
          fontsize=9, color=COLOR_INK_MUTED, bg=True)

    # ─── (4) Inter-agent data flow lane (BELOW the agent boxes) ──────────
    # Lane y-coordinate. Arrows live in their own visual band so they
    # never cross box content.
    lane_y = 2.55
    # Agent centers + edges in the lane:
    arrow_pairs = [
        # (from_idx, to_idx, label)
        (0, 1, "deliveries"),         # Supplier → Monitor
        (1, 2, "demand observations"),# Monitor → Forecaster
        (2, 3, "μ, σ"),               # Forecaster → Replenishment
        # Replenishment → Supplier (purchase orders) — curved back-flow on
        # its own lower lane to avoid crossing μ,σ.
    ]
    for fi, ti, lbl in arrow_pairs:
        fx, _, _ = centers[fi]
        tx, _, _ = centers[ti]
        # Vertical down-leg from agent bottom into the lane.
        arrow(ax, fx, agent_y - 0.02, fx, lane_y + 0.05,
              color=COLOR_INK, lw=1.1, style="-",
              shrink_a=2, shrink_b=2, zorder=1)
        # Horizontal in the lane.
        arrow(ax, fx, lane_y, tx, lane_y,
              color=COLOR_INK, lw=1.4, style="-|>",
              shrink_a=0, shrink_b=2, zorder=1)
        # Vertical up-leg into the receiving agent's bottom.
        arrow(ax, tx, lane_y, tx, agent_y - 0.02,
              color=COLOR_INK, lw=1.1, style="-|>",
              shrink_a=2, shrink_b=2, zorder=1)
        # Label centered on the horizontal segment.
        mx = (fx + tx) / 2
        label(ax, mx, lane_y + 0.20, lbl,
              fontsize=8.5, color=COLOR_INK, weight="bold", style="normal",
              bg=True)

    # Replenishment (4) → Supplier (1): curved purchase-order back-flow
    # routed on a deeper lane so it never crosses the forward flow.
    back_lane_y = 1.50
    fx_4, _, _ = centers[3]
    tx_1, _, _ = centers[0]
    arrow(ax, fx_4, agent_y - 0.02, fx_4, back_lane_y + 0.05,
          color=COLOR_INK, lw=1.1, style="-", shrink_a=2, shrink_b=2, zorder=0)
    arrow(ax, fx_4, back_lane_y, tx_1, back_lane_y,
          color=COLOR_INK, lw=1.4, style="-|>",
          shrink_a=0, shrink_b=2, zorder=0)
    arrow(ax, tx_1, back_lane_y, tx_1, agent_y - 0.02,
          color=COLOR_INK, lw=1.1, style="-|>",
          shrink_a=2, shrink_b=2, zorder=0)
    label(ax, (fx_4 + tx_1) / 2, back_lane_y + 0.20,
          "purchase orders",
          fontsize=8.5, color=COLOR_INK, weight="bold", style="normal", bg=True)

    # ─── (5) Analytics observation (dashed, read-only) ───────────────────
    # Analytics (5) observes every operational agent. Drawn as a thin
    # dashed line that drops below the back-flow lane to keep it visually
    # subordinate.
    obs_lane_y = 0.85
    ax_x, _, _ = centers[4]
    # Down-leg from analytics into the obs lane.
    arrow(ax, ax_x, agent_y - 0.02, ax_x, obs_lane_y + 0.05,
          color=COLOR_INK_MUTED, lw=0.9, style="-", dashed=True,
          shrink_a=2, shrink_b=2, zorder=0)
    # Horizontal traversal back to Supplier.
    arrow(ax, ax_x, obs_lane_y, centers[0][0], obs_lane_y,
          color=COLOR_INK_MUTED, lw=0.9, style="-|>", dashed=True,
          shrink_a=0, shrink_b=2, zorder=0)
    # Tick marks up to each agent it observes (1..4).
    for i in range(4):
        cx, _, _ = centers[i]
        arrow(ax, cx, obs_lane_y, cx, agent_y - 0.02,
              color=COLOR_INK_MUTED, lw=0.7, style="-|>", dashed=True,
              shrink_a=2, shrink_b=2, zorder=0)
    label(ax, (centers[0][0] + ax_x) / 2, obs_lane_y - 0.22,
          "read-only metrics snapshot",
          fontsize=8, color=COLOR_INK_MUTED, weight="normal", style="italic",
          bg=True)

    # ─── (6) Execution-order legend ──────────────────────────────────────
    # Single small note explaining the numbered badges.
    label(ax, env_x, agent_y + agent_h + 0.32,
          "Numbered badges 1–5: deterministic per-tick execution order",
          ha="left", color=COLOR_TEXT_DARK,
          fontsize=9, style="italic", weight="bold", bg=False)

    # ─── (7) Caption ─────────────────────────────────────────────────────
    fig.text(
        0.5, 0.025,
        "Figure 3.1. High-level architecture. Five autonomous agents are coordinated "
        "through a shared Mesa simulation environment. Solid arrows show data flow "
        "during one tick; the dashed line is the Analytics agent's read-only "
        "observation of post-decision state.",
        ha="center", va="bottom",
        fontsize=9.5, color=COLOR_TEXT_DARK, wrap=True,
    )

    plt.tight_layout(rect=[0, 0.04, 1, 1])
    out_png = FIG / "architecture.png"
    out_pdf = FIG / "architecture.pdf"
    fig.savefig(out_png, dpi=220, bbox_inches="tight", facecolor=COLOR_BG)
    fig.savefig(out_pdf, bbox_inches="tight", facecolor=COLOR_BG)
    print(f"Wrote {out_png} and {out_pdf}")
    plt.close(fig)


if __name__ == "__main__":
    main()
