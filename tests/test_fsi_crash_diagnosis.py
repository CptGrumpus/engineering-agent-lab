"""FSI crash diagnosis (study 6): cell volumes, centres and non-orthogonality on two hexes with known answers."""

import importlib.util
from pathlib import Path

import numpy as np
import pytest

_spec = importlib.util.spec_from_file_location(
    "fcd", Path(__file__).resolve().parent.parent / "scripts/fsi_crash_diagnosis.py")
D = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(D)


def two_cubes(shift=0.0):
    """Cells [0,1]^3 and [1,2]x[0,1]^2; `shift` moves the far face's top edge in x (shear of cell 1)."""
    P = np.array([[x, y, z] for z in (0, 1) for y in (0, 1) for x in (0, 1, 2)], float)
    for k in (11, 8):                       # x = 2 at y = 1 (z = 1 and z = 0): shear the second cell's far face
        P[k, 0] += shift
    idx = lambda x, y, z: z * 6 + y * 3 + x  # noqa: E731
    faces = [[idx(1, 0, 0), idx(1, 1, 0), idx(1, 1, 1), idx(1, 0, 1)]]          # internal, normal +x
    own = [0]
    for c, x0 in ((0, 0), (1, 1)):
        x1 = x0 + 1
        bfaces = [[idx(x0, 0, 0), idx(x0, 0, 1), idx(x0, 1, 1), idx(x0, 1, 0)] if c == 0 else None,
                  [idx(x1, 0, 0), idx(x1, 1, 0), idx(x1, 1, 1), idx(x1, 0, 1)] if c == 1 else None,
                  [idx(x0, 0, 0), idx(x1, 0, 0), idx(x1, 0, 1), idx(x0, 0, 1)],
                  [idx(x0, 1, 0), idx(x0, 1, 1), idx(x1, 1, 1), idx(x1, 1, 0)],
                  [idx(x0, 0, 0), idx(x0, 1, 0), idx(x1, 1, 0), idx(x1, 0, 0)],
                  [idx(x0, 0, 1), idx(x1, 0, 1), idx(x1, 1, 1), idx(x0, 1, 1)]]
        for f in bfaces:
            if f is not None:
                faces.append(f)
                own.append(c)
    return P, faces, np.array(own), np.array([1])


def test_unit_cubes():
    V, C, no = D.geometry(*two_cubes(), 2)
    assert V == pytest.approx([1.0, 1.0])
    assert C[0] == pytest.approx([0.5, 0.5, 0.5]) and C[1] == pytest.approx([1.5, 0.5, 0.5])
    assert no == pytest.approx([0.0], abs=1e-9)


def test_shear_changes_volume_and_angle():
    V, C, no = D.geometry(*two_cubes(shift=0.5), 2)
    assert V[1] == pytest.approx(1.25)                 # a prism with the top edge moved 0.5 in x: +0.25
    assert no[0] > 1.0                                 # the second cell's centre moves up and out: non-orthogonal
