"""Generate the system-architecture diagram for thesis §3.1.2.

Outputs:
  figures/architecture.png
  figures/architecture.pdf

The diagram shows the five autonomous agents below the shared simulation
environment, with the inter-agent data flows annotated.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

FIG = Path("figures")
FIG.mkdir(exist_ok=True)


# Palette — match the rest of the figures (colorblind-safe Wong / Okabe-Ito).
COLOR_ENV   = "#264653"  # slate
COLOR_AGENT = "#2A9D8F"  # MAS teal
COLOR_TEXT  = "#FFFFFF"
COLOR_NOTE  = "#6B7280"
COLOR_LINE  = "#374151"


def box(ax, x, y, w, h, label, sublabel="", facecolor=COLOR_AGENT,
        text_color=COLOR_TEXT, fontsize=10):
    rect = FancyBboxPatch(
        (x, y), w, h,
        boxstyle="round,pad=0.02,rounding_size=0.08",
        linewidth=1.4,
        edgecolor=COLOR_LINE,
        facecolor=facecolor,
    )
    ax.add_patch(rect)
    ax.text(x + w / 2, y + h / 2 + (0.18 if sublabel else 0.0),
            label, ha="center", va="center",
            color=text_color, fontsize=fontsize, fontweight="bold")
    if sublabel:
        ax.text(x + w / 2, y + h / 2 - 0.20,
                sublabel, ha="center", va="center",
                color=text_color, fontsize=fontsize - 1.5, alpha=0.88,
                style="italic")


def arrow(ax, x1, y1, x2, y2, label=None, color=COLOR_LINE, style="-|>",
          shrink_a=10, shrink_b=10, rad=0.0):
    arr = FancyArrowPatch(
        (x1, y1), (x2, y2),
        arrowstyle=style,
        mutation_scale=14,
        linewidth=1.2,
        color=color,
        shrinkA=shrink_a,
        shrinkB=shrink_b,
        connectionstyle=f"arc3,rad={rad}",
    )
    ax.add_patch(arr)
    if label:
        # Mid-point label, slightly offset perpendicular to the arrow.
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        ax.text(mx, my + 0.05, label, ha="center", va="bottom",
                fontsize=7.5, color=COLOR_NOTE, style="italic")


def main() -> None:
    fig, ax = plt.subplots(figsize=(11, 5.0))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 6)
    ax.set_aspect("equal")
    ax.axis("off")

    # --- Top: simulation environment ---
    env_x, env_y, env_w, env_h = 1.0, 4.6, 10.0, 1.0
    box(ax, env_x, env_y, env_w, env_h,
        "Simulation Environment",
        "Mesa Model · Order Replay · Drift Injector · Logger",
        facecolor=COLOR_ENV, fontsize=12)

    # Five agent boxes, evenly spaced in a row.
    agents = [
        ("Supplier\nAgent",            "Pending orders\n· Lead time"),
        ("Inventory\nMonitoring Agent", "Per-SKU stock\n· Stockouts"),
        ("Demand\nForecasting Agent",  "History · Tier ladder\n· Global ADWIN"),
        ("Replenishment\nAgent",       "(s, S) policy\n· Each step"),
        ("Analytics\nAgent",           "Timeseries\n· Run summary"),
    ]
    agent_w, agent_h = 1.85, 1.55
    gap = (env_w - 5 * agent_w) / 4
    agent_y = 1.55
    centers = []
    for i, (label, sub) in enumerate(agents):
        ax.text  # noop
        x = env_x + i * (agent_w + gap)
        box(ax, x, agent_y, agent_w, agent_h, label, sub,
            facecolor=COLOR_AGENT, fontsize=10)
        centers.append((x + agent_w / 2, agent_y + agent_h))

    # --- Vertical arrow: env -> top of each agent (the broadcast) ---
    for cx, top_y in centers:
        arrow(ax, cx, env_y, cx, top_y, color=COLOR_NOTE,
              style="-|>", shrink_a=2, shrink_b=2)

    # Label the broadcast arrow (only over the central column to keep clean).
    ax.text(env_x + env_w / 2, (env_y + agent_y + agent_h) / 2 + 0.05,
            "demand events / step",
            ha="center", va="bottom",
            fontsize=8.5, color=COLOR_NOTE, style="italic")

    # --- Horizontal flow arrows between agents (left to right) ---
    # Supplier -> Monitor (deliveries land)
    # Monitor -> Forecaster (observations)
    # Forecaster -> Replenisher (predictions)
    # Replenisher -> Supplier (purchase orders, wrap-around)
    # Analytics watches all.
    pairs = [
        (0, 1, "deliveries"),       # supplier -> monitor
        (1, 2, "demand obs."),      # monitor -> forecaster
        (2, 3, "μ, σ"),             # forecaster -> replenisher
    ]
    for i, j, lbl in pairs:
        x1, y_top = centers[i]
        x2, _ = centers[j]
        y = agent_y + agent_h / 2
        arrow(ax, x1 + agent_w / 2 - 0.05, y, x2 - agent_w / 2 + 0.05, y,
              label=lbl, color=COLOR_LINE)

    # Replenisher -> Supplier (curved feedback)
    sx, _ = centers[3]
    tx, _ = centers[0]
    arrow(ax,
          sx - agent_w / 2 + 0.05, agent_y + agent_h / 4,
          tx + agent_w / 2 - 0.05, agent_y + agent_h / 4,
          label="purchase orders",
          color=COLOR_LINE, rad=0.35, shrink_a=2, shrink_b=2)

    # Analytics reads from monitor (snapshot) - dotted line.
    ax_x, _ = centers[4]
    mn_x, _ = centers[1]
    arr = FancyArrowPatch(
        (ax_x - agent_w / 2 + 0.05, agent_y + agent_h * 0.20),
        (mn_x + agent_w / 2 - 0.05, agent_y + agent_h * 0.20),
        arrowstyle="-|>", mutation_scale=12, linewidth=1.0,
        color=COLOR_NOTE, linestyle=(0, (3, 3)),
        connectionstyle="arc3,rad=-0.25",
    )
    ax.add_patch(arr)
    ax.text((ax_x + mn_x) / 2, agent_y - 0.1,
            "metrics snapshot (read-only)",
            ha="center", va="top", fontsize=7.5,
            color=COLOR_NOTE, style="italic")

    # --- Caption-like header ---
    fig.suptitle(
        "Figure 3.1. High-level architecture: five autonomous agents "
        "coordinated through a shared simulation environment.",
        y=0.04, fontsize=10
    )

    plt.tight_layout()
    fig.savefig(FIG / "architecture.png", dpi=200, bbox_inches="tight")
    fig.savefig(FIG / "architecture.pdf", bbox_inches="tight")
    print(f"Wrote {FIG / 'architecture.png'} and {FIG / 'architecture.pdf'}")
    plt.close(fig)


if __name__ == "__main__":
    main()
