"""Grader: sagging strip clearance (reference: CalculiX nonlinear plane strain, confirmed by the elastica)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from _grading import equals, summary, within  # noqa: E402

REFERENCE = {"tip_drop_mm": 86.5, "tip_pull_in_mm": 10.85, "bending_modulus_MPa": 12.54, "clearance_met": True}


def grade(answer: dict) -> dict:
    r = REFERENCE
    return summary([
        within(answer, "tip_drop_mm", r["tip_drop_mm"], rel=0.015),
        within(answer, "tip_pull_in_mm", r["tip_pull_in_mm"], rel=0.03),
        within(answer, "bending_modulus_MPa", r["bending_modulus_MPa"], rel=0.01),
        equals(answer, "clearance_met", r["clearance_met"]),
    ])
