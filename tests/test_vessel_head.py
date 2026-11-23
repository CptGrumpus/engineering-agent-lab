"""Study 18 head-to-shell junction: mesh generator and the closed forms (models/fea/vessel_head_axi.py)."""

import importlib.util
import math
from pathlib import Path

import numpy as np
import pytest

_spec = importlib.util.spec_from_file_location(
    "vh_model", Path(__file__).resolve().parent.parent / "models" / "fea" / "vessel_head_axi.py")
W = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(W)

P = {"shell_inner_radius_mm": 500.0, "shell_thickness_mm": 16.0, "head_thickness_mm": 16.0, "shell_length_mm": 1000.0,
     "pressure_MPa": 3.5, "youngs_modulus_MPa": 2e5, "poisson_ratio": 0.3, "element_size_mm": 2.0,
     "element_aspect": 2.0}


@pytest.mark.parametrize("th", [16.0, 8.0])
def test_elements_counterclockwise_and_interface_shared(th):
    p = P | {"head_thickness_mm": th}
    nodes, elems, cyl, head = W.build_mesh(p)
    for _, c, *_ in elems:
        q = np.array([nodes[k] for k in c[:4]])
        assert 0.5 * np.sum(q[:, 0] * np.roll(q[:, 1], -1) - np.roll(q[:, 0], -1) * q[:, 1]) > 0
    d = W.dims(p)
    for i in range(2 * d["nh"] + 1):  # the head's first row is the shell's top row
        assert head[(i, 0)] == cyl[(i, 2 * d["na"])]
    axis = [nodes[head[(i, 2 * d["nphi"])]] for i in range(2 * d["nh"] + 1) if (i, 2 * d["nphi"]) in head]
    assert all(r == 0.0 for r, _ in axis)


def test_thickness_must_be_a_whole_number_of_elements():
    with pytest.raises(ValueError):
        W.dims(P | {"head_thickness_mm": 7.0})


def test_lame_solutions_satisfy_their_boundary_conditions():
    Ri, t = 500.0, 16.0
    sr, sh, sa, _ = W.lame_cylinder(P, np.array([Ri, Ri + t]))
    assert sr[0] == pytest.approx(-3.5) and abs(sr[1]) < 1e-12
    assert sa[0] * (2 * Ri * t + t ** 2) == pytest.approx(3.5 * Ri ** 2)  # end thrust
    sr, st, _ = W.lame_sphere(P, np.array([Ri, Ri + t]))
    assert sr[0] == pytest.approx(-3.5) and abs(sr[1]) < 1e-12
    # mean hoop of the cylinder is p Ri / t exactly
    r = np.linspace(Ri, Ri + t, 2001)
    assert np.trapezoid(W.lame_cylinder(P, r)[1], r) / t == pytest.approx(3.5 * Ri / t, rel=1e-9)


def test_discontinuity_theory_thin_limit():
    th = W.discontinuity_theory(P)
    assert th["Q0_N_per_mm"] == pytest.approx(th["Q0_thin_N_per_mm"], rel=2e-3)  # p / (8 beta)
    # thin limit of the junction hoop membrane: 3/4 of p R / t
    assert th["hoop_membrane_junction_MPa"] == pytest.approx(0.75 * 3.5 * 508 / 16, rel=0.03)
    assert th["x_bending_max_mm"] == pytest.approx(math.pi / 4 / th["beta_per_mm"])
    assert W.discontinuity_theory(P | {"head_thickness_mm": 8.0}) == {}
