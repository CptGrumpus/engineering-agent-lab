"""Run-level mesh verification over mesh levels that ran as separate single-point runs (side by side, to save wall
time), using the study's own verify_run_level unchanged.

usage: .venv/Scripts/python.exe scripts/combine_mesh_levels.py OUT.json RUN_DIR RUN_DIR RUN_DIR [--parameter NAME]
Each run must have one completed point. The case (tolerances, numerics) is taken from the first run's inputs; the three
cases must differ only in the swept parameter (checked). Writes OUT.json: the points used, the checks, the detail.
"""

from __future__ import annotations

import argparse
import json
import sys
import tomllib
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from harness.registry import study_for  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("runs", nargs="+")
    ap.add_argument("--parameter", default="fluid_cell_size_m")
    a = ap.parse_args()
    cases, points = [], []
    for r in a.runs:
        r = Path(r)
        case = tomllib.loads((r / "inputs" / "case.toml").read_text(encoding="utf-8"))
        man = json.loads((r / "manifest.json").read_text(encoding="utf-8"))
        done = [pt for pt in man["points"] if pt["status"] == "completed"]
        if len(done) != 1:
            raise SystemExit(f"{r}: expected one completed point, found {len(done)}")
        cases.append(case)
        points.append(done[0] | {"label": f"{r.name}/{done[0]['label']}"})
    ref = cases[0]
    for c in cases[1:]:
        for sec in ("numerics", "verification"):
            if c.get(sec) != ref.get(sec):
                raise SystemExit(f"cases differ in [{sec}]")
        pa, pr = dict(c["parameters"]), dict(ref["parameters"])
        pa.pop(a.parameter, None), pr.pop(a.parameter, None)
        if pa != pr:
            raise SystemExit(f"cases differ in parameters other than {a.parameter}: "
                             f"{sorted(k for k in pa if pa[k] != pr.get(k))}")
    case = dict(ref) | {"sweep": {"parameter": a.parameter}}
    study = study_for(ref["case"]["model"])
    checks, detail = study.verify_run_level(case, {"points": points}, points)
    out = {"runs": [str(Path(r).name) for r in a.runs], "parameter": a.parameter,
           "values": [pt["parameters"][a.parameter] for pt in points], "checks": checks, "detail": detail}
    Path(a.out).write_text(json.dumps(out, indent=1, default=float), encoding="utf-8")
    for c in checks:
        print(f"{c['id']:40s} {c['status']}  value {c['value']:.3e}  tol {c['tolerance']:.1e}")


if __name__ == "__main__":
    main()
