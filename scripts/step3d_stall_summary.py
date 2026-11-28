"""Study 19 part 3: the numbers page 19 quotes about the located stall, recomputed from the committed run files only.

Reads a step3d_stall_locate run's stall_cells.csv (the cells ranked by continuity error, by U's change and by p's
change, with whether U's change reversed between the last two snapshot intervals) and its every-iteration probes
(postProcessing/stallProbe), and prints:
  - in the cells holding the continuity error (the top 2,000 by |div(phi)| V) and in the first cell columns behind
    the step face (x < 1.3 mm): their share of the error, the fraction whose U change reversed, the median change;
  - the same for the cells with the largest U change (ranked by |dU| V), for contrast;
  - per probe over the last 1,000 iterations: Uz / U_ref range, the linearly detrended standard deviation (as the
    harness's probe_history), and the lag-1 autocorrelation of that detrended residual (near 0: jitter uncorrelated
    from one iteration to the next; near 1: a slow motion).
Run evidence is only read.

    python scripts/step3d_stall_summary.py runs/20261128-112429_step3d_stall_locate

Written 2026-11-28 after the dashboard session's review of page 19's first stall paragraph: a statistic over the
largest-change cells had been quoted as if it held in the stalled cells, and two probe numbers came from a scratch
calculation. Every number on the page now comes from this script.
"""

from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

import numpy as np

U_REF = 44.2      # m/s, the case's reference velocity (cases/step3d_stall_locate.toml)
TOP = 2000


def cells(case: Path) -> dict:
    rows = list(csv.DictReader(open(case / "stall_cells.csv", encoding="utf-8")))
    return {k: np.array([float(r[k]) for r in rows]) for k in rows[0]}


def probes(case: Path) -> tuple[np.ndarray, np.ndarray]:
    f = sorted((case / "postProcessing/stallProbe").iterdir(), key=lambda d: float(d.name))[-1] / "U"
    it, uz = [], []
    for ln in f.read_text(encoding="utf-8").splitlines():
        if ln.startswith("#") or not ln.strip():
            continue
        vecs = re.findall(r"\(([^)]*)\)", ln)
        it.append(float(ln.split()[0]))
        uz.append([float(v.split()[2]) for v in vecs])
    return np.array(it), np.array(uz) / U_REF


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 2
    case = next((Path(argv[0]) / "points").iterdir()) / "solver/case3d"
    c = cells(case)
    cont, du, vol, flip, x = (c[k] for k in ("continuity_err_m3_per_s", "du_over_uref", "volume_mm3", "u_sign_flip",
                                             "x_mm"))
    hot = np.argsort(-cont)[:TOP]
    face = hot[x[hot] < 1.3]
    big = np.argsort(-du * vol)[:TOP]
    print(f"continuity hot cells (top {TOP}): U change reversed in {int(flip[hot].sum())} ({flip[hot].mean():.0%}), "
          f"median |dU| / U_ref {np.median(du[hot]):.2e}")
    print(f"  first columns behind the step face (x < 1.3 mm): {len(face)} cells, {cont[face].sum() / cont[hot].sum():.0%}"
          f" of the hot cells' error, reversed in {int(flip[face].sum())} ({flip[face].mean():.0%}), median |dU| / U_ref "
          f"{np.median(du[face]):.2e}")
    print(f"largest-change cells (top {TOP} by |dU| V): x {x[big].min():.0f}-{x[big].max():.0f} mm, reversed in "
          f"{int(flip[big].sum())}, median |dU| / U_ref {np.median(du[big]):.2e}")
    it, uz = probes(case)
    m = it > it[-1] - 1000
    t = it[m] - it[m][0]
    stats = []
    for k in range(uz.shape[1]):
        s = uz[m, k]
        res = s - np.polyval(np.polyfit(t, s, 1), t)
        res2 = s - np.polyval(np.polyfit(t, s, 2), t)
        lag1 = float(np.corrcoef(res[:-1], res[1:])[0, 1])
        lag1q = float(np.corrcoef(res2[:-1], res2[1:])[0, 1])
        stats.append((float(np.ptp(s)), float(res.std()), lag1))
        print(f"probe {k} (iterations {it[m][0]:.0f}-{it[-1]:.0f}): Uz / U_ref mean {s.mean():+.4f}, range {stats[-1][0]:.2e}, "
              f"detrended std {stats[-1][1]:.2e}, lag-1 autocorrelation of the residual {lag1:+.2f} (linear trend "
              f"removed), {lag1q:+.2f} (quadratic)")
    print(f"probe 0 against probe 1 (mid-span): range {stats[0][0] / stats[1][0]:.1f} x, detrended std "
          f"{stats[0][1] / stats[1][1]:.1f} x")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
