#!/usr/bin/env python3
"""Shared typography and palette, so the figures look like one publication.

Journal figures are read at column width on paper, not at screen size, which
sets most of the choices here: hairline axes, no top or right spine, a light
horizontal grid behind the data, and type that stays legible when the page is
reduced. The palette is colour-blind safe and each colour keeps a distinct
lightness, so the panels survive greyscale printing.

Figures are drawn at exactly the text width of the manuscript, ``WIDTH_IN``.
This matters more than it sounds. A figure authored wider than the text block is
scaled down by ``\\includegraphics``, and every label shrinks with it: a figure
drawn at 7.1 in and placed in a 5.4 in text block loses a quarter of its type
size, so a 9 pt label lands on the page at under 7 pt against 12 pt body text.
Drawing at the final width keeps the point sizes below meaningful, and they are
set close to the body size rather than to the smallest thing that still prints.
"""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402

# The manuscript's \textwidth, 390 TeX pt, in inches. Every figure is authored
# at this width so that \includegraphics[width=\textwidth] neither shrinks nor
# stretches it.
WIDTH_IN = 390.0 / 72.27
# Nothing in a figure goes below this. The body text is 12 pt; a label at 9 pt
# is three quarters of it, which reads as "smaller", and anything under that
# reads as "unreadable".
SMALLEST_PT = 10.0

INK = "#1a1a1a"
MUTED = "#8c8c8c"
FAINT = "#e8e8e8"
ACCENT = "#67000d"
COLD = "#2166ac"
WARM = "#b2182b"
NEUTRAL = "#4d4d4d"

# Development / holdout, distinct in hue and in lightness.
DEVELOPMENT = "#3a5a8c"
HOLDOUT = "#c07a2c"

# --- one palette for the whole paper ---------------------------------------
# Colour encodes the *task*, never the network. An earlier version used blue for
# reconstruction in the synthetic figures and blue for outflow in the empirical
# ones, so the same colour meant opposite things on facing pages. Networks are
# separated by marker and outline instead.
#
# Okabe-Ito, so the pairs stay distinguishable in the common colour deficiencies
# and in greyscale.
TASK = {
    "reconstruction": "#0072B2",   # blue
    "temperature": "#0072B2",
    "conjunctive": "#D55E00",      # vermillion
    "outflow": "#D55E00",
    "disjunctive": "#666666",      # grey
}
NETWORK_MARKER = {"AVAMET": "o", "SwissMetNet": "D"}
NETWORK_FILL = {"AVAMET": "#333333", "SwissMetNet": "white"}


def apply() -> None:
    plt.rcParams.update(
        {
            "font.family": "serif",
            "font.serif": ["DejaVu Serif"],
            "mathtext.fontset": "dejavuserif",
            "font.size": 11,
            "axes.titlesize": 11.5,
            "axes.labelsize": 11,
            "xtick.labelsize": 10.5,
            "ytick.labelsize": 10.5,
            "legend.fontsize": 10.5,
            "axes.linewidth": 0.7,
            "axes.edgecolor": INK,
            "axes.labelcolor": INK,
            "text.color": INK,
            "xtick.color": INK,
            "ytick.color": INK,
            "xtick.direction": "out",
            "ytick.direction": "out",
            "xtick.major.width": 0.7,
            "ytick.major.width": 0.7,
            "xtick.major.size": 3.0,
            "ytick.major.size": 3.0,
            "legend.frameon": False,
            "figure.dpi": 150,
            "savefig.dpi": 400,
            # NOT "tight": a tight bbox crops to the drawn content, which is
            # wider than figsize once labels stick out, so the saved PDF comes
            # back at 5.9 in, LaTeX scales it to the 5.4 in text block, and
            # every label lands 9% smaller than authored. tight_layout already
            # fits everything inside the figure, so the box can stay fixed and
            # the figure reaches the page at exactly 1:1.
            "savefig.bbox": None,
            "savefig.pad_inches": 0.02,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
        }
    )


def tidy(axis, grid: str = "y") -> None:
    """Strip the box, keep a faint grid behind the data."""
    axis.spines[["top", "right"]].set_visible(False)
    if grid:
        axis.grid(axis=grid, color=FAINT, linewidth=0.6, zorder=0)
    axis.set_axisbelow(True)


def panel_label(axis, letter: str, title: str = "") -> None:
    """A bold letter at the top left, the way most journals set panels.

    Matplotlib is not rendering through LaTeX here, so titles must use real
    characters: en dashes, a plain per-cent sign, no backslash escapes.
    """
    axis.set_title(title, loc="left", pad=8, fontsize=10.5)
    # Out in the left margin, clear of the title, which is where journals put it.
    axis.annotate(
        letter,
        xy=(0, 1), xycoords="axes fraction",
        xytext=(-30, 10), textcoords="offset points",
        fontsize=11.5, fontweight="bold", va="bottom", ha="left",
    )


def save(figure, destination_dir, stem: str) -> None:
    destination_dir.mkdir(parents=True, exist_ok=True)
    for suffix in ("pdf", "png"):
        path = destination_dir / f"{stem}.{suffix}"
        figure.savefig(path)
        print(f"escrito: {path}")


def scale_bar(axis, length_km: float, latitude: float, position=(0.06, 0.08)) -> None:
    """A scale bar in degrees of longitude at the map's latitude.

    Maps drawn in geographic coordinates have no intrinsic scale, and a reader
    cannot judge whether a feature is 5 or 50 km across without one.
    """
    import math

    degrees = length_km / (111.32 * math.cos(math.radians(latitude)))
    left, bottom = axis.get_xlim()[0], axis.get_ylim()[0]
    width = axis.get_xlim()[1] - left
    height = axis.get_ylim()[1] - bottom
    x = left + position[0] * width
    y = bottom + position[1] * height
    axis.plot([x, x + degrees], [y, y], color=INK, linewidth=1.6,
              solid_capstyle="butt", zorder=6)
    for end in (x, x + degrees):
        axis.plot([end, end], [y, y + 0.012 * height], color=INK, linewidth=1.6,
                  zorder=6)
    axis.annotate(f"{length_km:.0f} km", ((x + x + degrees) / 2, y),
                  textcoords="offset points", xytext=(0, 4), ha="center",
                  fontsize=SMALLEST_PT, color=INK, zorder=6)


def north_arrow(axis, position=(0.93, 0.10)) -> None:
    """North is up in these projections, but saying so costs one glyph."""
    left, bottom = axis.get_xlim()[0], axis.get_ylim()[0]
    width = axis.get_xlim()[1] - left
    height = axis.get_ylim()[1] - bottom
    x = left + position[0] * width
    y = bottom + position[1] * height
    axis.annotate(
        "N", xy=(x, y + 0.055 * height), xytext=(x, y),
        arrowprops=dict(arrowstyle="-|>", color=INK, linewidth=1.2,
                        mutation_scale=10),
        ha="center", va="top", fontsize=SMALLEST_PT, color=INK, zorder=6,
    )
