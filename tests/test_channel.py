from pathlib import Path

import numpy as np
import pytest

from harness import openfoam as of
from validation import channel_flow as ref

FIELD = """FoamFile
{
    format      ascii;
    class       volVectorField;
    object      U;
}
dimensions      [0 1 -1 0 0 0 0];
internalField   nonuniform List<vector>
3
(
(0.1 0 0)
(0.2 -1e-05 0)
(3e-01 2.5e-3 0)
)
;
boundaryField
{
    inlet
    {
        type            fixedValue;
        value           uniform (0.1 0 0);
    }
    outlet
    {
        type            zeroGradient;
    }
    walls
    {
        type            calculated;
        value           nonuniform List<vector> 2((0 0 0) (1 2 3));
    }
}
"""

PHI = """FoamFile { class surfaceScalarField; object phi; }
internalField   nonuniform List<scalar> 2(1.5 2.5);
boundaryField
{
    inlet
    {
        type            calculated;
        value           nonuniform List<scalar>
2
(
-1e-05
-2.5e-05
)
;
    }
    outlet
    {
        type            calculated;
        value           uniform 3e-05;
    }
}
"""


def test_read_vector_field_and_patches(tmp_path):
    f = tmp_path / "U"
    f.write_text(FIELD, encoding="utf-8")
    u = of.read_internal_field(f)
    assert u.shape == (3, 3)
    assert np.allclose(u[:, 0], [0.1, 0.2, 0.3]) and u[2, 1] == pytest.approx(2.5e-3)
    assert np.allclose(of.read_patch_value(f, "inlet", 4), [[0.1, 0, 0]] * 4)
    assert of.read_patch_value(f, "outlet") is None  # zeroGradient writes no value
    assert np.allclose(of.read_patch_value(f, "walls"), [[0, 0, 0], [1, 2, 3]])


def test_read_scalar_patch(tmp_path):
    f = tmp_path / "phi"
    f.write_text(PHI, encoding="utf-8")
    assert np.allclose(of.read_internal_field(f), [1.5, 2.5])
    assert np.allclose(of.read_patch_value(f, "inlet"), [-1e-5, -2.5e-5])
    assert np.allclose(of.read_patch_value(f, "outlet", 2), [3e-5, 3e-5])


def test_solver_log(tmp_path):
    f = tmp_path / "log.foamRun"
    f.write_text("Time = 1\n\nsmoothSolver:  Solving for Ux, Initial residual = 1, Final residual = 0.1\n"
                 "GAMG:  Solving for p, Initial residual = 1, Final residual = 0.01\n"
                 "Time = 2\n\nsmoothSolver:  Solving for Ux, Initial residual = 5e-07, Final residual = 1e-9\n"
                 "GAMG:  Solving for p, Initial residual = 8e-07, Final residual = 1e-9\n\n"
                 "SIMPLE solution converged in 2 iterations\n\nEnd\n", encoding="utf-8")
    log = of.read_solver_log(f)
    assert log["converged"] and log["iterations"] == 2 and log["ended"]
    assert log["final_initial_residuals"] == {"Ux": 5e-7, "p": 8e-7}


def test_wsl_path():
    assert of.to_wsl_path(Path("C:/Users/a b/x")) == "/mnt/c/Users/a b/x"


def test_poiseuille_relations():
    U, H, mu = 0.1, 1e-3, 1.002e-3
    y = np.linspace(0, H, 2001)
    u = ref.velocity_profile(y, U, H)
    assert np.trapezoid(u, y) / H == pytest.approx(U, rel=1e-6)   # mean velocity
    assert u.max() == pytest.approx(1.5 * U, rel=1e-6)
    # force balance on the fluid slab: tau_w = (-dp/dx) H / 2
    assert ref.wall_shear_stress(U, H, mu) == pytest.approx(ref.pressure_gradient(U, H, mu) * H / 2)
    du = np.gradient(u, y)
    assert mu * du[0] == pytest.approx(ref.wall_shear_stress(U, H, mu), rel=1e-3)


def test_shah_london_limits():
    # far downstream f_app Re -> 24 + K(inf)/(4 x+): fully developed plus a fixed excess
    x_plus = 50.0
    assert ref.apparent_friction_re(x_plus) == pytest.approx(24 + 0.674 / (4 * x_plus), rel=1e-6)
    # so the long-channel drop is the Poiseuille drop plus K(inf) * rho U^2 / 2
    U, H, rho, mu = 0.1, 1e-3, 998.2, 1.002e-3
    Re = ref.reynolds(U, H, rho, mu)
    L = x_plus * 2 * H * Re
    excess = ref.pressure_drop_developing(L, U, H, rho, mu) - ref.pressure_gradient(U, H, mu) * L
    assert excess == pytest.approx(0.674 * 0.5 * rho * U**2, rel=1e-3)
    assert ref.entrance_length(U, H, rho, mu) == pytest.approx(
        2 * H * (0.315 / (1 + 0.0175 * Re) + 0.011 * Re))


try:
    of.find_openfoam_bashrc()
    HAVE_OPENFOAM = True
except Exception:
    HAVE_OPENFOAM = False


@pytest.mark.skipif(not HAVE_OPENFOAM, reason="OpenFOAM (WSL) not installed")
def test_channel_pipeline_coarse(tmp_path):
    from harness.run import run_case
    from harness.runio import read_json
    from harness.verify import verify_run

    text = Path("cases/channel_mesh.toml").read_text(encoding="utf-8").replace(
        "values = [10, 20, 40, 80]", "values = [20]")
    case = tmp_path / "c.toml"
    case.write_text(text, encoding="utf-8")
    run_dir = run_case(case, runs_root=tmp_path / "runs")
    manifest = read_json(run_dir / "manifest.json")
    assert manifest["status"] == "completed"
    pt = manifest["points"][0]
    assert (run_dir / "points" / pt["label"] / "solver" / "system" / "blockMeshDict").exists()
    assert pt["solver_outputs"]["converged"]
    summary = verify_run(run_dir)
    by_id = {c["id"]: c for c in summary["points"][0]["checks"]}
    for cid in ("mass_conservation", "momentum_balance", "velocity_profile_reference",
                "pressure_gradient_reference", "wall_shear_reference", "fully_developed"):
        assert by_id[cid]["status"] == "PASS", by_id[cid]


def test_duct_series_limits_and_mean():
    H, mu, U = 1e-3, 1.0016e-3, 0.1
    # wide duct -> parallel plates; square duct -> known f Re = 56.91 (Shah & London)
    assert ref.duct_flow_factor(H, 1000 * H) == pytest.approx(1.0, abs=1e-3)
    G_sq = ref.duct_pressure_gradient(U, H, H, mu)
    fanning_re = G_sq * H**2 / (2 * mu * U)  # D_h = H for a square duct
    assert fanning_re == pytest.approx(14.227, rel=1e-4)  # Darcy f Re = 56.91
    # the exact field integrates back to the mean velocity
    W = 20 * H
    G = ref.duct_pressure_gradient(U, H, W, mu)
    y = np.linspace(-H / 2, H / 2, 401)
    z = np.linspace(-W / 2, W / 2, 2001)
    u = ref.duct_velocity(*np.meshgrid(y, z, indexing="ij"), G, H, W, mu)
    assert np.trapezoid(np.trapezoid(u, z, axis=1), y) / (H * W) == pytest.approx(U, rel=1e-4)
    assert np.max(np.abs(u[0])) < 1e-12 and np.max(np.abs(u[:, 0])) < 1e-12  # no slip
