"""OpenFOAM case writer: the backward-facing step of Driver and Seegmiller (ERCOFTAC classic case 030, parallel walls),
2D steady RANS (study 19, part 2).

Geometry (x streamwise, y wall-normal; step height H, inlet duct height Yr H, so the expansion ratio is (Yr + 1) / Yr):
  block A  inlet duct    x in [-Lup, 0],      y in [H, (1 + Yr) H]   (its floor is the step-side wall upstream)
  block B  below the lip x in [0, Ldown],     y in [0, H]           (the step face at x = 0, the floor at y = 0)
  block C  above the lip x in [0, Ldown],     y in [H, (1 + Yr) H]
One cell thick in z (empty sides). Every wall is resolved to the viscous sublayer (first cell y1 at the walls; the
lip's shear layer gets the same fine cells, since blocks B and C meet there). Lengths along x are graded
geometrically: finest at x = 0 (dx_lip), growing upstream through A and downstream through B / C in two segments
(to x = 15 H, then to the outlet). Refinement: mesh_level f multiplies every cell count by f and divides y1 and
dx_lip by f.

Inflow: uniform velocity U_in with turbulence intensity Tu and eddy-viscosity ratio at the inlet, Lup upstream of the
step; both walls grow their own boundary layers, and Lup is chosen so the step-side layer has the stated momentum
thickness at x = -4 H (as the experiment's trip 1 m upstream). Outlet: fixed pressure; zero gradient for the rest.

Run in WSL by models/cfd/run_step.sh. openfoam.org v14 (foamRun, incompressibleFluid), k-omega SST, low-Re walls.
"""

from __future__ import annotations

import math
from pathlib import Path

PARAMS = ("step_height_m", "inlet_height_ratio", "reynolds_number_h", "inlet_velocity_m_per_s", "reference_velocity_m_per_s",
          "upstream_length_m", "downstream_length_over_h", "inlet_turbulence_intensity", "inlet_viscosity_ratio",
          "mesh_level", "turbulence_model")

HEADER = """FoamFile
{{
    format      ascii;
    class       {cls};
    object      {obj};
}}
"""
#: base mesh (mesh_level 1): cell counts and the finest sizes
BASE = {"ny_duct": 120, "ny_step": 60, "nx_up": 200, "nx_near": 160, "nx_far": 100, "y1_m": 8e-6, "dx_lip_over_h": 1 / 40}
X_NEAR_OVER_H = 15.0


def growth_for(length: float, n: int, first: float) -> float:
    """Geometric growth g with first * (g^n - 1) / (g - 1) = length (bisection; g < 1 allowed)."""
    if abs(first * n - length) < 1e-15 * length:
        return 1.0
    lo, hi = (1.0 + 1e-12, 2.0) if first * n < length else (1e-6, 1.0 - 1e-12)
    for _ in range(200):
        g = 0.5 * (lo + hi)
        s = first * (g ** n - 1) / (g - 1)
        lo, hi = (g, hi) if s < length else (lo, g)  # the sum increases with g either side of 1
    return 0.5 * (lo + hi)


def _f(p, k):
    return float(p[k])


def geometry(p: dict) -> dict:
    H, Yr = _f(p, "step_height_m"), _f(p, "inlet_height_ratio")
    f = _f(p, "mesh_level")
    n = {k: max(2, int(round(BASE[k] * f))) for k in ("ny_duct", "ny_step", "nx_up", "nx_near", "nx_far")}
    for k in ("ny_duct", "ny_step"):
        n[k] += n[k] % 2  # two-sided grading: even counts
    y1 = BASE["y1_m"] / f
    dx_lip = BASE["dx_lip_over_h"] * H / f
    Lup, Ldown = _f(p, "upstream_length_m"), _f(p, "downstream_length_over_h") * H
    Ud, Ub = Yr * H, H
    g_duct = growth_for(Ud / 2, n["ny_duct"] // 2, y1)
    g_step = growth_for(Ub / 2, n["ny_step"] // 2, y1)
    g_up = growth_for(Lup, n["nx_up"], dx_lip)
    xn = X_NEAR_OVER_H * H
    g_near = growth_for(xn, n["nx_near"], dx_lip)
    dx_near_end = dx_lip * g_near ** n["nx_near"]
    g_far = growth_for(Ldown - xn, n["nx_far"], dx_near_end)
    nu = _f(p, "reference_velocity_m_per_s") * H / _f(p, "reynolds_number_h")
    return {"H_m": H, "duct_height_m": Ud, "Lup_m": Lup, "Ldown_m": Ldown, "y1_m": y1, "dx_lip_m": dx_lip,
            "nu_m2_per_s": nu, **n,
            "R_duct": g_duct ** (n["ny_duct"] // 2 - 1), "R_step": g_step ** (n["ny_step"] // 2 - 1),
            "R_up": g_up ** (n["nx_up"] - 1), "R_near": g_near ** (n["nx_near"] - 1),
            "R_far": g_far ** (n["nx_far"] - 1), "dx_up_max_m": dx_lip * g_up ** (n["nx_up"] - 1),
            "dx_far_max_m": dx_near_end * g_far ** (n["nx_far"] - 1),
            "cells": n["nx_up"] * n["ny_duct"] + (n["nx_near"] + n["nx_far"]) * (n["ny_duct"] + n["ny_step"])}


def _write(path: Path, cls: str, obj: str, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(HEADER.format(cls=cls, obj=obj) + body, encoding="utf-8", newline="\n")


def _g(v: float) -> str:
    return f"{v:.12g}"


def write_case(params: dict, numerics: dict, case: Path) -> dict:
    case = Path(case)
    g = geometry(params)
    H, Ud, Lup, Ld = g["H_m"], g["duct_height_m"], g["Lup_m"], g["Ldown_m"]
    Yt = H + Ud
    xn = X_NEAR_OVER_H * H
    fn = xn / Ld
    two = lambda R: f"((0.5 0.5 {_g(R)}) (0.5 0.5 {_g(1 / R)}))"  # noqa: E731
    xdown = f"(({_g(fn)} {_g(g['nx_near'] / (g['nx_near'] + g['nx_far']))} {_g(g['R_near'])}) " \
            f"({_g(1 - fn)} {_g(g['nx_far'] / (g['nx_near'] + g['nx_far']))} {_g(g['R_far'])}))"
    z = 0.1 * H
    pts = [(-Lup, H), (0, H), (0, Yt), (-Lup, Yt), (0, 0), (Ld, 0), (Ld, H), (Ld, Yt)]
    verts = [f"({_g(x)} {_g(y)} 0)" for x, y in pts] + [f"({_g(x)} {_g(y)} {_g(z)})" for x, y in pts]
    v = lambda *ids: " ".join(str(i) for i in ids)  # noqa: E731
    _write(case / "system/blockMeshDict", "dictionary", "blockMeshDict", f"""
convertToMeters 1;
vertices
(
    {chr(10).join('    ' + s for s in verts).strip()}
);
blocks
(
    hex ({v(0, 1, 2, 3, 8, 9, 10, 11)}) ({g['nx_up']} {g['ny_duct']} 1) simpleGrading ({_g(1 / g['R_up'])} {two(g['R_duct'])} 1)
    hex ({v(4, 5, 6, 1, 12, 13, 14, 9)}) ({g['nx_near'] + g['nx_far']} {g['ny_step']} 1) simpleGrading ({xdown} {two(g['R_step'])} 1)
    hex ({v(1, 6, 7, 2, 9, 14, 15, 10)}) ({g['nx_near'] + g['nx_far']} {g['ny_duct']} 1) simpleGrading ({xdown} {two(g['R_duct'])} 1)
);
boundary
(
    inlet          {{ type patch; faces (({v(0, 8, 11, 3)})); }}
    outlet         {{ type patch; faces (({v(5, 6, 14, 13)}) ({v(6, 7, 15, 14)})); }}
    upperWall      {{ type wall;  faces (({v(3, 11, 10, 2)}) ({v(2, 10, 15, 7)})); }}
    upstreamFloor  {{ type wall;  faces (({v(0, 1, 9, 8)})); }}
    stepFace       {{ type wall;  faces (({v(4, 12, 9, 1)})); }}
    lowerWall      {{ type wall;  faces (({v(4, 5, 13, 12)})); }}
    frontAndBack   {{ type empty; faces (({v(0, 3, 2, 1)}) ({v(4, 1, 6, 5)}) ({v(1, 2, 7, 6)}) ({v(8, 9, 10, 11)}) ({v(12, 13, 14, 9)}) ({v(9, 14, 15, 10)})); }}
);
""")
    iters = int(numerics.get("max_iterations", 20000))
    n1 = int(numerics.get("stage1_iterations", 500))
    for fname, start, end in (("controlDict", "startTime", n1), ("controlDict.stage2", "latestTime", iters)):
        _write(case / "system" / fname, "dictionary", "controlDict", f"""
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
}}
""")
    # stage 1 (start-up): first-order convection of k and omega (SST blew up behind the step with linearUpwind from
    # a uniform start, and again on switching to it after 600 iterations); stage 2: the bounded TVD scheme
    # limitedLinear 1, second order where the solution is smooth. The converged steady state does not depend on stage 1.
    for fname, turb in (("fvSchemes", "upwind"), ("fvSchemes.stage2", "limitedLinear 1")):
        _write(case / "system" / fname, "dictionary", "fvSchemes", f"""
ddtSchemes      {{ default steadyState; }}
gradSchemes     {{ default Gauss linear; }}
divSchemes
{{
    default         none;
    div(phi,U)      bounded Gauss linearUpwind grad(U);
    div(phi,k)      bounded Gauss {turb};
    div(phi,omega)  bounded Gauss {turb};
    div((nuEff*dev2(T(grad(U))))) Gauss linear;
}}
laplacianSchemes     {{ default Gauss linear corrected; }}
interpolationSchemes {{ default linear; }}
snGradSchemes        {{ default corrected; }}
wallDist             {{ method meshWave; }}
""")
    _write(case / "system/fvSolution", "dictionary", "fvSolution", f"""
solvers
{{
    p {{ solver GAMG; smoother GaussSeidel; tolerance 1e-10; relTol 0.05; }}
    "(U|k|omega)" {{ solver smoothSolver; smoother symGaussSeidel; tolerance 1e-12; relTol 0.05; }}
}}
SIMPLE
{{
    nNonOrthogonalCorrectors 0;
    consistent      {"yes" if numerics.get("consistent", False) else "no"};
    residualControl {{ p {_g(float(numerics["residual_p"]))}; U {_g(float(numerics["residual_U"]))}; "(k|omega)" {_g(float(numerics["residual_turb"]))}; }}
}}
relaxationFactors
{{
    fields {{ p {_g(float(numerics.get("relax_p", 0.3)))}; }}
    equations {{ U {_g(float(numerics.get("relax_U", 0.7)))}; "(k|omega)" {_g(float(numerics.get("relax_turb", 0.5)))}; }}
}}
""")
    _write(case / "constant/momentumTransport", "dictionary", "momentumTransport", f"""
simulationType  RAS;
RAS {{ model {params["turbulence_model"]}; turbulence on; printCoeffs on; }}
""")
    nu = g["nu_m2_per_s"]
    _write(case / "constant/physicalProperties", "dictionary", "physicalProperties",
           f"\nviscosityModel  constant;\nnu              {_g(nu)};\n")
    Uin = _f(params, "inlet_velocity_m_per_s")
    k_in = 1.5 * (_f(params, "inlet_turbulence_intensity") * Uin) ** 2
    om_in = k_in / (nu * _f(params, "inlet_viscosity_ratio"))
    walls = ("upperWall", "upstreamFloor", "stepFace", "lowerWall")
    for name, cls, dim, val, inlet, outlet, wall in (
            ("U", "volVectorField", "[0 1 -1 0 0 0 0]", f"({_g(Uin)} 0 0)", f"{{ type fixedValue; value uniform ({_g(Uin)} 0 0); }}",
             f"{{ type inletOutlet; inletValue uniform (0 0 0); value uniform ({_g(Uin)} 0 0); }}", "{ type noSlip; }"),
            ("p", "volScalarField", "[0 2 -2 0 0 0 0]", "0", "{ type zeroGradient; }",
             "{ type fixedValue; value uniform 0; }", "{ type zeroGradient; }"),
            ("k", "volScalarField", "[0 2 -2 0 0 0 0]", _g(k_in), f"{{ type fixedValue; value uniform {_g(k_in)}; }}",
             f"{{ type inletOutlet; inletValue uniform {_g(k_in)}; value uniform {_g(k_in)}; }}",
             "{ type fixedValue; value uniform 1e-15; }"),
            ("omega", "volScalarField", "[0 0 -1 0 0 0 0]", _g(om_in), f"{{ type fixedValue; value uniform {_g(om_in)}; }}",
             f"{{ type inletOutlet; inletValue uniform {_g(om_in)}; value uniform {_g(om_in)}; }}",
             f"{{ type omegaWallFunction; value uniform {_g(om_in)}; }}"),
            ("nut", "volScalarField", "[0 2 -1 0 0 0 0]", "0", "{ type calculated; value uniform 0; }",
             "{ type calculated; value uniform 0; }", "{ type nutLowReWallFunction; value uniform 0; }")):
        body = "".join(f"    {w:<14}{wall}\n" for w in walls)
        _write(case / "0" / name, cls, name, f"""
dimensions      {dim};
internalField   uniform {val};
boundaryField
{{
    inlet         {inlet}
    outlet        {outlet}
{body}    frontAndBack  {{ type empty; }}
}}
""")
    return g
