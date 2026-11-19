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


def _limit_lines(ax, limit, symmetric=True, label=None):
    if limit is None:
        return
    for y in ((limit, -limit) if symmetric else (limit,)):
        ax.axhline(y, color=TEXT_2, linewidth=1, linestyle=(0, (2, 2)))
    if label:
        ax.annotate(label, (1.0, limit), xycoords=("axes fraction", "data"), xytext=(-2, 3),
                    textcoords="offset points", ha="right", va="bottom", fontsize=8.5,
                    color=TEXT_2)


def _legend(ax, loc="upper right"):
    leg = ax.legend(loc=loc, frameon=False, fontsize=8.5)
    for txt in leg.get_texts():
        txt.set_color(TEXT)


def quarter_car_bump_figure(path, t, acc, acc_ref, travel_mm, load_ratio, road_mm, *,
                            accel_limit, travel_limit_mm, load_limit, title, t_show=1.5):
    sel = t <= t_show
    fig, axes = plt.subplots(3, 1, figsize=(8, 7.4), sharex=True, facecolor=SURFACE)
    ax1, ax2, ax3 = axes
    ax1.plot(t[sel], acc[sel], color=SERIES_1, linewidth=2, label="Numerical")
    ax1.plot(t[sel], acc_ref[sel], color=SERIES_2, linewidth=2, linestyle=(0, (4, 3)),
             label="State-space reference")
    _limit_lines(ax1, accel_limit, label=f"Limit \u00b1{accel_limit:g}" if accel_limit else None)
    ax1.set_ylabel("Body accel. (m/s\u00b2)")
    ax1.set_title(title, color=TEXT, fontsize=11, loc="left")
    _legend(ax1, loc="lower right")

    ax2.plot(t[sel], travel_mm[sel], color=SERIES_1, linewidth=2, label="Suspension travel")
    ax2.plot(t[sel], road_mm[sel], color=TEXT_2, linewidth=1.2, label="Road profile")
    _limit_lines(ax2, travel_limit_mm,
                 label=f"Limit \u00b1{travel_limit_mm:g} mm" if travel_limit_mm else None)
    ax2.set_ylabel("Displacement (mm)")
    _legend(ax2, loc="lower right")

    ax3.plot(t[sel], load_ratio[sel], color=SERIES_1, linewidth=2)
    _limit_lines(ax3, load_limit, label=f"Limit \u00b1{load_limit:g}" if load_limit else None)
    ax3.axhline(1.0, color=TEXT, linewidth=0.8)
    ax3.annotate("wheel lift-off", (0.0, 1.0), xycoords=("axes fraction", "data"),
                 xytext=(2, 3), textcoords="offset points", fontsize=8.5, color=TEXT)
    ax3.set_title("Dynamic tire load / static load", color=TEXT, fontsize=10, loc="left")
    ax3.set_xlabel("Time (s)")
    for ax in axes:
        _style(ax)
    fig.tight_layout()
    fig.savefig(path, dpi=130, facecolor=SURFACE)
    plt.close(fig)


def quarter_car_road_figure(path, t_win, acc_win, freq_hz, amp_expected, *, title, t_show=5.0):
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8, 6.6), facecolor=SURFACE,
                                   gridspec_kw={"height_ratios": [1, 1.3]})
    sel = t_win <= t_win[0] + t_show
    ax1.plot(t_win[sel], acc_win[sel], color=SERIES_1, linewidth=1.2)
    ax1.set_title(title, color=TEXT, fontsize=11, loc="left")
    ax1.annotate(f"Body acceleration, first {t_show:g} s of the analysis window",
                 (0, 1), xycoords="axes fraction", xytext=(0, -2), textcoords="offset points",
                 va="top", fontsize=9, color=TEXT_2)
    ax1.set_xlabel("Time (s)")
    ax1.set_ylabel("m/s\u00b2")

    n = len(acc_win)
    spec = np.fft.rfft(acc_win) * 2 / n
    f_fft = np.fft.rfftfreq(n, d=t_win[1] - t_win[0])
    idx = np.searchsorted(f_fft, freq_hz)
    ax2.semilogy(freq_hz, np.abs(spec[idx]), "o", color=SERIES_1, markersize=4,
                 label="Simulation (FFT of window)")
    ax2.semilogy(freq_hz, amp_expected, color=SERIES_2, linewidth=2,
                 label="Transfer function |H| \u00d7 road amplitude")
    ax2.set_xlabel("Frequency (Hz)")
    ax2.set_ylabel("Accel. amplitude (m/s\u00b2)")
    ax2.set_title("Body acceleration spectrum", color=TEXT, fontsize=10.5, loc="left")
    _legend(ax2)
    for ax in (ax1, ax2):
        _style(ax)
    fig.tight_layout()
    fig.savefig(path, dpi=130, facecolor=SURFACE)
    plt.close(fig)


def sweep_figure(path, sweep_name, rows, requirements, title):
    """One panel per requirement: metric vs sweep value, limit line, pass/fail markers.

    rows: [(sweep_value, {metric: value}), ...] for completed points.
    """
    n = len(requirements)
    fig, axes = plt.subplots(1, n, figsize=(3.6 * n, 3.4), facecolor=SURFACE, squeeze=False)
    xs = np.array([r[0] for r in rows], float)
    order = np.argsort(xs)
    for ax, req in zip(axes[0], requirements):
        ys = np.array([r[1].get(req["metric"], np.nan) for r in rows], float)
        ax.plot(xs[order], ys[order], color=SERIES_1, linewidth=2)
        ok = {"<=": ys <= req["limit"], "<": ys < req["limit"],
              ">=": ys >= req["limit"], ">": ys > req["limit"]}[req["operator"]]
        ax.plot(xs[ok], ys[ok], "o", color=SERIES_1, markersize=8, label="meets")
        ax.plot(xs[~ok], ys[~ok], "o", markerfacecolor=SURFACE, markeredgecolor=SERIES_1,
                markeredgewidth=2, markersize=8, label="violates")
        ax.axhline(req["limit"], color=TEXT_2, linewidth=1, linestyle=(0, (2, 2)))
        ax.annotate(f"limit {req['operator']} {req['limit']:g}", (1.0, req["limit"]),
                    xycoords=("axes fraction", "data"), xytext=(-2, 3),
                    textcoords="offset points", ha="right", va="bottom", fontsize=8.5,
                    color=TEXT_2)
        ax.set_title(f"{req['id']}: {req['metric']}", color=TEXT, fontsize=9.5, loc="left")
        ax.set_xlabel(sweep_name)
        ax.set_ylabel(req["units"] if req["units"] != "-" else "ratio")
        _style(ax)
    _legend(axes[0][0], loc="best")
    fig.suptitle(title, color=TEXT, fontsize=11, x=0.01, ha="left")
    fig.tight_layout()
    fig.savefig(path, dpi=130, facecolor=SURFACE)
    plt.close(fig)
