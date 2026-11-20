"""OpenFOAM case writer: 2D laminar flow between parallel plates.

Writes a complete case directory (blockMesh, laminar incompressibleFluid,
steady SIMPLE) from engineering parameters in mm and SI units. The geometry is
one structured block: inlet at x = 0 (uniform velocity), outlet at x = L
(p = 0), no-slip walls at y = 0 and y = H, and empty front/back faces (2D).

Run in WSL by models/cfd/run_channel.sh.
"""

from __future__ import annotations

from pathlib import Path

PARAMS = ("gap_mm", "length_mm", "mean_velocity_m_per_s", "density_kg_per_m3",
          "dynamic_viscosity_Pa_s", "cells_across_gap", "cell_aspect_ratio",
          "window_start_mm", "window_end_mm")

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
    walls_empty = """
    walls        { type noSlip; }
    frontAndBack { type empty; }
"""
    _write(case / "0/U", "volVectorField", "U", f"""
dimensions      [0 1 -1 0 0 0 0];
internalField   uniform (0 0 0);
boundaryField
{{
    inlet        {{ type fixedValue; value uniform ({U!r} 0 0); }}
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
    return {"nx": nx, "ny": ny, "cells": nx * ny, "depth_mm": depth, "nu_m2_per_s": nu}
