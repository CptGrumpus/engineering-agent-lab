"""OpenFOAM case writer: fully developed turbulent pipe flow, RANS (study 19).

An axisymmetric wedge (angle 5 deg, one cell thick) of a pipe of diameter D, short in x (a few cells) with cyclic
inlet/outlet, so the flow is the fully developed (streamwise-periodic) state. A meanVelocityForce constraint drives it
at the bulk velocity Ub, adjusting the uniform pressure gradient it applies; the wall shear stress and that gradient
then give the friction factor two ways (in steady periodic flow, dp/dx pi R^2 = tau_w 2 pi R exactly).

Radial cells: n_radial, graded geometrically towards the wall so the first cell's height is about the requested
first_cell_yplus in wall units (estimated from the smooth-pipe friction factor at this Reynolds number).
Wall treatment: low_re (y+ about 1, the k-omega SST model resolves the viscous sublayer; nutLowReWallFunction) or
wall_function (first cell in the log layer; nutkWallFunction).

Run in WSL by models/cfd/run_pipe.sh. openfoam.org v14 (foamRun, incompressibleFluid).
"""

from __future__ import annotations

import math
from pathlib import Path

PARAMS = ("diameter_m", "reynolds_number", "kinematic_viscosity_m2_per_s", "n_radial", "first_cell_yplus",
          "wall_treatment", "turbulence_model")

HEADER = """FoamFile
{{
    format      ascii;
    class       {cls};
    object      {obj};
}}
"""
WEDGE_HALF_ANGLE_DEG = 2.5


def friction_prandtl(re: float) -> float:
    """Darcy friction factor of a smooth pipe, Prandtl's law 1/sqrt(f) = 2.0 log10(Re sqrt(f)) - 0.8 (iterated)."""
    f = 0.02
    for _ in range(100):
        f = (2.0 * math.log10(re * math.sqrt(f)) - 0.8) ** -2
    return f


def grading(params: dict) -> dict:
    """Radial grading so the first (wall) cell is about first_cell_yplus wall units high."""
    D, re, nu = float(params["diameter_m"]), float(params["reynolds_number"]), float(params["kinematic_viscosity_m2_per_s"])
    n, yp = int(params["n_radial"]), float(params["first_cell_yplus"])
    R, Ub = D / 2, re * nu / D
    u_tau = Ub * math.sqrt(friction_prandtl(re) / 8)
    h1 = yp * nu / u_tau
    # geometric progression from the wall: h1 (1 + q + ... + q^(n-1)) = R; solve for q
    lo, hi = 1.0 + 1e-12, 2.0
    if h1 * n >= R:
        q = 1.0
    else:
        for _ in range(200):
            q = (lo + hi) / 2
            if h1 * (q ** n - 1) / (q - 1) > R:
                hi = q
            else:
                lo = q
    ratio = q ** -(n - 1)  # blockMesh expansion: last (wall) cell / first (axis) cell
    return {"R_m": R, "Ub_m_per_s": Ub, "u_tau_est_m_per_s": u_tau, "h1_m": h1, "growth": q, "expansion": ratio,
            "length_m": max(2 * h1 * 4, D / 50)}


def _write(path: Path, cls: str, obj: str, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(HEADER.format(cls=cls, obj=obj) + body, encoding="utf-8", newline="\n")


def write_case(params: dict, numerics: dict, case: Path) -> dict:
    case = Path(case)
    g = grading(params)
    R, Ub, L = g["R_m"], g["Ub_m_per_s"], float(numerics.get("axial_length_m", 0.0)) or g["length_m"]
    nu = float(params["kinematic_viscosity_m2_per_s"])
    n = int(params["n_radial"])
    if numerics.get("axial_length_rule") == "geometric_mean":
        # checkMesh's aspect ratio on a wedge (a 2D mesh) is about axial length / radial height, so a fixed D/50 is
        # thousands of times the sub-micron wall cells at high Re. The geometric mean of the wall and axis cell
        # heights makes both ends' ratio sqrt(axis / wall cell). Fully developed flow has no axial gradient, so the
        # length should not change the answer (checked against the D/50 length in the case that adopts this).
        L = math.sqrt(g["h1_m"] * g["h1_m"] * g["growth"] ** (n - 1))
    a = math.radians(WEDGE_HALF_ANGLE_DEG)
    c, s = math.cos(a), math.sin(a)
    nx = int(numerics.get("axial_cells", 1))
    _write(case / "system/blockMeshDict", "dictionary", "blockMeshDict", f"""
convertToMeters 1;
vertices
(
    (0 0 0) ({L!r} 0 0)
    ({L!r} {R * c!r} {R * s!r}) (0 {R * c!r} {R * s!r})
    (0 {R * c!r} {-R * s!r}) ({L!r} {R * c!r} {-R * s!r})
);
blocks ( hex (0 1 5 4 0 1 2 3) ({nx} {n} 1) simpleGrading (1 {g['expansion']!r} 1) );
boundary
(
    inlet  {{ type cyclic; neighbourPatch outlet; faces ((0 3 4 0)); }}
    outlet {{ type cyclic; neighbourPatch inlet;  faces ((1 5 2 1)); }}
    wall   {{ type wall;  faces ((3 2 5 4)); }}
    front  {{ type wedge; faces ((0 1 2 3)); }}
    back   {{ type wedge; faces ((0 4 5 1)); }}
    axis   {{ type empty; faces ((0 1 1 0)); }}
);
""")
    iters = int(numerics.get("max_iterations", 20000))
    _write(case / "system/controlDict", "dictionary", "controlDict", f"""
solver          incompressibleFluid;
startFrom       startTime;
startTime       0;
stopAt          endTime;
endTime         {iters};
deltaT          1;
writeControl    timeStep;
writeInterval   {iters};
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
    _write(case / "system/fvConstraints", "dictionary", "fvConstraints", f"""
momentumSource
{{
    type            meanVelocityForce;
    cellZone        all;
    Ubar            ({Ub!r} 0 0);
}}
""")
    _write(case / "system/fvSchemes", "dictionary", "fvSchemes", """
ddtSchemes      { default steadyState; }
gradSchemes     { default Gauss linear; }
divSchemes
{
    default         none;
    div(phi,U)      bounded Gauss linearUpwind grad(U);
    div(phi,k)      bounded Gauss linearUpwind grad(k);
    div(phi,omega)  bounded Gauss linearUpwind grad(omega);
    div((nuEff*dev2(T(grad(U))))) Gauss linear;
}
laplacianSchemes     { default Gauss linear corrected; }
interpolationSchemes { default linear; }
snGradSchemes        { default corrected; }
wallDist             { method meshWave; }
""")
    _write(case / "system/fvSolution", "dictionary", "fvSolution", f"""
solvers
{{
    p {{ solver GAMG; smoother GaussSeidel; tolerance 1e-12; relTol 0.01; }}
    "(U|k|omega)" {{ solver smoothSolver; smoother symGaussSeidel; tolerance 1e-14; relTol 0.01; }}
}}
SIMPLE
{{
    nNonOrthogonalCorrectors 0;
    consistent      yes;
    pRefCell        0;
    pRefValue       0;
    residualControl {{ p {float(numerics["residual_p"])!r}; U {float(numerics["residual_U"])!r}; "(k|omega)" {float(numerics["residual_turb"])!r}; }}
}}
relaxationFactors
{{
    equations {{ U 0.9; "(k|omega)" 0.7; }}
}}
""")
    _write(case / "constant/momentumTransport", "dictionary", "momentumTransport", f"""
simulationType  RAS;
RAS {{ model {params["turbulence_model"]}; turbulence on; printCoeffs on; }}
""")
    _write(case / "constant/physicalProperties", "dictionary", "physicalProperties",
           f"\nviscosityModel  constant;\nnu              {nu!r};\n")
    # initial turbulence: 5 % intensity, mixing length 0.07 D
    k0 = 1.5 * (0.05 * Ub) ** 2
    om0 = math.sqrt(k0) / (0.09 ** 0.25 * 0.07 * 2 * R)
    low_re = params["wall_treatment"] == "low_re"
    nut_wall = "nutLowReWallFunction" if low_re else "nutkWallFunction"
    cyc = "    inlet  { type cyclic; }\n    outlet { type cyclic; }\n    front  { type wedge; }\n    back   { type wedge; }\n    axis   { type empty; }\n"
    for name, cls, dim, val, wall in (
            ("U", "volVectorField", "[0 1 -1 0 0 0 0]", f"({Ub!r} 0 0)", "{ type noSlip; }"),
            ("p", "volScalarField", "[0 2 -2 0 0 0 0]", "0", "{ type zeroGradient; }"),
            ("k", "volScalarField", "[0 2 -2 0 0 0 0]", repr(k0),
             "{ type fixedValue; value uniform 1e-15; }" if low_re else f"{{ type kqRWallFunction; value uniform {k0!r}; }}"),
            ("omega", "volScalarField", "[0 0 -1 0 0 0 0]", repr(om0), f"{{ type omegaWallFunction; value uniform {om0!r}; }}"),
            ("nut", "volScalarField", "[0 2 -1 0 0 0 0]", "0", f"{{ type {nut_wall}; value uniform 0; }}")):
        _write(case / "0" / name, cls, name, f"""
dimensions      {dim};
internalField   uniform {val};
boundaryField
{{
    wall   {wall}
{cyc}}}
""")
    return g | {"length_m": L, "nu_m2_per_s": nu}
