"""Bolted joint: the VDI 2230 hand method and the joint mesh that the slip check depends on."""

import importlib.util
from pathlib import Path

import numpy as np
import pytest

from studies.bolted_joint import contact_diameter
from validation import bolted_joint as bj

ROOT = Path(__file__).resolve().parent.parent
E = 210000.0


def test_bolt_compliance_parts_add_up_and_scale_with_length():
    d0, parts = bj.bolt_compliance(E, "M8", 8.0, 4.0)
    assert d0 == pytest.approx(sum(parts.values()))
    d1, _ = bj.bolt_compliance(E, "M8", 9.0, 4.0)
    assert d1 - d0 == pytest.approx(1.0 / (E * np.pi * 8.0**2 / 4))


def test_plate_compliance_cone_matches_a_numerical_integral_of_the_cone():
    # two opposed cones from the washers to the interface, angle phi: integrate dz / (E A(z))
    lK, dW, dh, DA = 12.0, 13.0, 9.0, 40.0
    tphi = bj.cone_tan_phi(lK, dW, DA)
    z = np.linspace(0, lK / 2, 200001)
    D = dW + 2 * z * tphi
    A = np.pi / 4 * (D**2 - dh**2)
    num = 2 * np.trapezoid(1.0 / (E * A), z)
    assert bj.plate_compliance(E, lK, dW, dh, DA) == pytest.approx(num, rel=1e-6)


def test_joint_diagram_relations():
    assert bj.slip_load(0.2, 15000.0) == pytest.approx(3000.0)
    assert bj.opening_load(12000.0, 0.0) == pytest.approx(12000.0)
    assert bj.load_factor(1.0, 1.0, 1.0) == pytest.approx(0.5)
    assert bj.embedding_loss(0.01, 2e-6, 5e-7) == pytest.approx(4000.0)


def test_cone_formula_refuses_a_plate_narrower_than_the_cone():
    with pytest.raises(ValueError):
        bj.plate_compliance(E, 12.0, 13.0, 9.0, 15.0)


def test_washer_load_uses_the_meshed_area():
    spec = importlib.util.spec_from_file_location("bj_t", ROOT / "models/fea/bolted_joint_ccx.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    p = dict(plate_outer_diameter_mm=40, hole_diameter_mm=9, washer_diameter_mm=13, top_thickness_mm=6,
             bottom_thickness_mm=6, youngs_modulus_MPa=E, poisson_ratio=0.3, preload_N=15000, friction_coefficient=0.2,
             element_size_mm=1.0, contact_stiffness_factor=50, stick_slope_factor=50, slip_displacement_mm=0.012,
             slip_increments=6)
    g = m.JointMesh(p)
    assert g.r[g.i_w] == pytest.approx(6.5) and g.r[0] == pytest.approx(4.5) and g.r[-1] == pytest.approx(20.0)
    deck = m.write_deck(p, g)
    pw = float(next(ln for ln in deck.splitlines() if ", P2, " in ln).split(",")[2])
    a_mesh = sum(0.5 * (g.r[i + 1] ** 2 - g.r[i] ** 2) * np.sin(g.th[j + 1] - g.th[j])
                 for j in range(g.nt) for i in range(g.i_w))
    assert pw * a_mesh == pytest.approx(7500.0, rel=1e-12)          # exactly F_V / 2 on the half model


def test_contact_diameter_interpolates_the_zero_crossing():
    r = np.array([4.5, 6.0, 8.0, 10.0, 12.0])
    p = np.array([100.0, 80.0, 30.0, -0.0, 0.0])
    assert contact_diameter(r, p) == pytest.approx(2 * 10.0)
    p2 = np.array([100.0, 80.0, 30.0, 10.0, 0.0])
    assert contact_diameter(r, p2) == pytest.approx(2 * 12.0)


def test_rigid_limit_slip_extrapolation_recovers_coulomb():
    """Measured plateaus (1.0 mm half model x 2): 2996.062 N at E, 2999.960 N at 100 E, mu F_V = 3000 N."""
    from studies.bolted_joint import rigid_limit_slip

    s = rigid_limit_slip(2996.062, 2999.960, 100.0)
    assert abs(s - 3000.0) / 3000.0 < 1e-5
    assert rigid_limit_slip(2900.0, 2990.0, 10.0) == pytest.approx(3000.0)   # exact for S = 3000 - c / E
