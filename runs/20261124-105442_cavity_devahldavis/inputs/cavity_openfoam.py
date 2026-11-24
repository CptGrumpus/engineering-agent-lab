"""Differentially heated square cavity (study 11, stage 1), OpenFOAM 14 `foamRun -solver fluid`, steady, laminar.

The de Vahl Davis (1983) problem: a 2D square cavity of side L, the wall at x = 0 hot (Th), x = L cold (Tc), top and
bottom adiabatic, no slip, Pr = 0.71. OpenFOAM's Boussinesq equation of state (rho = rho0 (1 - beta (T - T0))) enters
every term, not only buoyancy, so the temperature difference is kept small (beta dT = 3.3e-4) and the Rayleigh number
is set through g: g = Ra nu kappa / (beta dT L^3).

Mesh: blockMesh, one cell deep (2D, empty front and back), N x N cells graded symmetrically towards every wall
(edge-to-centre cell size ratio `wall_grading`). Second-order convection (linearUpwind) and SIMPLE with residual
control; the run stops on the residuals or at max_iterations.

Run in WSL by models/cfd/run_cavity.sh. Must not import from validation/.
"""

from __future__ import annotations

from pathlib import Path

PARAMS = ("rayleigh", "prandtl", "cells", "wall_grading", "side_m", "delta_T_K", "max_iterations")
RHO0, T0, BETA, MU, CP = 1.0, 300.0, 1.0 / 300.0, 1.8e-5, 1000.0


def properties(params: dict) -> dict:
    Pr, L, dT = float(params["prandtl"]), float(params["side_m"]), float(params["delta_T_K"])
    nu = MU / RHO0
    kappa = nu / Pr
    g = float(params["rayleigh"]) * nu * kappa / (BETA * dT * L ** 3)
    return {"nu": nu, "kappa": kappa, "k": MU * CP / Pr, "g": g, "L": L, "dT": dT,
            "Th": T0 + dT / 2, "Tc": T0 - dT / 2, "Pr": Pr}


def _write(path: Path, cls: str, obj: str, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("FoamFile\n{\n    format ascii;\n    class " + cls + ";\n    object " + obj + ";\n}\n" + body,
                    encoding="utf-8", newline="\n")


def write_case(params: dict, numerics: dict, case: Path) -> dict:
    p = properties(params)
    n, L, r = int(params["cells"]), p["L"], float(params["wall_grading"])
    if n % 2:
        raise ValueError("an even cell count (the grading is symmetric about the mid-planes)")
    depth = L / n
    grade = f"((0.5 0.5 {r!r}) (0.5 0.5 {1.0 / r!r}))"
    _write(case / "system/blockMeshDict", "dictionary", "blockMeshDict", f"""
convertToMeters 1;
vertices ( (0 0 0) ({L!r} 0 0) ({L!r} {L!r} 0) (0 {L!r} 0) (0 0 {depth!r}) ({L!r} 0 {depth!r}) ({L!r} {L!r} {depth!r}) (0 {L!r} {depth!r}) );
blocks ( hex (0 1 2 3 4 5 6 7) ({n} {n} 1) simpleGrading ({grade} {grade} 1) );
boundary
(
    hot {{ type wall; faces ((0 4 7 3)); }}
    cold {{ type wall; faces ((1 2 6 5)); }}
    adiabatic {{ type wall; faces ((0 1 5 4) (3 7 6 2)); }}
    frontAndBack {{ type empty; faces ((0 3 2 1) (4 5 6 7)); }}
);
""")
    _write(case / "constant/physicalProperties", "dictionary", "physicalProperties", f"""
thermoType {{ type heRhoThermo; mixture pureMixture; transport const; thermo hConst; equationOfState Boussinesq;
             specie specie; energy sensibleEnthalpy; }}
mixture
{{
    specie {{ molWeight 28.9; }}
    equationOfState {{ rho0 {RHO0!r}; T0 {T0!r}; beta {BETA!r}; }}
    thermodynamics {{ Cp {CP!r}; hf 0; }}
    transport {{ mu {MU!r}; Pr {p['Pr']!r}; }}
}}
""")
    _write(case / "constant/g", "uniformDimensionedVectorField", "g", f"\ndimensions [0 1 -2 0 0 0 0];\nvalue (0 {-p['g']!r} 0);\n")
    _write(case / "constant/momentumTransport", "dictionary", "momentumTransport", "\nsimulationType laminar;\n")
    walls = "    hot { type noSlip; }\n    cold { type noSlip; }\n    adiabatic { type noSlip; }\n    frontAndBack { type empty; }\n"
    _write(case / "0/U", "volVectorField", "U", "\ndimensions [0 1 -1 0 0 0 0];\ninternalField uniform (0 0 0);\n"
           "boundaryField\n{\n" + walls + "}\n")
    _write(case / "0/T", "volScalarField", "T", f"\ndimensions [0 0 0 1 0 0 0];\ninternalField uniform {T0!r};\n"
           "boundaryField\n{\n"
           f"    hot {{ type fixedValue; value uniform {p['Th']!r}; }}\n"
           f"    cold {{ type fixedValue; value uniform {p['Tc']!r}; }}\n"
           "    adiabatic { type zeroGradient; }\n    frontAndBack { type empty; }\n}\n")
    pf = "    hot { type calculated; value $internalField; }\n    cold { type calculated; value $internalField; }\n" \
         "    adiabatic { type calculated; value $internalField; }\n    frontAndBack { type empty; }\n"
    _write(case / "0/p", "volScalarField", "p", "\ndimensions [1 -1 -2 0 0 0 0];\ninternalField uniform 1e5;\n"
           "boundaryField\n{\n" + pf + "}\n")
    pr = "    hot { type fixedFluxPressure; value $internalField; }\n    cold { type fixedFluxPressure; value $internalField; }\n" \
         "    adiabatic { type fixedFluxPressure; value $internalField; }\n    frontAndBack { type empty; }\n"
    _write(case / "0/p_rgh", "volScalarField", "p_rgh", "\ndimensions [1 -1 -2 0 0 0 0];\ninternalField uniform 1e5;\n"
           "boundaryField\n{\n" + pr + "}\n")
    _write(case / "system/controlDict", "dictionary", "controlDict", f"""
solver          fluid;
startFrom       startTime;
startTime       0;
stopAt          endTime;
endTime         {int(params['max_iterations'])};
deltaT          1;
writeControl    timeStep;
writeInterval   {int(params['max_iterations'])};
purgeWrite      0;
writeFormat     ascii;
writePrecision  12;
timeFormat      general;
timePrecision   8;
runTimeModifiable false;
""")
    _write(case / "system/fvSchemes", "dictionary", "fvSchemes", """
ddtSchemes { default steadyState; }
gradSchemes { default Gauss linear; }
divSchemes
{
    default none;
    div(phi,U) bounded Gauss linearUpwind grad(U);
    div(phi,h) bounded Gauss linearUpwind grad(h);
    div(phi,K) bounded Gauss linear;
    div(((rho*nuEff)*dev2(T(grad(U))))) Gauss linear;
}
laplacianSchemes { default Gauss linear corrected; }
interpolationSchemes { default linear; }
snGradSchemes { default corrected; }
""")
    tol = float(numerics.get("residual_tolerance", 1e-8))
    _write(case / "system/fvSolution", "dictionary", "fvSolution", f"""
solvers
{{
    p_rgh {{ solver GAMG; smoother GaussSeidel; tolerance 1e-9; relTol 0.01; maxIter 200; }}
    "(U|h)" {{ solver PBiCGStab; preconditioner DILU; tolerance 1e-12; relTol 0.05; }}
}}
PIMPLE
{{
    momentumPredictor yes;
    pRefCell 0;
    pRefValue 1e5;
    residualControl {{ p_rgh {100 * tol!r}; U {tol!r}; h {tol!r}; }}
}}
relaxationFactors
{{
    fields {{ p_rgh {float(numerics.get("relax_p", 0.7))!r}; }}
    equations {{ U {float(numerics.get("relax_U", 0.3))!r}; h {float(numerics.get("relax_h", 0.5))!r}; }}
}}
""")
    return {"cells": n * n, "g_m_per_s2": p["g"], "kappa_m2_per_s": p["kappa"], "conductivity_W_per_mK": p["k"],
            "depth_m": depth}
