"""Grader: track roller contact stress (reference: Hertz line contact, confirmed by FE)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from _grading import equals, summary, within  # noqa: E402

REFERENCE = {"contact_half_width_mm": 0.5252, "peak_contact_pressure_MPa": 606.04,
             "max_subsurface_shear_MPa": 181.98, "max_shear_depth_mm": 0.4129,
             "pressure_limit_met": True, "shear_limit_met": True}


def grade(answer: dict) -> dict:
    r = REFERENCE
    return summary([
        within(answer, "contact_half_width_mm", r["contact_half_width_mm"], rel=0.02),
        within(answer, "peak_contact_pressure_MPa", r["peak_contact_pressure_MPa"], rel=0.02),
        within(answer, "max_subsurface_shear_MPa", r["max_subsurface_shear_MPa"], rel=0.03),
        within(answer, "max_shear_depth_mm", r["max_shear_depth_mm"], rel=0.05),
        equals(answer, "pressure_limit_met", r["pressure_limit_met"]),
        equals(answer, "shear_limit_met", r["shear_limit_met"]),
    ])
