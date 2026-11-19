"""Helpers for building verification check records."""

from __future__ import annotations

import math


def check(cid: str, description: str, value: float, tolerance: float, kind: str = "numerical"
          ) -> dict:
    """A PASS/FAIL record: value must be finite and <= tolerance.

    kind: 'numerical' (is the math solved correctly?) or 'validity' (does an
    assumption of the model hold for this result?). Both gate verification.
    """
    value = float(value)
    ok = math.isfinite(value) and value <= tolerance
    return {
        "id": cid,
        "description": description,
        "kind": kind,
        "value": value,
        "tolerance": float(tolerance),
        "comparison": "<=",
        "status": "PASS" if ok else "FAIL",
    }
