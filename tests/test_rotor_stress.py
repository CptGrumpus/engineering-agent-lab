"""Rotor overspeed study (study 7): linearization and the rotating-disk reference on cases with known answers."""

import importlib.util
import math
from pathlib import Path

import numpy as np
import pytest

from models.fea.rotor_ccx import linearize, rotating_disk

ROOT = Path(__file__).resolve().parent.parent


def test_linearize_separates_membrane_and_bending():
    s = np.linspace(0.0, 2.0, 201)
    stt = 100.0 + 50.0 * (1 - s)           # 100 MPa membrane, 50 MPa bending (linear across t = 2)
    zero = np.zeros_like(s)
    m, mb = linearize(s, zero, stt, zero)
    assert m == pytest.approx(100.0, rel=1e-9)
    assert mb == pytest.approx(150.0, rel=1e-9)


def test_linearize_removes_a_peak():
    s = np.linspace(0.0, 1.0, 2001)
    peak = 400.0 * np.exp(-((s - 0.0) / 0.02) ** 2)   # a local peak at one surface, like a notch
    zero = np.zeros_like(s)
    m, mb = linearize(s, zero, 100.0 + peak, zero)
    assert mb < 100.0 + 400.0 / 2                      # the linearized value is far below the peak


def test_linearize_von_mises_with_shear():
    s = np.linspace(0.0, 1.0, 11)
    m, mb = linearize(s, np.zeros_like(s), np.zeros_like(s), np.full_like(s, 10.0))
    assert m == pytest.approx(math.sqrt(3) * 10.0) and mb == pytest.approx(math.sqrt(3) * 10.0)


def test_rotating_disk_free_edges_and_bore_value():
    a, b, rho, w, nu = 55.0, 80.0, 7650e-12, 754.0, 0.3
    sr, st = rotating_disk(np.array([a, b]), a, b, rho, w, nu)
    assert abs(sr[0]) < 1e-12 and abs(sr[1]) < 1e-12          # traction-free bore and rim
    assert st[0] == pytest.approx((3 + nu) / 4 * rho * w ** 2 * (b * b + (1 - nu) / (3 + nu) * a * a), rel=1e-12)


def _exporter():
    spec = importlib.util.spec_from_file_location("erp", ROOT / "models/motor/export_rotor_pole.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class _Line:
    def __init__(self, d):
        self.a, self.b = complex(d["begin"]), complex(d["end"])
        self.kind = d["__class__"]

    def get_begin(self):
        return self.a

    def get_end(self):
        return self.b

    def get_center(self):
        return 0j          # revision 5's only arc is the bridge arc about the rotor centre


class _Surf:
    def __init__(self, d):
        self.label = d["label"]
        self.lines = []
        for ln in d["line_list"]:
            obj = _Line(ln)
            obj.__class__ = type(ln["__class__"], (_Line,), {})   # the exporter reads the class name
            self.lines.append(obj)

    def get_lines(self):
        return self.lines


class _Hole:
    def __init__(self, surfs):
        self.surfs = surfs

    def build_geometry(self):
        return self.surfs


def test_drawn_pocket_outline_is_the_union_of_its_surfaces():
    """Revision 5's HoleUD (end voids, magnets, 0.15 mm strips, centre void across the pole axis): the half outline,
    found from edges used once, is the same eight-segment chain as the HoleM50 pocket, ending on the outer edge."""
    import json
    E = _exporter()
    hole = json.loads((ROOT / "models/motor/Toyota_Prius_ORNL_rev5centre.json").read_text())["rotor"]["hole"][0]
    seq, mag = E._holeud_chain(_Hole([_Surf(s) for s in hole["surf_list"]]))
    kinds = [s[0] for s in seq]
    assert kinds == ["line"] * 6 + ["arc", "line"]
    assert abs(seq[0][1] - complex(63.4597, 0)) < 1e-3 and abs(seq[-1][2] - complex(69.5378, 0)) < 1e-3
    assert abs(seq[6][3] - 78.7378) < 1e-4                       # the bridge arc: 80.1878 - 1.45 mm
    A, _ = E._polygon_area_centroid(mag)
    assert abs(abs(A) - 18.9 * 6.5) < 1e-6
    end, gap = E._seat_on_outer_edge(seq, mag)
    assert abs(abs(end - seq[-1][2]) - 18.9) < 1e-6 and abs(gap - 0.15) < 1e-6
