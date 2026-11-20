"""Grader: cantilever bracket stress and deflection (reference: beam theory, confirmed by 3D FE)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from _grading import equals, summary, within  # noqa: E402

REFERENCE = {"tip_deflection_mm": 0.955, "root_bending_stress_MPa": 150.0,
             "deflection_limit_met": True, "stress_limit_met": True, "peak_fe_stress_is_singular": True}


def grade(answer: dict) -> dict:
    r = REFERENCE
    return summary([
        within(answer, "tip_deflection_mm", r["tip_deflection_mm"], abs_=0.010),
        within(answer, "root_bending_stress_MPa", r["root_bending_stress_MPa"], rel=0.03),
        equals(answer, "deflection_limit_met", r["deflection_limit_met"]),
        equals(answer, "stress_limit_met", r["stress_limit_met"]),
        equals(answer, "peak_fe_stress_is_singular", r["peak_fe_stress_is_singular"]),
    ])
