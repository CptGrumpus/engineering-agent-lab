"""OpenFOAM case writer: the backward-facing step of Driver and Seegmiller (ERCOFTAC classic case 030) in 3D, with the
wind tunnel's side walls (study 19, part 3).

The 2D model (models/cfd/step_openfoam.py, part 2) is extruded in z over half the tunnel's span: z = 0 is the mid-span
plane (symmetry), z = half_span_m (75.5 mm: span 151 mm) the side wall. Every x-y detail (blocks A / B / C, cell counts,
gradings, the inflow, the numerics) is the 2D writer's own, called here, so the 3D mesh's x-y plane is the 2D mesh at the
same mesh_level, exactly. Spanwise: spanwise_level s gives NZ_BASE * s cells, graded geometrically from Y1Z_BASE / s at
the side wall (resolved to the viscous sublayer, as the floors) to the mid-span plane.

side_wall = 1: the side wall is a no-slip wall (low-Re treatment as the other walls). side_wall = 0: it is a symmetry
plane, so the flow is the 2D flow exactly (the limit that checks this pipeline against the 2D model).
side_wall_start_m (optional, < 0): upstream of this x the side wall is a symmetry plane (slip) and downstream a no-slip
wall, so its boundary layer starts there instead of at the inlet (thinner at the step). Block A is then split at the
2D mesh's cell face nearest that x, keeping every cell of the 2D x-y mesh.

The side walls' own inflow is not in the case description. Default: their boundary layers grow from the same uniform
inlet as the floor's and the top wall's (the 2D model already treats the top wall so), i.e. they start like the floor's.

Initial field: the converged 2D solution at the same mesh_level (the backend runs it first), copied to every spanwise
layer (extrude_index maps each 3D cell to its 2D cell through blockMesh's cell order: block by block, i fastest, then
j, then k; the backend checks the mapping on the cell centres after the run). The steady state does not depend on it.

Run in WSL by models/cfd/run_step3d.sh (decomposePar, mpirun foamRun -parallel, reconstructPar). openfoam.org v14.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np


def _load_2d():
    spec = importlib.util.spec_from_file_location("step_openfoam_for_3d", Path(__file__).resolve().parent / "step_openfoam.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


S2 = _load_2d()
PARAMS_3D = ("half_span_m", "side_wall", "spanwise_level", "side_wall_start_m")
PARAMS = S2.PARAMS + PARAMS_3D
NZ_BASE = 32          # spanwise cells at spanwise_level 1
Y1Z_BASE = 6e-6       # m, first cell at the side wall at spanwise_level 1 (the floor's at mesh_level 0.5)
_g = S2._g


def _f(p, k, default=None):
    v = p.get(k, default)
    return None if v is None else float(v)


def geometry(p: dict) -> dict:
    """The 2D geometry plus the spanwise mesh and the optional split of block A."""
    g = S2.geometry(p)
    s = _f(p, "spanwise_level", 1.0)
    W = _f(p, "half_span_m")
    if not 0 < W:
        raise ValueError("half_span_m must be positive")
    nz = max(2, int(round(NZ_BASE * s)))
    y1z = Y1Z_BASE / s
    gz = S2.growth_for(W, nz, y1z)
    if abs(y1z * (gz ** nz - 1) / (gz - 1) / W - 1) > 1e-6:  # growth_for searches g up to 2 only
        raise ValueError(f"{nz} spanwise cells from {y1z:.3g} m cannot fill the half-span with a growth up to 2")
    out = {**g, "half_span_m": W, "nz": nz, "y1z_m": y1z, "growth_z": gz, "R_z": gz ** (nz - 1),
           "dz_mid_m": y1z * gz ** (nz - 1), "cells_2d": g["cells"], "cells": g["cells"] * nz}
    xs = _f(p, "side_wall_start_m")
    out["split"] = None
    if xs is not None and xs > -g["Lup_m"]:
        if xs >= 0:
            raise ValueError("side_wall_start_m must lie upstream of the step (x < 0)")
        # block A's cell faces from x = 0 upstream: x_m = -dx_lip (g^m - 1) / (g - 1), m = 0 .. nx_up (the 2D grading)
        gu = S2.growth_for(g["Lup_m"], g["nx_up"], g["dx_lip_m"])
        m = np.arange(g["nx_up"] + 1)
        xf = -g["dx_lip_m"] * (gu ** m - 1) / (gu - 1)
        ms = int(np.argmin(np.abs(xf - xs)))
        ms = min(max(ms, 1), g["nx_up"] - 1)
        out["split"] = {"m_s": ms, "x_s_m": float(xf[ms]), "growth_up": gu}
    return out


def extrude_index(g: dict) -> np.ndarray:
    """idx with field_3d = field_2d[idx]: blockMesh numbers cells block by block, i fastest, then j, then k."""
    nxd = g["nx_near"] + g["nx_far"]
    nA, nB = g["nx_up"] * g["ny_duct"], nxd * g["ny_step"]
    a2d = np.arange(nA).reshape(g["ny_duct"], g["nx_up"])
    blocks = []
    if g["split"]:
        ms = g["split"]["m_s"]
        blocks += [a2d[:, :g["nx_up"] - ms], a2d[:, g["nx_up"] - ms:]]
    else:
        blocks.append(a2d)
    blocks += [nA + np.arange(nB).reshape(g["ny_step"], nxd),
               nA + nB + np.arange(nxd * g["ny_duct"]).reshape(g["ny_duct"], nxd)]
    return np.concatenate([np.tile(b.ravel(), g["nz"]) for b in blocks])


def _block_mesh(g: dict) -> str:
    H, Ud, Lup, Ld, W = g["H_m"], g["duct_height_m"], g["Lup_m"], g["Ldown_m"], g["half_span_m"]
    Yt = H + Ud
    fn = S2.X_NEAR_OVER_H * H / Ld
    nxd = g["nx_near"] + g["nx_far"]
    two = lambda R: f"((0.5 0.5 {_g(R)}) (0.5 0.5 {_g(1 / R)}))"  # noqa: E731
    xdown = f"(({_g(fn)} {_g(g['nx_near'] / nxd)} {_g(g['R_near'])}) ({_g(1 - fn)} {_g(g['nx_far'] / nxd)} {_g(g['R_far'])}))"
    rz = _g(1 / g["R_z"])  # local z runs from the mid-span plane (coarse) to the side wall (fine): last / first
    pts = [(-Lup, H), (0, H), (0, Yt), (-Lup, Yt), (0, 0), (Ld, 0), (Ld, H), (Ld, Yt)]
    sp = g["split"]
    if sp:
        pts += [(sp["x_s_m"], H), (sp["x_s_m"], Yt)]  # 8, 9 (z = 0); their side-wall twins follow all z = 0 points
    n0 = len(pts)
    verts = [f"({_g(x)} {_g(y)} 0)" for x, y in pts] + [f"({_g(x)} {_g(y)} {_g(W)})" for x, y in pts]
    z = lambda i: i + n0  # noqa: E731  (the same point on the side-wall plane)
    v = lambda *ids: " ".join(str(i) for i in ids)  # noqa: E731
    ny, nys, nz = g["ny_duct"], g["ny_step"], g["nz"]
    blocks, inlet, upfloor, upper, mid, side, slip = [], [], [], [], [], [], []
    if sp:
        ms, gu, nxu = sp["m_s"], sp["growth_up"], g["nx_up"]
        a, b = 8, 9  # the split points (x_s, H) and (x_s, Yt)
        blocks += [f"hex ({v(0, a, b, 3, z(0), z(a), z(b), z(3))}) ({nxu - ms} {ny} {nz}) simpleGrading "
                   f"({_g(1 / gu ** (nxu - 1 - ms))} {two(g['R_duct'])} {rz})",
                   f"hex ({v(a, 1, 2, b, z(a), z(1), z(2), z(b))}) ({ms} {ny} {nz}) simpleGrading "
                   f"({_g(1 / gu ** (ms - 1))} {two(g['R_duct'])} {rz})"]
        upfloor += [f"({v(0, a, z(a), z(0))})", f"({v(a, 1, z(1), z(a))})"]
        upper += [f"({v(3, z(3), z(b), b)})", f"({v(b, z(b), z(2), 2)})"]
        mid += [f"({v(0, 3, b, a)})", f"({v(a, b, 2, 1)})"]
        slip.append(f"({v(z(0), z(a), z(b), z(3))})")
        side.append(f"({v(z(a), z(1), z(2), z(b))})")
    else:
        blocks.append(f"hex ({v(0, 1, 2, 3, z(0), z(1), z(2), z(3))}) ({g['nx_up']} {ny} {nz}) simpleGrading "
                      f"({_g(1 / g['R_up'])} {two(g['R_duct'])} {rz})")
        upfloor.append(f"({v(0, 1, z(1), z(0))})")
        upper.append(f"({v(3, z(3), z(2), 2)})")
        mid.append(f"({v(0, 3, 2, 1)})")
        side.append(f"({v(z(0), z(1), z(2), z(3))})")
    blocks += [f"hex ({v(4, 5, 6, 1, z(4), z(5), z(6), z(1))}) ({nxd} {nys} {nz}) simpleGrading ({xdown} {two(g['R_step'])} {rz})",
               f"hex ({v(1, 6, 7, 2, z(1), z(6), z(7), z(2))}) ({nxd} {ny} {nz}) simpleGrading ({xdown} {two(g['R_duct'])} {rz})"]
    inlet.append(f"({v(0, z(0), z(3), 3)})")
    upper.append(f"({v(2, z(2), z(7), 7)})")
    mid += [f"({v(4, 1, 6, 5)})", f"({v(1, 2, 7, 6)})"]
    side += [f"({v(z(4), z(5), z(6), z(1))})", f"({v(z(1), z(6), z(7), z(2))})"]
    side_type = "wall" if g["side_wall"] else "symmetry"
    nl = chr(10)
    return f"""
convertToMeters 1;
vertices
(
{nl.join('    ' + s for s in verts)}
);
blocks
(
{nl.join('    ' + s for s in blocks)}
);
boundary
(
    inlet          {{ type patch; faces ({' '.join(inlet)}); }}
    outlet         {{ type patch; faces (({v(5, 6, z(6), z(5))}) ({v(6, 7, z(7), z(6))})); }}
    upperWall      {{ type wall;  faces ({' '.join(upper)}); }}
    upstreamFloor  {{ type wall;  faces ({' '.join(upfloor)}); }}
    stepFace       {{ type wall;  faces (({v(4, z(4), z(1), 1)})); }}
    lowerWall      {{ type wall;  faces (({v(4, 5, z(5), z(4))})); }}
    sideWall       {{ type {side_type}; faces ({' '.join(side)}); }}
{f"    sideWallSlip   {{ type symmetry; faces ({' '.join(slip)}); }}{nl}" if slip else ""}    midPlane       {{ type symmetry; faces ({' '.join(mid)}); }}
);
"""


def _field_text(values: np.ndarray) -> str:
    """internalField entry for a 3D list of scalars or vectors (plain floats, 12 significant digits)."""
    a = np.asarray(values, dtype=float)
    if a.ndim == 1:
        body = "\n".join(f"{float(x):.12g}" for x in a)
        return f"nonuniform List<scalar>\n{len(a)}\n(\n{body}\n)"
    body = "\n".join(f"({float(r[0]):.12g} {float(r[1]):.12g} {float(r[2]):.12g})" for r in a)
    return f"nonuniform List<vector>\n{len(a)}\n(\n{body}\n)"


def write_case(params: dict, numerics: dict, case: Path, initial: dict | None = None) -> dict:
    """Write the 3D case. initial: 2D internal fields {"U": (n2d, 3), "p", "k", "omega", "nut": (n2d,)} to copy to
    every spanwise layer (None: the 2D writer's uniform start)."""
    case = Path(case)
    sw = int(round(float(params["side_wall"])))
    if sw not in (0, 1):
        raise ValueError("side_wall must be 0 (symmetry) or 1 (no-slip wall)")
    S2.write_case(params, numerics, case)  # system/, constant/, 0/ of the 2D model; 3D parts replaced below
    g = geometry(params)
    g["side_wall"] = sw
    S2._write(case / "system/blockMeshDict", "dictionary", "blockMeshDict", _block_mesh(g))
    H = g["H_m"]
    z0 = 0.5 * g["dz_mid_m"]
    y_wall_cell = 0.5 * g["y1_m"]
    probes = [(-4 * H, H + y_wall_cell, z0), (30 * H, y_wall_cell, z0), (-4 * H, H + 0.5 * g["duct_height_m"], z0)]
    probe_txt = " ".join(f"({_g(x)} {_g(y)} {_g(zz)})" for x, y, zz in probes)
    iters = int(numerics.get("max_iterations", 20000))
    n1 = int(numerics.get("stage1_iterations", 500))
    every = int(numerics.get("probe_interval", 50))
    for fname, start, end in (("controlDict", "startTime", n1), ("controlDict.stage2", "latestTime", iters)):
        S2._write(case / "system" / fname, "dictionary", "controlDict", f"""
solver          incompressibleFluid;
startFrom       {start};
startTime       0;
stopAt          endTime;
endTime         {end};
deltaT          1;
writeControl    timeStep;
writeInterval   {end};
writeFormat     ascii;
writePrecision  12;
writeCompression off;
timeFormat      general;
timePrecision   8;
runTimeModifiable false;
functions
{{
    #includeFunc wallShearStress
    #includeFunc yPlus
    inletFlow  {{ type surfaceFieldValue; libs ("libfieldFunctionObjects.so"); executeControl writeTime; writeControl writeTime; writeFields false; log false; patch inlet; fields (phi); operation sum; }}
    outletFlow {{ type surfaceFieldValue; libs ("libfieldFunctionObjects.so"); executeControl writeTime; writeControl writeTime; writeFields false; log false; patch outlet; fields (phi); operation sum; }}
    probes     {{ type probes; libs ("libsampling.so"); writeControl timeStep; writeInterval {every}; fields (p U); probeLocations ({probe_txt}); }}
}}
""")
    nproc = int(numerics.get("n_procs", 1))
    S2._write(case / "system/decomposeParDict", "dictionary", "decomposeParDict",
              f"\nnumberOfSubdomains {nproc};\nmethod          scotch;\n")
    # boundary conditions: the 2D model's, with the empty sides replaced by the mid-span plane and the side wall
    nu = g["nu_m2_per_s"]
    Uin = float(params["inlet_velocity_m_per_s"])
    k_in = 1.5 * (float(params["inlet_turbulence_intensity"]) * Uin) ** 2
    om_in = k_in / (nu * float(params["inlet_viscosity_ratio"]))
    walls = ["upperWall", "upstreamFloor", "stepFace", "lowerWall"] + (["sideWall"] if sw else [])
    syms = ["midPlane"] + ([] if sw else ["sideWall"]) + (["sideWallSlip"] if g["split"] else [])
    idx = extrude_index(g) if initial is not None else None
    for name, cls, dim, val, inlet, outlet, wall in (
            ("U", "volVectorField", "[0 1 -1 0 0 0 0]", f"uniform ({_g(Uin)} 0 0)",
             f"{{ type fixedValue; value uniform ({_g(Uin)} 0 0); }}",
             f"{{ type inletOutlet; inletValue uniform (0 0 0); value uniform ({_g(Uin)} 0 0); }}", "{ type noSlip; }"),
            ("p", "volScalarField", "[0 2 -2 0 0 0 0]", "uniform 0", "{ type zeroGradient; }",
             "{ type fixedValue; value uniform 0; }", "{ type zeroGradient; }"),
            ("k", "volScalarField", "[0 2 -2 0 0 0 0]", f"uniform {_g(k_in)}", f"{{ type fixedValue; value uniform {_g(k_in)}; }}",
             f"{{ type inletOutlet; inletValue uniform {_g(k_in)}; value uniform {_g(k_in)}; }}",
             "{ type fixedValue; value uniform 1e-15; }"),
            ("omega", "volScalarField", "[0 0 -1 0 0 0 0]", f"uniform {_g(om_in)}", f"{{ type fixedValue; value uniform {_g(om_in)}; }}",
             f"{{ type inletOutlet; inletValue uniform {_g(om_in)}; value uniform {_g(om_in)}; }}",
             f"{{ type omegaWallFunction; value uniform {_g(om_in)}; }}"),
            ("nut", "volScalarField", "[0 2 -1 0 0 0 0]", "uniform 0", "{ type calculated; value uniform 0; }",
             "{ type calculated; value uniform 0; }", "{ type nutLowReWallFunction; value uniform 0; }")):
        if initial is not None:
            a = np.asarray(initial[name], dtype=float)
            if len(a) != g["cells_2d"]:
                raise ValueError(f"initial {name}: {len(a)} values for {g['cells_2d']} 2D cells")
            if name == "U":
                a = np.column_stack([a[:, 0], a[:, 1], np.zeros(len(a))])
            val = _field_text(a[idx])
        body = "".join(f"    {w:<14}{wall}\n" for w in walls) + "".join(f"    {s:<14}{{ type symmetry; }}\n" for s in syms)
        S2._write(case / "0" / name, cls, name, f"""
dimensions      {dim};
internalField   {val};
boundaryField
{{
    inlet         {inlet}
    outlet        {outlet}
{body}}}
""")
    return g
