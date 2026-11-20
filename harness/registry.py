"""Model registry: case-file `model` name -> (study, backend class)."""

from __future__ import annotations

from harness.backend_base import Backend
from harness.study import Study


def _studies() -> list[Study]:
    from studies import (cantilever, channel_flow, duct_flow,  # lazy: avoids cycles
                         fin, mounting_plate, msd, quarter_car, strap_hole)

    return [msd.STUDY, quarter_car.STUDY, cantilever.STUDY, mounting_plate.STUDY,
            channel_flow.STUDY, duct_flow.STUDY, fin.STUDY, strap_hole.STUDY]


def models() -> dict[str, tuple[Study, type[Backend]]]:
    return {name: (s, b) for s in _studies() for name, b in s.models.items()}


def resolve(model: str) -> tuple[Study, Backend]:
    table = models()
    if model not in table:
        raise ValueError(f"unsupported model {model!r}; supported: {sorted(table)}")
    study, backend_cls = table[model]
    return study, backend_cls()


def study_for(model: str) -> Study:
    table = models()
    if model not in table:
        raise ValueError(f"unsupported model {model!r}; supported: {sorted(table)}")
    return table[model][0]
