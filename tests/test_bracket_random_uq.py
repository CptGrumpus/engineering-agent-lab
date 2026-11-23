"""Study H: the vectorised damage, the surrogate and the response from a modal basis, against study C's functions."""

import math

import numpy as np
import pytest

from studies import bracket_random as R
from studies import bracket_random_uq as H


def _moments():
    f = np.linspace(200.0, 2000.0, 3000)
    out = []
    for f0, w in ((262.0, 5.0), (262.0, 60.0), (900.0, 300.0)):
        G = 50.0 * np.exp(-0.5 * ((f - f0) / w) ** 2) + 0.5 * np.exp(-0.5 * ((f - 1600) / 80) ** 2)
        out.append(R.spectral_moments(G, f))
    return np.array(out)


def test_vectorised_dirlik_reproduces_study_c():
    m = _moments()
    want = [R.dirlik_damage(tuple(mm), 3600.0, 160.0) for mm in m]
    assert H.dirlik_damage_vec(m, 3600.0, 160.0) == pytest.approx(want, rel=1e-10)
    got = H.dirlik_damage_vec(m, 3600.0, np.array([160.0, 140.0, 180.0]))
    assert got[1] == pytest.approx(R.dirlik_damage(tuple(m[1]), 3600.0, 140.0), rel=1e-10)


def test_a_stronger_detail_category_is_a_scaled_stress():
    m = _moments()[:1]
    c = 1.13                                              # N(s; c dsc) = N(s / c; dsc), and m_k scales with stress^2
    a = H.dirlik_damage_vec(m, 3600.0, 160.0 * c)
    b = H.dirlik_damage_vec(m / c ** 2, 3600.0, 160.0)
    assert a == pytest.approx(b, rel=1e-9)


def test_surrogate_is_exact_on_its_nodes_and_close_between_them():
    zetas = np.geomspace(0.005, 0.08, 9)
    hs = [6.5, 6.75, 7.0, 7.25, 7.5]

    def fake(z, h):                                       # smooth power laws, like the real response
        vm = np.full((3, 2), 100.0 * z ** -1.0 * h ** -1.0)
        mom = np.stack([vm * 1.0, vm * 300, vm * 300 ** 2, vm * 300 ** 4], axis=-1)
        return {"vm_ms": vm, "moments": mom, "tip_ms": np.full(3, z ** -1.0 * h ** -3.0)}
    sur = H.Surrogate(zetas, hs, [[fake(z, h) for h in hs] for z in zetas])
    r = sur(np.array([zetas[3], 0.0123]), np.array([7.0, 6.9]))
    assert r["vm_ms"][0, 0, 0] == pytest.approx(fake(zetas[3], 7.0)["vm_ms"][0, 0], rel=1e-10)
    assert r["tip_ms"][1, 2] == pytest.approx(fake(0.0123, 6.9)["tip_ms"][2], rel=1e-6)
    assert r["moments"].shape == (2, 3, 2, 4)
    sur.clipped = 0
    sur(np.array([1e-4]), np.array([7.0]))
    assert sur.clipped == 1


def test_one_mode_basis_gives_miles_tip_and_proportional_stress():
    fn, gz, phi, zeta = 262.0, 0.0112, 30.0, 0.02
    basis = {"frequency_Hz": np.array([fn]), "participation": np.array([[0.0, 0.0, gz, 0.0, 0.0, 0.0]]),
             "phi_tip": np.array([[0.0, 0.0, phi]]), "hotspot_modal_stress": np.zeros((1, 6, 1))}
    basis["hotspot_modal_stress"][0, 0, 0] = 5.0e4         # sigma_xx per unit modal coordinate
    S0 = 0.04 * R.G ** 2
    r = H.response_moments(basis, zeta, S0, 1.0, 20000.0, n_log=2000, n_res=400)
    assert math.sqrt(r["tip_ms"][2]) == pytest.approx(R.miles_tip_rms(phi * gz, fn, zeta, S0), rel=3e-3)
    assert math.sqrt(r["vm_ms"][2, 0]) == pytest.approx(5.0e4 / phi * math.sqrt(r["tip_ms"][2]), rel=1e-10)
    assert r["tip_ms"][0] == 0.0


def test_distributions_have_the_stated_medians_and_spreads():
    p = {"damping_ratio": 0.02, "damping_sigma_ln": math.log(2) / 1.645, "test_level_tolerance_dB": 1.5,
         "sn_factor_cov": 0.10, "thickness_mm": 7.0, "thickness_sd_mm": 0.1}
    d = H.distributions(p)
    assert d[0].ppf(0.05) == pytest.approx(0.01, rel=1e-3) and d[0].ppf(0.95) == pytest.approx(0.04, rel=1e-3)
    assert d[1].ppf(0.0) == -1.5 and d[1].ppf(1.0) == 1.5
    assert d[2].median() == pytest.approx(1.0) and d[2].std() / d[2].mean() == pytest.approx(0.10, rel=1e-9)
    assert d[3].std() == 0.1


def test_scale_thickness_scales_only_z(tmp_path):
    from studies.bracket_random import _W
    inp = tmp_path / "mesh.inp"
    inp.write_text("*Heading\n mesh\n*NODE\n1, 0.0, -12.5, 3.5\n2, 150.0, 12.5, -3.5\n*ELEMENT, type=C3D10, ELSET=ARM\n"
                   "1, 1, 2\n", encoding="utf-8")
    _W.scale_thickness(inp, 7.5 / 7.0)
    ids, xyz = _W.read_mesh_nodes(inp)
    assert ids.tolist() == [1, 2] and xyz[1, 0] == 150.0 and xyz[0, 1] == -12.5
    assert xyz[0, 2] == pytest.approx(3.75) and xyz[1, 2] == pytest.approx(-3.75)
    assert "*ELEMENT, type=C3D10, ELSET=ARM\n1, 1, 2" in inp.read_text(encoding="utf-8")
