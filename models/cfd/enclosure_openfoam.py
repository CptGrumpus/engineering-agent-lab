"""Sealed electronics enclosure, 2D section (study 11, stage 3): conjugate heat transfer. The air inside (natural
convection, perfect gas, laminar) with surface radiation (fvDOM), a solid board with a solid component on it (heat
sources, conduction), the box's walls losing heat to the ambient by convection and radiation; OpenFOAM 14
`foamMultiRun` (regions fluid, board, component), steady.

Section W x H of the box; a board of length Lb and thickness tb centred at mid-height; its middle Lc is the component
(a separate solid region; same conductivity as the board here: the board's copper spreads the heat). Heat sources: the
component P_c / (Lc tb depth_box), the board P_b / ((Lb - Lc) tb depth_box) (W/m3). Board effective conductivity
`board_k_W_mK` (synthetic: FR4 with copper planes). Walls: `externalTemperature` with h_ext and Ta, emissivity eps_ext
to the ambient, and the inside radiation qr. Internal surfaces grey diffuse at eps_int. The 2D section leaves out the
box's end walls (less wall area: conservative).

Why a solid board (2026-11-24 prototype): with the board as a hollow obstacle and fixed surface fluxes the component
reached 154 C, because its 5 W could not spread into the board; the hottest-component verdict depends on that spreading.

Mesh: blockMesh, 5 x 3 blocks; the middle row's centre three blocks are the board (zones board, component, board), the
rest the zone fluid; `splitMeshRegions -cellZones` makes the regions. Uniform cell size `cell_mm`.

Run in WSL by models/cfd/run_enclosure.sh. Must not import from validation/.
"""

from __future__ import annotations

from pathlib import Path

PARAMS = ("width_mm", "height_mm", "box_depth_mm", "board_length_mm", "board_thickness_mm", "component_length_mm",
          "power_component_W", "power_board_W", "board_k_W_mK", "ambient_C", "h_ext_W_m2K", "eps_ext", "eps_int",
          "cell_mm", "n_phi", "max_iterations")
MU, CP, PR, MW = 1.8e-5, 1005.0, 0.71, 28.96


def _write(path: Path, cls: str, obj: str, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("FoamFile\n{\n    format ascii;\n    class " + cls + ";\n    object " + obj + ";\n}\n" + body,
                    encoding="utf-8", newline="\n")


def layout(params: dict) -> dict:
    W, H = float(params["width_mm"]) / 1e3, float(params["height_mm"]) / 1e3
    Lb, tb, Lc = (float(params[k]) / 1e3 for k in ("board_length_mm", "board_thickness_mm", "component_length_mm"))
    db = float(params["box_depth_mm"]) / 1e3
    return {"xs": [0.0, (W - Lb) / 2, (W - Lc) / 2, (W + Lc) / 2, (W + Lb) / 2, W],
            "ys": [0.0, (H - tb) / 2, (H + tb) / 2, H], "W": W, "H": H,
            "q_component": float(params["power_component_W"]) / (Lc * tb * db),
            "q_board": float(params["power_board_W"]) / ((Lb - Lc) * tb * db)}


SOLID_FV = """
ddtSchemes { default steadyState; }
gradSchemes { default Gauss linear; }
divSchemes { default none; }
laplacianSchemes { default Gauss linear corrected; }
interpolationSchemes { default linear; }
snGradSchemes { default corrected; }
"""
SOLID_SOL = """
solvers { e { solver PCG; preconditioner DIC; tolerance 1e-10; relTol 0.01; } }
PIMPLE { nNonOrthogonalCorrectors 0; }
relaxationFactors { equations { e 0.9; } }
"""


def write_case(params: dict, numerics: dict, case: Path) -> dict:
    lay = layout(params)
    xs, ys = lay["xs"], lay["ys"]
    h = float(params["cell_mm"]) / 1e3
    depth = h
    n = lambda a, b: max(1, round((b - a) / h))  # noqa: E731
    vid, verts = {}, []
    for zl, z in ((0, 0.0), (1, depth)):
        for j, y in enumerate(ys):
            for i, x in enumerate(xs):
                vid[(i, j, zl)] = len(verts)
                verts.append((x, y, z))
    zone = {(1, 1): "board", (2, 1): "component", (3, 1): "board"}
    blocks = []
    for j in range(3):
        for i in range(5):
            v = [vid[(i, j, 0)], vid[(i + 1, j, 0)], vid[(i + 1, j + 1, 0)], vid[(i, j + 1, 0)],
                 vid[(i, j, 1)], vid[(i + 1, j, 1)], vid[(i + 1, j + 1, 1)], vid[(i, j + 1, 1)]]
            blocks.append(f"    hex ({' '.join(map(str, v))}) {zone.get((i, j), 'fluid')} "
                          f"({n(xs[i], xs[i + 1])} {n(ys[j], ys[j + 1])} 1) simpleGrading (1 1 1)")

    def face(i0, j0, i1, j1):
        return f"({vid[(i0, j0, 0)]} {vid[(i1, j1, 0)]} {vid[(i1, j1, 1)]} {vid[(i0, j0, 1)]})"
    walls = [face(i, 0, i + 1, 0) for i in range(5)] + [face(5, j, 5, j + 1) for j in range(3)] \
        + [face(i + 1, 3, i, 3) for i in range(5)] + [face(0, j + 1, 0, j) for j in range(3)]
    fb = []
    for j in range(3):
        for i in range(5):
            fb.append(f"({vid[(i, j, 0)]} {vid[(i, j + 1, 0)]} {vid[(i + 1, j + 1, 0)]} {vid[(i + 1, j, 0)]})")
            fb.append(f"({vid[(i, j, 1)]} {vid[(i + 1, j, 1)]} {vid[(i + 1, j + 1, 1)]} {vid[(i, j + 1, 1)]})")
    _write(case / "system/blockMeshDict", "dictionary", "blockMeshDict",
           "\nconvertToMeters 1;\nvertices\n(\n" + "\n".join(f"    ({x!r} {y!r} {z!r})" for x, y, z in verts) + "\n);\n"
           + "blocks\n(\n" + "\n".join(blocks) + "\n);\nedges ();\nboundary\n(\n"
           + f"    walls {{ type wall; faces ({' '.join(walls)}); }}\n"
           + f"    frontAndBack {{ type empty; faces ({' '.join(fb)}); }}\n);\n")
    Ta = float(params["ambient_C"]) + 273.15
    T0 = Ta + 20.0
    it = int(params["max_iterations"])
    _write(case / "system/controlDict", "dictionary", "controlDict", f"""
regionSolvers {{ fluid fluid; board solid; component solid; }}
startFrom startTime;
startTime 0;
stopAt endTime;
endTime {it};
deltaT 1;
writeControl timeStep;
writeInterval {it};
writeFormat ascii;
writePrecision 12;
timeFormat general;
timePrecision 8;
runTimeModifiable false;
""")
    _write(case / "system/fvSolution", "dictionary", "fvSolution", "\nPIMPLE { nOuterCorrectors 1; }\n")
    # ---- fluid
    _write(case / "constant/fluid/physicalProperties", "dictionary", "physicalProperties", f"""
thermoType {{ type heRhoThermo; mixture pureMixture; transport const; thermo hConst; equationOfState perfectGas;
             specie specie; energy sensibleEnthalpy; }}
mixture
{{
    specie {{ molWeight {MW!r}; }}
    thermodynamics {{ Cp {CP!r}; hf 0; }}
    transport {{ mu {MU!r}; Pr {PR!r}; }}
}}
""")
    _write(case / "constant/fluid/g", "uniformDimensionedVectorField", "g", "\ndimensions [0 1 -2 0 0 0 0];\nvalue (0 -9.81 0);\n")
    _write(case / "constant/fluid/pRef", "uniformDimensionedScalarField", "pRef", "\ndimensions [1 -1 -2 0 0 0 0];\nvalue 1e5;\n")
    _write(case / "constant/fluid/momentumTransport", "dictionary", "momentumTransport", "\nsimulationType laminar;\n")
    _write(case / "constant/fluid/fvModels", "dictionary", "fvModels", '\nradiation { type radiation; libs ("libradiationModels.so"); }\n')
    _write(case / "constant/fluid/radiationProperties", "dictionary", "radiationProperties", f"""
radiationModel  fvDOM;
fvDOM {{ nPhi {int(params['n_phi'])}; nTheta 0; tolerance 1e-5; maxIter 20; }}
solverFreq 5;
absorptionEmissionModel constant;
constant {{ absorptivity 0; emissivity 0; E 0; }}
scatterModel none;
sootModel none;
""")
    fl = lambda wall, iface: (f"    walls {{ {wall} }}\n    \".*_to_.*\" {{ {iface} }}\n"  # noqa: E731
                              "    frontAndBack { type empty; }\n")
    _write(case / "0/fluid/U", "volVectorField", "U", "\ndimensions [0 1 -1 0 0 0 0];\ninternalField uniform (0 0 0);\n"
           "boundaryField\n{\n" + fl("type noSlip;", "type noSlip;") + "}\n")
    _write(case / "0/fluid/T", "volScalarField", "T", f"\ndimensions [0 0 0 1 0 0 0];\ninternalField uniform {T0!r};\n"
           "boundaryField\n{\n" + fl(f"type externalTemperature; Ta constant {Ta!r}; h uniform {float(params['h_ext_W_m2K'])!r}; "
                                    f"emissivity {float(params['eps_ext'])!r}; qr qr; relaxation 0.5; value uniform {T0!r};",
                                    f"type coupledTemperature; qr qr; value uniform {T0!r};") + "}\n")
    _write(case / "0/fluid/p", "volScalarField", "p", "\ndimensions [1 -1 -2 0 0 0 0];\ninternalField uniform 1e5;\n"
           "boundaryField\n{\n" + fl("type calculated; value $internalField;", "type calculated; value $internalField;") + "}\n")
    _write(case / "0/fluid/p_rgh", "volScalarField", "p_rgh", "\ndimensions [1 -1 -2 0 0 0 0];\ninternalField uniform 0;\n"
           "boundaryField\n{\n" + fl("type fixedFluxPressure; value $internalField;", "type fixedFluxPressure; value $internalField;") + "}\n")
    e = float(params["eps_int"])
    rad = f"type greyDiffusiveRadiation; emissivityMode lookup; emissivity uniform {e!r}; value uniform 0;"
    _write(case / "0/fluid/IDefault", "volScalarField", "IDefault", "\ndimensions [1 0 -3 0 0 0 0];\ninternalField uniform 0;\n"
           "boundaryField\n{\n" + fl(rad, rad) + "}\n")
    _write(case / "0/fluid/G", "volScalarField", "G", "\ndimensions [1 0 -3 0 0 0 0];\ninternalField uniform 0;\n"
           "boundaryField\n{\n" + fl("type calculated; value uniform 0;", "type calculated; value uniform 0;") + "}\n")
    _write(case / "system/fluid/fvSchemes", "dictionary", "fvSchemes", """
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
    _write(case / "system/fluid/fvSolution", "dictionary", "fvSolution", """
solvers
{
    "(rho|rhoFinal)" { solver diagonal; }
    p_rgh { solver GAMG; smoother GaussSeidel; tolerance 1e-9; relTol 0.01; maxIter 200; }
    "(U|h)" { solver PBiCGStab; preconditioner DILU; tolerance 1e-12; relTol 0.05; }
    Ii { solver GAMG; smoother symGaussSeidel; tolerance 1e-8; relTol 0; maxIter 100; }
}
PIMPLE { momentumPredictor yes; nNonOrthogonalCorrectors 0; pRefCell 0; pRefValue 0; }
relaxationFactors { fields { p_rgh 0.7; } equations { U 0.3; h 0.5; } }
""")
    # ---- solids
    k = float(params["board_k_W_mK"])
    for reg, q in (("board", lay["q_board"]), ("component", lay["q_component"])):
        _write(case / f"constant/{reg}/physicalProperties", "dictionary", "physicalProperties",
               f"\nthermoType constSolidThermo;\nrho {{ type uniform; value 1900; }}\nCv {{ type uniform; value 1100; }}\n"
               f"kappa {{ type uniform; value {k!r}; }}\n")
        _write(case / f"constant/{reg}/fvModels", "dictionary", "fvModels",
               f"\nheat {{ type heatSource; cellZone all; q {q!r}; }}\n")
        _write(case / f"0/{reg}/T", "volScalarField", "T", f"\ndimensions [0 0 0 1 0 0 0];\ninternalField uniform {T0 + 10!r};\n"
               "boundaryField\n{\n    \".*_to_fluid\" { type coupledTemperature; qrNbr qr; value $internalField; }\n"
               "    \".*_to_.*\" { type coupledTemperature; value $internalField; }\n    frontAndBack { type empty; }\n}\n")
        _write(case / f"system/{reg}/fvSchemes", "dictionary", "fvSchemes", SOLID_FV)
        _write(case / f"system/{reg}/fvSolution", "dictionary", "fvSolution", SOLID_SOL)
    end = numerics.get("transient_end_s")
    if end is not None:
        # transient to a settled state (the steady coupled solve diverged after 9,000 iterations, 2026-11-24): Euler in
        # every region, adjustable time step at Courant 0.5, no under-relaxation, ten writes to see the settling
        end = float(end)
        for f in [case / "system/fluid/fvSchemes"] + [case / f"system/{r}/fvSchemes" for r in ("board", "component")]:
            f.write_text(f.read_text().replace("default steadyState;", "default Euler;"), encoding="utf-8", newline="\n")
        cd = case / "system/controlDict"
        cd.write_text(cd.read_text().replace(f"endTime {it};", f"endTime {end!r};").replace("deltaT 1;", "deltaT 0.001;")
                      .replace("writeControl timeStep;", "writeControl adjustableRunTime;")
                      .replace(f"writeInterval {it};", f"writeInterval {end / 10!r};\nadjustTimeStep yes;\nmaxCo 0.5;\nmaxDi 50;"),
                      encoding="utf-8", newline="\n")
        ff = case / "system/fluid/fvSolution"
        ff.write_text(ff.read_text().replace("PIMPLE { momentumPredictor yes; nNonOrthogonalCorrectors 0;",
                                             "PIMPLE { momentumPredictor yes; nOuterCorrectors 1; nCorrectors 2; nNonOrthogonalCorrectors 0;")
                      .replace("relaxationFactors { fields { p_rgh 0.7; } equations { U 0.3; h 0.5; } }",
                               'relaxationFactors { equations { ".*" 1; } }')
                      .replace('"(U|h)" { solver PBiCGStab; preconditioner DILU; tolerance 1e-12; relTol 0.05; }',
                               '"(U|h)" { solver PBiCGStab; preconditioner DILU; tolerance 1e-10; relTol 0.05; }\n'
                               '    "(U|h)Final" { solver PBiCGStab; preconditioner DILU; tolerance 1e-10; relTol 0; }\n'
                               '    p_rghFinal { solver GAMG; smoother GaussSeidel; tolerance 1e-9; relTol 0; maxIter 200; }'), encoding="utf-8", newline="\n")
        for r in ("board", "component"):
            fs = case / f"system/{r}/fvSolution"
            fs.write_text(fs.read_text().replace("relaxationFactors { equations { e 0.9; } }", 'relaxationFactors { equations { ".*" 1; } }')
                          .replace("solvers { e { solver PCG; preconditioner DIC; tolerance 1e-10; relTol 0.01; } }",
                                   "solvers { e { solver PCG; preconditioner DIC; tolerance 1e-10; relTol 0.01; }\n"
                                   "          eFinal { solver PCG; preconditioner DIC; tolerance 1e-10; relTol 0; } }"),
                          encoding="utf-8", newline="\n")
    return {"q_component_W_m3": lay["q_component"], "q_board_W_m3": lay["q_board"]}
