"""OpenFOAM case writer: cold-plate coolant channel with a wall heat-flux profile.

Same channel and solution method as models/cfd/heated_channel_openfoam.py (2D parallel
plates, developed parabolic inflow at an exact flow rate, steady laminar flow, temperature
as a passive scalar by the scalarTransport function object, flow first and then
temperature alone on the frozen flow), with one difference: each wall carries a heat-flux
profile, one value per wall face, set by the coupling with the plate model instead of a
uniform flux over the heated length.

Geometry (mm): x = -(unplated + entry) .. footprint + exit + unplated, y = 0..H; five blocks
(unplated inlet section, plate entry, footprint, plate exit, unplated outlet section) with the
same cell size along x, so the wall faces are uniform and the plate's faces match them one to
one. The plate covers x = -entry .. footprint + exit; the unplated sections have adiabatic
walls and keep the inlet and outlet boundaries away from the heated wall (with heat reaching
the wall at the inlet cells, the fixed inlet temperature drew heat out and the outlet column
missed the last half cell: 5e-4 of the energy balance in the smoke test). Two wall patches,
wall_bottom (y = 0) and wall_top (y = H), each spanning all five blocks; their faces run in
increasing x (checked by the backend from the face centres).

Wall condition: fixedGradient q(x)/k with q into the water. The case is symmetric (a plate
on each wall), so both walls get the same profile.

Run in WSL by models/cfd/run_cold_plate.sh: `full` meshes and runs flow then temperature;
`temperature` continues the temperature stage on the frozen flow from the latest time,
after set_wall_flux() and set_end_time() have updated the latest T file and controlDict.
"""

from __future__ import annotations

import re
from pathlib import Path

import numpy as np

PARAMS = ("gap_mm", "footprint_length_mm", "entry_length_mm", "exit_length_mm", "unplated_length_mm",
          "mean_velocity_m_per_s", "density_kg_per_m3", "dynamic_viscosity_Pa_s",
          "specific_heat_J_per_kgK", "conductivity_W_per_mK", "inlet_temperature_C",
          "cells_across_gap", "cell_aspect_ratio")

BLOCK_KEYS = ("unplated_length_mm", "entry_length_mm", "footprint_length_mm", "exit_length_mm",
              "unplated_length_mm")
HEADER = """FoamFile
{{
    format      ascii;
    class       {cls};
    object      {obj};
}}
"""
WALLS = ("wall_bottom", "wall_top")


def _write(path: Path, cls: str, obj: str, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(HEADER.format(cls=cls, obj=obj) + body, encoding="utf-8", newline="\n")


def block_counts(params: dict) -> list[tuple[int, int]]:
    """[(nx, ny)] for the five blocks along x. The cell size along x is the same in all of
    them; each block length must be a whole number of cells."""
    ny = int(params["cells_across_gap"])
    dx = float(params["cell_aspect_ratio"]) * float(params["gap_mm"]) / ny
    out = []
    for key in BLOCK_KEYS:
        n = float(params[key]) / dx
        if abs(n - round(n)) > 1e-9 or round(n) < 1:
            raise ValueError(f"{key} must be a whole number of {dx:g} mm cells")
        out.append((int(round(n)), ny))
    return out


def block_x_mm(params: dict) -> list[float]:
    """x at the block boundaries (mm): inlet, plate start, footprint start (0), footprint end,
    plate end, outlet."""
    Lu, Le, Lf, Lx = (float(params[k]) for k in ("unplated_length_mm", "entry_length_mm",
                                                  "footprint_length_mm", "exit_length_mm"))
    return [-Le - Lu, -Le, 0.0, Lf, Lf + Lx, Lf + Lx + Lu]


def face_edges_mm(params: dict) -> np.ndarray:
    """x edges of the wall faces (mm), inlet to outlet."""
    xb = block_x_mm(params)
    nx = sum(b[0] for b in block_counts(params))
    return xb[0] + (xb[-1] - xb[0]) * np.arange(nx + 1) / nx


def plate_faces(params: dict) -> np.ndarray:
    """Boolean mask of the wall faces covered by the plate."""
    xb = block_x_mm(params)
    fe = face_edges_mm(params)
    xc = 0.5 * (fe[1:] + fe[:-1])
    return (xc > xb[1]) & (xc < xb[4])


def _list(values) -> str:
    vals = " ".join(f"{float(v)!r}" for v in values)
    return f"nonuniform List<scalar> {len(values)} ({vals})"


def write_case(params: dict, numerics: dict, case: Path, wall_flux_W_per_m2) -> dict:
    case = Path(case)
    H = float(params["gap_mm"])
    U, rho, mu = (float(params[k]) for k in ("mean_velocity_m_per_s", "density_kg_per_m3", "dynamic_viscosity_Pa_s"))
    cp, k = float(params["specific_heat_J_per_kgK"]), float(params["conductivity_W_per_mK"])
    T_in = float(params["inlet_temperature_C"])
    nu = mu / rho
    Pr = mu * cp / k
    depth = H
    blocks = block_counts(params)
    q = np.asarray(wall_flux_W_per_m2, float)
    if len(q) != sum(b[0] for b in blocks):
        raise ValueError("one wall flux value per wall face")
    xs = block_x_mm(params)
    nb = len(xs) - 1
    off = 2 * len(xs)                      # back-plane vertex offset
    v = []
    for x in xs:
        v.append(f"({x!r} 0 0)")
        v.append(f"({x!r} {H!r} 0)")
    for x in xs:
        v.append(f"({x!r} 0 {depth!r})")
        v.append(f"({x!r} {H!r} {depth!r})")

    def hexb(i, n):
        a, b = 2 * i, 2 * (i + 1)
        return (f"hex ({a} {b} {b + 1} {a + 1} {a + off} {b + off} {b + 1 + off} {a + 1 + off}) "
                f"({n[0]} {n[1]} 1) simpleGrading (1 1 1)")

    bottom = " ".join(f"({2*i} {2*i+2} {2*i+2+off} {2*i+off})" for i in range(nb))
    top = " ".join(f"({2*i+1} {2*i+1+off} {2*i+3+off} {2*i+3})" for i in range(nb))
    fb = " ".join(f"({2*i} {2*i+1} {2*i+3} {2*i+2}) ({2*i+off} {2*i+2+off} {2*i+3+off} {2*i+1+off})"
                  for i in range(nb))
    last = 2 * nb
    _write(case / "system/blockMeshDict", "dictionary", "blockMeshDict", f"""
convertToMeters 0.001;

vertices
(
    {' '.join(v)}
);

blocks
(
    {chr(10).join("    " + hexb(i, blocks[i]) for i in range(nb))}
);

boundary
(
    inlet        {{ type patch; faces ((0 {off} {off + 1} 1)); }}
    outlet       {{ type patch; faces (({last} {last + 1} {last + 1 + off} {last + off})); }}
    wall_bottom  {{ type wall;  faces ({bottom}); }}
    wall_top     {{ type wall;  faces ({top}); }}
    frontAndBack {{ type empty; faces ({fb}); }}
);
""")
    n_flow = int(numerics.get("flow_iterations", 1000))
    n_temp = int(numerics.get("temperature_iterations", 1500))
    every = int(numerics.get("write_interval", 100))
    functions = f"""
functions
{{
    T
    {{
        type            scalarTransport;
        libs            ("libsolverFunctionObjects.so");
        field           T;
        diffusivity     viscosity;
        alphal          {1.0 / Pr!r};
        alphat          1;
        writeControl    writeTime;
    }}
}}
"""
    common = """deltaT          1;
writeControl    timeStep;
writeFormat     ascii;
writePrecision  12;
writeCompression off;
timeFormat      general;
timePrecision   8;
runTimeModifiable false;
"""
    _write(case / "system/controlDict", "dictionary", "controlDict", f"""
solver          incompressibleFluid;
startFrom       startTime;
startTime       0;
stopAt          endTime;
endTime         {n_flow};
writeInterval   {n_flow};
{common}{functions}""")
    _write(case / "system/controlDict.temperature", "dictionary", "controlDict", f"""
solver          functions;
subSolver       incompressibleFluid;
startFrom       latestTime;
stopAt          endTime;
endTime         {n_flow + n_temp};
writeInterval   {every};
purgeWrite      2;
{common}{functions}""")
    t_grad = "limitedGradT" if numerics.get("temperature_gradient_limiter", False) else "grad(T)"
    _write(case / "system/fvSchemes", "dictionary", "fvSchemes", """
ddtSchemes      { default steadyState; }
gradSchemes     { default Gauss linear; limitedGradT cellLimited Gauss linear 1; }
divSchemes
{
    default         none;
    div(phi,U)      bounded Gauss linearUpwind grad(U);
    div(phi,T)      bounded Gauss linearUpwind {T_GRAD};
    div((nuEff*dev2(T(grad(U))))) Gauss linear;
}
laplacianSchemes     { default Gauss linear corrected; }
interpolationSchemes { default linear; }
snGradSchemes        { default corrected; }
""".replace("{T_GRAD}", t_grad))
    _write(case / "system/fvSolution", "dictionary", "fvSolution", f"""
solvers
{{
    p {{ solver GAMG; smoother GaussSeidel; tolerance 1e-12; relTol 0.01; }}
    U {{ solver smoothSolver; smoother symGaussSeidel; tolerance 1e-14; relTol 0.01; }}
    T {{ solver PBiCGStab; preconditioner DILU; tolerance 1e-14; relTol 0; }}
}}

SIMPLE
{{
    nNonOrthogonalCorrectors 0;
    consistent      yes;
}}

relaxationFactors {{ equations {{ U 0.9; T {float(numerics.get("relaxation_T", 1.0))!r}; }} }}
""")
    _write(case / "constant/momentumTransport", "dictionary", "momentumTransport", "\nsimulationType laminar;\n")
    _write(case / "constant/physicalProperties", "dictionary", "physicalProperties",
           f"\nviscosityModel  constant;\nnu              {nu!r};\n")
    flow = U * H * 1e-3 * depth * 1e-3
    _write(case / "0/U", "volVectorField", "U", f"""
dimensions      [0 1 -1 0 0 0 0];
internalField   uniform ({U!r} 0 0);
boundaryField
{{
    inlet        {{ type flowRateInletVelocity; volumetricFlowRate {flow!r}; profile laminarBL; value uniform (0 0 0); }}
    outlet       {{ type zeroGradient; }}
    "wall_.*"    {{ type noSlip; }}
    frontAndBack {{ type empty; }}
}}
""")
    _write(case / "0/p", "volScalarField", "p", """
dimensions      [0 2 -2 0 0 0 0];
internalField   uniform 0;
boundaryField
{
    inlet        { type zeroGradient; }
    outlet       { type fixedValue; value uniform 0; }
    "wall_.*"    { type zeroGradient; }
    frontAndBack { type empty; }
}
""")
    g = _list(q / k)
    _write(case / "0/T", "volScalarField", "T", f"""
dimensions      [0 0 0 1 0 0 0];
internalField   uniform {T_in!r};
boundaryField
{{
    inlet        {{ type fixedValue; value uniform {T_in!r}; }}
    outlet       {{ type zeroGradient; }}
    wall_bottom  {{ type fixedGradient; gradient {g}; value uniform {T_in!r}; }}
    wall_top     {{ type fixedGradient; gradient {g}; value uniform {T_in!r}; }}
    frontAndBack {{ type empty; }}
}}
""")
    return {"cells": sum(a * b for a, b in blocks), "blocks": blocks, "depth_mm": depth,
            "nu_m2_per_s": nu, "prandtl": Pr, "n_flow": n_flow, "n_temp": n_temp}


def _patch_span(text: str, patch: str) -> tuple[int, int]:
    """(start, end) of the brace block of `patch` inside boundaryField."""
    bf = text.index("boundaryField")
    m = re.compile(rf"\b{patch}\b\s*\{{").search(text, bf)
    if not m:
        raise ValueError(f"patch {patch} not found")
    depth, i = 0, m.end() - 1
    while True:
        c = text[i]
        depth += c == "{"
        depth -= c == "}"
        i += 1
        if depth == 0:
            return m.end(), i - 1


def set_wall_flux(T_file: Path, wall_flux_W_per_m2, k: float) -> None:
    """Replace the gradient of both wall patches in a written T field (in place)."""
    text = Path(T_file).read_text(encoding="utf-8")
    g = _list(np.asarray(wall_flux_W_per_m2, float) / float(k))
    for patch in WALLS:
        a, b = _patch_span(text, patch)
        body = text[a:b]
        m = re.search(r"gradient\s+(nonuniform\s+List<scalar>\s+\d+\s*\(.*?\)|uniform\s+\S+?)\s*;", body, re.S)
        if not m:
            raise ValueError(f"no gradient entry in patch {patch}")
        body = body[:m.start()] + f"gradient {g};" + body[m.end():]
        text = text[:a] + body + text[b:]
    Path(T_file).write_text(text, encoding="utf-8", newline="\n")


def set_end_time(control_dict: Path, end_time: int) -> None:
    text = Path(control_dict).read_text(encoding="utf-8")
    text, n = re.subn(r"(\nendTime\s+)\S+;", rf"\g<1>{int(end_time)};", text)
    if n != 1:
        raise ValueError("endTime not found in controlDict")
    Path(control_dict).write_text(text, encoding="utf-8", newline="\n")
