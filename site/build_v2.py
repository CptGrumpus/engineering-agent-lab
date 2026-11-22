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
               "Range stops at 240 MPa · the sharp inner corner peaks higher, and the code's limits exclude it",
               "Linearised through the wall beside the weld: PL 205.1 MPa against 207 · passes with a 0.9 % margin"]},
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
    {"id": "heat", "study": "heat", "kind": "figure", "img": "v2/heat_response.webp",
     "model": "Cold-plate channel · water in a 1 mm gap, 30 kW/m² on both walls",
     "lines": ["Solver: OpenFOAM 14 · laminar flow with heat transfer",
               "Wall and bulk temperature, and the local Nusselt number, against the Graetz thermal-entry solution",
               "Wall peak 44.03 °C against 45 · coolant rise 7.2 K"]},
    {"id": "pipe", "study": "pipe", "kind": "figure", "img": "v2/pipe_friction.webp",
     "model": "Smooth pipe, fully developed turbulent flow · 100 mm bore, Re 2 × 10⁴ to 2 × 10⁶",
     "lines": ["Solver: OpenFOAM 14 · k-omega SST on a periodic 5° wedge",
               "Friction factor against Prandtl's law: the mesh study, the Reynolds sweep and the wall-function placement",
               "+2.4 % when converged against a 5 % limit · one mesh alone gave the wrong sign"]},
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
    ("pv_nozzle", "18", "struct", "New · Design code", "Pressure vessel nozzle, design code check", "Passes ASME-style design by analysis with a 0.9 % margin: 205.1 MPa against 207, verified to 0.03 %. The wall needs 11.7 mm, where a simpler rule asks for 16.", "pass", "CadQuery · Gmsh · CalculiX"),
    ("bolted_joint", "16", "struct", "New · Friction contact", "Bolted joint, slip and opening", "Fails narrowly: once the joint settles it slips at 2.39 kN, 4.4 % short of the 2.5 kN it must carry. A 15.6 kN preload fixes it, and it stays closed to 13.1 kN.", "fail", "CalculiX"),
    ("strap_proof", "14", "struct", "New · Plasticity", "Strap proof test, notch plasticity", "A 15 kN proof test strains the hole edge to 0.58 %, inside a 1 % limit, and leaves −77 MPa of compression behind, which helps fatigue.", "pass", "CadQuery · Gmsh · CalculiX"),
    ("strut", "13", "struct", "New · Stability", "Strut buckling, with an imperfect strut", "The longest acceptable strut is about 587 mm. The bow costs 4 to 7 % of the buckling load, so a buckling check alone would overstate the capacity.", "pass", "CalculiX"),
    ("contact", "10", "struct", "Contact", "Roller-on-plate contact, nonlinear FEA", "A track roller carrying 500 N/mm. The contact pressure peaks at 609 MPa against a 650 MPa limit, and the shear under the surface reaches 184 MPa against 200. The CalculiX model lands within 0.4 % of the exact Hertz solution.", "pass", "Gmsh · CalculiX"),
    ("fea", "01", "struct", "Structures", "Cantilever bracket, 3D FEA", "Passes with room to spare at 0.953 mm and 150 MPa.", "pass", "FreeCAD · Gmsh · CalculiX"),
    ("cantilever_opt", "01b", "struct", "Design automation", "The same cantilever, optimised", "Under a 100 MPa fatigue limit a linear taper from 26.0 to 8.7 mm weighs 546 g, 30 % less than the lightest straight bar that passes, and lands within 0.13 % of an independent beam-theory optimum.", "pass", "CadQuery · Gmsh · CalculiX · SciPy"),
    ("strap", "02", "struct", "Structures", "Cable hole in a strap, CAD to FEA", "The hole can go up to about 16.7 mm. 16 mm passes at 117 MPa and 18 mm fails.", "pass", "CadQuery · Gmsh · CalculiX"),
    ("fatigue", "03", "struct", "Fatigue", "Strap fatigue life, chained analysis", "Predicted to last with a wide margin; rated 7.8 kN cyclic for 3 × 10⁷ cycles, the lower of two data sets, extrapolated past the test data.", "pass", "CalculiX · Python"),
    ("modal", "04", "struct", "Vibration", "Bracket arm modal analysis", "7 mm thick puts the first mode at 261.7 Hz and the weight at 206 g.", "pass", "CadQuery · Gmsh · CalculiX"),
    ("cold_plate", "15", "fluid", "New · Multiphysics", "Cold plate, the full thermal chain", "Passes on all three counts, from the coolant flow through the plate's conduction to its thermal stress: 40.99 °C, a 7.20 K coolant rise and 46.8 MPa.", "pass", "OpenFOAM · CalculiX"),
    ("pipe", "19", "fluid", "New · Turbulence", "Turbulent pipe friction, against measured data", "Passes: converged, the turbulence model lands 2.4 % above Prandtl's law against a 5 % limit. The first mesh agreed to 0.9 %, with the wrong sign. Wall functions sit 5 % low on every mesh.", "pass", "OpenFOAM"),
    ("cfd", "05", "fluid", "CFD", "Coolant channel pressure budget", "Fails. It needs 33.4 Pa against a 30 Pa budget, and no gap size fixes it.", "fail", "OpenFOAM"),
    ("thermal", "06", "fluid", "Heat transfer", "Heat-sink fin temperature", "The tip sits at 73.2 °C, and still 65.9 °C with every input at its worst.", "pass", "CalculiX"),
    ("heat", "11", "fluid", "Heat transfer", "Cold-plate channel heat transfer", "Passes, verified: the wall peaks at 44.03 °C against 45, and the coolant warms 7.2 K. A finer mesh study was needed to settle the peak.", "pass", "OpenFOAM"),
    ("suspension", "07", "vehicle", "Vehicle dynamics", "Quarter car, ride and road holding", "600 to 1000 N·s/m works at 18 km/h. At 36 km/h the wheel leaves the road.", "mixed", "SciPy · OpenModelica"),
    ("cad", "08", "geom", "Geometry", "Parametric mounting plate", "Only the 9 mm (M8 clearance) hole meets both the weight and edge-distance rules.", "pass", "CadQuery"),
    ("baseline", "09", "workflow", "Workflow", "Mass-spring-damper baseline", "All 72 checks pass, and the two tools agree to a few parts per million.", "pass", "SciPy · OpenModelica"),
]
VERDICT = {"pass": "Passes", "fail": "Fails", "mixed": "Depends on speed", "held": "One result on hold"}

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
PART_OF = {p: g for g, gd in GROUPS.items() for p in gd["parts"]}
PART_LABEL = {"fea": "01 · Stress check", "cantilever_opt": "01b · Optimised",
              "strap": "02 · Cable hole", "fatigue": "03 · Fatigue life", "strap_proof": "14 · Proof test",
              "heat": "11 · Coolant channel", "cold_plate": "15 · Full thermal chain"}
WIDE = {"bracket_opt", "pv_nozzle", "strap", "cantilever_bracket", "cold_plate"}

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
        "cantilever_bracket": "cantilever-bracket", "modal": "bracket-modal", "cold_plate": "cold-plate",
        "pipe": "turbulent-pipe-friction", "cfd": "coolant-channel", "thermal": "heat-sink-fin",
        "suspension": "quarter-car", "cad": "mounting-plate", "baseline": "mass-spring-damper"}
assert set(SLUG) == {c[0] for c in GALLERY}, "every gallery card needs a page name"
FILE = {k: f"{s}.html" for k, s in SLUG.items()}
DISC = {"struct": "Structures and vibration", "fluid": "Thermal and fluids", "vehicle": "Vehicle dynamics",
        "geom": "Geometry automation", "workflow": "Workflow validation"}
NAV = [("index.html#work", "Studies", "index"), ("how-i-work.html", "How I work", "how-i-work"),
       ("grading.html", "Grading", "grading"), ("in-progress.html", "In progress", "in-progress"),
       ("requirements.html", "Requirements", "requirements")]
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
         "pv_nozzle": ["pv_nozzle_mesh"], "bracket_opt": ["clevis_opt_r2"], "cfd": ["channel_header_tolerance", "duct_side_walls"],
         "thermal": ["fin_tolerance"], "heat": ["heated_channel_mesh_r2"], "cold_plate": ["cold_plate_mesh_r1"],
         "pipe": ["pipe_rans_mesh_r2"], "suspension": ["qc_speed_bump", "qc_bump_liftoff"], "cad": ["mounting_plate"],
         "baseline": ["msd_step"]}
HIGHLIGHTS = [("bracket_opt", "Optimised bracket"), ("pv_nozzle", "Pressure vessel"), ("bolted_joint", "Bolted joint slip"),
              ("strut", "Strut buckling"), ("cold_plate", "Cold plate")]

import tomllib

import extras
import make_og

LOOPS = json.loads((HERE / "v2" / "loops.json").read_text(encoding="utf-8")) if (HERE / "v2" / "loops.json").exists() else {}
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


def study_body(key: str, level: int, prefix: str = "") -> tuple[str, list]:
    """A study's body with its headings at `level` (2 on its own page, 3 as a part of a report), each given an
    id for the page's contents list; the case record goes where the body asks for it ({{CASE}}) or at the end."""
    body = fragment(key)["body"]
    rec = case_record(key)
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
    items = [f'<li><a class="ext" href="{ev["doc"]}">Full write-up on GitHub</a></li>']
    if ev.get("memo"):
        items.append(f'<li><a class="ext" href="{ev["memo"]}">Sample client memo from this study</a></li>')
    runs = "".join(f'<li><a class="ext" href="{u}">{esc(label)}</a></li>' for label, u in ev["runs"])
    return ('    <div class="side-card"><ul class="ev-list">' + "".join(items) + "</ul>"
            + (f'<p class="label">Run reports, with every check and the saved inputs</p><ul class="ev-list ev-runs">{runs}</ul>' if runs else "")
            + "</div>")


CHIP = {"met": ("pass", "Met"), "fail": ("fail", "Not met"), "held": ("warn", "Withheld")}


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
    toc_html = []
    if gk in GROUPS:
        label = GROUPS[gk]["label"]
        chunks = []
        for p in parts:
            fr = fragment(p)
            body, toc = study_body(p, 3, prefix=f"{p}-")
            chunks.append(f'      <section class="part" id="{p}" data-part="{p}">\n        <div class="part-head"><span class="label">{fr["label"]}</span>'
                          f'<h2>{fr["title"]}</h2></div>{body}\n      </section>')
            toc_html.append(f'<li class="t-part"><a href="#{p}">{esc(PART_LABEL[p])}</a></li>')
            toc_html += [f'<li class="t-sub"><a href="#{hid}">{esc(t)}</a></li>' for hid, t in toc]
        main = "\n".join(chunks)
    else:
        fr = fragment(gk)
        label = fr["label"]
        main, toc = study_body(gk, 2)
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
    body = f'''  <div class="wrap">
    <nav class="crumbs" aria-label="Breadcrumb"><a href="index.html#work">All studies</a><span>/</span><span>{DISC[group]}</span></nav>
    <header class="study-hero">
      <p class="eyebrow">{label}</p>
      <h1>{esc(title)}</h1>
      <span class="v v-{verdict}">{VERDICT[verdict]}</span>
      <p class="study-lede">{esc(answer)}</p>
    </header>
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
    og = make_og.study(SLUG[gk], f"Study {no} · {d.replace('New · ', '').replace('Featured · ', '')}", title,
                       VERDICT[verdict], HERE / "v2" / f"th_{thumb}.webp", figure=entries[0].get("kind") == "figure")
    return {"file": FILE[gk], "title": f"{title} · {AUTHOR}", "og_title": title, "desc": answer, "nav": "index",
            "main": body, "scripts": viewer_scripts(entries), "og": og, "og_alt": f"{title}: result render",
            "viewer": True, "has3d": any(v.get("mesh") for v in entries)}


def home_page(facts) -> dict:
    cards = "\n".join(
        f'''      <a class="card{' wide' if k in WIDE else ''}" href="{FILE[k]}" data-study="{k}" data-group="{g}">
        <span class="thumb"><img src="v2/th_{th}.webp" alt="" loading="lazy" width="800" height="500"{f' data-loop="{LOOPS[th]}"' if th in LOOPS else ""}></span>
        <span class="card-body">
          <span class="meta"><span class="no">{n}</span><span>{esc(d.replace("New · ", "").replace("Featured · ", ""))}</span></span>
          <span class="card-title">{esc(t)}</span>
          <span class="card-foot"><span class="v v-{v}">{VERDICT[v]}</span><span class="tools">{tools}</span></span>
        </span>
      </a>''' for k, n, g, d, t, a, v, tools, th in GALLERY)
    entries = []
    for i, (study, label) in enumerate(HIGHLIGHTS):
        v = dict(next(x for x in VP if x["study"] == study))
        v.update(part=label, main=i == 0, href=STUDY_URL[study])
        entries.append(v)
    n_req = sum(len(items) for _, _, _, items in extras.REQS)
    main = ((PAGES / "home.html").read_text(encoding="utf-8")
            .replace("{{VIEWER}}", viewer_html(entries)).replace("{{CARDS}}", cards)
            .replace("{{REQ_COUNT}}", str(n_req)))
    legacy = {**STUDY_URL, **{k: FILE[k] for k in FILE}, **{k: v for k, v in SECTION_URL.items() if k not in ("work", "top")}}
    legacy.update({k: STUDY_URL[k] for k in PART_OF})          # a study inside a report keeps its own address
    scripts = f"<script>window.LEGACY = {json.dumps(legacy)};</script>\n" + viewer_scripts(entries)
    return {"file": "index.html", "title": f"{AUTHOR} · Simulation portfolio", "og_title": "Simulation, proof attached",
            "desc": f"{WORDS[len(CARDS)][1]} open-source simulation studies by {AUTHOR}, mechanical engineer: FEA, CFD, coupled "
                    "multiphysics and an optimisation loop, each checked against an independent reference.",
            "nav": "index", "main": main, "scripts": scripts, "og": make_og.make({**facts, "studies": len(CARDS)}),
            "og_alt": "A machined clevis bracket rendered with its stress contours, beside the page headline and its counts of studies, checks and runs",
            "viewer": True, "has3d": True, "home": True}


def reqs_page() -> dict:
    rows, counts = [], {"met": 0, "fail": 0, "held": 0}
    for sid, no, title, items in extras.REQS:
        for i, (req, limit, result, v) in enumerate(items):
            counts[v] += 1
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
      <p>{n} requirements across the studies: <b class="c-pass">{counts["met"]} met</b>, <b class="c-fail">{counts["fail"]} not met</b>, <b class="c-warn">{counts["held"]} withheld</b>. "Not met" is still a verified answer: the design fails, and the study explains what would fix it. "Withheld" means the checks didn't support calling it either way. Each study's name links to its page.</p>
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
         18: ("eighteen", "Eighteen"), 19: ("nineteen", "Nineteen"), 20: ("twenty", "Twenty")}
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
              "how-i-work", {"{{TERMINAL}}": term_html, "{{CAPS}}": extras.CAPS, "{{CODE_FACTS}}": extras.code_facts(facts)}),
    text_page("grading.html", "grading.html", "Grading tasks", "Try grading an engineering answer",
              f"{TASK_WORDS[len(gdata)].capitalize()} engineering evaluation tasks built from verified simulation studies, each "
              "with a reference solution and an automated grader you can try on the page.",
              "grading", {"{{GRADER}}": grader_body, "{{TASK_COUNT_WORD}}": TASK_WORDS[len(gdata)]},
              scripts=f"<script>\n{grader_js}\n</script>"),
    text_page("in-progress.html", "progress.html", "In progress", "Two studies in progress",
              "A flexible flag behind a cylinder (fluid-structure interaction) and a production traction motor checked "
              "blind against a laboratory's test data.", "in-progress", {}),
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
        if href.startswith(("http", "mailto:", "assets/", "v2/", "img/")):
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
    if old.name not in built:
        old.unlink()
for f, doc in built.items():
    (DOCS / f).write_text(doc, encoding="utf-8")
(DOCS / "pages.json").write_text(json.dumps(
    {"viewer": [p["file"] for p in pages if p.get("has3d") and not p.get("home")], "all": sorted(built)}, indent=1), encoding="utf-8")
print(f"written {len(built)} pages to docs/ ({sum(len(d) for d in built.values()) // 1024} KB of HTML);", facts,
      f"; page grader matches Python on {gcheck['checked']} answers")
