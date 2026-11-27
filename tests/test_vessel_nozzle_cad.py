"""Study 18 part 2: the detailed nozzle assembly (models/cad/vessel_nozzle.py) against hand volumes, the analysed
solid and clearances."""
import math
import tempfile
from pathlib import Path

import numpy as np
import pytest

pytest.importorskip("cadquery")

from models.cad import vessel_nozzle as vn  # noqa: E402


def volume(w) -> float:
    """OCC's volume with a tight tolerance: the default one is only good to about 1e-6 on the saddle-cut faces."""
    from OCP.BRepGProp import BRepGProp
    from OCP.GProp import GProp_GProps

    g = GProp_GProps()
    BRepGProp.VolumeProperties_s(w.val().wrapped, g, 1e-9)
    return g.Mass()


@pytest.fixture(scope="module", params=["t12", "t12_pad"])
def design(request):
    return request.param, vn.build(request.param)


def test_every_part_matches_its_hand_volume(design):
    name, parts = design
    hv = vn.hand_volumes(name)
    assert set(parts) == set(hv)
    for k, w in parts.items():
        # exact quadratures to 1e-8; the welds' section-by-section Pappus leaves out the shell's curvature across the
        # fillet (0.8 % at 10 mm, shrinking with the fillet: test_weld_formula_converges)
        assert volume(w) == pytest.approx(hv[k], rel=1e-2 if "weld" in k else 1e-8), k


def test_no_part_overlaps_another(design):
    _, parts = design
    names = list(parts)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            common = parts[a].intersect(parts[b]).vals()
            assert (common[0].Volume() if common else 0.0) < 1e-3, (a, b)


def test_assembly_metal_is_the_analysed_solid():
    """Shell, nozzle and weld of the unpadded design are the FE model's quarter, four times over."""
    from models.fea import pressure_vessel as pv

    s = vn.DESIGNS["t12"]
    p = {"shell_inner_radius_mm": s["Ri"], "shell_thickness_mm": s["t"], "shell_half_length_mm": s["L"],
         "nozzle_inner_radius_mm": s["rni"], "nozzle_thickness_mm": s["tn"], "nozzle_length_mm": s["Ln"],
         "weld_fillet_radius_mm": s["rf"]}
    quarter = pv.build_step(p, Path(tempfile.mkdtemp()) / "v.step")["volume_mm3"]
    parts = vn.build("t12")
    assert vn.analysed_metal(parts) == pytest.approx(4 * quarter, rel=1e-5)


def test_weld_formula_converges():
    """The weld's hand volume approaches the CAD's as the fillet shrinks (the curvature term goes as f^2)."""
    gaps = []
    for f in (10.0, 5.0):
        vn.DESIGNS["_f"] = vn.BASE | {"pad": False, "rf": f}
        try:
            gaps.append(abs(volume(vn.build("_f")["weld_nozzle"]) / vn.hand_volumes("_f")["weld_nozzle"] - 1))
        finally:
            del vn.DESIGNS["_f"]
    assert gaps[1] < gaps[0] / 3


def test_spandrel_against_closed_forms():
    A, uc = vn.spandrel(np.array([math.pi / 2, 2 * math.pi / 3]), 2.0)
    assert A[0] == pytest.approx(4 * (1 - math.pi / 4), rel=1e-5)
    assert uc[0] == pytest.approx(2 * (10 - 3 * math.pi) / (3 * (4 - math.pi)), rel=1e-5)
    a = 2 * math.pi / 3
    assert A[1] == pytest.approx(4 * (1 / math.tan(a / 2) - (math.pi - a) / 2), rel=1e-5)


def test_disk_quadrature_against_a_closed_form():
    # a flat layer (R1, R2 -> infinity with R2 - R1 = h) over a disk is pi a^2 h
    R, h, a = 1e7, 3.0, 50.0
    assert vn.wall_in_disk(a, R, R + h) == pytest.approx(math.pi * a * a * h, rel=1e-6)


def test_the_analysed_geometry():
    s = vn.DESIGNS["t12"]
    assert (s["Ri"], s["t"], s["L"], s["rni"], s["tn"], s["Ln"], s["rf"]) == (500, 16, 1000, 100, 12, 350, 10)
