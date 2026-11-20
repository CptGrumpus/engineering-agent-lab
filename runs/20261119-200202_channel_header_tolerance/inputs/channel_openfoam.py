"""OpenFOAM case writer: 2D laminar flow between parallel plates.

Writes a complete case directory (blockMesh, laminar incompressibleFluid,
steady SIMPLE) from engineering parameters in mm and SI units. The channel is
x = 0..L, y = 0..H, with no-slip walls, outlet at x = L (p = 0), and empty
front/back faces (2D). Two inlet treatments:

- Plain (default): uniform velocity imposed at x = 0. Idealized; the corner
  where the uniform inlet meets the no-slip wall is singular.
- Supply header (when HEADER_PARAMS are given): a supply duct of height Hs
  (centred on the channel) and length Ls, then a smooth cosine contraction of
  length Lc into the channel. The inlet carries a fully developed (parabolic)
  profile at an exact volumetric flow rate (flowRateInletVelocity, laminarBL
  profile), so no velocity discontinuity touches a wall.

Cells are ordered block by block (supply, contraction, channel), x fastest.

Run in WSL by models/cfd/run_channel.sh.
"""

from __future__ import annotations

from pathlib import Path

PARAMS = ("gap_mm", "length_mm", "mean_velocity_m_per_s", "density_kg_per_m3",
          "dynamic_viscosity_Pa_s", "cells_across_gap", "cell_aspect_ratio",
          "window_start_mm", "window_end_mm")

HEADER_PARAMS = ("supply_height_mm", "supply_length_mm", "contraction_length_mm")

HEADER = """FoamFile
{{
    format      ascii;
    class       {cls};
    object      {obj};
}}
"""


def mesh_counts(params: dict) -> tuple[int, int]:
    """(nx, ny): ny cells across the gap, nx along the channel (dx = aspect * dy)."""
    ny = int(params["cells_across_gap"])
    dy = float(params["gap_mm"]) / ny
    nx = round(float(params["length_mm"]) / (float(params["cell_aspect_ratio"]) * dy))
    return nx, ny


def has_header(params: dict) -> bool:
    return all(k in params for k in HEADER_PARAMS)


def contraction_height(s, H: float, Hs: float):
    """Duct height along the contraction, s = 0 (supply end) .. 1 (channel entry).

    Cosine shape: zero wall slope at both ends.
    """
    import numpy as np

    return H + (Hs - H) * (1 + np.cos(np.pi * np.asarray(s))) / 2


def block_counts(params: dict) -> list[tuple[int, int]]:
    """[(nx, ny)] per block in cell order: [supply, contraction,] channel."""
    nx, ny = mesh_counts(params)
    if not has_header(params):
        return [(nx, ny)]
    dx = float(params["cell_aspect_ratio"]) * float(params["gap_mm"]) / ny
    n_s = max(1, round(float(params["supply_length_mm"]) / dx))
    n_c = max(1, round(float(params["contraction_length_mm"]) / dx))
    return [(n_s, ny), (n_c, ny), (nx, ny)]


def _block_mesh_header(params: dict, depth: float) -> str:
    import numpy as np

    H, L = float(params["gap_mm"]), float(params["length_mm"])
    Hs, Ls = float(params["supply_height_mm"]), float(params["supply_length_mm"])
    Lc = float(params["contraction_length_mm"])
    if Hs <= H:
        raise ValueError("supply_height_mm must exceed gap_mm")
    (n_s, ny), (n_c, _), (nx, _) = block_counts(params)
    yc = H / 2
    x0, x1 = -Lc - Ls, -Lc
    lo, hi = yc - Hs / 2, yc + Hs / 2
    pts = [(x0, lo), (x1, lo), (x1, hi), (x0, hi), (0, 0), (0, H), (L, 0), (L, H)]
    verts = [(x, y, 0.0) for x, y in pts] + [(x, y, depth) for x, y in pts]
    vtxt = "\n".join(f"    ({float(x)!r} {float(y)!r} {float(z)!r})" for x, y, z in verts)
    s = np.linspace(0, 1, 41)[1:-1]
    h = contraction_height(s, H, Hs)
    xs = x1 + s * Lc

    def poly(a, b, sign, z):
        inner = " ".join(f"({float(x)!r} {float(yc + sign * hh / 2)!r} {float(z)!r})"
                         for x, hh in zip(xs, h))
        return f"    polyLine {a} {b} ({inner})"

    edges = "\n".join([poly(1, 4, -1, 0.0), poly(9, 12, -1, depth),
                        poly(2, 5, +1, 0.0), poly(10, 13, +1, depth)])
    return f"""
convertToMeters 0.001;

vertices
(
{vtxt}
);

blocks
(
    hex (0 1 2 3 8 9 10 11) ({n_s} {ny} 1) simpleGrading (1 1 1)
    hex (1 4 5 2 9 12 13 10) ({n_c} {ny} 1) simpleGrading (1 1 1)
    hex (4 6 7 5 12 14 15 13) ({nx} {ny} 1) simpleGrading (1 1 1)
);

edges
(
{edges}
);

boundary
(
    inlet        {{ type patch; faces ((0 8 11 3)); }}
    outlet       {{ type patch; faces ((6 7 15 14)); }}
    walls
    {{
        type wall;
        faces ((0 1 9 8) (3 11 10 2) (1 4 12 9) (2 10 13 5) (4 6 14 12) (5 13 15 7));
    }}
    frontAndBack
    {{
        type empty;
        faces ((0 3 2 1) (1 2 5 4) (4 5 7 6) (8 9 10 11) (9 12 13 10) (12 14 15 13));
    }}
);
"""


def _write(path: Path, cls: str, obj: str, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(HEADER.format(cls=cls, obj=obj) + body, encoding="utf-8", newline="\n")


def write_case(params: dict, numerics: dict, case: Path) -> dict:
    case = Path(case)
    H, L = float(params["gap_mm"]), float(params["length_mm"])
    U = float(params["mean_velocity_m_per_s"])
    nu = float(params["dynamic_viscosity_Pa_s"]) / float(params["density_kg_per_m3"])
    nx, ny = mesh_counts(params)
    depth = H  # arbitrary for a 2D (empty) case
    max_iter = int(numerics.get("max_iterations", 20000))
    scheme = numerics.get("convection_scheme", "linearUpwind grad(U)")

    header = has_header(params)
    blocks = block_counts(params)
    if header:
        _write(case / "system/blockMeshDict", "dictionary", "blockMeshDict",
               _block_mesh_header(params, depth))
    else:
        _write(case / "system/blockMeshDict", "dictionary", "blockMeshDict", f"""
convertToMeters 0.001;

vertices
(
    (0 0 0) ({L!r} 0 0) ({L!r} {H!r} 0) (0 {H!r} 0)
    (0 0 {depth!r}) ({L!r} 0 {depth!r}) ({L!r} {H!r} {depth!r}) (0 {H!r} {depth!r})
);

blocks ( hex (0 1 2 3 4 5 6 7) ({nx} {ny} 1) simpleGrading (1 1 1) );

boundary
(
    inlet        {{ type patch; faces ((0 4 7 3)); }}
    outlet       {{ type patch; faces ((1 2 6 5)); }}
    walls        {{ type wall;  faces ((0 1 5 4) (3 7 6 2)); }}
    frontAndBack {{ type empty; faces ((0 3 2 1) (4 5 6 7)); }}
);
""")
    _write(case / "system/controlDict", "dictionary", "controlDict", f"""
solver          incompressibleFluid;
startFrom       startTime;
startTime       0;
stopAt          endTime;
endTime         {max_iter};
deltaT          1;
writeControl    timeStep;
writeInterval   {max_iter};
writeFormat     ascii;
writePrecision  12;
writeCompression off;
timeFormat      general;
timePrecision   8;
runTimeModifiable false;
""")
    _write(case / "system/fvSchemes", "dictionary", "fvSchemes", f"""
ddtSchemes      {{ default steadyState; }}
gradSchemes     {{ default Gauss linear; }}
divSchemes
{{
    default         none;
    div(phi,U)      bounded Gauss {scheme};
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
    p
    {{
        solver          GAMG;
        smoother        GaussSeidel;
        tolerance       1e-12;
        relTol          0.01;
    }}
    U
    {{
        solver          smoothSolver;
        smoother        symGaussSeidel;
        tolerance       1e-14;
        relTol          0.01;
    }}
}}

SIMPLE
{{
    nNonOrthogonalCorrectors 0;
    consistent      yes;
    residualControl
    {{
        p   {float(numerics["residual_p"])!r};
        U   {float(numerics["residual_U"])!r};
    }}
}}

relaxationFactors
{{
    equations {{ U {float(numerics.get("relaxation_U", 0.9))!r}; }}
}}
""")
    _write(case / "constant/momentumTransport", "dictionary", "momentumTransport",
           "\nsimulationType laminar;\n")
    _write(case / "constant/physicalProperties", "dictionary", "physicalProperties",
           f"\nviscosityModel  constant;\nnu              {nu!r};\n")
    if header:  # exact flow rate U*H*depth with a fully developed (parabolic) profile
        q = U * H * 1e-3 * depth * 1e-3
        inlet_u = (f"inlet {{ type flowRateInletVelocity; volumetricFlowRate {q!r}; "
                   f"profile laminarBL; value uniform (0 0 0); }}")
        u0 = U * H / float(params["supply_height_mm"])
    else:
        inlet_u = f"inlet        {{ type fixedValue; value uniform ({U!r} 0 0); }}"
        u0 = 0.0
    walls_empty = """
    walls        { type noSlip; }
    frontAndBack { type empty; }
"""
    _write(case / "0/U", "volVectorField", "U", f"""
dimensions      [0 1 -1 0 0 0 0];
internalField   uniform ({u0!r} 0 0);
boundaryField
{{
    {inlet_u}
    outlet       {{ type zeroGradient; }}{walls_empty}}}
""")
    _write(case / "0/p", "volScalarField", "p", """
dimensions      [0 2 -2 0 0 0 0];
internalField   uniform 0;
boundaryField
{
    inlet        { type zeroGradient; }
    outlet       { type fixedValue; value uniform 0; }
    walls        { type zeroGradient; }
    frontAndBack { type empty; }
}
""")
    return {"nx": nx, "ny": ny, "cells": sum(a * b for a, b in blocks), "blocks": blocks,
            "depth_mm": depth, "nu_m2_per_s": nu, "header": header}
