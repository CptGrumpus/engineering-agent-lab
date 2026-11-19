"""Evidence figures (static PNG) for human review."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

# Reference palette (light mode) from the dataviz skill.
SURFACE = "#fcfcfb"
TEXT = "#0b0b0b"
TEXT_2 = "#52514e"
GRID = "#e4e3df"
SERIES_1 = "#2a78d6"  # numerical
SERIES_2 = "#eb6834"  # analytical reference


def _style(ax):
    ax.set_facecolor(SURFACE)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(GRID)
    ax.tick_params(colors=TEXT_2, labelsize=9)
    ax.grid(True, color=GRID, linewidth=0.6)
    ax.xaxis.label.set_color(TEXT_2)
    ax.yaxis.label.set_color(TEXT_2)


def plot_response(
    path: Path,
    t: np.ndarray,
    x: np.ndarray,
    x_ref: np.ndarray,
    *,
    static_deflection_m: float,
    settling_band_fraction: float,
    overshoot_limit_pct: float | None,
    settling_limit_s: float | None,
    error_tolerance: float,
    title: str,
) -> None:
    xs_mm = static_deflection_m * 1e3
    fig, (ax1, ax2) = plt.subplots(
        2, 1, figsize=(8, 6.2), sharex=True, gridspec_kw={"height_ratios": [3, 1.3]},
        facecolor=SURFACE,
    )

    # Panel 1: response overlay.
    ax1.axhspan(xs_mm * (1 - settling_band_fraction), xs_mm * (1 + settling_band_fraction),
                color=TEXT_2, alpha=0.10, linewidth=0,
                label=f"±{settling_band_fraction:.0%} settling band")
    ax1.plot(t, x * 1e3, color=SERIES_1, linewidth=2, label="Numerical (solve_ivp)")
    ax1.plot(t, x_ref * 1e3, color=SERIES_2, linewidth=2, linestyle=(0, (4, 3)),
             label="Analytical reference")
    if overshoot_limit_pct is not None:
        y = xs_mm * (1 + overshoot_limit_pct / 100)
        ax1.axhline(y, color=TEXT_2, linewidth=1, linestyle=(0, (2, 2)))
        ax1.annotate(f"Overshoot limit {overshoot_limit_pct:g} %", (t[-1], y), xytext=(0, 4),
                     textcoords="offset points", ha="right", va="bottom", fontsize=9, color=TEXT_2)
    if settling_limit_s is not None:
        ax1.axvline(settling_limit_s, color=TEXT_2, linewidth=1, linestyle=(0, (2, 2)))
        ax1.annotate(f"Settling limit {settling_limit_s:g} s", (settling_limit_s, 0),
                     xytext=(4, 4), textcoords="offset points", fontsize=9, color=TEXT_2)
    ax1.set_ylabel("Displacement (mm)")
    ax1.set_title(title, color=TEXT, fontsize=11, loc="left")
    leg = ax1.legend(loc="lower right", frameon=False, fontsize=9)
    for txt in leg.get_texts():
        txt.set_color(TEXT)
    _style(ax1)

    # Panel 2: normalized error (single series - title names it, no legend).
    err = np.abs(x - x_ref) / abs(static_deflection_m)
    ax2.semilogy(t, np.maximum(err, 1e-16), color=SERIES_1, linewidth=1.5)
    ax2.axhline(error_tolerance, color=TEXT_2, linewidth=1, linestyle=(0, (2, 2)))
    ax2.annotate(f"Tolerance {error_tolerance:g}", (t[-1], error_tolerance), xytext=(0, 4),
                 textcoords="offset points", ha="right", va="bottom", fontsize=9, color=TEXT_2)
    ax2.set_title("|numerical − analytical| / static deflection", color=TEXT, fontsize=10,
                  loc="left")
    ax2.set_xlabel("Time (s)")
    _style(ax2)

    fig.tight_layout()
    fig.savefig(path, dpi=130, facecolor=SURFACE)
    plt.close(fig)
