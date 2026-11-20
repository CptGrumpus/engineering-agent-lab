"""OpenFOAM case writer: fully developed laminar flow in a rectangular duct (3D).

Checks the 2D (infinitely wide) assumption of the channel model by adding the
side walls back. Only a quarter of the cross-section is meshed:

    y = 0      plate wall          y = H/2    symmetry plane (mid-gap)
    z = 0      side wall           z = W/2    symmetry plane (mid-width)
    x          periodic (cyclic), two cells long

The flow is driven by OpenFOAM's meanVelocityForce constraint, which finds the
pressure gradient that gives the requested mean velocity; that gradient is the
result. The z cells are graded toward the side wall.

Run in WSL by models/cfd/run_channel.sh (blockMesh, checkMesh, foamRun,
writeCellCentres).
"""

from __future__ import annotations

from pathlib import Path

PARAMS = ("gap_mm", "width_mm", "mean_velocity_m_per_s", "density_kg_per_m3",
          "dynamic_viscosity_Pa_s", "cells_across_gap", "width_cells_per_gap_cell",
          "side_wall_grading")

HEADER = """FoamFile
{{
    format      ascii;
    class       {cls};
    object      {obj};
}}
"""


def mesh_counts(params: dict) -> tuple[int, int, int]:
    """(nx, ny, nz) for the quarter section: ny = half the cells across the gap."""
    n = int(params["cells_across_gap"])
    if n % 2:
        raise ValueError("cells_across_gap must be even (half the gap is meshed)")
    return 2, n // 2, int(round(n * float(params["width_cells_per_gap_cell"])))


def _write(path: Path, cls: str, obj: str, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(HEADER.format(cls=cls, obj=obj) + body, encoding="utf-8", newline="\n")


def write_case(params: dict, numerics: dict, case: Path) -> dict:
    case = Path(case)
    H, W = float(params["gap_mm"]), float(params["width_mm"])
    U = float(params["mean_velocity_m_per_s"])
    nu = float(params["dynamic_viscosity_Pa_s"]) / float(params["density_kg_per_m3"])
    nx, ny, nz = mesh_counts(params)
    h, b = H / 2, W / 2
    lx = nx * h / ny  # cubic cells near the plate
    # blockMesh expansion ratio = last cell / first cell along z; the first cell is at
    # the side wall (z = 0), so a ratio > 1 makes the cells finest there
    gz = float(params["side_wall_grading"])
    # Fixed iteration count: no residualControl. In fully developed duct flow the
    # exact Uy, Uz are zero and p is uniform, so their normalised residuals stall at
    # round-off noise; convergence is judged afterwards on Ux, on the pressure
    # gradient history, and on the cross-flow velocity (see studies/duct_flow.py).
    # The slow mode is diffusion across the width in SIMPLE's pseudo-time, so the
    # count must grow with the mesh; relaxation above ~0.99 diverges.
    max_iter = int(numerics["iterations"])

    _write(case / "system/blockMeshDict", "dictionary", "blockMeshDict", f"""
convertToMeters 0.001;

vertices
(
    (0 0 0) ({lx!r} 0 0) ({lx!r} {h!r} 0) (0 {h!r} 0)
    (0 0 {b!r}) ({lx!r} 0 {b!r}) ({lx!r} {h!r} {b!r}) (0 {h!r} {b!r})
);

blocks ( hex (0 1 2 3 4 5 6 7) ({nx} {ny} {nz}) simpleGrading (1 1 {gz!r}) );

boundary
(
    periodic0 {{ type cyclic; neighbourPatch periodic1; faces ((0 4 7 3)); }}
    periodic1 {{ type cyclic; neighbourPatch periodic0; faces ((1 2 6 5)); }}
    plate     {{ type wall; faces ((0 1 5 4)); }}
    sideWall  {{ type wall; faces ((0 3 2 1)); }}
    midGap    {{ type symmetryPlane; faces ((3 7 6 2)); }}
    midWidth  {{ type symmetryPlane; faces ((4 5 6 7)); }}
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
    _write(case / "system/fvSchemes", "dictionary", "fvSchemes", """
ddtSchemes      { default steadyState; }
gradSchemes     { default Gauss linear; }
divSchemes
{
    default         none;
    div(phi,U)      bounded Gauss linearUpwind grad(U);
    div((nuEff*dev2(T(grad(U))))) Gauss linear;
}
laplacianSchemes     { default Gauss linear corrected; }
interpolationSchemes { default linear; }
snGradSchemes        { default corrected; }
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
    pRefCell        0;
    pRefValue       0;
}}

relaxationFactors
{{
    equations {{ U {float(numerics.get("relaxation_U", 0.9))!r}; }}
}}
""")
    _write(case / "system/fvConstraints", "dictionary", "fvConstraints", f"""
meanVelocity
{{
    type            meanVelocityForce;
    cellZone        all;
    Ubar            ({U!r} 0 0);
}}
""")
    _write(case / "constant/momentumTransport", "dictionary", "momentumTransport",
           "\nsimulationType laminar;\n")
    _write(case / "constant/physicalProperties", "dictionary", "physicalProperties",
           f"\nviscosityModel  constant;\nnu              {nu!r};\n")
    bc = """
    periodic0 { type cyclic; }
    periodic1 { type cyclic; }
    midGap    { type symmetryPlane; }
    midWidth  { type symmetryPlane; }
"""
    _write(case / "0/U", "volVectorField", "U", f"""
dimensions      [0 1 -1 0 0 0 0];
internalField   uniform ({U!r} 0 0);
boundaryField
{{{bc}
    plate     {{ type noSlip; }}
    sideWall  {{ type noSlip; }}
}}
""")
    _write(case / "0/p", "volScalarField", "p", f"""
dimensions      [0 2 -2 0 0 0 0];
internalField   uniform 0;
boundaryField
{{{bc}
    plate     {{ type zeroGradient; }}
    sideWall  {{ type zeroGradient; }}
}}
""")
    return {"nx": nx, "ny": ny, "nz": nz, "cells": nx * ny * nz, "nu_m2_per_s": nu}
