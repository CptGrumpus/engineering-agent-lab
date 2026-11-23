"""Turek-Hron FSI (study 6, coupled stage): OpenFOAM v2512 (fluid) + CalculiX (solid) through preCICE.

Writes one case folder:
  precice-config.xml        parallel-implicit coupling, IQN-ILS, Force (fluid -> solid, conservative)
                            and Displacement (solid -> fluid, consistent), both RBF; watch point at A
  fluid/                    Gmsh .geo (cylinder and flag as separate patches) and the OpenFOAM v2512
                            dictionaries: pimpleFoam, displacementLaplacian mesh motion, the preCICE
                            adapter function object, forces on cylinder + flag
  solid/flag.inp, config.yml  the verified flag of studies/flag_csm.py, in SI units, one C3D8I layer
                            as thick as the fluid is deep, NLGEOM *DYNAMIC; Nsurface = nodes on the
                            wetted faces (top, bottom, tip; not the clamped root), Nfix = nodes on
                            the cylinder arc

Units: m, kg, s, N, Pa throughout (the fluid solver's own units; preCICE exchanges forces in N).
Inflow: the benchmark's parabola 1.5 U 4 y (H - y) / H^2 with its start-up ramp (1 - cos(pi t / 2)) / 2
for t < 2 s (codedFixedValue). No gravity in the FSI tests.
Steady cases (FSI1): numerical damping in the solid (ALPHA < 0) only changes how fast the flag settles,
not where; the periodic cases (FSI2, FSI3) must use ALPHA = 0.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

PARAMS = ("solid_density_kg_per_m3", "shear_modulus_Pa", "poisson_ratio", "fluid_density_kg_per_m3",
          "kinematic_viscosity_m2_per_s", "mean_velocity_m_per_s", "fluid_cell_size_m", "solid_element_size_mm",
          "time_step_s", "end_time_s")
CH_L, CH_H, XC, YC, R, FLAG_L, FLAG_H, DEPTH = 2.5, 0.41, 0.2, 0.2, 0.05, 0.35, 0.02, 0.01
HEADER = "FoamFile\n{{\n    version 2.0;\n    format      ascii;\n    class       {cls};\n    object      {obj};\n}}\n"


def _flag_module():
    # a run saves its model sources flat in inputs/, so look beside this file first (harness rerun), then in
    # the repo's models/fea/
    here = Path(__file__).resolve().parent
    p = here / "flag_ccx.py" if (here / "flag_ccx.py").exists() else here.parent / "fea" / "flag_ccx.py"
    spec = importlib.util.spec_from_file_location("flag_ccx_for_fsi", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _w(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def _foam(path: Path, cls: str, obj: str, body: str) -> None:
    _w(path, HEADER.format(cls=cls, obj=obj) + body)


# ------------------------------------------------------------------ fluid

def write_geo(params: dict, path: Path) -> None:
    h = float(params["fluid_cell_size_m"])
    x_end = XC + R + FLAG_L
    x_root = XC + (R * R - (FLAG_H / 2) ** 2) ** 0.5           # where the flag's faces meet the arc
    _w(path, f"""SetFactory("OpenCASCADE");
Rectangle(1) = {{0, 0, 0, {CH_L!r}, {CH_H!r}}};
Disk(2) = {{{XC!r}, {YC!r}, 0, {R!r}}};
Rectangle(3) = {{{XC!r}, {YC - FLAG_H / 2!r}, 0, {x_end - XC!r}, {FLAG_H!r}}};
BooleanUnion{{ Surface{{2}}; Delete; }}{{ Surface{{3}}; Delete; }}
BooleanDifference{{ Surface{{1}}; Delete; }}{{ Surface{{2}}; Delete; }}
eps = 1e-6;
d = {DEPTH!r};
body() = Curve In BoundingBox{{{XC - R}-eps, {YC - R}-eps, -eps, {x_end}+eps, {YC + R}+eps, eps}};
Field[1] = Distance; Field[1].CurvesList = {{body()}}; Field[1].Sampling = 400;
Field[2] = Threshold; Field[2].InField = 1; Field[2].SizeMin = {h!r}; Field[2].SizeMax = {6 * h!r};
Field[2].DistMin = 0.0; Field[2].DistMax = 0.3;
Background Field = 2;
Mesh.MeshSizeExtendFromBoundary = 0; Mesh.MeshSizeFromPoints = 0; Mesh.MeshSizeFromCurvature = 0;
Mesh.Algorithm = 8; Recombine Surface{{1}};
ex[] = Extrude{{0, 0, d}}{{ Surface{{1}}; Layers{{1}}; Recombine; }};
Physical Surface("inlet") = Surface In BoundingBox{{-eps, -eps, -eps, eps, {CH_H}+eps, d+eps}};
Physical Surface("outlet") = Surface In BoundingBox{{{CH_L}-eps, -eps, -eps, {CH_L}+eps, {CH_H}+eps, d+eps}};
Physical Surface("walls") = {{Surface In BoundingBox{{-eps, -eps, -eps, {CH_L}+eps, eps, d+eps}}, Surface In BoundingBox{{-eps, {CH_H}-eps, -eps, {CH_L}+eps, {CH_H}+eps, d+eps}}}};
Physical Surface("flag") = Surface In BoundingBox{{{x_root}-1e-4, {YC - FLAG_H / 2}-eps, -eps, {x_end}+eps, {YC + FLAG_H / 2}+eps, d+eps}};
Physical Surface("cylinder") = Surface In BoundingBox{{{XC - R}-eps, {YC - R}-eps, -eps, {x_root}+eps, {YC + R}+eps, d+eps}};
Physical Surface("frontAndBack") = {{Surface In BoundingBox{{-eps, -eps, -eps, {CH_L}+eps, {CH_H}+eps, eps}}, Surface In BoundingBox{{-eps, -eps, d-eps, {CH_L}+eps, {CH_H}+eps, d+eps}}}};
Physical Volume("fluid") = {{ex[1]}};
""")


def write_fluid(params: dict, numerics: dict, d: Path) -> None:
    U, nu = float(params["mean_velocity_m_per_s"]), float(params["kinematic_viscosity_m2_per_s"])
    rho = float(params["fluid_density_kg_per_m3"])
    dt, t_end = float(params["time_step_s"]), float(params["end_time_s"])
    write_every = float(numerics.get("write_interval_s", 1.0))
    if abs(t_end / write_every - round(t_end / write_every)) > 1e-9:
        # OpenFOAM writes only at whole write intervals: the final state must be one of them
        raise ValueError(f"end time {t_end} is not a whole number of write intervals ({write_every})")
    _foam(d / "system/controlDict", "dictionary", "controlDict", f"""
application     pimpleFoam;
startFrom       startTime;
startTime       0;
stopAt          endTime;
endTime         {t_end!r};
deltaT          {dt!r};
writeControl    adjustableRunTime;
writeInterval   {write_every!r};
writeFormat     ascii;
writePrecision  10;
timeFormat      general;
timePrecision   8;
libs ("libpreciceAdapterFunctionObject.so");
functions
{{
    preCICE_Adapter
    {{
        type preciceAdapterFunctionObject;
        errors strict;
    }}
    forces
    {{
        type            forces;
        libs            ("libforces.so");
        writeControl    timeStep;
        writeInterval   1;
        patches         (cylinder flag);
        rho             rhoInf;
        rhoInf          {rho!r};
        CofR            ({XC!r} {YC!r} 0);
        log             false;
    }}
    forcesFlag
    {{
        type            forces;
        libs            ("libforces.so");
        writeControl    timeStep;
        writeInterval   1;
        patches         (flag);
        rho             rhoInf;
        rhoInf          {rho!r};
        CofR            ({XC!r} {YC!r} 0);
        log             false;
    }}
}}
""")
    _foam(d / "system/fvSchemes", "dictionary", "fvSchemes", """
ddtSchemes      { default backward; }
gradSchemes     { default Gauss linear; }
divSchemes
{
    default         none;
    div(phi,U)      Gauss linearUpwind grad(U);
    div((nuEff*dev2(T(grad(U))))) Gauss linear;
}
laplacianSchemes     { default Gauss linear corrected; }
interpolationSchemes { default linear; }
snGradSchemes        { default corrected; }
""")
    _foam(d / "system/fvSolution", "dictionary", "fvSolution", """
solvers
{
    p { solver GAMG; smoother GaussSeidel; tolerance 1e-9; relTol 1e-3; }
    pFinal { $p; relTol 0; }
    pcorr { $p; }
    pcorrFinal { $pcorr; relTol 0; }
    Phi { $p; }
    "(U|cellDisplacement)" { solver smoothSolver; smoother symGaussSeidel; tolerance 1e-10; relTol 1e-4; minIter 2; }
    "(U|cellDisplacement)Final" { $U; relTol 0; }
}
PIMPLE
{
    nCorrectors 3;
    nNonOrthogonalCorrectors 1;
    consistent  true;
    correctPhi  true;
    momentumPredictor true;
    nOuterCorrectors 1;
}
potentialFlow { nNonOrthogonalCorrectors 10; }
""")
    _foam(d / "system/preciceDict", "dictionary", "preciceDict", f"""
preciceConfig "../precice-config.xml";
participant Fluid;
modules (FSI);
interfaces
{{
  Interface1
  {{
    mesh              Fluid-Mesh;
    patches           (flag);
    locations         faceCenters;
    readData          (Displacement);
    writeData         (Force);
  }};
}};
FSI
{{
  rho rho [1 -3 0 0 0 0 0] {rho!r};
}}
""")
    _foam(d / "constant/transportProperties", "dictionary", "transportProperties",
          f"\ntransportModel  Newtonian;\nnu              nu [ 0 2 -1 0 0 0 0 ] {nu!r};\n")
    _foam(d / "constant/turbulenceProperties", "dictionary", "turbulenceProperties", "\nsimulationType laminar;\n")
    _foam(d / "constant/dynamicMeshDict", "dictionary", "dynamicMeshDict", """
dynamicFvMesh dynamicMotionSolverFvMesh;
motionSolverLibs ("libfvMotionSolvers.so");
solver      displacementLaplacian;
displacementLaplacianCoeffs { diffusivity quadratic inverseDistance (flag cylinder); }
""")
    ramp = float(numerics.get("ramp_time_s", 2.0))
    _foam(d / "0/U", "volVectorField", "U", f"""
dimensions      [0 1 -1 0 0 0 0];
internalField   uniform (0 0 0);
boundaryField
{{
    inlet
    {{
        type            codedFixedValue;
        value           uniform (0 0 0);
        name            turekHronInlet;
        code
        #{{
            const vectorField& Cf = patch().Cf();
            vectorField& field = *this;
            const scalar t = this->db().time().value();
            const scalar H = {CH_H!r}, Um = {U!r}, T = {ramp!r};
            const scalar ramp = (T > 0 && t < T) ? 0.5*(1.0 - Foam::cos(constant::mathematical::pi*t/T)) : 1.0;
            forAll(Cf, i)
            {{
                const scalar y = Cf[i].y();
                field[i] = vector(1.5*Um*4.0*y*(H - y)/(H*H)*ramp, 0, 0);
            }}
        #}};
    }}
    outlet       {{ type zeroGradient; }}
    walls        {{ type noSlip; }}
    cylinder     {{ type noSlip; }}
    flag         {{ type movingWallVelocity; value uniform (0 0 0); }}
    frontAndBack {{ type empty; }}
}}
""")
    _foam(d / "0/p", "volScalarField", "p", """
dimensions      [0 2 -2 0 0 0 0];
internalField   uniform 0;
boundaryField
{
    inlet        { type zeroGradient; }
    outlet       { type fixedValue; value uniform 0; }
    walls        { type zeroGradient; }
    cylinder     { type zeroGradient; }
    flag         { type zeroGradient; }
    frontAndBack { type empty; }
}
""")
    _foam(d / "0/pointDisplacement", "pointVectorField", "pointDisplacement", """
dimensions      [0 1 0 0 0 0 0];
internalField   uniform (0 0 0);
boundaryField
{
    inlet        { type fixedValue; value uniform (0 0 0); }
    outlet       { type fixedValue; value uniform (0 0 0); }
    walls        { type fixedValue; value uniform (0 0 0); }
    cylinder     { type fixedValue; value uniform (0 0 0); }
    flag         { type fixedValue; value $internalField; }
    frontAndBack { type empty; }
}
""")
    write_geo(params, d / "mesh.geo")


# ------------------------------------------------------------------ solid

def solid_params(params: dict) -> dict:
    """The flag_ccx parameter set for the same flag (gravity off for the FSI tests)."""
    return {"density_kg_per_m3": params["solid_density_kg_per_m3"], "shear_modulus_Pa": params["shear_modulus_Pa"],
            "poisson_ratio": params["poisson_ratio"], "gravity_m_per_s2": 0.0, "flag_length_m": FLAG_L,
            "flag_height_m": FLAG_H, "cylinder_radius_m": R, "element_size_mm": params["solid_element_size_mm"]}


def write_solid(params: dict, numerics: dict, d: Path) -> dict:
    F = _flag_module()
    m = F.FlagMesh(solid_params(params), thickness_mm=DEPTH * 1e3)
    nu = float(params["poisson_ratio"])
    E = 2 * float(params["shear_modulus_Pa"]) * (1 + nu)
    rho = float(params["solid_density_kg_per_m3"])
    dt, t_end = float(params["time_step_s"]), float(params["end_time_s"])
    alpha = float(numerics.get("solid_alpha", 0.0))
    nodes = []
    for line in m.node_lines():                                  # mm -> m
        i, x, y, z = line.split(",")
        nodes.append(f"{i}, {float(x) * 1e-3:.12e}, {float(y) * 1e-3:.12e}, {float(z) * 1e-3:.12e}")
    # wetted nodes: top, bottom and tip faces, without the clamped root column (i = 0). CalculiX leaves loads on
    # constrained nodes out of its reaction totals, which the force-transfer check relies on; preCICE's
    # conservative mapping gives their share to the neighbouring nodes instead
    wet = sorted({m.nid(i, j, k) for k in (0, 1) for i in range(1, m.nx + 1) for j in (0, m.ny)}
                 | {m.nid(m.nx, j, k) for k in (0, 1) for j in range(m.ny + 1)})
    sets = (F._set("Nfix", m.clamp_nodes()) + F._set("Nsurface", wet) + F._set("NA", [m.point_a()]))
    deck = (["*HEADING", "Turek-Hron flag, FSI participant (SI units)", "*NODE, NSET=Nall"] + nodes
            + ["*ELEMENT, TYPE=C3D8I, ELSET=Eall"]
            + [f"{e}, " + ", ".join(str(v) for v in n) for e, n in m.connectivity().items()] + sets
            + ["*MATERIAL, NAME=EL", "*ELASTIC", f"{E!r}, {nu!r}", "*DENSITY", f"{rho!r}",
               "*SOLID SECTION, ELSET=Eall, MATERIAL=EL",
               "*STEP, NLGEOM, INC=1000000", f"*DYNAMIC, ALPHA={alpha!r}, DIRECT", f"{dt!r}, {t_end!r}",
               "*BOUNDARY", "Nfix, 1, 3", "*BOUNDARY", "Nall, 3",
               "*CLOAD", " Nsurface, 1, 0.0", " Nsurface, 2, 0.0", " Nsurface, 3, 0.0",
               "*NODE PRINT, NSET=NA, FREQUENCY=1", "U",
               "*NODE PRINT, NSET=Nfix, TOTALS=ONLY, FREQUENCY=1", "RF",
               "*NODE FILE, FREQUENCY=100000", "U", "*END STEP"])
    _w(d / "flag.inp", "\n".join(deck) + "\n")
    _w(d / "config.yml", """participants:
    Solid:
        interfaces:
        - nodes-mesh: Solid-Mesh
          patch: surface
          read-data: [Force]
          write-data: [Displacement]
precice-config-file: ../precice-config.xml
""")
    return {"solid_divisions": [m.nx, m.ny], "solid_nodes": len(nodes), "wet_nodes": len(wet),
            "point_a_node": m.point_a()}


# ------------------------------------------------------------------ coupling

def write_precice(params: dict, numerics: dict, path: Path) -> None:
    dt, t_end = float(params["time_step_s"]), float(params["end_time_s"])
    radius = float(numerics.get("rbf_support_radius_m", 0.05))
    tol = float(numerics.get("coupling_rel_tol", 1e-4))
    _w(path, f"""<?xml version="1.0" encoding="UTF-8" ?>
<precice-configuration>
  <log>
    <sink filter="%Severity% > debug and %Rank% = 0" format="---[precice] %ColorizedSeverity% %Message%" enabled="true" />
  </log>
  <data:vector name="Force" />
  <data:vector name="Displacement" />
  <mesh name="Fluid-Mesh" dimensions="2">
    <use-data name="Force" />
    <use-data name="Displacement" />
  </mesh>
  <mesh name="Solid-Mesh" dimensions="2">
    <use-data name="Displacement" />
    <use-data name="Force" />
  </mesh>
  <participant name="Fluid">
    <provide-mesh name="Fluid-Mesh" />
    <receive-mesh name="Solid-Mesh" from="Solid" />
    <write-data name="Force" mesh="Fluid-Mesh" />
    <read-data name="Displacement" mesh="Fluid-Mesh" />
    <watch-integral mesh="Fluid-Mesh" name="Wet" scale-with-connectivity="false" />
    <mapping:rbf direction="write" from="Fluid-Mesh" to="Solid-Mesh" constraint="conservative">
      <basis-function:compact-polynomial-c6 support-radius="{radius!r}" />
    </mapping:rbf>
    <mapping:rbf direction="read" from="Solid-Mesh" to="Fluid-Mesh" constraint="consistent">
      <basis-function:compact-polynomial-c6 support-radius="{radius!r}" />
    </mapping:rbf>
  </participant>
  <participant name="Solid">
    <provide-mesh name="Solid-Mesh" />
    <write-data name="Displacement" mesh="Solid-Mesh" />
    <read-data name="Force" mesh="Solid-Mesh" />
    <watch-integral mesh="Solid-Mesh" name="Wet" scale-with-connectivity="false" />
    <watch-point mesh="Solid-Mesh" name="A" coordinate="{XC + R + FLAG_L!r};{YC!r}" />
  </participant>
  <m2n:sockets acceptor="Fluid" connector="Solid" exchange-directory=".." />
  <coupling-scheme:parallel-implicit>
    <time-window-size value="{dt!r}" />
    <max-time value="{t_end!r}" />
    <participants first="Fluid" second="Solid" />
    <exchange data="Force" mesh="Solid-Mesh" from="Fluid" to="Solid" />
    <exchange data="Displacement" mesh="Solid-Mesh" from="Solid" to="Fluid" />
    <max-iterations value="{int(numerics.get("coupling_max_iterations", 50))}" />
    <relative-convergence-measure limit="{tol!r}" data="Displacement" mesh="Solid-Mesh" />
    <relative-convergence-measure limit="{tol!r}" data="Force" mesh="Solid-Mesh" />
    <acceleration:IQN-ILS>
      <data name="Displacement" mesh="Solid-Mesh" />
      <data name="Force" mesh="Solid-Mesh" />
      <filter type="QR2" limit="1e-2" />
      <initial-relaxation value="0.5" />
      <max-used-iterations value="100" />
      <time-windows-reused value="15" />
    </acceleration:IQN-ILS>
  </coupling-scheme:parallel-implicit>
</precice-configuration>
""")


def write_case(params: dict, numerics: dict, root: Path) -> dict:
    write_fluid(params, numerics, root / "fluid")
    info = write_solid(params, numerics, root / "solid")
    write_precice(params, numerics, root / "precice-config.xml")
    return info | {"depth_m": DEPTH}
