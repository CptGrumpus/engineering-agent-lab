"""Build the portfolio site into docs/: a home page, one page per study (or report of related studies), and the
how-I-work, grading, in-progress and requirements pages, from pages/*.html, studies/*.html and extras.py."""
import html
import json
import re
from pathlib import Path

HERE = Path(__file__).parent
REPO = Path(__file__).resolve().parent.parent
scenes = json.loads((HERE / "v2" / "scenes.json").read_text(encoding="utf-8"))

# real pipeline output for the terminal panel
log = (REPO / "runs/20261120-105126_qc_bump_liftoff/run.log").read_text(encoding="utf-8").splitlines()
pick = [l for l in log if "p00_" in l and ("PASS" in l or "FAIL" in l)][:6]
term_lines = []
for l in pick:
    m = re.search(r"(p00_\S+):\s+(\S+)\s+(PASS|FAIL)\s+value\s+(\S+)\s+tol\s+(\S+)", l)
    if m:
        term_lines.append((m.group(2), m.group(3), m.group(4), m.group(5)))

# --- viewport scenes ------------------------------------------------------------
VP = [
    {"id": "bracket_opt", "study": "bracket_opt", "tab": "Optimised", "legend": "S, Mises", "unit": "MPa",
     "model": "Optimised clevis bracket · 6061-T6, 100 × 100 mm base, (1.5, 1.0, 4.5) kN on the pin",
     "lines": ["Solver: CalculiX 2.22 · C3D10 · design D on the finest of its three meshes",
               "Deformation scale factor: +1.000e+02",
               "Peak 98.3 MPa against 100, at the lug fillet · 372 g, 4 % lighter than the start"]},
    {"id": "cantilever", "study": "fea", "tab": "Stress", "legend": "S, Mises", "unit": "MPa",
     "model": "Cantilever bracket · steel, 200 × 20 × 20 mm, 1 kN at the tip",
     "lines": ["Solver: CalculiX 2.22 · C3D10 · 5 758 surface nodes",
               "Deformation scale factor: +2.500e+01",
               "Range capped at the 150 MPa beam-theory stress; the clamp corners are singular"]},
    {"id": "cantilever_opt", "study": "cantilever_opt", "tab": "Optimised", "legend": "S, Mises", "unit": "MPa",
     "model": "The same cantilever, optimised · steel, 200 mm × 20 mm wide, tapered 26.0 → 8.7 mm, 1 kN at the tip",
     "lines": ["Solver: CalculiX 2.22 · C3D10 · the confirmation run's finest mesh (2 mm)",
               "Deformation scale factor: +2.500e+01 · same scale and framing as study 1's straight bar",
               "546 g, 30 % under the lightest straight bar that passes · peak 99.5 MPa along the span against 100"]},
    {"id": "contact_detail", "study": "contact", "tab": "Contact", "legend": "S, Mises", "unit": "MPa",
     "model": "Roller on plate · steel, R = 50 mm, 501 N/mm · section through the contact",
     "lines": ["Solver: CalculiX 2.22 · surface-to-surface penalty contact",
               "Peak contact pressure +6.092e+02 · Hertz exact +6.067e+02",
               "Highest stress 0.41 mm below the surface, where Hertz puts it"]},
    {"id": "bolted_joint", "study": "bolted_joint", "tab": "Joint", "legend": "Friction used", "unit": "%",
     "model": "Bolted joint · two 6 mm steel plates, M8 at 15 kN, μ = 0.2, half model mirrored",
     "lines": ["Solver: CalculiX 2.22 · C3D8I, surface-to-surface contact with friction",
               "Share of the available friction (μ × local pressure) in use on the bottom plate's face; outside the 21 mm contact patch the plates don't touch",
               "Drag the slider to push the top plate sideways: the stuck region shrinks until the whole joint slides"]},
    {"id": "pv_nozzle", "study": "pv_nozzle", "tab": "Vessel", "legend": "S, Mises", "unit": "MPa",
     "model": "Shell with a radial nozzle · steel, 1000 mm bore × 16 mm, 200 mm nozzle × 12 mm, 3.5 MPa inside",
     "lines": ["Solver: CalculiX 2.22 · C3D10 · the mesh study's finest mesh, a quarter model mirrored into the whole vessel",
               "Range stops at 240 MPa · the inner corner peaks at 351 MPa, a peak stress the membrane limits exclude",
               "Linearised beside the weld: PL 205.1 MPa, passes · through the corner: 256.7 MPa, fails · limit 207"]},
    {"id": "strap_proof", "study": "strap_proof", "tab": "Plasticity", "legend": "S11", "unit": "MPa",
     "model": "Strap through its proof test · 6061-T6, 40 × 4 mm, 16 mm hole, loaded to 15 kN and back",
     "lines": ["Solver: CalculiX 2.22 · elastic-plastic, quarter model mirrored",
               "The top three bands, from 225 MPa, are past yield: 1.8 mm deep",
               "Hole edge 274 MPa and 0.58 % strain · play it through to see the −77 MPa left after unloading"]},
    {"id": "strut", "study": "strut", "tab": "Buckling", "legend": "S, Mises", "unit": "MPa",
     "model": "Strut · 6061-T6, 500 mm, 25 × 16 mm, pinned, bowed L/1000",
     "lines": ["Solver: CalculiX 2.22 · C3D8I, geometrically nonlinear, 19 load steps up to first yield",
               "Deformation scale factor: +5.000e+00",
               "Buckling load 23.14 kN · first yield at 21.80 kN · drag the slider to load it step by step"]},
    {"id": "fatigue", "study": "fatigue", "tab": "Fatigue", "legend": "S11 amplitude", "unit": "MPa",
     "model": "Strap with a 16 mm hole · 160 × 40 × 4 mm, 0 → 5 kN cyclic",
     "lines": ["Solver: CalculiX 2.22 · plane stress, quarter model mirrored",
               "Peak amplitude +5.85e+01 at the sides of the hole",
               "Life about 8 × 10⁹ cycles against 3 × 10⁷ required"]},
    {"id": "fin", "study": "thermal", "tab": "Thermal", "legend": "NT11", "unit": "°C",
     "model": "Heat-sink fin · 6061-T6, 40 × 20 × 2 mm, h = 25 W/m²K",
     "lines": ["Solver: CalculiX 2.22 · steady heat transfer",
               "Tip 73.2 °C against a 60 °C minimum",
               "Energy balance: base heat in equals convection out"]},
    {"id": "cold_plate", "study": "cold_plate", "tab": "Cold plate", "legend": "NT11", "unit": "°C",
     "model": "Cold plate · 3 mm 6061-T6 on a 1 mm water channel, 30 kW/m²",
     "lines": ["Solver: OpenFOAM 14 → CalculiX 2.22 · coupled, 28 passes",
               "A 30 mm slice of the plane-strain section · coolant left to right · the 3D view keeps every fourth node through the thickness",
               "Component face 40.99 °C against 45 · coolant rise 7.20 K"]},
    {"id": "duct", "study": "cfd", "tab": "Flow", "legend": "U, axial", "unit": "m/s",
     "model": "Coolant passage · 20 × 1 mm, water at 0.1 m/s mean, Re 199",
     "lines": ["Solver: OpenFOAM 14 · 3D laminar, quarter section mirrored",
               "Height = velocity; gap direction drawn 5× wider",
               "Pressure gradient within 0.03 % of the exact rectangular-duct solution"],
     "check_text": "Render check: the volume under the surface equals the imposed flow rate to {err} · {col} of pixels on the legend"},
    {"id": "mode1", "study": "modal", "tab": "Modal", "legend": "U, Magnitude", "unit": "normalised",
     "model": "Bracket arm · steel, 150 × 25 × 7 mm, clamped",
     "lines": ["Solver: CalculiX 2.22 · *FREQUENCY, mode 1 of 4",
               "261.7 Hz flapwise · requirement ≥ 250 Hz (engine 2nd order + 25 %)",
               "Within 0.9 % of an independent Timoshenko beam model · in 3D, the mode can be animated (motion exaggerated)"]},
    {"id": "random_vib", "study": "random_vib", "kind": "figure", "img": "v2/fig_random_vibration.svg",
     "model": "Bracket arm on a shaker table · 0.04 g²/Hz from 20 to 2,000 Hz, one hour per axis",
     "lines": ["Solver: CalculiX 2.22 modes, summed in Python · finest of three meshes (1.22 mm)",
               "Stress at the clamp across the frequency range, and each requirement against its limit",
               "3-sigma stress 38.6 MPa against 236.7 · damage 0.0024 against 0.5 · tip 0.345 mm against 1.0"]},
    {"id": "bracket_uq", "study": "bracket_uq", "kind": "figure", "img": "v2/fig_bracket_uncertainty.svg",
     "model": "Bracket arm on a shaker table · damping, test level, fatigue strength and thickness uncertain",
     "lines": ["Monte Carlo, Sobol indices, FORM and importance sampling · study 21's finest mesh (1.22 mm)",
               "Left: what drives each result. Right: the chance of failing each requirement against the 1-in-1,000 limit",
               "Chance of failing 2.2 × 10⁻⁶ · tip clearance governs · damping drives 71 % of the fatigue spread"]},
    {"id": "fan_rotor", "study": "fan_rotor", "tab": "Rotor", "legend": "Deflection", "unit": "% of largest", "fixed": 0,
     "model": "Fan rotor, 400 mm impeller on a 1 m shaft · 1,000 to 3,000 rpm · bearings 10⁷ to 10⁸ N/m",
     "lines": ["ROSS 3.1 · 20 Timoshenko elements with gyroscopic terms · the recommended 65 mm shaft on the softest bearings",
               "Its forward whirl at the first critical speed, 3,714 rpm, drawn exaggerated; outlines show the shaft at rest",
               "50 mm fails (critical speed in the range) · 60 mm fails on soft bearings (14.3 %) · 65 mm passes (23.8 % or more)"],
     "check_text": "Render check: the mode rebuilt from the run's own files and matched to its critical speed and rotor mass · volume within {err} · {col} of pixels on the legend"},
    {"id": "crack", "study": "crack", "kind": "figure", "img": "v2/fig_crack_growth.svg",
     "model": "Edge-cracked S355 plate, 100 × 10 mm · 150 MPa peak, R = 0.1 · detectable crack 2 mm",
     "lines": ["CalculiX plane strain · K by energy release and by crack opening · finest tip mesh 0.025 mm",
               "Left: stress intensity against Tada's handbook. Right: crack growth from 2 mm to critical",
               "Critical crack 37.0 mm · life about 92,000 cycles · inspect at least every 46,000"]},
    {"id": "oring", "study": "oring", "kind": "figure", "img": "v2/fig_oring_seal.svg",
     "model": "O-ring face seal, 3.53 mm NBR 70 in a 2.79 × 4.80 mm groove · coolant at 3 bar · three tolerance corners",
     "lines": ["CalculiX, axisymmetric, the upper half of the ring · neo-Hookean rubber, stiffness from hardness (Gent)",
               "Left: pressure on the cover. Middle: closing force as the cover comes down (hollow dot: a cross-check missed). Right: groove fill",
               "Loosest 1.50 MPa (need 0.6) · tightest 5.94 N/mm (budget 12) · fill at most 80.4 % (limit 85)"]},
    {"id": "steel_frame", "study": "steel_frame", "tab": "Frame", "legend": "H1-1 ratio", "unit": "1.0 = limit", "fixed": 1,
     "model": "Steel portal for an equipment platform, W10x33 columns 4.0 m, W14x30 beam 6.0 m, fixed bases · 35 kN/m and 15 kN factored",
     "lines": ["Python, a plane-frame solver with exact stability functions · AISC 360-22 Direct Analysis Method",
               "Each member coloured by its combined axial and bending ratio along its length, from the second-order moments · 1.0 is the code limit",
               "Largest 0.80 at the beam's midspan, unbraced over 6 m · leeward column 0.45 at its top · deflection 4.1 of 16.7 mm · drift 2.6 of 10.0 mm"]},
    {"id": "shaft", "study": "shaft", "kind": "figure", "img": "v2/fig_shaft_fillet.svg",
     "model": "Gearbox shaft shoulder, 42CrMo4, D 40 → d 32 mm, fillet 1.6 +0.4 / -0.2 · rotating bending 300 N m, steady torque 500 N m",
     "lines": ["CalculiX, half the shaft in 10-node tetrahedra, 0.14 mm on the fillet · Kt and Kts from the model, fatigue by Shigley's method",
               "Left: safety against fillet radius as drawn. Middle: the step scaled up. Right: stress along the drawn fillet",
               "As drawn 1.19 (need 1.5), yield 1.83 (need 2.0) · best fillet that fits 1.47 · d 36 / D 45: 1.62 and 2.52 · hollow dot: unverified"]},
    {"id": "enclosure", "study": "enclosure", "tab": "Enclosure", "legend": "T", "unit": "°C", "fixed": 0,
     "model": "Sealed aluminium enclosure, 150 × 60 mm section · 15 W inside, still air at 40 °C outside · bare or painted inside",
     "lines": ["OpenFOAM 14, the air and the solids solved together: natural convection, conduction and surface radiation, marched to a settled state",
               "Top: as drawn, painted inside. Bottom: the aluminium shell and the 2 W/mK bridge to the lid · each 2 mm cell as solved; the 2D section's solids given 12 mm of depth, the air the sheet behind",
               "As drawn, painted: C1 89 to 91 °C (limit 70) · bare: all four fail · with a 125 °C capacitor and a 2 to 5 W/mK bridge: C1 79 to 82 °C (limit 90), U1 69 to 77 °C"]},
]
VP += [
    {"id": "strap_detail", "study": "strap", "legend": "S11", "unit": "MPa",
     "model": "Strap with a cable hole · 6061-T6, 40 × 4 mm, 5 kN",
     "lines": ["Solver: CalculiX 2.22 · plane stress, quarter model mirrored",
               "The 10 mm hole of the mesh study, 0.125 mm elements at its edge",
               "Peak at the two sides of the hole · Kt within 0.6 % of Peterson's handbook"]},
    {"id": "cad_plate", "study": "cad", "kind": "plain",
     "model": "Mounting plate · generated by a CadQuery script",
     "lines": ["One script, every hole size: the CAD is a function of the inputs",
               "Only the 9 mm (M8 clearance) hole meets both the weight and edge-distance rules"]},
    {"id": "heat", "study": "heat", "kind": "figure", "img": "v2/fig_heat_response.svg",
     "model": "Cold-plate channel · water in a 1 mm gap, 30 kW/m² on both walls",
     "lines": ["Solver: OpenFOAM 14 · laminar flow with heat transfer",
               "Wall and bulk temperature, and the local Nusselt number, against the Graetz thermal-entry solution",
               "Wall peak 44.03 °C against 45 · coolant rise 7.2 K"]},
    {"id": "pipe", "study": "pipe", "kind": "figure", "img": "v2/fig_pipe_friction.svg",
     "model": "Smooth pipe, fully developed turbulent flow · 100 mm bore, Re 2 × 10⁴ to 2 × 10⁶",
     "lines": ["Solver: OpenFOAM 14 · k-omega SST on a periodic 5° wedge",
               "Friction factor against Prandtl's law: the mesh study, the Reynolds sweep and the wall-function placement",
               "+2.4 % extrapolated to zero cell size, against a 5 % limit · one mesh alone gave the wrong sign"]},
    {"id": "step", "study": "step", "kind": "figure", "img": "v2/fig_step_comparison.svg",
     "model": "Backward-facing step · Driver and Seegmiller's experiment, 12.7 mm step, air at 44.2 m/s",
     "lines": ["Solver: OpenFOAM 14 · 2D k-omega SST, walls resolved, finest of three meshes",
               "Skin friction and pressure along the floor against the measurements, scored once",
               "Reattachment +2.3 % and friction 7.0 % rms pass · pressure recovery 0.023 high against 0.02 misses"]},
    {"id": "motor", "study": "motor", "kind": "figure", "img": "v2/fig_motor_comparison.svg",
     "model": "2004 Toyota Prius traction motor · the client-data model against Oak Ridge National Laboratory's test",
     "lines": ["Model: FEMM 4.2 magnetostatics through Pyleecan · drawing, parts list and measured magnet material as inputs, nothing tuned",
               "Left: back-EMF against speed. Right: locked-rotor torque against current, the largest over shaft angle, as the test reports it",
               "Back-EMF +17.7 %, torque 17 to 19 % high at most currents · about 18 % too much magnet flux, traced to the magnets"]},
    {"id": "suspension", "study": "suspension", "kind": "figure", "img": "img/anim_quarter_car.webp",
     "model": "Quarter car over a bump · SciPy and OpenModelica",
     "lines": ["Drawn from the simulation at 36 km/h and 600 N·s/m, with the tire load and body acceleration",
               "The wheel leaves the road twice",
               "600 to 1000 N·s/m passes at 18 km/h; at 36 km/h no damping rate does"]},
    {"id": "baseline", "study": "baseline", "kind": "figure", "img": "img/anim_msd.webp",
     "model": "Mass-spring-damper · SciPy against OpenModelica",
     "lines": ["The same step force at three damping ratios, with the exact solution dotted underneath",
               "All 72 checks pass",
               "The two tools agree to a few parts per million"]},
]
import make_mesh3d
mesh3d = make_mesh3d.index()
for v in VP:
    if v.get("kind") == "figure":
        v["check"] = ""
        continue
    if v["id"] in mesh3d:          # interactive 3D view: same surface and bands as the render
        m = mesh3d[v["id"]]
        v.update(mesh=m["file"], mesh_kb=m["kb"], elev=m["elev"], azim=m["azim"])
    s = scenes[v["id"]]
    vol, col = s["volume"], s["color"]
    v["img"] = f"v2/vp_{v['id']}.webp"
    if v.get("kind") == "plain":                 # a CAD render: geometry check only, no field
        v["check"] = (f"Render check: encloses {vol['enclosed_mm3']:,.1f} mm³ of {vol['design_mm3']:,.1f} design"
                      ).replace(",", " ")
        continue
    v["bands"] = [("#%02x%02x%02x" % tuple(round(c * 255) for c in rgb)) for rgb in s["band_colors"]]
    v["vmin"], v["vmax"] = s["vmin"], s["vmax"]
    v["check"] = (f"Render check: encloses {vol['enclosed_mm3']:,.1f} mm³ of {vol['design_mm3']:,.1f} design · "
                  f"{100 * col['fraction_on_legend']:.1f} % of pixels on the legend").replace(",", " ")
    v["img"] = f"v2/vp_{v['id']}.webp"
    if "check_text" in v:
        v["check"] = v["check_text"].format(err=f"{100 * abs(vol['rel_error']):.2f} %",
                                            col=f"{100 * col['fraction_on_legend']:.1f} %")

# --- case gallery ---------------------------------------------------------------
CARDS = [
    ("bracket_opt", "12", "struct", "Featured · Design automation", "Bracket optimisation loop, driven by the agent", "The agent searched 78 designs over three runs for the lightest machined clevis bracket that stays under 100 MPa. The checks threw out its first two answers. The final one is 372 g, 4 % lighter than the start, at 98.3 MPa, and its own mesh study confirms it.", "pass", "CadQuery · Gmsh · CalculiX · SciPy"),
    ("pv_nozzle", "18", "struct", "New · Design code", "Pressure vessel nozzle, design code check", "Passes ASME-style design by analysis on lines at the weld toes (205.1 MPa against 207), fails by 24 % on a line through the corner. I'd judge it by the corner: about 21 mm, or a pad.", "line", "CadQuery · Gmsh · CalculiX"),
    ("bolted_joint", "16", "struct", "New · Friction contact", "Bolted joint, slip and opening", "Fails narrowly: once the joint settles it slips at 2.39 kN, 4.4 % short of the 2.5 kN it must carry. A 15.6 kN preload fixes it, and it stays closed to 13.1 kN.", "fail", "CalculiX"),
    ("strap_proof", "14", "struct", "New · Plasticity", "Strap proof test, notch plasticity", "A 15 kN proof test strains the hole edge to 0.58 %, inside a 1 % limit, and leaves −77 MPa of compression behind, which helps fatigue.", "pass", "CadQuery · Gmsh · CalculiX"),
    ("strut", "13", "struct", "New · Stability", "Strut buckling, with an imperfect strut", "The longest acceptable strut is about 587 mm. The bow costs 4 to 7 % of the buckling load, so a buckling check alone would overstate the capacity.", "pass", "CalculiX"),
    ("contact", "10", "struct", "Contact", "Roller-on-plate contact, nonlinear FEA", "A track roller carrying 500 N/mm. The contact pressure peaks at 609 MPa against a 650 MPa limit, and the shear under the surface reaches 184 MPa against 200. The CalculiX model lands within 0.4 % of the exact Hertz solution.", "pass", "Gmsh · CalculiX"),
    ("fea", "01", "struct", "Structures", "Cantilever bracket, 3D FEA", "Passes with room to spare at 0.953 mm and 150 MPa.", "pass", "FreeCAD · Gmsh · CalculiX"),
    ("cantilever_opt", "01b", "struct", "Design automation", "The same cantilever, optimised", "Under a 100 MPa fatigue limit a linear taper from 26.0 to 8.7 mm weighs 546 g, 30 % less than the lightest straight bar that passes, and lands within 0.13 % of an independent beam-theory optimum.", "pass", "CadQuery · Gmsh · CalculiX · SciPy"),
    ("strap", "02", "struct", "Structures", "Cable hole in a strap, CAD to FEA", "The hole can go up to about 16.7 mm. 16 mm passes at 117 MPa and 18 mm fails.", "pass", "CadQuery · Gmsh · CalculiX"),
    ("fatigue", "03", "struct", "Fatigue", "Strap fatigue life, chained analysis", "Predicted to last with a wide margin; rated 7.8 kN cyclic for 3 × 10⁷ cycles, the lower of two data sets, extrapolated past the test data.", "pass", "CalculiX · Python"),
    ("modal", "04", "struct", "Vibration", "Bracket arm modal analysis", "7 mm thick puts the first mode at 261.7 Hz and the weight at 206 g.", "pass", "CadQuery · Gmsh · CalculiX"),
    ("random_vib", "21", "struct", "New · Random vibration", "Bracket arm on a shaker table, random vibration", "Passes one hour per axis of random vibration with wide margins: 38.6 MPa at the clamp against 236.7, fatigue damage 0.0024 against 0.5, tip 0.345 mm against 1.0.", "pass", "CalculiX · Python"),
    ("bracket_uq", "22", "struct", "New · Uncertainty", "How robust is the bracket arm's pass?", "With damping, test level, fatigue strength and thickness uncertain, the chance of failing is about 2 in a million against a 1-in-1,000 limit. Damping drives the spread: measure it first.", "pass", "CalculiX · Python"),
    ("fan_rotor", "23", "struct", "New · Rotordynamics", "Fan rotor: critical speeds and unbalance response", "The drawn 50 mm shaft runs through its first critical speed inside the 1,000 to 3,000 rpm range, and 60 mm fails on soft bearings. A 65 mm shaft clears the range by at least 23.8 % on any bearing in the band, with the impeller's vibration under 5 µm.", "fix", "ROSS · Python"),
    ("crack", "24", "struct", "New · Fracture mechanics", "Cracked steel plate: critical crack and fatigue crack growth", "A 2 mm edge crack, the smallest inspection finds, grows to the critical 37.0 mm in about 92,000 cycles. Inspect at least every 46,000 cycles; the planned 40,000 has margin. Stress intensity checked against the handbook to 0.66 %.", "pass", "Gmsh · CalculiX · Python"),
    ("oring", "25", "struct", "New · Elastomer seals", "O-ring face seal across its tolerance stack", "Passes at all three corners: 1.50 MPa of sealing pressure at the loosest against 0.6 needed, and 5.94 N/mm to close at the tightest against a 12 N/mm budget. A squeezed ring grows in diameter, and the groove wall that stops it adds 40 % to the force.", "checkmiss", "Gmsh · CalculiX"),
    ("steel_frame", "28", "struct", "New · Steel design code", "Steel portal frame to AISC 360-22", "Passes every requirement: the largest member ratio is 0.80, in the beam taken as unbraced over 6 m, with the columns at 0.45, live-load deflection 4.1 of 16.7 mm and drift 2.6 of 10 mm. The frame solver and member checks reproduce AISC's own worked examples within 0.7 %.", "pass", "Python · AISC 360-22"),
    ("shaft", "26", "struct", "New · Machine elements", "Gearbox shaft shoulder: fatigue at the fillet", "Fails as drawn: fatigue safety 1.19 against 1.5 and yield safety 1.83 against 2.0, and no fillet that fits under the 4 mm shoulder reaches 1.5. A 36 mm seat with a 45 mm shoulder passes at 1.62 and 2.52.", "fix", "Gmsh · CalculiX · Python"),
    ("enclosure", "27", "fluid", "New · Electronics cooling", "Sealed electronics enclosure: the capacitor that decides the design", "Fails as drawn: painted inside, the bulk capacitor runs at 89 to 91 °C against its 70 °C life limit, and bare inside every part fails. A bridge to the lid cools the regulator but not the capacitor. Paint, a 125 °C capacitor and a 2 W/mK bridge pass every limit.", "fix", "OpenFOAM · Python"),
    ("cold_plate", "15", "fluid", "New · Multiphysics", "Cold plate, the full thermal chain", "Passes on all three counts, from the coolant flow through the plate's conduction to its thermal stress: 40.99 °C, a 7.20 K coolant rise and 46.8 MPa.", "pass", "OpenFOAM · CalculiX"),
    ("pipe", "19", "fluid", "New · Turbulence", "Turbulent pipe friction, against measured data", "Passes: extrapolated to zero cell size, the turbulence model lands 2.4 % above Prandtl's law against a 5 % limit. The first mesh agreed to 0.9 %, with the wrong sign. Wall functions sit 5 % low on every mesh.", "pass", "OpenFOAM"),
    ("step", "19", "fluid", "New · Measured data", "Flow over a backward-facing step, against measurements", "Two of three agreed limits pass: reattachment 2.3 % long and skin friction 7.0 % rms. The pressure recovers 0.023 too far against a 0.02 limit, most likely because a 2D model has no tunnel side walls.", "most", "OpenFOAM"),
    ("cfd", "05", "fluid", "CFD", "Coolant channel pressure budget", "Fails. It needs 33.4 Pa against a 30 Pa budget, and no gap size fixes it.", "fail", "OpenFOAM"),
    ("thermal", "06", "fluid", "Heat transfer", "Heat-sink fin temperature", "The tip sits at 73.2 °C, and still 65.9 °C with every input at its worst.", "pass", "CalculiX"),
    ("heat", "11", "fluid", "Heat transfer", "Cold-plate channel heat transfer", "Passes, verified: the wall peaks at 44.03 °C against 45, and the coolant warms 7.2 K. A finer mesh study was needed to settle the peak.", "pass", "OpenFOAM"),
    ("motor", "20", "em", "Electric machines", "Traction motor, modelled from client data and checked against test", "The 2004 Prius motor, modelled from the drawings, parts list and measured magnet material, with nothing tuned. Against the laboratory's test it reads about 18 % high on both back-EMF and torque. I traced that to the magnets: the measured air-gap field is the model's scaled down by 14.8 % with the same shape, and one test on one magnet would confirm it. Rated torque and power pass; the rotor bridges at overspeed and the top-speed voltage fail.", "closed", "Pyleecan · FEMM · ElmerFEM · CalculiX"),
    ("suspension", "07", "vehicle", "Vehicle dynamics", "Quarter car, ride and road holding", "600 to 1000 N·s/m works at 18 km/h. At 36 km/h the wheel leaves the road.", "mixed", "SciPy · OpenModelica"),
    ("cad", "08", "geom", "Geometry", "Parametric mounting plate", "Only the 9 mm (M8 clearance) hole meets both the weight and edge-distance rules.", "pass", "CadQuery"),
    ("baseline", "09", "workflow", "Workflow", "Mass-spring-damper baseline", "All 72 checks pass, and the two tools agree to a few parts per million.", "pass", "SciPy · OpenModelica"),
]
VERDICT = {"pass": "Passes", "fail": "Fails", "mixed": "Depends on speed", "held": "One result on hold",
           "wip": "In progress", "closed": "Closed, with client questions", "checkmiss": "Passes; two cross-checks just missed", "fix": "Fails as drawn; fix found", "partfix": "Fails; the fix covers one limit of two", "line": "Depends on one judgement call", "most": "Passes, with one miss"}

# studies of the same part, shown as one card and one panel; each study keeps its own write-up, viewer
# result, requirements rows and evidence, and links to a study land on its part of the panel
GROUPS = {
    "cantilever_bracket": dict(parts=["fea", "cantilever_opt"], main="cantilever_opt", no="01 · 01b",
                               d="Two studies", title="Cantilever bracket: stress check, then optimised",
                               label="Studies 1 and 1b · FreeCAD, CadQuery, Gmsh, CalculiX and SciPy", verdict="pass",
                               tools="CalculiX · SciPy",
                               answer="First the straight steel bar: 0.953 mm and 150 MPa, inside its 213 MPa limit. Then a "
                                      "100 MPa fatigue limit rules that bar out, and the optimiser tapers it from 26.0 to 8.7 mm: "
                                      "546 g, 30 % under the lightest straight bar that passes, verified against beam theory "
                                      "to 0.13 %."),
    "strap": dict(parts=["strap", "fatigue", "strap_proof"], main="strap_proof", no="02 · 03 · 14",
                  d="Three studies", title="Aluminium strap: cable hole, fatigue life and proof test",
                  label="Studies 2, 3 and 14 · CadQuery, Gmsh, CalculiX and Python", verdict="pass",
                  tools="CadQuery · Gmsh · CalculiX · Python",
                  answer="One strap, three questions. A 16 mm cable hole passes at 117 MPa against 120. At its 5 kN "
                         "service load the strap is predicted to last with a wide margin, and it's rated 7.8 kN cyclic, "
                         "an extrapolation on the more cautious of two data sets. A 15 kN proof test strains "
                         "the hole edge to 0.58 % and leaves −77 MPa of compression behind, which helps fatigue."),
    "cold_plate": dict(parts=["heat", "cold_plate"], main="cold_plate", no="11 · 15",
                       d="Two studies", title="Cold plate: the coolant channel, then the full thermal chain",
                       label="Studies 11 and 15 · OpenFOAM and CalculiX", verdict="pass", tools="OpenFOAM · CalculiX",
                       answer="First the coolant channel on its own: the wall peaks at 44.03 °C against 45, verified. Then "
                              "the full chain, coolant to plate conduction to thermal stress: the component face peaks at "
                              "40.99 °C, the coolant warms 7.20 K and the stress reaches 46.8 MPa, all inside their limits."),
}
GROUPS["bracket_arm"] = dict(parts=["modal", "random_vib", "bracket_uq"], main="modal", no="04 · 21 · 22", d="Three studies",
                             title="Bracket arm: modal analysis, random vibration and how robust the pass is",
                             label="Studies 4, 21 and 22 · CadQuery, Gmsh, CalculiX and Python", verdict="pass",
                             tools="CadQuery · Gmsh · CalculiX · Python",
                             answer="7 mm thick puts the first mode at 261.7 Hz and the weight at 206 g. Then the same arm on a "
                                    "shaker table, one hour per axis of random vibration: 38.6 MPa at the clamp against 236.7, "
                                    "fatigue damage 0.0024 against 0.5 and 0.345 mm of tip movement against 1 mm. With the damping, "
                                    "test level, fatigue strength and thickness uncertain, the chance of failing that test is "
                                    "about 2 in a million; damping is the input to measure.")
GROUPS["turbulent_flow"] = dict(parts=["pipe", "step"], main="pipe", no="19", d="Two parts",
                                title="Turbulent flow: pipe friction, then flow over a step",
                                label="Study 19 · OpenFOAM, against measured data", verdict="most", tools="OpenFOAM",
                                answer="Attached flow first: resolved at the wall, the friction factor lands 2.4 % above "
                                       "Prandtl's law against a 5 % limit, while wall functions sit 5 % low. Then separated flow "
                                       "behind a step, scored once against measurements: reattachment and skin friction pass, "
                                       "and the pressure recovers 0.023 too far against a 0.02 limit.")
PART_OF = {p: g for g, gd in GROUPS.items() for p in gd["parts"]}
PART_LABEL = {"fea": "01 · Stress check", "cantilever_opt": "01b · Optimised",
              "strap": "02 · Cable hole", "fatigue": "03 · Fatigue life", "strap_proof": "14 · Proof test",
              "heat": "11 · Coolant channel", "cold_plate": "15 · Full thermal chain",
              "modal": "04 · Modal analysis", "random_vib": "21 · Random vibration", "bracket_uq": "22 · How robust the pass is",
              "pipe": "19 · Pipe friction", "step": "19, part 2 · Flow over a step"}

GALLERY, _seen = [], set()        # (key, no, group, d, title, answer, verdict, tools, thumb key)
for k, n, g, d, title, a, v, tools in CARDS:
    if k in PART_OF:
        gk = PART_OF[k]
        if gk in _seen:
            continue
        _seen.add(gk)
        gd = GROUPS[gk]
        GALLERY.append((gk, gd["no"], g, gd["d"], gd["title"], gd["answer"], gd["verdict"], gd["tools"], gd["main"]))
    else:
        GALLERY.append((k, n, g, d, title, a, v, tools, k))

# ================================================================= the site: one page per gallery card
SITE_URL = "https://cptgrumpus.github.io/engineering-agent-lab/"
AUTHOR = "Justin Smith"
DOCS = REPO / "docs"
PAGES = HERE / "pages"
SLUG = {"bracket_opt": "bracket-optimisation", "pv_nozzle": "pressure-vessel-nozzle", "bolted_joint": "bolted-joint",
        "strap": "aluminium-strap", "strut": "strut-buckling", "contact": "roller-contact",
        "cantilever_bracket": "cantilever-bracket", "bracket_arm": "bracket-modal", "cold_plate": "cold-plate",
        "turbulent_flow": "turbulent-pipe-friction", "cfd": "coolant-channel", "thermal": "heat-sink-fin",
        "suspension": "quarter-car", "cad": "mounting-plate", "baseline": "mass-spring-damper",
        "motor": "traction-motor", "fan_rotor": "fan-rotor", "crack": "cracked-plate", "oring": "o-ring-face-seal", "shaft": "shaft-shoulder-fatigue",
        "enclosure": "sealed-enclosure", "steel_frame": "steel-portal-frame"}
assert set(SLUG) == {c[0] for c in GALLERY}, "every gallery card needs a page name"
FILE = {k: f"{s}.html" for k, s in SLUG.items()}
DISC = {"struct": "Structures and vibration", "fluid": "Thermal and fluids", "vehicle": "Vehicle dynamics",
        "geom": "Geometry automation", "workflow": "Workflow validation", "em": "Electric machines"}
# the top bar speaks to a visitor deciding whether to hire: the lead studies, all the work, what's on offer and the
# method. The requirements table, the grading tasks and the in-progress page are linked where they matter on the
# home page, and from every page's footer.
NAV = [("index.html#cases", "Case studies", "cases"), ("index.html#work", "All work", "work"),
       ("index.html#offer", "Working together", "offer"), ("how-i-work.html", "How I work", "how-i-work")]
# a study's address: its own page, or its part of a report's page
STUDY_URL = {c[0]: (f"{FILE[PART_OF[c[0]]]}#{c[0]}" if c[0] in PART_OF else FILE[c[0]]) for c in CARDS}
# the old single page's sections, for links written as "#section" and for links people already shared
SECTION_URL = {"work": "index.html#work", "tasks": "grading.html", "findings": "how-i-work.html#lessons",
               "how": "how-i-work.html", "next": "in-progress.html", "get-in-touch": "#contact",
               "reqs": "requirements.html", "top": "index.html"}
# case files whose recorded assumptions, limits and inputs are shown on the study's page
CASES = {"fea": ["cantilever_tet10"], "cantilever_opt": ["bracket_opt"], "strap": ["strap_hole_size"],
         "fatigue": ["strap_fatigue_load"], "strap_proof": ["strap_proof_r1"], "contact": ["contact_roller_mesh"],
         "modal": ["bracket_modal_thickness"], "strut": ["strut_length"], "bolted_joint": ["bolted_joint_mesh_r1"],
         "pv_nozzle": ["pv_nozzle_mesh", "pv_nozzle_crotch_mesh_r1"], "bracket_opt": ["clevis_opt_r2"], "cfd": ["channel_header_tolerance", "duct_side_walls"],
         "thermal": ["fin_tolerance"], "heat": ["heated_channel_mesh_r2"], "cold_plate": ["cold_plate_mesh_r1"],
         "pipe": ["pipe_rans_mesh_r3"], "step": ["step_mesh"], "random_vib": ["bracket_random_mesh"], "bracket_uq": ["bracket_random_uq"],
         "fan_rotor": ["rotor_fan_design"], "crack": ["edge_crack_mesh_r2"], "oring": ["oring_seal_corners"], "shaft": ["shaft_fillet_radius", "shaft_fillet_size"], "enclosure": ["enclosure_k5_eps0p9_e", "enclosure_fix_k5_eps0p9_br2_long"], "steel_frame": ["steel_frame_portal", "steel_frame_beam_bracing"], "suspension": ["qc_speed_bump", "qc_bump_liftoff"], "cad": ["mounting_plate"],
         "baseline": ["msd_step"], "motor": ["motor_prius_rev5_torque"]}
# drawings from scripts/make_drawings.py (site/v2/dwg_<key>.webp), shown in each study's model section
DRAWINGS = {
    "fea": ("Side view of the bar with its fixed root and tip load, and its square section", "The bar as modelled: fixed at the root, 1 kN at the tip."),
    "cantilever_opt": ("Side view of the tapered bar over the dashed outline of a straight bar", "The optimised taper against the lightest straight bar that passes, shown dashed."),
    "strap": ("Plan and edge view of the strap with its central hole and the pull at each end", "The strap in plan and edge view. The darker quarter is the part that's modelled."),
    "modal": ("Plan and side view of the clamped arm with its first mode shape", "The arm in plan and side view, with the shape of its first mode sketched in blue."),
    "strut": ("Side view of the strut on its pinned ends with the bow drawn enlarged", "The strut, its pinned ends and its initial bow, which is drawn 40 times larger than it is."),
    "contact": ("The roller on its plate, with the contact strip enlarged in a circle", "The roller on its plate. The contact is too small to see at this scale, so it's enlarged on the right."),
    "bolted_joint": ("Section through the two plates and the bolt hole, with the clamp force on the washer faces and the side load", "A section through the bolt axis. The bolt is drawn dashed for reference; in the model it's represented by its clamp force on the washer faces."),
    "pv_nozzle": ("Section through the shell and nozzle walls at the junction, with the weld fillet, the lines at the weld toes and the line through the inner corner", "A section through both axes at the junction. Right: the lines at the weld toes, where the 12 mm nozzle passes. Left: the line through the sharp inner corner, where it fails. The junction is symmetric, so each side shows one placement."),
    "bracket_opt": ("Front, side and three-quarter views of the clevis bracket with its main dimensions", "The chosen design, drawn from its CAD model: hidden-line views with the dimensions the optimiser set."),
    "cad": ("Plan and edge view of the plate with six holes and its dimensions", "The plate with the 9 mm holes, the only size that meets both rules."),
    "cfd": ("The flow domain: a supply header narrowing smoothly into a long thin channel", "The flow domain: the supply header, the smooth contraction and the 1 mm channel. Heights are drawn larger so the channel can be seen."),
    "thermal": ("Front and side view of the fin standing on its base", "The fin on its base, in front and side view."),
    "heat": ("The channel between two walls, heated over 50 mm", "The heated channel. Heights are drawn five times larger."),
    "cold_plate": ("Two plates on a thin water channel, heated over a footprint and held at both ends", "The plates on their channel, heated over the footprint and held at both ends. Heights are drawn three times larger."),
    "pipe": ("The pipe's cross-section with a thin wedge marked, and the wedge enlarged with its mesh", "Left: the pipe and the thin wedge that's modelled. Right: the wedge, with its cells graded towards the wall."),
    "suspension": ("Schematic of the body on a spring and damper, on a wheel, on a tire, crossing a bump", "The quarter-car model: one corner of the car as two masses, a spring, a damper and a tire."),
    "baseline": ("Schematic of a mass on a spring and a damper with a force applied", "The system: one mass on a spring and a damper, pushed by a sudden force."),
    "motor": ("Cross-section of the motor, with one pole enlarged to show the magnets in their pockets, the slots and the air gap", "The motor's cross-section, drawn from the study's machine definition: eight poles of magnets in the rotor and 48 slots of copper in the stator. The magnets are 18.9 × 6.5 mm, from the parts list, centred in 6.80 mm pockets; the thin gap either side is polymer moulding."),
    "step": ("The channel in side view: the step, the inlet duct, the separation bubble behind the step and the reattachment point, with the stretch where skin friction is scored", "The channel as modelled, heights to scale and the length cut short. The flow separates at the step, turns back under the dashed line and reattaches at the dot. Skin friction is scored from 10 to 30 step heights; the pressure recovery from 4 step heights before the step to 30 after it."),
    "fatigue": ("Plan view of the strap with its hole and the pull at each end, beside a sketch of the load cycling from zero to 5 kN", "The strap from study 2 and its service load: zero to 5 kN and back, about ten million times. Fatigue is judged at the hole edge."),
    "strap_proof": ("Plan view of the strap with a small yielded zone at the hole edge, beside a sketch of one 15 kN proof load followed by smaller service cycles", "The same strap, pulled once to 15 kN before it goes into service. The hole edge yields in a small zone; the rest stays elastic."),
    "bracket_uq": ("Side view of the arm on the shaker table, above four small distributions for damping, test level, fatigue strength and thickness", "The shaker test from study 21, with the four inputs that are only known within a range, and the spread assumed for each."),
    "crack": ("The steel plate in side view, pulled at both ends, with a 2 mm crack at one edge and the 37 mm critical crack dashed, above a sketch of the stress cycle", "The plate, pulled at both ends with a stress that cycles from 15 to 150 MPa. A crack starts at the 2 mm that inspection can find and grows a little every cycle, until it reaches the critical 37 mm."),
    "oring": ("Section through the cover's face groove as the cover lands: the O-ring against the groove's outer wall, the 0.74 mm still to close, the coolant pressure from inside, and the tolerance stack", "The seal as the cover lands, to scale: the ring sits against the groove's outer wall and stands 0.74 mm proud, which the cover squeezes out. Coolant reaches it from the inside. The lighter upper half of the ring is what's modelled, axisymmetric about the pump's axis."),
    "steel_frame": ("Elevation of the single-bay steel portal: two W10x33 columns on fixed bases, a W14x30 beam across the 6 m span with the distributed load on it and the sideways load at the left knee, and the two sections drawn larger beside it", "The frame to scale, with the client's factored loads and the service loads in brackets, and the two W-shapes at four times the frame's scale. The beam's bracing isn't specified, so it's taken as unbraced over the whole span. On the right, the three limits."),
    "shaft": ("Side view of the stepped gearbox shaft, 32 mm stepping up to 40 mm, clamped at the large end with rotating bending and a steady torque on the small end, and the 1.6 mm fillet enlarged with its tolerance and the peak-stress point", "The shaft as drawn, to scale: the loads on the small end, the clamp 80 mm past the shoulder, and the fillet enlarged six times with its tolerance. The peak-stress point is the model's result, as is the fix in the last line."),
    "enclosure": ("Section through the sealed box: aluminium walls around still air, a circuit board at mid-height with the regulator U1 at its middle and the capacitor C1 near its left end, the recommended bridge from U1 up to the lid, and heat leaving through the walls to the air outside", "The box in section, to scale. The board hangs in the air with a gap at each edge, so as drawn its heat leaves only through the air and by radiation. The hatched block is the redesign: a bridge from U1 to the lid. C1 sits near the board's left end. On the right, what isn't known and the client's four limits."),
    "fan_rotor": ("Side view of the fan rotor: a shaft between two bearings on springs and dampers, a steel disc at mid-span with the unbalance marked, and below it the shaft's bent shape on soft and stiff pedestals", "The model: a centre-hung fan, its impeller between two bearings. The impeller is a steel disc at mid-span and each bearing with its pedestal is a spring and a damper. Below: the 65 mm shaft's first mode, from the rotor model, on soft and stiff pedestals. On soft ones the ends move a third as much as the middle, so the critical speed drops."),
    "random_vib": ("Side view of the arm clamped to a shaker table, with the three shaking directions and the flat input spectrum", "The test: the arm clamped to a shaker table and shaken on one axis at a time. The stress is read on the surface near the clamp and extrapolated to it; the tip clearance is drawn six times larger so it can be seen."),
}
# the one-line question each study page opens with, before the setup drawing and the answer
QUESTION = {
    "bracket_opt": "How light can a machined aluminium clevis bracket be and still carry its 4.8 kN pin load within 100 MPa and 0.10 mm of movement?",
    "pv_nozzle": "Can a 200 mm nozzle go into a 1 m pressure vessel at 3.5 MPa without a reinforcing pad, and how thin can the head be?",
    "bolted_joint": "Does an M8 bolt clamping two steel plates carry a 2 kN side load by friction alone, and stay closed under a 10 kN pull?",
    "strap": "How big a cable hole can an aluminium strap take, how long will it last in service, and what does a 15 kN proof test do to it?",
    "strut": "How long can a pinned aluminium strut be and still take twice its 8 kN load before it yields, allowing for a slight bow?",
    "contact": "Does a 100 mm steel roller carrying 500 N per millimetre stay within its limits on contact pressure and on shear below the surface?",
    "cantilever_bracket": "Does a 200 mm steel bracket carry 1 kN at its tip within its limits, and how light can it be made once fatigue matters?",
    "bracket_arm": "How thin can a steel bracket arm near an engine be, does it survive a random vibration test, and how sure is that pass?",
    "fan_rotor": "Is a 50 mm shaft stiff enough to keep a fan's critical speed out of its 1,000 to 3,000 rpm range, and if not, what is?",
    "crack": "A 2 mm crack at the edge of a steel plate in cyclic tension: how long until it fails, and how often must the plate be inspected?",
    "oring": "Does an O-ring seal a 3 bar coolant-pump cover at every corner of its tolerance stack, within the bolts' force and the groove's room?",
    "steel_frame": "Does a steel portal frame for an equipment platform meet AISC 360-22 on strength and deflection, and how much does the beam's bracing matter?",
    "shaft": "Does a gearbox shaft's shoulder fillet survive rotating bending and a 1.5 × overload, and if not, what step does?",
    "cold_plate": "Does a water-cooled aluminium plate keep the electronics on it under 45 °C, with the coolant and the thermal stress inside their limits?",
    "enclosure": "Does every part in a sealed electronics box stay within its own limit, bare or painted inside, and if not, what fixes it?",
    "turbulent_flow": "Can this CFD setup be trusted for pressure drop and flow layout? Checked against measurements, in a pipe and behind a step.",
    "cfd": "Does a 1 mm coolant passage stay within its 30 Pa pressure budget and keep enough shear on its walls to limit fouling?",
    "thermal": "Does the tip of an aluminium heat-sink fin stay above 60 °C, and how sure can I be?",
    "motor": "Can open-source tools model a production traction motor well enough for design work, judged against its test data?",
    "suspension": "Which damper rates give a compact car's front corner good ride, enough travel and steady tire load over a bump and a rough road?",
    "cad": "Which clearance hole size keeps a six-hole aluminium plate under 150 g and leaves enough material at the edges?",
    "baseline": "How much damping does a mass on a spring need to meet its targets, and does the workflow get a known answer right?",
}
# the drawing that opens a page made of several studies: the one that best shows the part
SETUP = {"cantilever_bracket": "fea", "strap": "strap", "cold_plate": "cold_plate", "bracket_arm": "modal", "turbulent_flow": "pipe"}


def setup_key(gk: str):
    k = SETUP.get(gk, gk)
    return k if k in DRAWINGS and (HERE / "v2" / f"dwg_{k}.webp").exists() else None


# the home page leads with the strongest studies (the user, 2026-11-24). Each is told as a pair, the part then the
# answer, with one headline number, two sentences and what the checks caught (its lesson on the How I Work page).
# The words are typed here; "quotes" are the numbers they use, and the build fails if the study's own card or lesson
# stops saying them, so a changed result can't leave the home page behind.
LEAD = [
    dict(key="motor", number="18 %", unit="above the laboratory's test", quotes=["about 18 % high"],
         line="A production traction motor, modelled from its drawings and parts list with nothing tuned. The model "
              "read high on back-EMF and torque, and I traced it, cause by cause, to the magnets."),
    dict(key="bracket_opt", number="78 designs", unit="searched by an AI agent", quotes=["78 designs", "372 g", "98.3 MPa"],
         line="The lightest machined bracket that stays under 100 MPa: 372 g at 98.3 MPa. The checks threw out the "
              "agent's first two answers before this one stood."),
    dict(key="pv_nozzle", number="24 %", unit="over the limit, or 0.9 % under", quotes=["fails by 24 %", "0.9 %"],
         line="A pressure vessel nozzle that passes its design code on one line and fails on another, on the same "
              "converged model. I'd judge it by the line that fails."),
]
# a lead study can show a different picture from its study page's viewer: the motor's field map catches the eye
LEAD_VIEW = {"motor": ("v2/fig_motor_field.webp", "The motor's cross-section coloured by flux density with no current in the "
                       "winding, and one pole enlarged: the thin steel bridges above the magnets saturate")}
# what can be hired, in the visitor's words (draft, 2026-11-24: the user has not signed these off yet)
SERVICES = [
    ("Build and check a model", "From your drawings and requirements to a verdict on each requirement, with the model, "
                                "the independent check behind it and the files to repeat it."),
    ("Check a result you already have", "An independent second answer to a number someone else produced: a hand "
                                        "calculation, a second tool or a mesh study, and a plain statement of what holds."),
    ("Automate a repeated analysis", "A sweep or an optimisation loop that an AI agent runs under written procedures, "
                                     "with the same checks on every run."),
    ("Engineering tasks for AI training", 'Requirement-to-verdict tasks with automated graders, like '
                                          '<a href="grading.html">the ones on the grading page</a>.'),
]
# card order on the home page and through the pager: these first, the rest as listed in CARDS
FRONT = ["motor", "bracket_opt", "turbulent_flow", "pv_nozzle", "steel_frame", "bracket_arm", "cold_plate", "enclosure", "fan_rotor", "shaft", "oring",
         "crack", "bolted_joint"]

import tomllib

import extras
import make_og
import titlecase

_fr = HERE / "v2" / "frames.json"
_frames = json.loads(_fr.read_text(encoding="utf-8")) if _fr.exists() else {}
for v in VP:                                   # load-step frames for the viewer's slider
    f = _frames.get(v["study"])
    if f:
        v["frames"], v["frames_main"] = f["frames"], f["main"]
assert sorted(v["study"] for v in VP) == sorted(c[0] for c in CARDS), "every study needs exactly one viewer entry"
for v in VP:
    v["card"] = PART_OF.get(v["study"], v["study"])
    if v["study"] in PART_OF:
        v["part"] = PART_LABEL[v["study"]]
        v["main"] = GROUPS[v["card"]]["main"] == v["study"]
assert set(FRONT) <= {c[0] for c in GALLERY}, set(FRONT) - {c[0] for c in GALLERY}
GALLERY.sort(key=lambda c: FRONT.index(c[0]) if c[0] in FRONT else len(FRONT))     # stable: the rest keep CARDS order
corder = [c[0] for c in GALLERY]
VP.sort(key=lambda v: (corder.index(v["card"]),
                       GROUPS[v["card"]]["parts"].index(v["study"]) if v["card"] in GROUPS else 0))

# gallery thumbnail for study 11: the wall and bulk temperature panel of its response plot
th_heat = HERE / "v2" / "th_heat.webp"
if not th_heat.exists():
    from PIL import Image
    src = Image.open(HERE / "v2" / "heat_response.webp").convert("RGB").crop((10, 80, 725, 535))
    src.thumbnail((760, 470), Image.LANCZOS)
    canvas = Image.new("RGB", (800, 500), (252, 252, 251))
    canvas.paste(src, ((800 - src.width) // 2, (500 - src.height) // 2))
    canvas.save(th_heat, "WEBP", quality=88)

# home cards open with the setup, the user's rule for every study (2026-11-23): the part first, then the result. Each
# card's left picture is cut from the study's drawing as the build runs, so it changes with the drawing; the result
# chart sits beside it, and the finding and the verdict under both.
CARD_CROP = {"oring": (0, 0, 0.655, 1), "fan_rotor": (0, 0, 1, 0.56), "shaft": (0, 0, 0.74, 0.73), "enclosure": (0.1, 0, 0.67, 0.84), "steel_frame": (0, 0, 0.75, 1)}     # study: (x0, y0, x1, y1) as fractions of the drawing's content, where the part is only part of it


def card_thumb(gk: str):
    """v2/tc_<gk>.webp from the study's setup drawing: title block cut off, trimmed to the drawing, fitted to 16:10."""
    import numpy as np
    from PIL import Image
    dk = setup_key(gk)
    if dk is None:
        return None
    im = Image.open(HERE / "v2" / f"dwg_{dk}.webp").convert("RGB")
    bg = im.getpixel((2, 2))
    ink = np.abs(np.asarray(im, dtype=int) - np.array(bg)).sum(axis=2) > 24
    h = ink.shape[0]
    rules = [r for r in np.where(ink.mean(axis=1) > 0.8)[0] if r > 0.7 * h]
    assert rules, f"no title-block rule found in dwg_{dk}"
    r = max(rules)                       # the title block's rule is the lowest long line (a road or a floor can be long too)
    while r - 1 in rules:
        r -= 1
    body = ink[: r - 6]
    ys, xs = np.where(body)
    x0, x1, y0, y1 = xs.min(), xs.max() + 1, ys.min(), ys.max() + 1
    if gk in CARD_CROP:
        f = CARD_CROP[gk]
        w, hh = x1 - x0, y1 - y0
        x0, y0, x1, y1 = (round(x0 + f[0] * w), round(y0 + f[1] * hh), round(x0 + f[2] * w), round(y0 + f[3] * hh))
    im = im.crop((x0, y0, x1, y1))       # only the drawing: padding to 16:10 can't bring back the title block or cut notes
    x0, y0, x1, y1 = 0, 0, x1 - x0, y1 - y0
    m = 0.04 * max(x1 - x0, y1 - y0)
    x0, y0, x1, y1 = x0 - m, y0 - m, x1 + m, y1 + m
    w, hh = x1 - x0, y1 - y0
    if w / hh > 1.6:
        cy, hh = (y0 + y1) / 2, w / 1.6
        y0, y1 = cy - hh / 2, cy + hh / 2
    else:
        cx, w = (x0 + x1) / 2, hh * 1.6
        x0, x1 = cx - w / 2, cx + w / 2
    canvas = Image.new("RGB", (round(w), round(hh)), bg)
    canvas.paste(im, (round(-x0), round(-y0)))
    canvas = canvas.resize((1200, 750), Image.LANCZOS)
    out = HERE / "v2" / f"tc_{gk}.webp"
    canvas.save(out, "WEBP", quality=90)
    return out.name


CARD_IMG = {g[0]: card_thumb(g[0]) for g in GALLERY}        # None for a study with no drawing: its card shows the result alone

esc = html.escape
CARD = {c[0]: c for c in CARDS}
GAL = {c[0]: c for c in GALLERY}


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", re.sub(r"<[^>]+>", "", text).lower()).strip("-")


def featured_fill(text: str) -> str:
    """The optimiser's write-up: the wipe's labels and the legends built from the renders' own bands."""
    w = json.loads((HERE / "v2" / "wipe.json").read_text(encoding="utf-8"))
    sec = json.loads((HERE / "v2" / "clevis_section.json").read_text(encoding="utf-8"))
    scols = ["#%02x%02x%02x" % tuple(round(c * 255) for c in rgb) for rgb in sec["band_colors"]]
    slegend = ('<span class="wipe-legend" aria-label="von Mises stress, MPa"><span class="wl-bar">'
               + "".join(f'<i style="background:{c}"></i>' for c in scols) + '</span><span class="wl-ticks">'
               + "".join(f'<span style="left:{100 * (v - sec["vmin"]) / (sec["vmax"] - sec["vmin"]):.3f}%">{lab}</span>'
                         for v, lab in ((0, "0"), (20, "20"), (40, "40 MPa"), (55, "55+")))
               + '</span></span>')
    s = scenes["bracket_opt"]                      # the same 0-110 MPa scale and bands as the pair
    cols = ["#%02x%02x%02x" % tuple(round(c * 255) for c in rgb) for rgb in s["band_colors"]]
    legend = ('<div class="wipe-legend" aria-label="von Mises stress, MPa"><span class="wl-bar">'
              + "".join(f'<i style="background:{c}"></i>' for c in cols) + '</span>'
              + '<span class="wl-ticks">'
              + "".join(f'<span style="left:{100 * (v - s["vmin"]) / (s["vmax"] - s["vmin"]):.3f}%">{lab}</span>'
                        for v, lab in ((s["vmin"], f'{s["vmin"]:.0f}'), (50, "50"), (100, "100 MPa limit")))
              + '</span></div>')
    return (text.replace("{{SECTION_MAX}}", f'{sec["cut_max_MPa"]:.0f}').replace("{{SECTION_LEGEND}}", slegend)
                .replace("{{WIPE_START}}", f'Start · {w["wipe_start"]["mass_g"]:.1f} g · peak {w["wipe_start"]["peak_MPa"]:.1f} MPa')
                .replace("{{WIPE_D}}", f'Design D · {w["wipe_d"]["mass_g"]:.1f} g · peak {w["wipe_d"]["peak_MPa"]:.1f} MPa')
                .replace("{{WIPE_LEGEND}}", legend))


_FRAG = re.compile(r'\s*<section class="study" id="(\w+)">\s*<div class="study-head">\s*<span class="label">(.*?)</span>\s*'
                   r'<h2>(.*?)</h2>\s*</div>(.*)</section>\s*$', re.S)


def fragment(key: str) -> dict:
    """A study's hand-written write-up (site/studies/<key>.html): its label, title and body."""
    m = _FRAG.match((HERE / "studies" / f"{key}.html").read_text(encoding="utf-8"))
    assert m and m.group(1) == key, f"studies/{key}.html isn't a study section"
    return {"label": m.group(2).strip(), "title": m.group(3).strip(), "body": featured_fill(m.group(4).rstrip())}


def case_record(key: str) -> str:
    """The case file's own record for a study: its description, assumptions, limits and inputs, as written
    before the run. Shown collapsed under the model section, for readers who want the exact inputs."""
    blocks = []
    for name in CASES.get(key, []):
        path = f"cases/{name}.toml"
        d = tomllib.loads((REPO / path).read_text(encoding="utf-8"))
        c = d.get("case", {})
        link = (f'<a class="ext" href="{extras.gh(path)}">{path} ↗</a>' if extras.tracked(path) else path)
        rows = "".join(f"<tr><td>{esc(k)}</td><td>{esc(', '.join(f'{x:g}' if isinstance(x, float) else str(x) for x in v) if isinstance(v, list) else (f'{v:g}' if isinstance(v, float) else str(v)))}</td></tr>"
                       for k, v in d.get("parameters", {}).items())
        blocks.append(
            f'<p class="case">{link}</p><p>{esc(c.get("description", ""))}</p>'
            + (f'<h4>Assumptions, and how each is checked</h4><ul>{"".join(f"<li>{esc(a)}</li>" for a in c["assumptions"])}</ul>' if c.get("assumptions") else "")
            + (f'<h4>Limits</h4><ul>{"".join(f"<li>{esc(a)}</li>" for a in c["limitations"])}</ul>' if c.get("limitations") else "")
            + (f'<h4>Inputs</h4><div class="table-wrap"><table><thead><tr><th>Input</th><th>Value</th></tr></thead><tbody>{rows}</tbody></table></div>' if rows else ""))
    if not blocks:
        return ""
    return ('<details class="record"><summary>The case file: recorded assumptions, limits and inputs</summary>'
            '<div class="record-body"><p>This is the study\'s own record, written before the run and saved with it, in the '
            'shorthand of the case file.</p>' + "".join(blocks) + "</div></details>")


def _block_start(body: str, i: int) -> int:
    """Where the section whose heading starts at i begins: before a wrapper such as <div class="caught"> that opens it."""
    head = body[:i].rstrip()
    if head.endswith(">") and re.search(r"<div[^>]*>$", head):
        return re.search(r"<div[^>]*>$", head).start()
    return i


def model_first(body: str) -> str:
    """Setup before significance: move "Why it matters" to just after "The model", so the model follows the answer."""
    hs = [(_block_start(body, m.start()), re.sub(r"<[^>]+>", "", m.group(1)).strip().lower())
          for m in re.finditer(r"<h3>(.*?)</h3>", body, re.S)]
    names = [n for _, n in hs]
    if "why it matters" not in names or "the model" not in names:
        return body
    i, j = names.index("why it matters"), names.index("the model")
    if j < i:
        return body
    w0, w1 = hs[i][0], hs[i + 1][0]
    m1 = hs[j + 1][0] if j + 1 < len(hs) else len(body)
    return body[:w0] + body[w1:m1] + body[w0:w1] + body[m1:]


def study_body(key: str, level: int, prefix: str = "", skip_dwg: bool = False) -> tuple[str, list]:
    """A study's body with its headings at `level` (2 on its own page, 3 as a part of a report), each given an
    id for the page's contents list; the case record goes where the body asks for it ({{CASE}}) or at the end."""
    body = model_first(fragment(key)["body"])
    rec = case_record(key)
    if not skip_dwg and key in DRAWINGS and (HERE / "v2" / f"dwg_{key}.webp").exists():
        alt, cap = DRAWINGS[key]
        rec = (f'<figure class="drawing"><div class="plate"><img src="v2/dwg_{key}.webp" alt="{esc(alt)}" loading="lazy"></div>'
               f'<figcaption>{cap}</figcaption></figure>\n    ' + rec)
    body = body.replace("{{CASE}}", rec) if "{{CASE}}" in body else body + ("\n    " + rec if rec else "")
    ev = evidence_block(key)
    if ev:
        body += f"\n    <h3>Evidence</h3>\n{ev}"
    toc = []

    def head(m):
        text = m.group(1)
        hid = f"{prefix}{slugify(text)}"
        toc.append((hid, re.sub(r"<[^>]+>", "", text)))
        return f'<h{level} id="{hid}">{text}</h{level}>'
    body = re.sub(r"<h3>(.*?)</h3>", head, body, flags=re.S)
    if level == 2:                                # sub-headings follow their section up one level, without ids
        body = re.sub(r"<h4>(.*?)</h4>", r"<h3>\1</h3>", body)
    return body, toc


def evidence_block(key: str) -> str:
    ev = extras.evidence(key)
    if not ev:
        return ""
    items = [f'<li><a class="ext" href="{ev["doc"]}">Full write-up on GitHub</a></li>'] if ev["doc"] else []
    if ev.get("memo"):
        items.append(f'<li><a class="ext" href="{ev["memo"]}">Sample client memo from this study</a></li>')
    runs = "".join(f'<li><a class="ext" href="{u}">{esc(label)}</a></li>' for label, u in ev["runs"])
    return ('    <div class="side-card">' + (f'<ul class="ev-list">{"".join(items)}</ul>' if items else "")
            + (f'<p class="label">Run reports, with every check and the saved inputs</p><ul class="ev-list ev-runs">{runs}</ul>' if runs else "")
            + "</div>")


CHIP = extras.CHIP


def side_reqs(keys: list[str]) -> str:
    rows = []
    for sid, no, title, items in extras.REQS:
        if sid not in keys:
            continue
        if len(keys) > 1:                               # a report: say which study each requirement belongs to
            rows.append(f'<li class="r-study"><a href="#{sid}">{esc(PART_LABEL[sid])}</a></li>')
        for req, limit, result, v in items:
            cls, word = CHIP[v]
            rows.append(f'<li><span class="r-what">{esc(req)}</span><span class="r-num">{esc(limit)} · {esc(result)}</span>'
                        f'<span class="chip {cls}">{word}</span></li>')
    return f'<div class="side-card"><h2>Requirements</h2><ul class="side-reqs">{"".join(rows)}</ul></div>' if rows else ""


def viewer_html(entries: list[dict]) -> str:
    first = next((v for v in entries if v.get("main")), entries[0])
    return ((PAGES / "viewer.html").read_text(encoding="utf-8")
            .replace("{{VP_FIRST_IMG}}", first["img"]).replace("{{VP_FIRST_ALT}}", esc(first["model"])))


def viewer_scripts(entries: list[dict]) -> str:
    s = f'<script>window.VP = {json.dumps(entries, ensure_ascii=False)};</script>\n<script src="assets/viewer.js?v={{{{ASSET_V}}}}"></script>'
    if any(v.get("mesh") for v in entries):
        s += '\n<script src="assets/viewer3d.js?v={{ASSET_V}}"></script>'
    return s


def study_page(gk: str) -> dict:
    key, no, group, d, title, answer, verdict, tools, thumb = GAL[gk]
    parts = GROUPS[gk]["parts"] if gk in GROUPS else [gk]
    entries = [v for v in VP if v["card"] == gk]
    top = setup_key(gk)
    toc_html = []
    if gk in GROUPS:
        label = GROUPS[gk]["label"]
        chunks = []
        for p in parts:
            fr = fragment(p)
            body, toc = study_body(p, 3, prefix=f"{p}-", skip_dwg=(p == top))
            chunks.append(f'      <section class="part" id="{p}" data-part="{p}">\n        <div class="part-head"><span class="label">{fr["label"]}</span>'
                          f'<h2>{fr["title"]}</h2></div>{body}\n      </section>')
            toc_html.append(f'<li class="t-part"><a href="#{p}">{esc(PART_LABEL[p])}</a></li>')
            toc_html += [f'<li class="t-sub"><a href="#{hid}">{esc(t)}</a></li>' for hid, t in toc]
        main = "\n".join(chunks)
    else:
        fr = fragment(gk)
        label = fr["label"]
        main, toc = study_body(gk, 2, skip_dwg=(gk == top))
        toc_html = [f'<li><a href="#{hid}">{esc(t)}</a></li>' for hid, t in toc]
    i = corder.index(gk)
    prev_, next_ = (GALLERY[i - 1] if i > 0 else None), (GALLERY[i + 1] if i + 1 < len(GALLERY) else None)
    pager = '<nav class="pager" aria-label="More studies">'
    if prev_:
        pager += f'<a class="prev" href="{FILE[prev_[0]]}"><small>← Previous study</small><b>{esc(prev_[4])}</b></a>'
    if next_:
        pager += f'<a class="next" href="{FILE[next_[0]]}"><small>Next study →</small><b>{esc(next_[4])}</b></a>'
    pager += "</nav>"
    side = (f'<div class="side-card"><h2>At a glance</h2><dl>'
            f'<div><dt>Study</dt><dd>{esc(no)}</dd></div><div><dt>Discipline</dt><dd>{DISC[group]}</dd></div>'
            f'<div><dt>Tools</dt><dd>{esc(tools)}</dd></div>'
            f'<div><dt>Verdict</dt><dd><span class="v v-{verdict}">{VERDICT[verdict]}</span></dd></div></dl></div>'
            + side_reqs(parts)
            + f'<div class="side-card side-toc"><h2>On this page</h2><ul class="toc">{"".join(toc_html)}</ul></div>')
    setup_html = ""
    if top:
        alt, cap = DRAWINGS[top]
        setup_html = (f'    <figure class="study-setup"><a class="plate" href="v2/dwg_{top}.webp" title="Open the drawing full size">'
                      f'<img src="v2/dwg_{top}.webp" alt="{esc(alt)}"></a>'
                      f'<figcaption><b>The setup.</b> {cap}</figcaption></figure>')
    body = f'''  <div class="wrap">
    <nav class="crumbs" aria-label="Breadcrumb"><a href="index.html#work">All studies</a><span>/</span><span>{DISC[group]}</span></nav>
    <header class="study-hero">
      <p class="eyebrow">{label}</p>
      <h1>{esc(title)}</h1>
      <p class="study-q"><span class="k">The question</span>{esc(QUESTION[gk])}</p>
    </header>
{setup_html}
    <div class="study-answer">
      <p class="k">The answer</p>
      <span class="v v-{verdict}">{VERDICT[verdict]}</span>
      <p class="study-lede">{esc(answer)}</p>
    </div>
{viewer_html(entries)}
    <div class="study-layout">
      <article class="study-main">
{main}
      </article>
      <aside class="study-side" aria-label="Summary of this study">
        {side}
      </aside>
    </div>
    {pager}
  </div>
'''
    og = make_og.study(SLUG[gk], f"Study {no} · {d.replace('New · ', '').replace('Featured · ', '')}", titlecase.title_case(title),
                       VERDICT[verdict], HERE / "v2" / f"th_{thumb}.webp", figure=entries[0].get("kind") == "figure")
    return {"file": FILE[gk], "title": f"{title} · {AUTHOR}", "og_title": title, "desc": answer, "nav": "work",
            "main": body, "scripts": viewer_scripts(entries), "og": og, "og_alt": f"{title}: result render",
            "viewer": True, "has3d": any(v.get("mesh") for v in entries)}


assert set(QUESTION) == set(GAL), "every study page needs its one-line question"


def kind(d: str) -> str:
    """A card's kind of analysis, without its 'New' or 'Featured' flag."""
    return re.sub(r"^(New|Featured) · ", "", d)


def first_part(text: str, least: int) -> str:
    """The opening of a card's answer: whole sentences until there are at least `least` characters."""
    out = ""
    for s in re.split(r"(?<=[.!?])\s+(?=[A-Z0-9])", text):
        out = (out + " " + s).strip()
        if len(out) >= least:
            break
    return out


def req_counts() -> dict:
    counts = {"met": 0, "fail": 0, "held": 0}
    for _, _, _, items in extras.REQS:
        for *_, v in items:
            counts[extras.COUNT_AS[v]] += 1
    return counts


# the method's four steps and the mistakes the checks caught are written once, on the How I Work page; the home
# page reads them from there
_how = (PAGES / "how.html").read_text(encoding="utf-8")
FLOW = re.findall(r"<li><b>(.*?)</b><span>(.*?)</span></li>", _how.split('<ol class="steps">')[1].split("</ol>")[0])
LESSONS = re.findall(r'<article class="finding"><span class="label">(.*?)</span><h3>(.*?)</h3><p>(.*?)</p><a href="#(\w+)">', _how)
assert len(FLOW) == 4 and len(LESSONS) == _how.count('<article class="finding">'), (len(FLOW), len(LESSONS))
LESSON = {k: (label, title, text) for label, title, text, k in LESSONS}


def memo_excerpt() -> str:
    """The top of the sample client memo, as a page: its title, subject, status, verdict and first two findings."""
    memo = (REPO / extras.MEMO).read_text(encoding="utf-8")

    def md(s: str) -> str:
        return re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", esc(s))
    title = re.search(r"^# Technical Memo: (.*)$", memo, re.M).group(1)
    subject = re.search(r"\*\*Subject\*\* \| (.*?) \|", memo).group(1)
    status = re.search(r"\*\*Status\*\* \| (.*?) \|", memo).group(1)
    lead = re.search(r"## 1\. .*?\n\n(\*\*.*?\*\*)", memo, re.S).group(1)
    bullets = re.findall(r"^- (.*)$", memo.split("## 1.")[1].split("**Recommendation.**")[0], re.M)[:2]
    assert len(bullets) == 2, bullets
    return (f'          <p class="m-h">Technical memo</p><h4>{esc(title)}</h4>\n'
            f'          <dl><dt>Subject</dt><dd>{esc(subject)}</dd><dt>Status</dt><dd>{esc(status)}</dd></dl>\n'
            f'          <p class="m-lead">{md(lead)}</p>\n          <ul>' + "".join(f"<li>{md(b)}</li>" for b in bullets) + "</ul>")


def lead_case(i: int, L: dict) -> str:
    k = L["key"]
    assert k in GAL and k not in GROUPS and k in LESSON, f"lead study {k} needs its own card and a lesson on the How I Work page"
    _, no, group, d, title, answer, verdict, tools, _ = GAL[k]
    label, caught, ltext = LESSON[k]
    for q in L["quotes"]:
        assert q in answer or q in ltext, f'the home page says "{q}" about {k}, and neither its card nor its lesson does any more'
    v = next(x for x in VP if x["study"] == k)
    img, alt = LEAD_VIEW.get(k, (v["img"], v["model"]))
    plate = " on-plate" if k in LEAD_VIEW or v.get("kind") == "figure" else ""
    sk = setup_key(k)
    assert sk and CARD_IMG[k], f"lead study {k} needs a setup drawing"
    return f'''    <article class="lead-case{" flip" if i % 2 else ""}">
      <div class="lead-text">
        <p class="lead-tag">{i + 1:02d} · {DISC[group]}</p>
        <h3>{esc(title)}</h3>
        <p class="lead-q">{esc(QUESTION[k])}</p>
        <p class="big"><b>{esc(L["number"])}</b><span>{esc(L["unit"])}</span></p>
        <p class="say">{esc(L["line"])}</p>
        <p class="lead-caught"><i>What the checks caught</i>{caught}</p>
        <p class="go"><span class="v v-{verdict}">{VERDICT[verdict]}</span><a href="{STUDY_URL[k]}">Read the study →</a></p>
      </div>
      <a class="pair" href="{STUDY_URL[k]}" aria-label="Open the study: {esc(title)}">
        <figure class="on-plate"><img src="v2/{CARD_IMG[k]}" alt="{esc(DRAWINGS[sk][0])}" loading="lazy" width="1200" height="750"><figcaption>The part</figcaption></figure>
        <figure class="{plate.strip()}"><img src="{img}" alt="{esc(alt)}" loading="lazy"><figcaption>The answer</figcaption></figure>
      </a>
    </article>'''


def home_page(facts) -> dict:
    cards = "\n".join(
        f'''      <a class="wcard" href="{FILE[k]}" data-study="{k}" data-group="{g}">
        <span class="duo{'' if CARD_IMG[k] else ' one'}">{f'<img src="v2/{CARD_IMG[k]}" alt="" loading="lazy" width="1200" height="750">' if CARD_IMG[k] else ''}<img src="v2/th_{th}.webp" alt="" loading="lazy" width="800" height="500"></span>
        <span class="wmeta">{n} · {esc(kind(d))}</span>
        <span class="card-title">{esc(t)}</span>
        <span class="find">{esc(first_part(a, 50))}</span>
        <span class="v v-{v}">{VERDICT[v]}</span>
      </a>''' for k, n, g, d, t, a, v, tools, th in GALLERY)
    # what I can model: every kind of analysis as a tag that opens its study, by discipline, the largest first
    ranges = []
    order = ["struct", "fluid", "em", "vehicle", "geom", "workflow"]              # ties keep the filter buttons' order
    assert set(order) == set(DISC)
    for g in sorted(order, key=lambda g: -sum(c[2] == g for c in CARDS)):
        items = {kind(c[3]): c[0] for c in reversed(CARDS) if c[2] == g}          # the first study of a kind keeps the tag
        n = sum(c[2] == g for c in CARDS)
        if n == 1:                       # one study: its kind only repeats the heading, so name the part
            items = {re.split(r"[,:]", CARD[k][4])[0]: k for k in items.values()}
        tags = "".join(f'<a href="{STUDY_URL[k]}">{esc(label)}</a>' for label, k in reversed(items.items()))
        ranges.append(f'      <div class="rg"><h3><b>{n}</b> {DISC[g]}</h3><div>{tags}</div></div>')
    counts = req_counts()
    n_req = sum(counts.values())
    dots = "".join(f'<i class="{c}"></i>' for c in ("met", "fail", "held") for _ in range(counts[c]))
    lessons = "\n".join(f'          <li><a href="{STUDY_URL[k]}"><i>{label}</i><h4>{title}</h4></a></li>'
                        for label, title, _, k in LESSONS[:6])
    fill = {"{{LEADS}}": "\n".join(lead_case(i, L) for i, L in enumerate(LEAD)), "{{RANGE}}": "\n".join(ranges),
            "{{SERVICES}}": "\n".join(f"        <li><h3>{esc(a)}</h3><p>{b}</p></li>" for a, b in SERVICES),
            "{{MEMO}}": memo_excerpt(), "{{FLOW}}": "\n".join(f"      <li><b>{a}</b><span>{b}</span></li>" for a, b in FLOW),
            "{{DOTS}}": dots, "{{LESSONS}}": lessons, "{{CARDS}}": cards, "{{PARTS}}": str(len(GALLERY)),
            "{{REQ_COUNT}}": str(n_req), "{{MET}}": str(counts["met"]), "{{NOT_MET}}": str(counts["fail"]),
            "{{HELD}}": str(counts["held"]), "{{CAUGHT}}": str(len(LESSONS))}
    main = (PAGES / "home.html").read_text(encoding="utf-8")
    for a, b in fill.items():
        main = main.replace(a, b)
    legacy = {**STUDY_URL, **{k: FILE[k] for k in FILE}, **{k: v for k, v in SECTION_URL.items() if k not in ("work", "top")}}
    legacy.update({k: STUDY_URL[k] for k in PART_OF})          # a study inside a report keeps its own address
    legacy.pop("contact")        # index.html#contact is the contact section on every page; the roller study has its own page
    scripts = f"<script>window.LEGACY = {json.dumps(legacy)};</script>"
    return {"file": "index.html", "title": f"{AUTHOR} · Simulation Portfolio", "og_title": "Simulation, Proof Attached",
            "desc": f"{WORDS[len(CARDS)][1]} open-source simulation studies by {AUTHOR}, mechanical engineer: FEA, CFD, coupled "
                    "multiphysics and an optimisation loop, each checked against an independent reference.",
            "nav": "home", "main": main, "scripts": scripts, "og": make_og.make({**facts, "studies": len(CARDS)}),
            "og_alt": "A machined clevis bracket rendered with its stress contours, beside the page headline and its counts of studies, checks and runs",
            "home": True}


def reqs_page() -> dict:
    rows, counts = [], {"met": 0, "fail": 0, "held": 0}
    for sid, no, title, items in extras.REQS:
        for i, (req, limit, result, v) in enumerate(items):
            counts[extras.COUNT_AS[v]] += 1
            cls, word = CHIP[v]
            study = f'<a href="{STUDY_URL[sid]}"><span class="r-no">{no}</span> {esc(title)}</a>' if i == 0 else ""
            rows.append(f'          <tr{" class=\"r-first\"" if i == 0 else ""}><td>{study}</td><td>{esc(req)}</td>'
                        f'<td class="num">{esc(limit)}</td><td>{esc(result)}</td>'
                        f'<td><span class="chip {cls}">{word}</span></td></tr>')
    n = sum(counts.values())
    main = f'''  <div class="wrap band" style="padding-top:0">
    <div class="page-head">
      <p class="eyebrow">Requirements</p>
      <h1>Every requirement in one table</h1>
      <p>{n} requirements across the studies: <b class="c-pass">{counts["met"]} met</b>, <b class="c-fail">{counts["fail"]} not met</b>, <b class="c-warn">{counts["held"]} withheld</b>. "Not met" is still a verified answer: the design fails, and the study explains what would fix it. "Withheld" means the checks didn't support calling it either way, or that the result waits on open work. Each study's name links to its page.</p>
    </div>
    <div class="reqs open">
      <div class="table-wrap">
        <table>
          <thead><tr><th>Study</th><th>Requirement</th><th>Limit</th><th>Result</th><th>Verdict</th></tr></thead>
          <tbody>
{chr(10).join(rows)}
          </tbody>
        </table>
      </div>
    </div>
  </div>
'''
    return {"file": "requirements.html", "title": f"Every requirement · {AUTHOR}", "og_title": "Every requirement in one table",
            "desc": f"All {n} requirements across the simulation studies, each with its limit, result and verdict.",
            "nav": "requirements", "main": main, "scripts": ""}


def text_page(file, tpl, title, og_title, desc, nav, repl, scripts="") -> dict:
    main = (PAGES / tpl).read_text(encoding="utf-8")
    for a, b in repl.items():
        main = main.replace(a, b)
    return {"file": file, "title": f"{title} · {AUTHOR}", "og_title": og_title, "desc": desc, "nav": nav, "main": main,
            "scripts": scripts}


WORDS = {15: ("fifteen", "Fifteen"), 16: ("sixteen", "Sixteen"), 17: ("seventeen", "Seventeen"),
         18: ("eighteen", "Eighteen"), 19: ("nineteen", "Nineteen"), 20: ("twenty", "Twenty"),
         21: ("twenty-one", "Twenty-one"), 22: ("twenty-two", "Twenty-two"), 23: ("twenty-three", "Twenty-three"),
         24: ("twenty-four", "Twenty-four"), 25: ("twenty-five", "Twenty-five"), 26: ("twenty-six", "Twenty-six"),
         27: ("twenty-seven", "Twenty-seven"), 28: ("twenty-eight", "Twenty-eight"), 29: ("twenty-nine", "Twenty-nine"),
         30: ("thirty", "Thirty"), 31: ("thirty-one", "Thirty-one"), 32: ("thirty-two", "Thirty-two")}
TASK_WORDS = {4: "four", 5: "five", 6: "six", 7: "seven"}

facts = extras.repo_facts()
gdata = extras.grader_data()
gcheck = extras.check_js_against_python(gdata)
grader_body, grader_js = extras.grader_html(gdata)
term_html = "".join(
    f'<span class="t-row"><span class="t-id">{cid}</span><span class="t-{st.lower()}">{st}</span><span class="t-num">{val}</span><span class="t-tol">tol {tol}</span></span>'
    for cid, st, val, tol in term_lines)

pages = [home_page(facts)] + [study_page(c[0]) for c in GALLERY] + [
    text_page("how-i-work.html", "how.html", "How I work", "How I work: the same method for every study",
              "Requirements first, a model built as code, every number checked against something independent, and a "
              "report that links each requirement to its evidence. Where the AI agent fits, and the mistakes the checks caught.",
              "how-i-work", {"{{TERMINAL}}": term_html, "{{CAPS}}": extras.CAPS, "{{CODE_FACTS}}": extras.code_facts(facts),
                            "{{FAILURES}}": extras.failures_panel()}),
    text_page("grading.html", "grading.html", "Grading tasks", "Try grading an engineering answer",
              f"{TASK_WORDS[len(gdata)].capitalize()} engineering evaluation tasks built from verified simulation studies, each "
              "with a reference solution and an automated grader you can try on the page.",
              "grading", {"{{GRADER}}": grader_body, "{{TASK_COUNT_WORD}}": TASK_WORDS[len(gdata)]},
              scripts=f"<script>\n{grader_js}\n</script>"),
    text_page("in-progress.html", "progress.html", "In progress", "Studies in progress",
              "A flexible flag behind a cylinder (fluid-structure interaction).", "in-progress", {}),
    reqs_page(),
]

# ------------------------------------------------------------------ assemble, check and write every page
asset_v = __import__("hashlib").sha1(b"".join((HERE / "assets" / n).read_bytes()
                                              for n in ("site.css", "site.js", "viewer.js", "viewer3d.js"))).hexdigest()[:10]
layout = (PAGES / "layout.html").read_text(encoding="utf-8")
home_fill = {"{{STUDY_COUNT_WORD}}": WORDS[len(CARDS)][0], "{{STUDY_COUNT_TITLE}}": WORDS[len(CARDS)][1],
             "{{STUDY_COUNT}}": str(len(CARDS)), "{{MEMO_URL}}": extras.gh(extras.MEMO), "{{CHECKS}}": f"{facts['checks']:,}",
             "{{RUNS}}": str(facts["runs"]), "{{TASK_COUNT_TITLE}}": TASK_WORDS[len(gdata)].capitalize()}
built = {}
for p in pages:
    main = p["main"]
    for a, b in home_fill.items():
        main = main.replace(a, b)
    ids = set(re.findall(r'\sid="([^"]+)"', main)) | {"contact", "top", "contact-title"}

    def relink(m):
        key = m.group(1)
        if key in ids:
            return m.group(0)                                   # an anchor on this page
        url = STUDY_URL.get(key) or SECTION_URL.get(key)
        assert url, f'{p["file"]}: link to "#{key}", which is neither on this page nor a known study or section'
        return f'href="{url}"'
    main = re.sub(r'href="#([^"]+)"', relink, main)
    nav = "\n".join(f'        <a href="{u}"{" aria-current=\"page\"" if key == p["nav"] else ""}>{t}</a>' for u, t, key in NAV)
    og_img = p.get("og")
    doc = (layout.replace("{{TITLE}}", esc(p["title"])).replace("{{DESC}}", esc(p["desc"]))
                 .replace("{{OG_TITLE}}", esc(p["og_title"])).replace("{{URL}}", SITE_URL + ("" if p["file"] == "index.html" else p["file"]))
                 .replace("{{OG_IMAGE}}", SITE_URL + (f"v2/{og_img.name}" if og_img else "v2/og_card.png"))
                 .replace("{{OG_ALT}}", esc(p.get("og_alt", "Simulation portfolio")))
                 .replace("{{NAV}}", nav).replace("{{MAIN}}", main).replace("{{SCRIPTS}}", p["scripts"])
                 .replace("{{ASSET_V}}", asset_v))
    doc = titlecase.apply(doc)                                  # every title in title case (site/titlecase.py)
    left = re.findall(r"\{\{[A-Z_]+\}\}", doc)
    assert not left, f'{p["file"]}: unfilled {left}'
    built[p["file"]] = doc

# every link must land: ids unique on each page, same-page anchors exist, and links to other pages name a
# page that exists and, where they carry an anchor, an id on it
page_ids = {f: re.findall(r'\sid="([^"]+)"', doc) for f, doc in built.items()}
for f, doc in built.items():
    dupes = sorted({i for i in page_ids[f] if page_ids[f].count(i) > 1})
    assert not dupes, f"{f}: duplicate ids {dupes}"
    for href in set(re.findall(r'href="([^"]+)"', doc)):
        if href.startswith(("http", "mailto:", "data:", "assets/", "v2/", "img/")):
            continue
        target, _, anchor = href.partition("#")
        target = target or f
        assert target in built, f"{f}: link to a page that doesn't exist: {href}"
        assert not anchor or anchor in page_ids[target], f"{f}: link to an id that doesn't exist: {href}"

DOCS.mkdir(exist_ok=True)
(DOCS / "assets").mkdir(exist_ok=True)
for n in ("site.css", "site.js", "viewer.js", "viewer3d.js"):
    (DOCS / "assets" / n).write_bytes((HERE / "assets" / n).read_bytes())
css = (HERE / "assets" / "site.css").read_text(encoding="utf-8")
depth = 0                              # an unclosed brace makes the browser drop every style rule after it
for line_no, line in enumerate(css.splitlines(), 1):
    depth += line.count("{") - line.count("}")
    assert depth >= 0, f"stray closing brace in site.css, line {line_no}"
assert depth == 0, "unclosed brace in site.css"
for old in DOCS.glob("*.html"):
    if old.name not in built and old.name != "404.html":
        old.unlink()
for f, doc in built.items():
    (DOCS / f).write_text(doc, encoding="utf-8")
nf = (layout.replace("{{TITLE}}", f"Page not found · {AUTHOR}").replace("{{DESC}}", "That page isn't here.")
            .replace("{{OG_TITLE}}", "Page not found").replace("{{URL}}", SITE_URL).replace("{{OG_IMAGE}}", SITE_URL + "v2/og_card.png")
            .replace("{{OG_ALT}}", "Simulation portfolio")
            .replace("{{NAV}}", "\n".join(f'        <a href="{u}">{t}</a>' for u, t, _ in NAV))
            .replace("{{MAIN}}", '  <div class="wrap band" style="padding-top:0"><div class="page-head"><p class="eyebrow">Not found</p>'
                     "<h1>That page isn't here</h1><p>The address may be out of date. Every study is listed on the home page.</p>"
                     '<p><a class="cta" href="index.html#work">See the studies</a></p></div></div>')
            .replace("{{SCRIPTS}}", "").replace("{{ASSET_V}}", asset_v))
# the 404 page is served at any address, so its relative links need the site's base
(DOCS / "404.html").write_text(titlecase.apply(nf).replace("<head>", '<head>\n<base href="/engineering-agent-lab/">', 1), encoding="utf-8")
(DOCS / "sitemap.xml").write_text(
    '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    + "".join(f"  <url><loc>{SITE_URL}{'' if f == 'index.html' else f}</loc></url>\n" for f in sorted(built))
    + "</urlset>\n", encoding="utf-8")
(DOCS / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {SITE_URL}sitemap.xml\n", encoding="utf-8")
(DOCS / "pages.json").write_text(json.dumps(
    {"viewer": [p["file"] for p in pages if p.get("has3d") and not p.get("home")], "all": sorted(built)}, indent=1), encoding="utf-8")
print(f"written {len(built)} pages to docs/ ({sum(len(d) for d in built.values()) // 1024} KB of HTML);", facts,
      f"; page grader matches Python on {gcheck['checked']} answers")
