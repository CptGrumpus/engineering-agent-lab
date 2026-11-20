"""Grader: cold-plate channel wall temperature (reference: Graetz thermal entry, confirmed by CFD)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from _grading import equals, summary, within  # noqa: E402

REFERENCE = {"coolant_rise_K": 7.1986, "peak_wall_temperature_C": 44.047,
             "nusselt_at_end_of_heating": 8.343, "wall_limit_met": True}


def grade(answer: dict) -> dict:
    r = REFERENCE
    return summary([
        within(answer, "coolant_rise_K", r["coolant_rise_K"], rel=0.005),
        within(answer, "peak_wall_temperature_C", r["peak_wall_temperature_C"], abs_=0.10),
        within(answer, "nusselt_at_end_of_heating", r["nusselt_at_end_of_heating"], abs_=0.05),
        equals(answer, "wall_limit_met", r["wall_limit_met"]),
    ])
