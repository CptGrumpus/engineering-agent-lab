"""Study 18 classification-line geometry (models/fea/pressure_vessel.py scl_lines)."""

import importlib.util
import math
from pathlib import Path

import numpy as np

_spec = importlib.util.spec_from_file_location(
    "pv_model", Path(__file__).resolve().parent.parent / "models" / "fea" / "pressure_vessel.py")
W = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(W)

P = {"shell_inner_radius_mm": 500.0, "shell_thickness_mm": 16.0, "shell_half_length_mm": 1000.0,
     "nozzle_inner_radius_mm": 100.0, "nozzle_thickness_mm": 12.0, "nozzle_length_mm": 350.0,
     "weld_fillet_radius_mm": 10.0}


def test_axes_orthonormal_and_lines_odd():
    for name, (pts, axes, _) in W.scl_lines(P, 21).items():
        assert len(pts) == 21, name
        assert np.allclose(axes @ axes.T, np.eye(3)), name
        # the first axis runs along the line
        d = (pts[-1] - pts[0]) / np.linalg.norm(pts[-1] - pts[0])
        assert abs(abs(d @ axes[0]) - 1) < 1e-12, name


def test_crotch_lines_start_at_the_inner_corner_and_end_on_the_fillet():
    d = W.dims(P)
    L = W.scl_lines(P, 21)
    for name, centre in (("crotch_long", (d["Ro"] + d["rf"], 0.0, d["rno"] + d["rf"])),
                         ("crotch_trans", (math.sqrt((d["Ro"] + d["rf"]) ** 2 - (d["rno"] + d["rf"]) ** 2),
                                           d["rno"] + d["rf"], 0.0))):
        pts = L[name][0]
        a, b = pts[0], pts[-1]
        assert abs(math.hypot(a[0], a[1]) - d["Ri"]) < 1e-9, name   # on the shell bore
        assert abs(math.hypot(a[1], a[2]) - d["rni"]) < 1e-9, name  # on the nozzle bore
        assert abs(np.linalg.norm(b - np.array(centre)) - d["rf"]) < 1e-9, name  # on the fillet
        # the ball centre is rf from both outer surfaces
        c = np.array(centre)
        assert abs(math.hypot(c[0], c[1]) - d["Ro"] - d["rf"]) < 1e-9
        assert abs(math.hypot(c[1], c[2]) - d["rno"] - d["rf"]) < 1e-9


def test_toe_offset_moves_only_the_toe_lines():
    base, moved = W.scl_lines(P, 21), W.scl_lines(P | {"scl_toe_offset_mm": 5.0}, 21)
    for name in ("far", "crotch_long", "crotch_trans"):
        assert np.array_equal(base[name][0], moved[name][0]), name
    assert np.allclose(moved["shell_long"][0][:, 2] - base["shell_long"][0][:, 2], 5.0)
    assert np.allclose(moved["nozzle_long"][0][:, 0] - base["nozzle_long"][0][:, 0], 5.0)
    # along the shell's outer surface in the transverse plane, an arc of 5 mm
    ang = lambda q: math.atan2(q[1], q[0])  # noqa: E731
    assert abs((ang(moved["shell_trans"][0][-1]) - ang(base["shell_trans"][0][-1])) * W.dims(P)["Ro"] - 5.0) < 1e-9
