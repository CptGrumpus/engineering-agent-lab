"""Study interface: everything the generic harness needs to know about one
family of engineering problems (its models, metrics, checks, and plots)."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from harness.backend_base import Backend


class Study:
    name = ""
    #: model name used in case files -> backend class
    models: dict[str, type[Backend]] = {}
    #: metric names requirements may reference
    metrics: frozenset[str] = frozenset()
    #: required keys in [parameters]
    param_names: tuple[str, ...] = ()
    series_file = "timeseries.csv"
    #: one-line description of what compare_point measures (shown in reports)
    compare_description = "max relative difference"

    def derive(self, params: dict) -> dict:
        """Validate parameters (raise ValueError) and return derived quantities."""
        return {}

    def compute_metrics(self, series: dict, params: dict, case: dict) -> dict:
        raise NotImplementedError

    def verify_point(self, case: dict, point: dict, pdir: Path, series: dict,
                     backend: Backend) -> list[dict]:
        """Run independent checks; may write evidence files/figures into pdir."""
        raise NotImplementedError

    def compare_point(self, case: dict, params: dict, a: dict, b: dict) -> float:
        """Max relative difference between two runs' series for the same point.

        Default: every non-time column, normalized by the column's max magnitude.
        """
        diffs = []
        for col in a:
            if col.startswith("t_") or col not in b:
                continue
            scale = max(np.max(np.abs(a[col])), np.max(np.abs(b[col])), 1e-300)
            diffs.append(float(np.max(np.abs(a[col] - b[col])) / scale))
        return max(diffs) if diffs else float("inf")
