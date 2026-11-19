"""Load and validate case files (TOML)."""

from __future__ import annotations

import hashlib
import operator
import tomllib
from pathlib import Path

from harness.metrics import METRICS

OPERATORS = {"<=": operator.le, ">=": operator.ge, "<": operator.lt, ">": operator.gt}
REQUIRED_SECTIONS = ("case", "parameters", "numerics", "metrics", "verification", "requirements")


class CaseError(ValueError):
    pass


def load_case(path: str | Path) -> tuple[dict, bytes, str]:
    """Return (case dict, raw bytes, sha256 hex) after validating structure."""
    path = Path(path)
    raw = path.read_bytes()
    try:
        case = tomllib.loads(raw.decode("utf-8"))
    except tomllib.TOMLDecodeError as e:
        raise CaseError(f"{path}: invalid TOML: {e}") from e

    missing = [s for s in REQUIRED_SECTIONS if s not in case]
    if missing:
        raise CaseError(f"{path}: missing sections {missing}")

    from harness.backends import BACKENDS

    if case["case"].get("model") not in BACKENDS:
        raise CaseError(f"{path}: unsupported model {case['case'].get('model')!r} "
                        f"(supported: {sorted(BACKENDS)})")

    xc = case.get("cross_check")
    if xc is not None and not {"against_case", "max_rel_diff"} <= set(xc):
        raise CaseError(f"{path}: [cross_check] needs 'against_case' and 'max_rel_diff'")

    ids = set()
    for r in case["requirements"]:
        for key in ("id", "text", "metric", "operator", "limit", "units"):
            if key not in r:
                raise CaseError(f"{path}: requirement missing '{key}': {r}")
        if r["id"] in ids:
            raise CaseError(f"{path}: duplicate requirement id {r['id']}")
        ids.add(r["id"])
        if r["operator"] not in OPERATORS:
            raise CaseError(f"{path}: {r['id']} operator must be one of {list(OPERATORS)}")
        if r["metric"] not in METRICS:
            raise CaseError(f"{path}: {r['id']} metric must be one of {sorted(METRICS)}")

    sweep = case.get("sweep")
    if sweep:
        if sweep.get("parameter") not in case["parameters"]:
            raise CaseError(f"{path}: sweep parameter must name an entry in [parameters]")
        if not sweep.get("values"):
            raise CaseError(f"{path}: sweep.values must be a non-empty list")

    return case, raw, hashlib.sha256(raw).hexdigest()


def expand_points(case: dict) -> list[tuple[str, dict]]:
    """Return [(label, parameters)] - one point per sweep value, or the baseline."""
    base = dict(case["parameters"])
    sweep = case.get("sweep")
    if not sweep:
        return [("p00_baseline", base)]
    name = sweep["parameter"]
    points = []
    for i, value in enumerate(sweep["values"]):
        params = dict(base)
        params[name] = value
        points.append((f"p{i:02d}_{name}-{value:g}", params))
    return points
