"""Study 7, revision 5 (client data): score the efficiency map against ORNL's Table B-1, once, after the run, with the
same function the calibrated map was scored with (scripts/motor_calibration.py, efficiency()). ORNL's efficiency is a
test result the job must predict: it is a target here, never an input.

usage: .venv/Scripts/python.exe scripts/motor_rev5_vs_ornl.py [EFF_RUN_ID]
  EFF_RUN_ID: the efficiency run of cases/motor_prius_efficiency_rev5.toml, for the side-by-side with the blind map
              (r1) at the case's named operating points.
Writes validation/motor_ornl/rev5_efficiency_vs_ornl.json; prints a summary.
"""

from __future__ import annotations

import json
import sys
import tomllib
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

from motor_blind_comparison import tables  # noqa: E402
from motor_calibration import efficiency  # noqa: E402

CASE = REPO / "cases/motor_prius_efficiency_rev5.toml"
BLIND_RUN = "20261122-175650_motor_prius_efficiency_r1"   # the blind map the predictions compare against
OUT = REPO / "validation/motor_ornl/rev5_efficiency_vs_ornl.json"


def metrics(run: str) -> dict:
    out = {}
    for pj in sorted((REPO / "runs" / run / "points").glob("*/point.json")):
        pt = json.loads(pj.read_text(encoding="utf-8"))
        out[pt["label"].split("_", 1)[1]] = pt["metrics"]
    return out


def main():
    case = tomllib.loads(CASE.read_text(encoding="utf-8"))
    tab = tables(case)
    out = {"case": str(CASE.relative_to(REPO)).replace("\\", "/"),
           "ornl": efficiency(case, {n: t["fine"] for n, t in tab.items()}, 1.0, {n: t["grid"] for n, t in tab.items()})}
    cal = REPO / "validation/motor_ornl/calibration.json"
    if cal.exists():
        c = json.loads(cal.read_text(encoding="utf-8"))
        out["earlier"] = {h: c[h]["efficiency"] for h in ("blind", "A_remanence") if "efficiency" in c.get(h, {})}
    if len(sys.argv) > 1:
        new, old = metrics(sys.argv[1]), metrics(BLIND_RUN)
        out["vs_blind"] = {"run": sys.argv[1], "blind_run": BLIND_RUN, "points": {
            sc: {k: {"rev5": new[sc][k], "blind": old[sc][k], "diff": new[sc][k] - old[sc][k]}
                 for k in new[sc] if k in old.get(sc, {}) and isinstance(new[sc][k], (int, float))}
            for sc in new}}
    OUT.write_text(json.dumps(out, indent=1), encoding="utf-8")
    print("ORNL Table B-1:", out["ornl"])
    for h, e in out.get("earlier", {}).items():
        print(f"  earlier {h}:", e)
    for sc, d in out.get("vs_blind", {}).get("points", {}).items():
        print(sc)
        for k, v in d.items():
            print(f"   {k:34s} rev5 {v['rev5']:9.3f}  blind {v['blind']:9.3f}  diff {v['diff']:+.3f}")


if __name__ == "__main__":
    main()
