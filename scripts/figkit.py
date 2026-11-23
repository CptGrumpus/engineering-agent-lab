"""House style for the site's charts: one look, vector output, labels a reader can follow.

A chart on the site is redrawn from a run's saved data (point.json, cells.csv, verification.json), never
copied from the harness's own response.png or sweep.png: those are working plots, saved small and labelled
with case and metric names. The rules this module carries:

  - vector (SVG) with text as outlines, so a chart is sharp at any size and looks the same on every machine;
  - one of two widths, FULL or HALF, matching how the page places it, so text lands near 13-14 px on screen;
  - a headline that says what the chart shows, in words, and a muted second line with the units;
  - the model in blue, the independent reference in orange, both named in a key; text is never coloured;
  - a limit drawn as a line with the failing side shaded, so pass and fail read without a legend;
  - status by shape as well as colour: filled circle meets, filled diamond misses, hollow circle not verified;
  - hairline solid grid, no box, 2 px lines, markers of 4 px radius or more with a surface-coloured ring;
  - labels on the few values that matter, not on every point.

Use: fig, ax = new(FULL, 3.2); style(ax); heading(fig, ...); ...; save(fig, "name")  ->  site/v2/fig_name.svg
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "site" / "v2"

SURFACE, INK, INK2, MUTED, GRID, AXIS = "#fcfcfb", "#0b0b0b", "#52514e", "#8b8a84", "#ecebe7", "#c7c6c0"
MODEL, REF, THIRD = "#2a78d6", "#eb6834", "#1baf7a"          # categorical slots 1 to 3 (validated all-pairs)
FAIL, HELD = "#d03b3b", "#8b8a84"
SEQ = "Blues"                                                # one hue, light to dark, for a magnitude
FULL, HALF = 8.4, 4.4                                        # figure widths in inches

plt.rcParams.update({
    "font.family": ["Segoe UI", "DejaVu Sans"], "font.size": 9.5,
    "svg.fonttype": "path", "svg.hashsalt": "site",
    "axes.edgecolor": AXIS, "axes.labelcolor": INK2, "axes.labelsize": 9.5, "axes.linewidth": 0.8,
    "xtick.color": INK2, "ytick.color": INK2, "xtick.labelsize": 9, "ytick.labelsize": 9,
    "lines.linewidth": 2.0, "lines.solid_capstyle": "round", "lines.solid_joinstyle": "round",
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
})


def new(width: float, height: float, nrows: int = 1, ncols: int = 1, top: float = 0.62, **gridspec):
    """A figure with room above the plots for the heading (`top`, in inches)."""
    fig = plt.figure(figsize=(width, height))
    gs = fig.add_gridspec(nrows, ncols, left=0.09 * FULL / width, right=1 - 0.035 * FULL / width,
                          bottom=0.52 / height, top=1 - top / height, **gridspec)
    return fig, gs


def style(ax, grid: str = "y"):
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(AXIS)
    ax.tick_params(length=0, pad=5)
    ax.grid(False)
    if grid:
        ax.grid(True, axis=grid, color=GRID, linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)


def heading(fig, title: str, sub: str | None = None, x: float = 0.012):
    """The chart's headline, top left of the figure, with a muted second line."""
    h = fig.get_figheight()
    fig.text(x, 1 - 0.20 / h, title, fontsize=12.5, fontweight="bold", color=INK, ha="left", va="center")
    if sub:
        fig.text(x, 1 - 0.42 / h, sub, fontsize=9.5, color=INK2, ha="left", va="center")


def panel(ax, title: str):
    ax.set_title(title, loc="left", fontsize=10, fontweight="bold", color=INK, pad=8)


def limit(ax, value: float, text: str, bad: str, axis: str = "x", at: float = 0.97):
    """A requirement: a line at the limit and the failing side shaded. bad: 'above' or 'below' the value."""
    span = ax.axvspan if axis == "x" else ax.axhspan
    lo, hi = (ax.get_xlim() if axis == "x" else ax.get_ylim())
    a, b = (value, max(hi, lo)) if bad == "above" else (min(lo, hi), value)
    span(a, b, color=FAIL, alpha=0.07, linewidth=0, zorder=0.5)
    (ax.axvline if axis == "x" else ax.axhline)(value, color=INK2, linewidth=1.1, zorder=1)
    off = (5 if bad == "above" else -5)
    if axis == "x":
        ax.annotate(text, (value, at), xycoords=("data", "axes fraction"), xytext=(off, 0), textcoords="offset points",
                    ha="left" if bad == "above" else "right", va="top", fontsize=8.5, color=INK2)
    else:
        ax.annotate(text, (at, value), xycoords=("axes fraction", "data"), xytext=(0, off), textcoords="offset points",
                    ha="right", va="bottom" if bad == "above" else "top", fontsize=8.5, color=INK2)


MARK = {"meets": dict(marker="o", color=MODEL), "misses": dict(marker="D", color=FAIL), "held": dict(marker="o", color=HELD)}


def status_dot(ax, x, y, status: str, size: float = 62):
    """One result: filled circle meets, filled diamond misses, hollow circle not verified."""
    m = MARK[status]
    hollow = status == "held"
    ax.scatter([x], [y], s=size * (0.8 if m["marker"] == "D" else 1), marker=m["marker"],
               facecolor=SURFACE if hollow else m["color"], edgecolor=m["color"] if hollow else SURFACE,
               linewidth=1.6, zorder=5)


def dots(ax, x, y, color=MODEL, size: float = 30, **kw):
    """Data points with a ring in the surface colour, so they stay legible where they cross a line."""
    return ax.scatter(x, y, s=size, facecolor=color, edgecolor=SURFACE, linewidth=1.1, zorder=4, **kw)


def label(ax, x, y, text: str, dx: float = 0, dy: float = 0, ha: str = "left", va: str = "center", color=INK,
          size: float = 9, bold: bool = False):
    ax.annotate(text, (x, y), xytext=(dx, dy), textcoords="offset points", ha=ha, va=va, fontsize=size, color=color,
                fontweight="bold" if bold else "normal", zorder=6)


def callout(ax, xy, xytext, text: str, ha: str = "left", va: str = "center"):
    ax.annotate(text, xy, xytext=xytext, textcoords="offset points", ha=ha, va=va, fontsize=8.5, color=INK2, zorder=6,
                arrowprops=dict(arrowstyle="-", color=MUTED, linewidth=0.8, shrinkA=3, shrinkB=3))


def key(fig, items, x: float = 0.988, y_in: float = 0.20):
    """A key in the heading row, top right. items: (label, kind, colour), kind 'line', 'dot', 'meets', 'misses', 'held'."""
    handles = []
    for text, kind, color in items:
        if kind == "line":
            handles.append(Line2D([], [], color=color, linewidth=2, label=text))
        elif kind == "dot":
            handles.append(Line2D([], [], color="none", marker="o", markerfacecolor=color, markeredgecolor=SURFACE,
                                  markersize=7, label=text))
        else:
            m = MARK[kind]
            handles.append(Line2D([], [], color="none", marker=m["marker"], markersize=7 if m["marker"] == "o" else 6,
                                  markerfacecolor=SURFACE if kind == "held" else m["color"],
                                  markeredgecolor=m["color"] if kind == "held" else SURFACE, markeredgewidth=1.4, label=text))
    fig.legend(handles=handles, loc="center right", bbox_to_anchor=(x, 1 - y_in / fig.get_figheight()), ncols=len(handles),
               frameon=False, fontsize=9, labelcolor=INK2, handlelength=1.6, columnspacing=1.6, handletextpad=0.5,
               borderaxespad=0)


def save(fig, name: str) -> Path:
    out = OUT / f"fig_{name}.svg"
    fig.savefig(out, format="svg", metadata={"Date": None, "Creator": None})
    plt.close(fig)
    print("fig", name, f"{out.stat().st_size // 1024} KB")
    return out
