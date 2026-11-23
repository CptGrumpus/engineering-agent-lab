"""Independent 2D magnetostatic model of the motor in ElmerFEM (study 7, the 18 % diagnosis: a second solver on the
same geometry as the Pyleecan + FEMM model).

Input: the JSON written by scripts/export_motor_elmer.py (exact segments and arcs, magnetisation angles, winding
phases and turns, magnet Hc and mu_r, the laminations' B-H table, all from the calls FEMM's driver uses).
What differs from the FEMM model, on purpose: the full 360 deg machine (FEMM: one pole, anti-periodic), plain air in
the gap remeshed at every rotor position (FEMM: a sliding band), gmsh's mesher, second-order triangles, Elmer's
MagnetoDynamics2D solver with Newton iterations. What is the same: geometry, materials, A = 0 at the stator's outer
radius, a natural boundary at the rotor bore (FEMM's default there), solid laminations (fill factor 1).

Conventions checked against Elmer's source (MagnetoDynamics2D.F90, release 26.1): B = mu (H + M) with M given as
'Magnetization 1/2' (so |M| = Hc = Br / (mu0 mu_r), the value FEMM receives); 'H-B Curve' is H as a function of |B|
(first column B, second H). The closed-form check `cylinder_check` tests the magnetisation convention.

Units: gmsh and Elmer work in mm (Coordinate Scaling 0.001); results in SI.
"""
from __future__ import annotations

import math
import os
import re
import shutil
import subprocess
from pathlib import Path

import numpy as np

MU0 = 4e-7 * math.pi
ELMER_HOME = Path(os.environ.get("ELMER_HOME", Path.home() / "tools/elmer-26.1/ElmerFEM-nogui-nompi-Windows-AMD64"))
SIZES_MM = {"gap": 0.40, "hole": 0.80, "far": 6.0}   # level 1; a refinement factor scales all three


def elmer_env() -> dict:
    env = dict(os.environ)
    env["ELMER_HOME"] = str(ELMER_HOME)
    env["PATH"] = os.pathsep.join([str(ELMER_HOME / "bin"), str(ELMER_HOME / "lib"), env.get("PATH", "")])
    return env


def elmer_version() -> str:
    r = subprocess.run([str(ELMER_HOME / "bin/ElmerSolver.exe"), "-v"], capture_output=True, text=True,
                       env=elmer_env(), timeout=60)
    m = re.search(r"Version:\s*(.+)", r.stdout)
    return (m.group(1).strip() if m else "?") + f" ({ELMER_HOME.name})"


# ---------------------------------------------------------------------------------------------------------- mesh

class _Occ:
    """Builds OCC curves from exported lines (mm), sharing points and curves within one side of the air gap."""

    def __init__(self, gmsh):
        self.g, self.pts, self.crv = gmsh, {}, {}

    def point(self, xy):
        # dedupe on rounded keys, but place the point at its exact coordinates: rounding the coordinates themselves
        # made an arc's start and end radii differ by ~2e-6 mm and OpenCASCADE refused the arc
        key = (round(xy[0] * 1e3, 6), round(xy[1] * 1e3, 6))
        if key not in self.pts:
            self.pts[key] = self.g.model.occ.addPoint(xy[0] * 1e3, xy[1] * 1e3, 0)
        return self.pts[key], key

    def curves(self, ln):
        b, kb = self.point(ln["b"])
        e, ke = self.point(ln["e"])
        if ln["kind"] == "seg":
            key = ("s",) + tuple(sorted([kb, ke]))
            if key not in self.crv:
                self.crv[key] = self.g.model.occ.addLine(b, e)
            return [self.crv[key]]
        c, kc = self.point(ln["c"])
        a = ln["angle"]
        if abs(a) > math.pi * 0.75:                       # OCC draws the shorter arc: split large ones
            z0 = complex(*ln["b"]) - complex(*ln["c"])
            zm = complex(*ln["c"]) + z0 * complex(math.cos(a / 2), math.sin(a / 2))
            half1 = {"kind": "arc", "b": ln["b"], "e": [zm.real, zm.imag], "c": ln["c"], "angle": a / 2}
            half2 = {"kind": "arc", "b": [zm.real, zm.imag], "e": ln["e"], "c": ln["c"], "angle": a / 2}
            return self.curves(half1) + self.curves(half2)
        key = ("a",) + tuple(sorted([kb, ke])) + (kc,)
        if key not in self.crv:
            self.crv[key] = self.g.model.occ.addCircleArc(b, c, e)
        return [self.crv[key]]


PRIORITY = {"magnet": 5, "void": 4, "winding": 3, "rotor_lam": 2, "stator_lam": 2, "air": 0}


def build_mesh(geo: dict, theta_deg: float, out_msh: Path, refine: float = 1.0, order: int = 2) -> dict:
    """Mesh the full machine with the rotor turned by theta_deg (mechanical, counter-clockwise). Returns the body
    table: {physical tag: {"name", "kind", ...}} and mesh statistics."""
    import gmsh
    gmsh.initialize(["-noenv"])
    try:
        gmsh.option.setNumber("General.Terminal", 0)
        gmsh.option.setNumber("Geometry.Tolerance", 1e-6)
        gmsh.option.setNumber("Geometry.ToleranceBoolean", 1e-6)
        gmsh.model.add("motor")
        occ = gmsh.model.occ
        builders = {"rotor": _Occ(gmsh), "stator": _Occ(gmsh)}
        inputs = []                                        # (dimtag, record)
        for rec in geo["surfaces"]:
            b = builders[rec["side"]]
            loops = []
            for lp in rec["loops"]:
                cs = [c for ln in lp for c in b.curves(ln)]
                loops.append(occ.addCurveLoop(cs))
            inputs.append(((2, occ.addPlaneSurface(loops)), rec))
        d = geo["dims"]
        rotor_tags = [dt for dt, rec in inputs if rec["side"] == "rotor"]
        if theta_deg:
            occ.rotate(rotor_tags, 0, 0, 0, 0, 0, 1, math.radians(theta_deg))
        outer = occ.addDisk(0, 0, 0, d["stator_Rext"] * 1e3, d["stator_Rext"] * 1e3)
        inner = occ.addDisk(0, 0, 0, d["rotor_Rint"] * 1e3, d["rotor_Rint"] * 1e3)
        ring, _ = occ.cut([(2, outer)], [(2, inner)])
        inputs.append((ring[0], {"kind": "air", "label": "air"}))
        out, out_map = occ.fragment([dt for dt, _ in inputs], [])
        occ.synchronize()
        owner = {}
        for (dt, rec), pieces in zip(inputs, out_map):
            for pc in pieces:
                if pc[0] == 2 and (pc not in owner or PRIORITY[rec["kind"]] > PRIORITY[owner[pc]["kind"]]):
                    owner[pc] = rec
        groups = {}                                        # name -> (kind, [tags], rec)
        for pc, rec in owner.items():
            kind = rec["kind"]
            if kind in ("air", "void", "winding_air"):
                name = "air"
            elif kind in ("rotor_lam", "stator_lam"):
                name = kind
            else:
                name = rec["label"]
            groups.setdefault(name, [kind if kind != "void" else "air", [], rec])[1].append(pc[1])
        bodies, tag = {}, 0
        order_names = ["air", "rotor_lam", "stator_lam"] + sorted(n for n in groups if n not in
                                                                  ("air", "rotor_lam", "stator_lam"))
        for name in order_names:
            kind, tags, rec = groups[name]
            tag += 1
            gmsh.model.addPhysicalGroup(2, tags, tag, name=name)
            info = {"name": name, "kind": kind}
            if kind == "magnet":
                info["mag_deg"] = rec["mag_deg"] + theta_deg
            if kind == "winding":
                info.update(phase=rec["phase"], turns=rec["turns"])
            bodies[tag] = info
        # boundary: the stator's outer circle (A = 0)
        r_out = d["stator_Rext"] * 1e3
        outer_curves = []
        gap_curves, hole_curves = [], []
        r_rot, r_bore = d["rotor_Rext"] * 1e3, d["stator_Rint"] * 1e3
        rotor_kind_tags = {pc[1] for pc, rec in owner.items() if rec["kind"] in ("magnet", "void")}
        for _, c in gmsh.model.getEntities(1):
            lo, hi = gmsh.model.getParametrizationBounds(1, c)
            pts = np.asarray(gmsh.model.getValue(1, c, np.linspace(lo[0], hi[0], 3).tolist()))
            r = np.hypot(pts[0::3], pts[1::3])
            if np.all(np.abs(r - r_out) < 1e-3):
                outer_curves.append(c)
            if np.all(r > r_rot - 0.5) and np.all(r < r_bore + 1.5):
                gap_curves.append(c)
        for s in rotor_kind_tags:
            for _, c in gmsh.model.getBoundary([(2, s)], oriented=False):
                hole_curves.append(abs(c))
        gmsh.model.addPhysicalGroup(1, outer_curves, 1, name="outer")
        f = gmsh.model.mesh.field
        h = {k: v * refine for k, v in SIZES_MM.items()}
        f.add("Distance", 1)
        f.setNumbers(1, "CurvesList", gap_curves)
        f.setNumber(1, "Sampling", 200)
        f.add("Threshold", 2)
        f.setNumber(2, "InField", 1)
        f.setNumber(2, "SizeMin", h["gap"])
        f.setNumber(2, "SizeMax", h["far"])
        f.setNumber(2, "DistMin", 0.5)
        f.setNumber(2, "DistMax", 10.0)
        f.add("Distance", 3)
        f.setNumbers(3, "CurvesList", sorted(set(hole_curves)))
        f.setNumber(3, "Sampling", 100)
        f.add("Threshold", 4)
        f.setNumber(4, "InField", 3)
        f.setNumber(4, "SizeMin", h["hole"])
        f.setNumber(4, "SizeMax", h["far"])
        f.setNumber(4, "DistMin", 0.0)
        f.setNumber(4, "DistMax", 6.0)
        f.add("Min", 5)
        f.setNumbers(5, "FieldsList", [2, 4])
        f.setAsBackgroundMesh(5)
        for opt in ("Mesh.MeshSizeExtendFromBoundary", "Mesh.MeshSizeFromPoints", "Mesh.MeshSizeFromCurvature"):
            gmsh.option.setNumber(opt, 0)
        gmsh.option.setNumber("Mesh.Algorithm", 6)
        gmsh.option.setNumber("Mesh.MshFileVersion", 2.2)
        gmsh.model.mesh.generate(2)
        if order > 1:
            gmsh.model.mesh.setOrder(order)
        gmsh.write(str(out_msh))
        nodes = len(gmsh.model.mesh.getNodes()[0])
        etypes, etags, _ = gmsh.model.mesh.getElements(2)
        n_el = int(sum(len(t) for t in etags))
        return {"bodies": bodies, "nodes": nodes, "elements": n_el, "sizes_mm": h,
                "n_gap_curves": len(gap_curves), "n_outer_curves": len(outer_curves)}
    finally:
        gmsh.finalize()


# ---------------------------------------------------------------------------------------------------------- solve

def _bh_table(h_b: list, n: int = 160) -> list[tuple[float, float]]:
    """H(B) rows for Elmer, densified with a monotone (PCHIP) interpolation of the exported points so that Elmer's
    piecewise-linear table has a smooth slope for Newton. The last segment extends linearly (nearly mu0)."""
    from scipy.interpolate import PchipInterpolator
    hb = np.asarray(h_b, float)
    H, B = hb[:, 0], hb[:, 1]
    keep = np.concatenate([[True], np.diff(B) > 0])
    H, B = H[keep], B[keep]
    f = PchipInterpolator(B, H)
    bs = np.unique(np.concatenate([np.linspace(0, B[-1], n), B]))
    return [(float(b), float(max(f(b), 0.0))) for b in bs]


def write_sif(case: Path, geo: dict, bodies: dict, nonlinear_tol: float = 1e-10) -> None:
    mats, blines = [], []
    steel_rows = {"rotor_lam": _bh_table(geo["materials"]["rotor_steel"]["H_B"]),
                  "stator_lam": _bh_table(geo["materials"]["stator_steel"]["H_B"])}
    hc, mur = geo["materials"]["magnet"]["Hc_A_per_m"], geo["materials"]["magnet"]["mur"]
    for tag, b in sorted(bodies.items()):
        mid = len(mats) + 1
        if b["kind"] in ("rotor_lam", "stator_lam"):
            rows = "\n".join(f"      {bb:.8g} {hh:.8g}" for bb, hh in steel_rows[b["kind"]])
            mats.append(f"Material {mid}\n  Name = \"{b['name']}\"\n  H-B Curve = Variable \"dummy\"\n    Real\n{rows}\n"
                        f"    End\nEnd\n")
        elif b["kind"] == "magnet":
            a = math.radians(b["mag_deg"])
            mats.append(f"Material {mid}\n  Name = \"{b['name']}\"\n  Relative Permeability = {mur:.8g}\n"
                        f"  Magnetization 1 = Real {hc * math.cos(a):.10g}\n"
                        f"  Magnetization 2 = Real {hc * math.sin(a):.10g}\nEnd\n")
        else:
            mats.append(f"Material {mid}\n  Name = \"{b['name']}\"\n  Relative Permeability = 1.0\nEnd\n")
        blines.append(f"Body {tag}\n  Name = \"{b['name']}\"\n  Equation = 1\n  Material = {mid}\nEnd\n")
    sif = f"""Header
  CHECK KEYWORDS Warn
  Mesh DB "." "mesh"
End

Simulation
  Coordinate System = Cartesian 2D
  Simulation Type = Steady state
  Steady State Max Iterations = 1
  Coordinate Scaling = 0.001
  Output Intervals = 1
End

Constants
  Permeability of Vacuum = {MU0:.12g}
End

{''.join(blines)}
{''.join(mats)}
Equation 1
  Active Solvers(1) = 1
End

Solver 1
  Equation = MgDyn2D
  Procedure = "MagnetoDynamics2D" "MagnetoDynamics2D"
  Variable = Potential
  Linear System Solver = Direct
  Linear System Direct Method = UMFPack
  Nonlinear System Max Iterations = 60
  Nonlinear System Convergence Tolerance = {nonlinear_tol:g}
  Nonlinear System Newton After Iterations = 4
  Nonlinear System Newton After Tolerance = 1.0e-3
  Nonlinear System Relaxation Factor = 1.0
End

Solver 2
  Exec Solver = After Simulation
  Equation = ResultOutput
  Procedure = "ResultOutputSolve" "ResultOutputSolver"
  Output File Name = case
  Vtu Format = Logical True
  Ascii Output = Logical True
  Save Geometry Ids = Logical True
End

Boundary Condition 1
  Name = "outer"
  Target Boundaries(1) = 1
  Potential = Real 0
End
"""
    # the output solver runs on its own, not in the equation
    case.joinpath("case.sif").write_text(sif, encoding="utf-8")


def run_elmer(case: Path, msh: Path, timeout: float = 1800) -> dict:
    env = elmer_env()
    g = subprocess.run([str(ELMER_HOME / "bin/ElmerGrid.exe"), "14", "2", msh.name, "-out", "mesh"], cwd=case,
                       capture_output=True, text=True, env=env, timeout=timeout)
    (case / "log.ElmerGrid").write_text(g.stdout + g.stderr, encoding="utf-8")
    if g.returncode != 0:
        raise RuntimeError(f"ElmerGrid failed ({g.returncode}); see {case / 'log.ElmerGrid'}")
    r = subprocess.run([str(ELMER_HOME / "bin/ElmerSolver.exe"), "case.sif"], cwd=case, capture_output=True,
                       text=True, env=env, timeout=timeout)
    log = r.stdout + r.stderr
    (case / "log.ElmerSolver").write_text(log, encoding="utf-8")
    if r.returncode != 0 or "ALL DONE" not in log:
        raise RuntimeError(f"ElmerSolver failed ({r.returncode}); see {case / 'log.ElmerSolver'}")
    ns = re.findall(r"NS \(ITER=(\d+)\) \(NRM,RELC\):\s*\(\s*([-\d.Ee+]+)\s+([-\d.Ee+]+)", log)
    changes = [float(c) for _, _, c in ns]
    return {"nonlinear_changes": changes, "nonlinear_iterations": int(ns[-1][0]) if ns else None,
            "final_change": changes[-1] if changes else None,
            "converged": bool(changes) and changes[-1] < 1e-8}


def read_vtu(path: Path) -> dict:
    """Points (m: Elmer writes the scaled coordinates), connectivity of second- or first-order triangles, GeometryIds, nodal potential (Wb/m)."""
    text = path.read_text(encoding="utf-8", errors="replace")

    def arr(name, dtype=float):
        m = re.search(r'<DataArray[^>]*Name="' + name + r'"[^>]*>(.*?)</DataArray>', text, flags=re.S | re.I)
        if not m:
            raise KeyError(f"{name} not in {path}")
        return np.array(m.group(1).split(), dtype=dtype)

    m = re.search(r"<Points>\s*<DataArray[^>]*>(.*?)</DataArray>", text, flags=re.S)
    pts = np.array(m.group(1).split(), dtype=float).reshape(-1, 3)
    pot = None
    for nm in ("potential", "Potential"):
        try:
            pot = arr(nm)
            break
        except KeyError:
            pass
    conn, offs, types = arr("connectivity", int), arr("offsets", int), arr("types", int)
    gid = arr("GeometryIds", int)
    return {"pts": pts, "pot": pot, "conn": conn, "offs": offs, "types": types, "gid": gid}


def body_integrals(v: dict) -> dict:
    """{body id: (integral of A over the body in Wb, area in m2)} for linear (5) or quadratic (22) triangles; the
    quadratic rule weights the mid-side nodes 1/3 each (exact for straight-sided P2 elements)."""
    out = {}
    start = np.concatenate([[0], v["offs"][:-1]])
    for i, (s, t) in enumerate(zip(start, v["types"])):
        nid = v["conn"][s:v["offs"][i]]
        p = v["pts"][nid[:3], :2]
        area = 0.5 * abs((p[1, 0] - p[0, 0]) * (p[2, 1] - p[0, 1]) - (p[2, 0] - p[0, 0]) * (p[1, 1] - p[0, 1]))
        if t == 22:
            a_mean = float(np.mean(v["pot"][nid[3:6]]))
        elif t == 5:
            a_mean = float(np.mean(v["pot"][nid[:3]]))
        else:
            continue
        b = int(v["gid"][i])
        ia, ar = out.get(b, (0.0, 0.0))
        out[b] = (ia + a_mean * area, ar + area)
    return out


def gap_br(v: dict, radius_m: float, n: int = 1440) -> np.ndarray:
    """Radial flux density on a circle in the gap, B_r = (1/r) dA/dtheta, from the nodal potential interpolated
    linearly (scipy griddata on the gap's nodes)."""
    from scipy.interpolate import griddata
    r = np.hypot(v["pts"][:, 0], v["pts"][:, 1])
    sel = np.abs(r - radius_m) < 0.6e-3
    th = np.linspace(0, 2 * np.pi, n, endpoint=False)
    a = griddata(v["pts"][sel, :2], v["pot"][sel], np.c_[radius_m * np.cos(th), radius_m * np.sin(th)],
                 method="cubic")
    dadt = np.gradient(np.concatenate([a, a[:1]]), np.concatenate([th, [2 * np.pi]]))[:-1]
    return dadt / radius_m


def solve_position(geo: dict, theta_deg: float, work: Path, refine: float = 1.0, order: int = 2,
                   keep_vtu: bool = False) -> dict:
    """One static solve with the rotor at theta_deg. Returns the phase flux linkages (Wb) and diagnostics."""
    work.mkdir(parents=True, exist_ok=True)
    msh = work / "machine.msh"
    meta = build_mesh(geo, theta_deg, msh, refine=refine, order=order)
    write_sif(work, geo, meta["bodies"])
    sol = run_elmer(work, msh)
    vtus = sorted(work.glob("mesh/case*.vtu")) or sorted(work.glob("case*.vtu"))
    if not vtus:
        raise RuntimeError(f"no VTU written in {work}")
    v = read_vtu(vtus[-1])
    ints = body_integrals(v)
    L = geo["dims"]["L_m"] / geo["dims"]["Npcp"]
    lam = np.zeros(geo["dims"]["qs"])
    for tag, b in meta["bodies"].items():
        if b["kind"] == "winding":
            ia, ar = ints[tag]
            lam[b["phase"]] += b["turns"] * ia / ar * L
    r_mid = 0.5 * (geo["dims"]["rotor_Rext"] + geo["dims"]["stator_Rint"])
    br = gap_br(v, r_mid)
    if not keep_vtu:
        for f in vtus:
            f.unlink()
        (work / "machine.msh").unlink(missing_ok=True)
        shutil.rmtree(work / "mesh", ignore_errors=True)
    return {"theta_deg": theta_deg, "lambda_Wb": lam.tolist(), "nodes": meta["nodes"], "elements": meta["elements"],
            "sizes_mm": meta["sizes_mm"], "gap_Br_T": br.tolist(), "r_gap_m": r_mid, **sol}


# ------------------------------------------------------------------------------------------- closed-form check

def cylinder_check(work: Path, br: float = 1.2487, mur: float = 1.129, R: float = 10.0, R_out: float = 400.0,
                   h: float = 0.5) -> dict:
    """A uniformly magnetised cylinder (radius R mm, along x) in air, A = 0 at R_out: B inside = Br / (1 + mu_r)
    (2D transverse demagnetising factor 1/2), up to (R / R_out)^2 from the finite outer boundary. Tests Elmer's
    magnetisation convention with the same keywords as the machine model."""
    import gmsh
    work.mkdir(parents=True, exist_ok=True)
    gmsh.initialize(["-noenv"])
    try:
        gmsh.option.setNumber("General.Terminal", 0)
        occ = gmsh.model.occ
        d_in = occ.addDisk(0, 0, 0, R, R)
        d_out = occ.addDisk(0, 0, 0, R_out, R_out)
        out, _ = occ.fragment([(2, d_out)], [(2, d_in)])
        occ.synchronize()
        surfs = [t for _, t in gmsh.model.getEntities(2)]
        mag = [s for s in surfs if gmsh.model.getBoundingBox(2, s)[3] < R + 1e-6]
        air = [s for s in surfs if s not in mag]
        gmsh.model.addPhysicalGroup(2, air, 1, name="air")
        gmsh.model.addPhysicalGroup(2, mag, 2, name="magnet")
        outer = [abs(c) for _, c in gmsh.model.getBoundary([(2, s) for s in air], oriented=False)
                 if gmsh.model.getBoundingBox(1, abs(c))[3] > R_out - 1e-3]
        gmsh.model.addPhysicalGroup(1, outer, 1, name="outer")
        f = gmsh.model.mesh.field
        f.add("MathEval", 1)
        f.setString(1, "F", f"{h} + 0.05 * Sqrt(x*x + y*y)")
        f.setAsBackgroundMesh(1)
        for opt in ("Mesh.MeshSizeExtendFromBoundary", "Mesh.MeshSizeFromPoints", "Mesh.MeshSizeFromCurvature"):
            gmsh.option.setNumber(opt, 0)
        gmsh.option.setNumber("Mesh.MshFileVersion", 2.2)
        gmsh.model.mesh.generate(2)
        gmsh.model.mesh.setOrder(2)
        gmsh.write(str(work / "machine.msh"))
    finally:
        gmsh.finalize()
    hc = br / (MU0 * mur)
    geo = {"materials": {"magnet": {"Hc_A_per_m": hc, "mur": mur}, "rotor_steel": {"H_B": [[0, 0], [1, 1]]},
                         "stator_steel": {"H_B": [[0, 0], [1, 1]]}}}
    bodies = {1: {"name": "air", "kind": "air"}, 2: {"name": "magnet", "kind": "magnet", "mag_deg": 0.0}}
    write_sif(work, geo, bodies)
    sol = run_elmer(work, work / "machine.msh")
    v = read_vtu(sorted(work.glob("mesh/case*.vtu"))[-1])
    # B_x = dA/dy inside: A is linear in y inside the cylinder; fit A = a + b y over the magnet's nodes
    r = np.hypot(v["pts"][:, 0], v["pts"][:, 1])
    sel = r < 0.8 * R * 1e-3
    coef = np.polyfit(v["pts"][sel, 1], v["pot"][sel], 1)
    bx = float(coef[0])
    expected = br / (1 + mur)                     # the finite outer boundary changes it by at most (R / R_out)^2
    return {"Bx_T": bx, "expected_T": expected, "rel_error": bx / expected - 1, "boundary_bound": (R / R_out) ** 2,
            # what the same input would give if Elmer used B = mu0 mu_r H + mu0 M (M would then need Br / mu0)
            "other_convention_T": br / (mur * (1 + mur)), **sol}
