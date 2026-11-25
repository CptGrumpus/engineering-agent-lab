"""Rescore study 11 runs against the client's requirement list, revision B (validation/enclosure/CLIENT_REQUIREMENTS.md).

Usage: python scripts/score_client_requirements.py OUT.json RUN_DIR [RUN_DIR ...]

For runs made before the C1 metric existed (the 9,000 s redesign set, enclosure_fix_k5_*_long): U1, the board maximum
and the air come from the run's final write (point.json); C1 from the kept final board field (T and the cell centres
C), with the same functions the study now uses (studies/enclosure_thermal.py: board_profile, part_max_C).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from harness import openfoam as of  # noqa: E402
from studies.enclosure_thermal import _W, board_profile, part_max_C  # noqa: E402

C1_SPAN_MM = (5.0, 15.0)
LIMITS = {"REQ-E1": ("component_max_C", 115.0), "REQ-E2": ("board_max_C", 105.0),
          "REQ-E3": ("C1_board_max_C", 70.0), "REQ-E4": ("air_mean_C", 70.0)}


def score(run: Path) -> dict:
    pj = next(run.glob("points/*/point.json"))
    p = json.loads(pj.read_text(encoding="utf-8"))
    final = p["solver_outputs"]["final"]
    vals = {k: final[k] for k in ("component_max_C", "board_max_C", "air_mean_C")}
    cs = sorted(pj.parent.glob("solver/*/board/C"), key=lambda f: float(f.parent.parent.name))
    if cs and float(cs[-1].parent.parent.name) == float(final["t"]):
        lay = _W.layout(p["parameters"])
        prof = board_profile(of.read_internal_field(cs[-1]), of.read_internal_field(cs[-1].parent / "T"),
                             lay["xs"][1])
        vals["C1_board_max_C"] = part_max_C(prof, C1_SPAN_MM)
        vals["board_profile"] = prof
    else:
        vals["C1_board_max_C"] = float("nan")     # no final board field kept: not evaluated
    verdicts = {}
    for rid, (m, lim) in LIMITS.items():
        v = vals[m]
        verdicts[rid] = "NOT EVALUATED" if v != v else ("PASS" if v <= lim else "FAIL")
    return {"run": run.name, "t_final_s": final["t"], "values": vals, "verdicts": verdicts}


def main(argv):
    out, runs = Path(argv[1]), [Path(a) for a in argv[2:]]
    res = [score(r) for r in runs]
    out.write_text(json.dumps({"requirements": "validation/enclosure/CLIENT_REQUIREMENTS.md (revision B)",
                               "limits": LIMITS, "c1_span_mm": C1_SPAN_MM, "runs": res}, indent=1), encoding="utf-8")
    for r in res:
        v = r["values"]
        print(f"{r['run'][:60]:60s} U1 {v['component_max_C']:7.2f} board {v['board_max_C']:7.2f} "
              f"C1 {v['C1_board_max_C']:7.2f} air {v['air_mean_C']:6.2f}  "
              + " ".join(f"{k[-2:]}:{s}" for k, s in r["verdicts"].items()))


if __name__ == "__main__":
    main(sys.argv)
