"""OpenFOAM case writer: heated laminar coolant channel (2D parallel plates).

The channel runs x = -entry .. heated + exit (mm), y = 0..H, three blocks:
  entry   adiabatic walls; the inlet carries a fully developed (parabolic) velocity
          profile at an exact flow rate (flowRateInletVelocity, laminarBL profile)
  heated  x = 0..heated_length: both walls at a uniform heat flux q into the water
  exit    adiabatic walls, so the outlet boundary sits away from the end of heating
Flow: incompressibleFluid, laminar, steady SIMPLE. Temperature: the scalarTransport
function object (constant properties, so temperature is a passive scalar):
    div(phi T) = laplacian(D, T),  D = alphal * nu  with alphal = 1/Pr,
heated walls fixedGradient q/k, inlet fixedValue T_in, outlet zeroGradient.

Temperature scheme: linearUpwind. It converges exactly (residual 1e-13, energy balance
1e-11) but overshoots by 0.06-0.11 K at the last heated cell, where the wall condition steps
from heated to adiabatic; the overshoot raises the reported peak (conservative) and shrinks
with the mesh, and the study's peak-vs-reference and mesh-convergence checks bound it.
Every TVD limiter tried (limitedLinear 1 and 0.2, vanLeer, Minmod) dithered from one
iteration to the next near the end of heating and never closed the energy balance, with or
without under-relaxation (runs 20261120-124736, -130606, -131818 and scratch tests).

Run in WSL by models/cfd/run_heated.sh: flow first, then temperature alone on the frozen flow
(the `functions` solver), which makes thousands of temperature iterations cheap.
"""

from __future__ import annotations

from pathlib import Path

PARAMS = ("gap_mm", "heated_length_mm", "entry_length_mm", "exit_length_mm",
          "mean_velocity_m_per_s", "density_kg_per_m3", "dynamic_viscosity_Pa_s",
          "specific_heat_J_per_kgK", "conductivity_W_per_mK", "inlet_temperature_C",
          "wall_heat_flux_W_per_m2", "cells_across_gap", "cell_aspect_ratio")

HEADER = """FoamFile
{{
    format      ascii;
    class       {cls};
    object      {obj};
}}
"""


def _write(path: Path, cls: str, obj: str, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(HEADER.format(cls=cls, obj=obj) + body, encoding="utf-8", newline="\n")


def block_counts(params: dict) -> list[tuple[int, int]]:
    """[(nx, ny)] for entry, heated and exit blocks (cells ordered block by block, x fastest)."""
    ny = int(params["cells_across_gap"])
    dx = float(params["cell_aspect_ratio"]) * float(params["gap_mm"]) / ny
    return [(max(1, round(float(params[k]) / dx)), ny)
            for k in ("entry_length_mm", "heated_length_mm", "exit_length_mm")]


def write_case(params: dict, numerics: dict, case: Path) -> dict:
    case = Path(case)
    H = float(params["gap_mm"])
    Le, Lh, Lx = (float(params[k]) for k in ("entry_length_mm", "heated_length_mm", "exit_length_mm"))
    U, rho, mu = (float(params[k]) for k in ("mean_velocity_m_per_s", "density_kg_per_m3", "dynamic_viscosity_Pa_s"))
    cp, k = float(params["specific_heat_J_per_kgK"]), float(params["conductivity_W_per_mK"])
    q, T_in = float(params["wall_heat_flux_W_per_m2"]), float(params["inlet_temperature_C"])
    nu = mu / rho
    Pr = mu * cp / k
    depth = H
    blocks = block_counts(params)
    xs = (-Le, 0.0, Lh, Lh + Lx)
    v = []
    for x in xs:
        v.append(f"({x!r} 0 0)")
        v.append(f"({x!r} {H!r} 0)")
    for x in xs:
        v.append(f"({x!r} 0 {depth!r})")
        v.append(f"({x!r} {H!r} {depth!r})")
    # vertex index: front (z=0) 2*i (bottom), 2*i+1 (top); back = +8
    def hexb(i, n):
        a, b = 2 * i, 2 * (i + 1)
        return (f"hex ({a} {b} {b + 1} {a + 1} {a + 8} {b + 8} {b + 9} {a + 9}) "
                f"({n[0]} {n[1]} 1) simpleGrading (1 1 1)")

    def walls(i):
        a, b = 2 * i, 2 * (i + 1)
        return f"({a} {b} {b + 8} {a + 8}) ({a + 1} {a + 9} {b + 9} {b + 1})"

    fb = " ".join(f"({2*i} {2*i+1} {2*i+3} {2*i+2}) ({2*i+8} {2*i+10} {2*i+11} {2*i+9})" for i in range(3))
    _write(case / "system/blockMeshDict", "dictionary", "blockMeshDict", f"""
convertToMeters 0.001;

vertices
(
    {' '.join(v)}
);

blocks
(
    {hexb(0, blocks[0])}
    {hexb(1, blocks[1])}
    {hexb(2, blocks[2])}
);

boundary
(
    inlet        {{ type patch; faces ((0 8 9 1)); }}
    outlet       {{ type patch; faces ((6 7 15 14)); }}
    wall_entry   {{ type wall;  faces ({walls(0)}); }}
    wall_heated  {{ type wall;  faces ({walls(1)}); }}
    wall_exit    {{ type wall;  faces ({walls(2)}); }}
    frontAndBack {{ type empty; faces ({fb}); }}
);
""")
    n_flow = int(numerics.get("flow_iterations", 600))
    n_temp = int(numerics.get("temperature_iterations", 4000))
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
    # stage 1: flow (and a first pass of temperature), written once at the end
    _write(case / "system/controlDict", "dictionary", "controlDict", f"""
solver          incompressibleFluid;
startFrom       startTime;
startTime       0;
stopAt          endTime;
endTime         {n_flow};
writeInterval   {n_flow};
{common}{functions}""")
    # stage 2: temperature only, on the frozen flow; keep the last two writes for the
    # convergence check (purgeWrite only removes times written by this stage)
    _write(case / "system/controlDict.temperature", "dictionary", "controlDict", f"""
solver          functions;
subSolver       incompressibleFluid;
startFrom       latestTime;
stopAt          endTime;
endTime         {n_flow + n_temp};
writeInterval   {every};
purgeWrite      2;
{common}{functions}""")
    _write(case / "system/fvSchemes", "dictionary", "fvSchemes", """
ddtSchemes      { default steadyState; }
gradSchemes     { default Gauss linear; }
divSchemes
{
    default         none;
    div(phi,U)      bounded Gauss linearUpwind grad(U);
    div(phi,T)      bounded Gauss linearUpwind grad(T);   // converges exactly; see the docstring
    div((nuEff*dev2(T(grad(U))))) Gauss linear;
}
laplacianSchemes     { default Gauss linear corrected; }
interpolationSchemes { default linear; }
snGradSchemes        { default corrected; }
""")
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
    grad = q / k
    _write(case / "0/T", "volScalarField", "T", f"""
dimensions      [0 0 0 1 0 0 0];
internalField   uniform {T_in!r};
boundaryField
{{
    inlet        {{ type fixedValue; value uniform {T_in!r}; }}
    outlet       {{ type zeroGradient; }}
    wall_entry   {{ type zeroGradient; }}
    wall_heated  {{ type fixedGradient; gradient uniform {grad!r}; value uniform {T_in!r}; }}
    wall_exit    {{ type zeroGradient; }}
    frontAndBack {{ type empty; }}
}}
""")
    return {"cells": sum(a * b for a, b in blocks), "blocks": blocks, "depth_mm": depth,
            "nu_m2_per_s": nu, "prandtl": Pr, "wall_gradient_K_per_m": grad}
