"""Hertz reference, the subsurface-peak metric, and a coarse CalculiX contact run."""

from pathlib import Path

import numpy as np
import pytest
from scipy.integrate import quad

from validation import hertz


def test_hertz_textbook_constants():
    r = hertz.line_contact(500.0, 50.0, 210000.0, 0.3)
    assert r["E_star_MPa"] == pytest.approx(210000 / (2 * 0.91))
    assert r["max_shear_MPa"] / r["peak_pressure_MPa"] == pytest.approx(0.3003, abs=2e-4)
    assert r["max_shear_depth_mm"] / r["half_width_mm"] == pytest.approx(0.7862, abs=2e-4)
    # the elliptical pressure carries the line load
    load, _ = quad(lambda x: hertz.pressure(x, r["half_width_mm"], r["peak_pressure_MPa"]),
                   -r["half_width_mm"], r["half_width_mm"])
    assert load == pytest.approx(500.0, rel=1e-9)
    # at the surface the subsurface field reduces to the surface pressure (equal biaxial)
    sx, sz = hertz.subsurface_stresses(0.0, r["half_width_mm"], r["peak_pressure_MPa"])
    assert sx == pytest.approx(-r["peak_pressure_MPa"]) and sz == pytest.approx(-r["peak_pressure_MPa"])


def test_subsurface_peak_interpolates_between_nodes():
    from studies.hertz_contact import subsurface_peak

    d = np.linspace(0.0, 1.0, 11)
    t = 5.0 - 3.0 * (d - 0.437) ** 2          # true peak between nodes 0.4 and 0.5
    tau, z = subsurface_peak({"depth_mm": d.tolist(), "tau_MPa": t.tolist()})
    assert z == pytest.approx(0.437, abs=1e-12) and tau == pytest.approx(5.0, abs=1e-12)


try:
    from studies.fin import find_ccx
    find_ccx()
    HAVE_CCX = True
except Exception:
    HAVE_CCX = False


@pytest.mark.skipif(not HAVE_CCX, reason="CalculiX not installed")
def test_coarse_contact_run_balances_and_matches_hertz_below_the_surface(tmp_path):
    from harness.run import run_case
    from harness.verify import verify_run

    text = Path("cases/contact_roller_mesh.toml").read_text(encoding="utf-8")
    text = text.replace("values = [0.08, 0.04, 0.02]", "values = [0.08]")
    case = tmp_path / "contact.toml"
    case.write_text(text, encoding="utf-8")
    run_dir = run_case(case, runs_root=tmp_path / "runs")
    checks = {c["id"]: c for c in verify_run(run_dir)["points"][0]["checks"]}
    for cid in ("equilibrium", "hertz_subsurface_shear", "hertz_shear_depth", "penalty_penetration"):
        assert checks[cid]["status"] == "PASS", checks[cid]
    # the coarse mesh is too coarse for the half-width: the check must say so
    assert checks["hertz_half_width"]["status"] == "FAIL"
