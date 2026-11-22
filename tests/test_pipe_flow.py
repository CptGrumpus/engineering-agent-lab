"""Study 19 pipe flow: the smooth-pipe reference, the radial grading and the axial length of the periodic wedge."""

import importlib.util
import math
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("pipe_openfoam_t", ROOT / "models/cfd/pipe_openfoam.py")
W = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(W)

BASE = dict(diameter_m=0.1, reynolds_number=1e5, kinematic_viscosity_m2_per_s=1e-6, n_radial=80,
            first_cell_yplus=0.5, wall_treatment="low_re", turbulence_model="kOmegaSST")
NUMERICS = dict(max_iterations=10, residual_p=1.0, residual_U=1e-9, residual_turb=1e-9)


def test_prandtl_law_satisfies_its_own_equation():
    for re_ in (1e4, 1e5, 1e6):
        f = W.friction_prandtl(re_)
        assert 1 / math.sqrt(f) == pytest.approx(2.0 * math.log10(re_ * math.sqrt(f)) - 0.8, rel=1e-12)
    assert W.friction_prandtl(1e5) == pytest.approx(0.017993, rel=1e-4)  # the Moody chart's smooth curve


@pytest.mark.parametrize("n,yp", [(40, 1.0), (80, 0.5), (640, 0.0625)])
def test_grading_fills_the_radius_and_hits_the_wall_cell(n, yp):
    g = W.grading(BASE | {"n_radial": n, "first_cell_yplus": yp})
    q, h1 = g["growth"], g["h1_m"]
    assert h1 * (q ** n - 1) / (q - 1) == pytest.approx(g["R_m"], rel=1e-9)
    assert h1 * g["u_tau_est_m_per_s"] / BASE["kinematic_viscosity_m2_per_s"] == pytest.approx(yp, rel=1e-12)


def _block_length(case: Path) -> float:
    text = (case / "system/blockMeshDict").read_text(encoding="utf-8")
    return float(re.search(r"\(0 0 0\) \(([-+0-9.eE]+) 0 0\)", text).group(1))


def test_default_axial_length_is_unchanged(tmp_path):
    # earlier cases (pipe_rans_mesh, pipe_rans_reynolds) must reproduce: D/50 unless the wall cells call for more
    out = W.write_case(BASE, NUMERICS, tmp_path)
    assert out["length_m"] == _block_length(tmp_path) == pytest.approx(BASE["diameter_m"] / 50)


@pytest.mark.parametrize("re_,n,yp", [(1e5, 640, 0.0625), (2e6, 120, 0.5), (2e6, 40, 160.0)])
def test_geometric_mean_length_bounds_the_aspect_ratio(tmp_path, re_, n, yp):
    p = BASE | {"reynolds_number": re_, "n_radial": n, "first_cell_yplus": yp}
    out = W.write_case(p, NUMERICS | {"axial_length_rule": "geometric_mean"}, tmp_path)
    g = W.grading(p)
    wall, axis = g["h1_m"], g["h1_m"] * g["growth"] ** (n - 1)
    L = _block_length(tmp_path)
    assert out["length_m"] == L
    # the same ratio at both ends, sqrt(axis / wall cell), and well under checkMesh's 1000
    assert L / wall == pytest.approx(axis / L, rel=1e-9)
    assert L / wall == pytest.approx(math.sqrt(axis / wall), rel=1e-9)
    assert L / wall < 100
    # the old fixed length is what checkMesh flagged at Re 2e6 (aspect ratio 2884 on n 120)
    if (re_, n) == (2e6, 120):
        assert g["length_m"] / wall > 1000
