"""Radiation between two long concentric cylinders through a transparent gas (study 11, stage 2), OpenFOAM 14 fluid
solver with the fvDOM radiation model, steady, no gravity (pure conduction plus surface radiation).

Constant density (rhoConst): with OpenFOAM's Boussinesq density over a 100 K span the conducted temperature profile
missed the exact log profile by up to 3 K (the density enters the energy equation's diffusion term), with rhoConst it
matches to about 0.15 K (prototype 2026-11-24). No gravity, so no buoyancy is needed.

The 2D annulus r1 < r < r2, inner wall at T1, outer at T2, grey diffuse walls of emissivity eps1 / eps2, the gas
transparent (absorptivity and emissivity 0). With no flow and a transparent gas, conduction and radiation decouple:
the conducted heat is the exact 2 pi k (T1 - T2) / ln(r2 / r1) per metre and the radiated heat the two-surface
exchange; both are independent references (validation/natural_convection.py).

Mesh: blockMesh, a full annulus in four blocks with arc edges, one cell deep (2D, empty front and back), n_r cells
radially and n_t per quarter. fvDOM: n_phi azimuthal directions per quarter (2D: in-plane directions only).

Run in WSL by models/cfd/run_annulus.sh. Must not import from validation/.
"""

from __future__ import annotations

import math
from pathlib import Path

PARAMS = ("r_inner_m", "r_outer_m", "T_inner_K", "T_outer_K", "eps_inner", "eps_outer", "cells_radial",
          "cells_per_quarter", "n_phi", "max_iterations")
RHO0, T0, BETA, MU, CP, PR = 1.0, 300.0, 1.0 / 300.0, 1.8e-5, 1000.0, 0.71


def conductivity() -> float:
    return MU * CP / PR


def _write(path: Path, cls: str, obj: str, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("FoamFile\n{\n    format ascii;\n    class " + cls + ";\n    object " + obj + ";\n}\n" + body,
                    encoding="utf-8", newline="\n")


def write_case(params: dict, numerics: dict, case: Path) -> dict:
    r1, r2 = float(params["r_inner_m"]), float(params["r_outer_m"])
    nr, nt = int(params["cells_radial"]), int(params["cells_per_quarter"])
    depth = 2 * math.pi * r1 / (4 * nt)
    vs, edges = [], []
    for z in (0.0, depth):
        for r in (r1, r2):
            for k in range(4):
                a = k * math.pi / 2
                vs.append((r * math.cos(a), r * math.sin(a), z))
    # vertex index: z-layer (0/1) * 8 + radius (0 inner / 1 outer) * 4 + quarter k
    vid = lambda zl, ri, k: zl * 8 + ri * 4 + (k % 4)  # noqa: E731
    blocks = []
    for k in range(4):
        blocks.append(f"    hex ({vid(0,0,k)} {vid(0,1,k)} {vid(0,1,k+1)} {vid(0,0,k+1)} {vid(1,0,k)} {vid(1,1,k)} "
                      f"{vid(1,1,k+1)} {vid(1,0,k+1)}) ({nr} {nt} 1) simpleGrading (1 1 1)")
        am = k * math.pi / 2 + math.pi / 4
        for zl, z in ((0, 0.0), (1, depth)):
            for ri, r in ((0, r1), (1, r2)):
                edges.append(f"    arc {vid(zl,ri,k)} {vid(zl,ri,k+1)} ({r * math.cos(am)!r} {r * math.sin(am)!r} {z!r})")
    faces_in = " ".join(f"({vid(0,0,k)} {vid(0,0,k+1)} {vid(1,0,k+1)} {vid(1,0,k)})" for k in range(4))
    faces_out = " ".join(f"({vid(0,1,k)} {vid(1,1,k)} {vid(1,1,k+1)} {vid(0,1,k+1)})" for k in range(4))
    faces_fb = " ".join(f"({vid(0,0,k)} {vid(0,0,k+1)} {vid(0,1,k+1)} {vid(0,1,k)}) "
                        f"({vid(1,0,k)} {vid(1,1,k)} {vid(1,1,k+1)} {vid(1,0,k+1)})" for k in range(4))
    _write(case / "system/blockMeshDict", "dictionary", "blockMeshDict",
           "\nconvertToMeters 1;\nvertices\n(\n" + "\n".join(f"    ({x!r} {y!r} {z!r})" for x, y, z in vs) + "\n);\n"
           + "blocks\n(\n" + "\n".join(blocks) + "\n);\nedges\n(\n" + "\n".join(edges) + "\n);\n"
           + f"boundary\n(\n    inner {{ type wall; faces ({faces_in}); }}\n    outer {{ type wall; faces ({faces_out}); }}\n"
           + f"    frontAndBack {{ type empty; faces ({faces_fb}); }}\n);\n")
    _write(case / "constant/physicalProperties", "dictionary", "physicalProperties", f"""
thermoType {{ type heRhoThermo; mixture pureMixture; transport const; thermo hConst; equationOfState rhoConst;
             specie specie; energy sensibleEnthalpy; }}
mixture
{{
    specie {{ molWeight 28.9; }}
    equationOfState {{ rho {RHO0!r}; }}
    thermodynamics {{ Cp {CP!r}; hf 0; }}
    transport {{ mu {MU!r}; Pr {PR!r}; }}
}}
""")
    _write(case / "constant/g", "uniformDimensionedVectorField", "g", "\ndimensions [0 1 -2 0 0 0 0];\nvalue (0 0 0);\n")
    _write(case / "constant/momentumTransport", "dictionary", "momentumTransport", "\nsimulationType laminar;\n")
    # radiation enters the fluid solver as an fvModel (OpenFOAM 11 and later)
    _write(case / "constant/fvModels", "dictionary", "fvModels",
           '\nradiation { type radiation; libs ("libradiationModels.so"); }\n')
    _write(case / "constant/radiationProperties", "dictionary", "radiationProperties", f"""
radiationModel  fvDOM;
fvDOM {{ nPhi {int(params['n_phi'])}; nTheta 0; tolerance 1e-6; maxIter 50; }}
solverFreq 1;
absorptionEmissionModel constant;
constant {{ absorptivity 0; emissivity 0; E 0; }}
scatterModel none;
sootModel none;
""")
    T1, T2 = float(params["T_inner_K"]), float(params["T_outer_K"])
    walls = lambda f: f"    inner {{ {f('inner')} }}\n    outer {{ {f('outer')} }}\n    frontAndBack {{ type empty; }}\n"  # noqa: E731
    _write(case / "0/U", "volVectorField", "U", "\ndimensions [0 1 -1 0 0 0 0];\ninternalField uniform (0 0 0);\n"
           "boundaryField\n{\n" + walls(lambda p: "type noSlip;") + "}\n")
    _write(case / "0/T", "volScalarField", "T", f"\ndimensions [0 0 0 1 0 0 0];\ninternalField uniform {(T1 + T2) / 2!r};\n"
           "boundaryField\n{\n" + walls(lambda p: f"type fixedValue; value uniform {T1 if p == 'inner' else T2!r};") + "}\n")
    calc = lambda p: "type calculated; value $internalField;"  # noqa: E731
    _write(case / "0/p", "volScalarField", "p", "\ndimensions [1 -1 -2 0 0 0 0];\ninternalField uniform 1e5;\n"
           "boundaryField\n{\n" + walls(calc) + "}\n")
    _write(case / "0/p_rgh", "volScalarField", "p_rgh", "\ndimensions [1 -1 -2 0 0 0 0];\ninternalField uniform 1e5;\n"
           "boundaryField\n{\n" + walls(lambda p: "type fixedFluxPressure; value $internalField;") + "}\n")
    eps = {"inner": float(params["eps_inner"]), "outer": float(params["eps_outer"])}
    _write(case / "0/IDefault", "volScalarField", "IDefault", "\ndimensions [1 0 -3 0 0 0 0];\ninternalField uniform 0;\n"
           "boundaryField\n{\n" + walls(lambda p: f"type greyDiffusiveRadiation; emissivityMode lookup; "
                                         f"emissivity uniform {eps[p]!r}; value uniform 0;") + "}\n")
    _write(case / "0/G", "volScalarField", "G", "\ndimensions [1 0 -3 0 0 0 0];\ninternalField uniform 0;\n"
           "boundaryField\n{\n" + walls(lambda p: "type calculated; value uniform 0;") + "}\n")
    n_it = int(params["max_iterations"])
    _write(case / "system/controlDict", "dictionary", "controlDict", f"""
solver fluid;
startFrom startTime;
startTime 0;
stopAt endTime;
endTime {n_it};
deltaT 1;
writeControl timeStep;
writeInterval {n_it};
writeFormat ascii;
writePrecision 12;
timeFormat general;
timePrecision 8;
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
    div(Ji,Ii_h) bounded Gauss linearUpwind grad(Ii_h);
}
laplacianSchemes { default Gauss linear corrected; }
interpolationSchemes { default linear; }
snGradSchemes { default corrected; }
""")
    _write(case / "system/fvSolution", "dictionary", "fvSolution", """
solvers
{
    p_rgh { solver GAMG; smoother GaussSeidel; tolerance 1e-9; relTol 0.01; maxIter 200; }
    "(U|h)" { solver PBiCGStab; preconditioner DILU; tolerance 1e-12; relTol 0.05; }
    Ii { solver GAMG; smoother symGaussSeidel; tolerance 1e-8; relTol 0; maxIter 100; }
}
PIMPLE { momentumPredictor no; pRefCell 0; pRefValue 1e5; residualControl { h 1e-9; } }
relaxationFactors { fields { p_rgh 0.7; } equations { U 0.3; h 0.7; } }
""")
    return {"cells": 4 * nr * nt, "depth_m": depth, "conductivity_W_per_mK": conductivity()}
