"""Half-court shot-chart rendering."""

from __future__ import annotations

from typing import Iterable, Optional

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Arc, Circle, Rectangle

from .court import HALF_COURT_L_FT, HALF_COURT_W_FT, RIM_FROM_BASELINE_FT
from .events import ShotEvent


def _draw_half_court(ax) -> None:
    """Draw a simplified half court (in feet)."""
    # Floor outline.
    ax.add_patch(
        Rectangle(
            (0, 0),
            HALF_COURT_W_FT,
            HALF_COURT_L_FT,
            fill=False,
            linewidth=1.5,
            color="#444",
        )
    )
    rim_x = HALF_COURT_W_FT / 2.0
    rim_y = RIM_FROM_BASELINE_FT
    # Backboard (4 ft from baseline, 6 ft wide).
    ax.plot(
        [rim_x - 3, rim_x + 3],
        [4.0, 4.0],
        color="#444",
        linewidth=2,
    )
    # Rim (18" diameter).
    ax.add_patch(Circle((rim_x, rim_y), 0.75, fill=False, color="#c44", linewidth=1.5))
    # Paint (key) — 16 ft wide, 19 ft long.
    ax.add_patch(
        Rectangle(
            (rim_x - 8, 0),
            16,
            19,
            fill=False,
            linewidth=1.2,
            color="#444",
        )
    )
    # Free-throw circle.
    ax.add_patch(
        Arc((rim_x, 19.0), 12.0, 12.0, theta1=0, theta2=180, color="#444", linewidth=1.0)
    )
    # 3-point arc — 22' on the corners, 23'9" up top.
    ax.plot([rim_x - 22.0, rim_x - 22.0], [0, 14.0], color="#444", linewidth=1.0)
    ax.plot([rim_x + 22.0, rim_x + 22.0], [0, 14.0], color="#444", linewidth=1.0)
    ax.add_patch(
        Arc(
            (rim_x, rim_y),
            2 * 23.75,
            2 * 23.75,
            theta1=22,
            theta2=158,
            color="#444",
            linewidth=1.0,
        )
    )


def shot_chart(
    shots: Iterable[ShotEvent],
    title: str = "Shot chart",
    figsize: tuple[float, float] = (6, 6),
):
    fig, ax = plt.subplots(figsize=figsize)
    _draw_half_court(ax)

    for s in shots:
        if s.shot_x_ft is None or s.shot_y_ft is None:
            continue
        color = "#2a9d8f" if s.made else "#e76f51"
        marker = "o" if s.made else "x"
        ax.plot(
            s.shot_x_ft, s.shot_y_ft,
            marker, color=color, markersize=8, markeredgewidth=1.6, alpha=0.9,
        )

    ax.set_xlim(-2, HALF_COURT_W_FT + 2)
    ax.set_ylim(-2, HALF_COURT_L_FT + 2)
    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_title(title)
    return fig
