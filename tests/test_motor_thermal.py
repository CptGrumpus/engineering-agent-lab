"""Study 7 thermal network: the T-equivalent pieces against the exact 1D conduction solutions."""

import math

import numpy as np
import pytest

from models.motor.thermal_network import Network, cyl_teq, slab_teq


def _piece_cyl(r_in, r_out, L, k, q_W, t_in, t_out):
    net = Network()
    Ro, Ri, Rc = cyl_teq(r_in, r_out, L, k)
    net.R("c", "m", Rc)
    net.R("c", "o", Ro)
    net.R("c", "i", Ri)
    net.Q("m", q_W)
    net.fix("o", t_out)
    net.fix("i", t_in)
    s = net.solve()
    return s["T"]["m"], (s["T"]["c"] - t_out) / Ro


@pytest.mark.parametrize("r_in,r_out", [(0.0553, 0.0802), (0.1145, 0.1346), (0.01, 0.1)])
def test_cylinder_mean_and_split_exact(r_in, r_out):
    L, k, qv = 0.08, 28.0, 2e5
    Q = qv * math.pi * (r_out ** 2 - r_in ** 2) * L
    for t_in, t_out in ((0.0, 0.0), (30.0, 10.0)):
        # exact: T = -q r^2 / (4k) + a ln r + b
        A = np.array([[math.log(r_in), 1], [math.log(r_out), 1]])
        a, b = np.linalg.solve(A, [t_in + qv * r_in ** 2 / (4 * k), t_out + qv * r_out ** 2 / (4 * k)])
        r = np.linspace(r_in, r_out, 200001)
        T = -qv * r ** 2 / (4 * k) + a * np.log(r) + b
        mean = np.trapezoid(T * r, r) / np.trapezoid(r, r)
        q_out = -k * (-qv * r_out / (2 * k) + a / r_out) * 2 * math.pi * r_out * L
        m, qo = _piece_cyl(r_in, r_out, L, k, Q, t_in, t_out)
        assert m == pytest.approx(mean, rel=1e-8, abs=1e-8)
        assert qo == pytest.approx(q_out, rel=1e-8, abs=1e-8)


def test_slab_mean_exact():
    Lx, A, k, qv = 0.004, 0.01, 1.0, 1e6
    Rh, Rc = slab_teq(Lx, A, k)
    net = Network()
    net.R("c", "m", Rc)
    net.R("c", "a", Rh)
    net.R("c", "b", Rh)
    net.Q("m", qv * Lx * A)
    net.fix("a", 0.0)
    net.fix("b", 5.0)
    T = net.solve()["T"]
    # exact: linear between faces + q x (L - x) / 2k; mean = (Ta + Tb)/2 + q L^2 / 12k
    assert T["m"] == pytest.approx(2.5 + qv * Lx ** 2 / (12 * k), rel=1e-12)


def test_network_energy_balance():
    net = Network()
    net.R("a", "b", 2.0)
    net.R("b", "s", 1.0)
    net.R("a", "s", 3.0)
    net.Q("a", 10.0)
    net.Q("b", 5.0)
    net.fix("s", 20.0)
    s = net.solve()
    assert s["balance_rel"] < 1e-12
