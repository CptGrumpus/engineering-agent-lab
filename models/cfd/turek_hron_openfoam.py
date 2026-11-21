"""Turek-Hron fluid stage (CFD1, CFD2; and Schaefer-Turek 2D-1 without the flag): Gmsh .geo and
an OpenFOAM 14 case for steady laminar flow round the cylinder and its rigid flag.

Geometry (m, the benchmark's own units): channel 2.5 x 0.41; cylinder centre (0.2, 0.2), radius 0.05;
flag y in [0.19, 0.21] from the cylinder to x = 0.2 + r + flag_length (0.6 for the benchmark), or no
flag when flag_length_m = 0. One cell deep in z (depth 0.01 m, `empty` front and back): forces are
divided by the depth to give N per metre, as the benchmark reports them.

Mesh: Gmsh OpenCASCADE booleans, quad-dominant (frontal-Delaunay for quads, recombined; the odd
triangle extrudes to a prism), size h at the body growing linearly to 6 h at 0.3 m from it, extruded
one layer and written as MSH 2.2 for gmshToFoam.

Flow: incompressibleFluid, steady SIMPLE (consistent), second-order linearUpwind for momentum,
one non-orthogonal corrector, residual control; inlet fixedProfile with the benchmark's parabola
(peak 1.5 U_mean) sampled at the face centres; outlet p = 0, U zero gradient; no slip on the channel
walls and the body. Forces on the body by the `forces` function object (rho = rhoInf).
"""

from __future__ import annotations

from pathlib import Path

PARAMS = ("mean_velocity_m_per_s", "kinematic_viscosity_m2_per_s", "density_kg_per_m3", "flag_length_m",
          "cell_size_m")
CHANNEL_L, CHANNEL_H, XC, YC, R, FLAG_H, DEPTH = 2.5, 0.41, 0.2, 0.2, 0.05, 0.02, 0.01
HEADER = "FoamFile\n{{\n    format      ascii;\n    class       {cls};\n    object      {obj};\n}}\n"


def write_geo(params: dict, path: Path) -> None:
    h = float(params["cell_size_m"])
    flag = float(params["flag_length_m"])
    body = "Disk(2) = {%r, %r, 0, %r};\n" % (XC, YC, R)
    if flag > 0:
        x_end = XC + R + flag
        body += ("Rectangle(3) = {%r, %r, 0, %r, %r};\n" % (XC, YC - FLAG_H / 2, x_end - XC, FLAG_H)
                 + "BooleanUnion{ Surface{2}; Delete; }{ Surface{3}; Delete; }\n")
    x_hi = XC + R + max(flag, 0.0)
    text = f"""SetFactory("OpenCASCADE");
Rectangle(1) = {{0, 0, 0, {CHANNEL_L!r}, {CHANNEL_H!r}}};
{body}BooleanDifference{{ Surface{{1}}; Delete; }}{{ Surface{{2}}; Delete; }}
eps = 1e-6;
d = {DEPTH!r};
body() = Curve In BoundingBox{{{XC - R}-eps, {YC - R}-eps, -eps, {x_hi}+eps, {YC + R}+eps, eps}};
Field[1] = Distance; Field[1].CurvesList = {{body()}}; Field[1].Sampling = 400;
Field[2] = Threshold; Field[2].InField = 1; Field[2].SizeMin = {h!r}; Field[2].SizeMax = {6 * h!r};
Field[2].DistMin = 0.0; Field[2].DistMax = 0.3;
Background Field = 2;
Mesh.MeshSizeExtendFromBoundary = 0; Mesh.MeshSizeFromPoints = 0; Mesh.MeshSizeFromCurvature = 0;
Mesh.Algorithm = 8; Recombine Surface{{1}};
ex[] = Extrude{{0, 0, d}}{{ Surface{{1}}; Layers{{1}}; Recombine; }};
Physical Surface("inlet") = Surface In BoundingBox{{-eps, -eps, -eps, eps, {CHANNEL_H}+eps, d+eps}};
Physical Surface("outlet") = Surface In BoundingBox{{{CHANNEL_L}-eps, -eps, -eps, {CHANNEL_L}+eps, {CHANNEL_H}+eps, d+eps}};
Physical Surface("walls") = {{Surface In BoundingBox{{-eps, -eps, -eps, {CHANNEL_L}+eps, eps, d+eps}}, Surface In BoundingBox{{-eps, {CHANNEL_H}-eps, -eps, {CHANNEL_L}+eps, {CHANNEL_H}+eps, d+eps}}}};
Physical Surface("body") = Surface In BoundingBox{{{XC - R}-eps, {YC - R}-eps, -eps, {x_hi}+eps, {YC + R}+eps, d+eps}};
Physical Surface("frontAndBack") = {{Surface In BoundingBox{{-eps, -eps, -eps, {CHANNEL_L}+eps, {CHANNEL_H}+eps, eps}}, Surface In BoundingBox{{-eps, -eps, d-eps, {CHANNEL_L}+eps, {CHANNEL_H}+eps, d+eps}}}};
Physical Volume("fluid") = {{ex[1]}};
"""
    path.write_text(text, encoding="utf-8", newline="\n")


def _w(case: Path, rel: str, cls: str, obj: str, body: str) -> None:
    p = case / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(HEADER.format(cls=cls, obj=obj) + body, encoding="utf-8", newline="\n")


def write_case(params: dict, numerics: dict, case: Path) -> dict:
    U = float(params["mean_velocity_m_per_s"])
    nu = float(params["kinematic_viscosity_m2_per_s"])
    rho = float(params["density_kg_per_m3"])
    n_iter = int(numerics["max_iterations"])
    res_p, res_U = float(numerics["residual_p"]), float(numerics["residual_U"])
    _w(case, "system/controlDict", "dictionary", "controlDict", f"""
solver          incompressibleFluid;
startFrom       startTime;
startTime       0;
stopAt          endTime;
endTime         {n_iter};
deltaT          1;
writeControl    timeStep;
writeInterval   {n_iter};
writeFormat     ascii;
writePrecision  12;
timeFormat      general;
runTimeModifiable false;
functions
{{
    forces
    {{
        type            forces;
        libs            ("libforces.so");
        writeControl    timeStep;
        writeInterval   1;
        patches         (body);
        rho             rhoInf;
        rhoInf          {rho!r};
        CofR            ({XC!r} {YC!r} 0);
        log             false;
    }}
}}
""")
    _w(case, "system/fvSchemes", "dictionary", "fvSchemes", """
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
    _w(case, "system/fvSolution", "dictionary", "fvSolution", f"""
solvers
{{
    p {{ solver GAMG; smoother GaussSeidel; tolerance 1e-12; relTol 0.01; }}
    U {{ solver smoothSolver; smoother symGaussSeidel; tolerance 1e-14; relTol 0.01; }}
}}
SIMPLE
{{
    nNonOrthogonalCorrectors 1;
    consistent      yes;
    residualControl {{ p {res_p!r}; U {res_U!r}; }}
}}
relaxationFactors {{ equations {{ U 0.9; }} }}
""")
    _w(case, "constant/momentumTransport", "dictionary", "momentumTransport", "\nsimulationType laminar;\n")
    _w(case, "constant/physicalProperties", "dictionary", "physicalProperties",
       f"\nviscosityModel  constant;\nnu              {nu!r};\n")
    flow = U * CHANNEL_H * DEPTH
    # the benchmark's parabola, U(y) = 1.5 U_mean 4 y (H - y) / H^2, as a fine table along y, evaluated
    # at each inlet face centre. flowRateInletVelocity's laminarBL profile is not used: it normalises
    # the wall distance by the largest face distance on the patch, not by H/2, which flattened the
    # profile by 1.6 % at mid-channel on the coarsest mesh
    n_tab = int(numerics.get("inlet_table_points", 4001))
    ys = [CHANNEL_H * k / (n_tab - 1) for k in range(n_tab)]
    table = " ".join(f"({y!r} ({1.5 * U * 4 * y * (CHANNEL_H - y) / CHANNEL_H**2!r} 0 0))" for y in ys)
    _w(case, "0/U", "volVectorField", "U", f"""
dimensions      [0 1 -1 0 0 0 0];
internalField   uniform (0 0 0);
boundaryField
{{
    inlet        {{ type fixedProfile; direction (0 1 0); origin 0; profile table ({table}); value uniform (0 0 0); }}
    outlet       {{ type zeroGradient; }}
    walls        {{ type noSlip; }}
    body         {{ type noSlip; }}
    frontAndBack {{ type empty; }}
}}
""")
    _w(case, "0/p", "volScalarField", "p", """
dimensions      [0 2 -2 0 0 0 0];
internalField   uniform 0;
boundaryField
{
    inlet        { type zeroGradient; }
    outlet       { type fixedValue; value uniform 0; }
    walls        { type zeroGradient; }
    body         { type zeroGradient; }
    frontAndBack { type empty; }
}
""")
    return {"depth_m": DEPTH, "flow_m3_per_s": flow}
