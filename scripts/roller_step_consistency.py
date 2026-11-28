"""Study 10 part 2: is the 3D FE roller's end-region pressure settled from one load step to the next?

Each FE point solves two to four approach steps and interpolates to the target load between the two that bracket it.
This script re-reads finished runs' point.json (every step's pressure along the roller is kept there) and, for each
point, prints per step the mid-length pressure and the largest pressure in the end region (beyond 0.8 of the
half-length from mid-length), then the end-consistency value the study now checks (the end/mid ratio's change
between the bracketing steps, tolerance 0.03 from roller_fe_end's P3) and the target peak two ways: the blend of each
step's own maximum (what the runs before 2026-11-28 12:00 reported) and the maximum of the interpolated profile (what
the study now reports). Run evidence is only read, never changed.

    python scripts/roller_step_consistency.py runs/20261127-180915_roller_fe_mesh runs/20261128-014852_roller_fe_end

Written 2026-11-28 after roller_fe_end's 0.05 mm point read 668.1 MPa at the end while its two neighbours read their
peak at mid-length.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from studies.roller_3d import END_CONSISTENCY_TOL, END_ZONE, bracket, end_consistency, interpolate_to_target  # noqa: E402


def point_rows(pdir: Path) -> list[str]:
    d = json.loads((pdir / "point.json").read_text(encoding="utf-8"))
    so, L2 = d["solver_outputs"], float(d["parameters"]["roller_length_mm"]) / 2
    steps, target = so["steps"], so["target_quarter_load_N"]
    j, w, _ = bracket(steps, target)
    out = [f"### {pdir.parent.parent.name} / {pdir.name}", "",
           "| step | load (N, quarter) | mid-length (MPa) | end max (MPa) | where (mm from the end) | end / mid |",
           "|---|---|---|---|---|---|"]
    for i, s in enumerate(steps):
        z, p = np.abs(np.asarray(s["z_profile_mm"])), np.asarray(s["p_along_z_MPa"])
        e = np.where(z > END_ZONE * L2)[0]
        k = e[int(np.argmax(p[e]))]
        mark = " (bracket)" if i in (j - 1, j) else ""
        out.append(f"| {i}{mark} | {abs(s['F_top_N']):.1f} | {s['p_mid_MPa']:.1f} | {p[k]:.1f} | {L2 - z[k]:.2f} | "
                   f"{p[k] / s['p_mid_MPa']:.3f} |")
    jump, _ = end_consistency(steps, j, L2)
    t, *_ = interpolate_to_target(steps, target)
    blend = (1 - w) * steps[j - 1]["p_peak_MPa"] + w * steps[j]["p_peak_MPa"]
    out += ["", f"end consistency {jump:.3f} (tolerance {END_CONSISTENCY_TOL:g}): "
            f"**{'PASS' if jump <= END_CONSISTENCY_TOL else 'FAIL'}**; target peak: blend of the steps' maxima "
            f"{blend:.1f} MPa, interpolated profile {t['p_peak_MPa']:.1f} MPa at {L2 - abs(t['p_peak_z_mm']):.2f} mm "
            f"from the end (mid-length {t['p_mid_MPa']:.1f})", ""]
    return out


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 2
    for run in argv:
        for pdir in sorted((Path(run) / "points").iterdir()):
            if (pdir / "point.json").exists():
                print("\n".join(point_rows(pdir)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
