"""Study: parametric mounting plate (CadQuery geometry automation).

Model:     cadquery_plate  (models/cad/mounting_plate.py)
Reference: closed-form area/volume and design-rule geometry (validation/plate_geometry.py)

Every point builds the solid, exports STEP and an SVG drawing, then measures
the result back out of the B-rep: volume, bounding box, and each hole's centre
and diameter. Verification compares those measurements with closed-form values
and re-imports the STEP file to prove the exchange file matches the model.
"""

from __future__ import annotations

import math
import shutil
import tempfile
from pathlib import Path

import numpy as np

from harness.backend_base import Backend, failed
from harness.checks import check
from harness.plotting import plate_figure
from harness.study import Study
from models.cad import mounting_plate as model
from validation import plate_geometry as ref


def measure(shape) -> dict:
    """Volume, bounding box, and through-holes (closed circular edges) of a solid."""
    bb = shape.BoundingBox()
    holes = {}
    for face in shape.Faces():
        if face.geomType() != "CYLINDER":
            continue
        for e in face.Edges():
            if e.geomType() == "CIRCLE" and e.IsClosed():
                c = e.arcCenter()
                key = (round(c.x, 6), round(c.y, 6))
                holes.setdefault(key, set()).add(round(2 * e.radius(), 9))
    table = sorted((x, y, max(ds)) for (x, y), ds in holes.items())
    return {
        "volume_mm3": shape.Volume(),
        "valid": bool(shape.isValid()),
        "bbox_mm": (bb.xlen, bb.ylen, bb.zlen),
        "holes": table,
    }


class CadQueryPlate(Backend):
    sources = ("models/cad/mounting_plate.py",)

    def prepare(self, source_dir=None, log_dir=None):
        import cadquery
        self._versions = {"cadquery": cadquery.__version__}

    def solve(self, params, numerics, tolerance_scale=1.0):
        import cadquery as cq

        work = Path(tempfile.mkdtemp(prefix="cq_plate_"))
        try:
            wp = model.build(params)
        except Exception as e:  # e.g. fillet larger than the plate, holes off the part
            return failed(f"CadQuery build failed: {type(e).__name__}: {e}")
        shape = wp.val()
        m = measure(shape)
        step = work / "plate.step"
        cq.exporters.export(wp, str(step))
        cq.exporters.export(wp, str(work / "plate_iso.svg"),
                            opt={"projectionDir": (1, -1, 0.8), "showHidden": False,
                                 "strokeWidth": 0.4, "width": 640, "height": 420})
        holes = np.array(m["holes"]) if m["holes"] else np.zeros((0, 3))
        series = {"hole_id": np.arange(len(holes), dtype=float),
                  "x_mm": holes[:, 0], "y_mm": holes[:, 1], "diameter_mm": holes[:, 2]}
        outline = [(p.x, p.y) for e in wp.faces("<Z").val().Edges()
                   for p in e.positions(np.linspace(0, 1, 24))]
        outputs = {"volume_mm3": m["volume_mm3"], "valid_solid": m["valid"],
                   "bbox_mm": list(m["bbox_mm"]), "outline_xy": outline}
        return {"success": True, "message": f"{len(holes)} holes measured", "nfev": None,
                "series": series, "outputs": outputs,
                "files": {"plate.step": step, "plate_iso.svg": work / "plate_iso.svg"},
                "cleanup": work}

    def tool_versions(self):
        return getattr(self, "_versions", {})


def _edge_distance_measured(series, params):
    L, W = float(params["length_mm"]), float(params["width_mm"])
    x, y = series["x_mm"], series["y_mm"]
    return float(np.min(np.minimum.reduce([L / 2 - np.abs(x), W / 2 - np.abs(y)])))


def _ligament_measured(series):
    x, y, d = series["x_mm"], series["y_mm"], series["diameter_mm"]
    if len(x) < 2:
        return math.inf
    dist = np.hypot(x[:, None] - x[None, :], y[:, None] - y[None, :])
    gap = dist - (d[:, None] + d[None, :]) / 2
    np.fill_diagonal(gap, np.inf)
    return float(np.min(gap))


class MountingPlateStudy(Study):
    name = "mounting_plate"
    models = {"cadquery_plate": CadQueryPlate}
    metrics = frozenset({"mass_g", "edge_distance_ratio", "ligament_mm"})
    param_names = model.PARAMS
    series_file = "holes.csv"
    compare_description = "max relative difference over hole table columns"

    def derive(self, params):
        L, W = float(params["length_mm"]), float(params["width_mm"])
        r, d = float(params["corner_radius_mm"]), float(params["hole_diameter_mm"])
        if min(L, W, float(params["thickness_mm"]), d) <= 0 or r < 0 or 2 * r > min(L, W):
            raise ValueError("invalid plate dimensions")
        e = ref.edge_distance(params)
        if e <= d / 2:
            raise ValueError("holes break out of the plate edge")
        return {"volume_closed_form_mm3": ref.volume(params),
                "mass_closed_form_g": ref.volume(params) * float(params["density_g_per_mm3"]),
                "edge_distance_design_mm": e,
                "ligament_design_mm": ref.ligament(params)}

    def compute_metrics(self, series, params, case, outputs=None):
        """All metrics come from the measured B-rep, not from the design intent."""
        d = float(np.max(series["diameter_mm"])) if len(series["diameter_mm"]) else math.nan
        return {"mass_g": outputs["volume_mm3"] * float(params["density_g_per_mm3"]),
                "edge_distance_ratio": _edge_distance_measured(series, params) / d,
                "ligament_mm": _ligament_measured(series)}

    def verify_point(self, case, point, pdir: Path, series, backend):
        import cadquery as cq

        tol = case["verification"]
        p, d, out = point["parameters"], point["derived"], point["solver_outputs"]
        n_expected = int(p["holes_x"]) * int(p["holes_y"])
        centres = np.array(model.hole_centres(p))
        meas = np.column_stack([series["x_mm"], series["y_mm"]])
        if len(meas) == n_expected:
            # match each intended centre to its nearest measured hole
            dists = np.hypot(*(centres[:, None, :] - meas[None, :, :]).transpose(2, 0, 1))
            pos_err = float(np.max(np.min(dists, axis=1)))
            dia_err = float(np.max(np.abs(series["diameter_mm"] - float(p["hole_diameter_mm"]))))
        else:
            pos_err = dia_err = math.inf
        expect_bb = (float(p["length_mm"]), float(p["width_mm"]), float(p["thickness_mm"]))
        bb_err = max(abs(a - b) for a, b in zip(out["bbox_mm"], expect_bb))

        reimported = cq.importers.importStep(str(pdir / "solver" / "plate.step")).val()
        rm = measure(reimported)

        checks = [
            check("valid_solid", "B-rep validity (0 = valid, 1 = invalid)",
                  0.0 if out["valid_solid"] else 1.0, 0.0),
            check("volume_reference", "|V_cad - V_closed_form| / V_closed_form",
                  abs(out["volume_mm3"] - d["volume_closed_form_mm3"]) / d["volume_closed_form_mm3"],
                  tol["volume_rel_tol"]),
            check("bounding_box", "max |bbox - (L, W, t)| in mm", bb_err, tol["length_abs_tol_mm"]),
            check("hole_count", "|holes found - holes intended|",
                  abs(len(meas) - n_expected), 0.0),
            check("hole_positions", "max distance from intended centre to measured hole (mm)",
                  pos_err, tol["length_abs_tol_mm"]),
            check("hole_diameters", "max |measured - nominal diameter| (mm)",
                  dia_err, tol["length_abs_tol_mm"]),
            check("step_roundtrip_volume", "|V_step - V_cad| / V_cad after STEP re-import",
                  abs(rm["volume_mm3"] - out["volume_mm3"]) / out["volume_mm3"],
                  tol["volume_rel_tol"]),
            check("step_roundtrip_holes", "|holes in STEP - holes in model|",
                  abs(len(rm["holes"]) - len(meas)), 0.0),
        ]
        plate_figure(pdir / "drawing.png", out["outline_xy"], series, p,
                     title=f"{point['label']}  (d = {p['hole_diameter_mm']:g} mm)",
                     mass_g=point["metrics"]["mass_g"])
        return checks


STUDY = MountingPlateStudy()
