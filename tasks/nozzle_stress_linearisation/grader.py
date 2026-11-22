"""Grader: nozzle junction stresses (reference: stress linearisation of the study-18 profile, Annex 5-A method)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from _grading import equals, summary, within  # noqa: E402

REFERENCE = {"pl_MPa": 205.13, "pq_MPa": 239.57, "pq_governing_surface": "inner",
             "pl_limit_met": True, "pq_limit_met": True}


def _surface(answer: dict) -> dict:
    v = str(answer.get("pq_governing_surface", "")).strip().lower()
    ok = v.startswith("inner") or v in ("s = 0", "s=0")
    return {"criterion": "pq_governing_surface", "passed": ok, "detail": f"{v!r} vs reference 'inner'"}


def grade(answer: dict) -> dict:
    r = REFERENCE
    return summary([
        within(answer, "pl_MPa", r["pl_MPa"], rel=0.003),
        within(answer, "pq_MPa", r["pq_MPa"], rel=0.005),
        _surface(answer),
        equals(answer, "pl_limit_met", r["pl_limit_met"]),
        equals(answer, "pq_limit_met", r["pq_limit_met"]),
    ])
