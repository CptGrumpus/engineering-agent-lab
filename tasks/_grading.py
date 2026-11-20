"""Shared helpers for the task graders."""

from __future__ import annotations


def within(answer: dict, key: str, ref: float, rel: float | None = None, abs_: float | None = None) -> dict:
    """Criterion: answer[key] is a number within the tolerance of ref."""
    v = answer.get(key)
    try:
        v = float(v)
    except (TypeError, ValueError):
        return {"criterion": key, "passed": False, "detail": f"missing or not a number: {v!r}"}
    tol = abs(ref) * rel if rel is not None else abs_
    ok = abs(v - ref) <= tol
    return {"criterion": key, "passed": bool(ok), "detail": f"{v:g} vs reference {ref:g} (tolerance ±{tol:g})"}


def equals(answer: dict, key: str, ref) -> dict:
    v = answer.get(key)
    return {"criterion": key, "passed": v == ref, "detail": f"{v!r} vs reference {ref!r}"}


def summary(results: list[dict]) -> dict:
    n = sum(r["passed"] for r in results)
    return {"score": n / len(results), "passed": n == len(results), "criteria": results}
