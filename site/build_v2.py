"""Assemble the portfolio page: the template, the study write-ups (studies.html) and the extras."""
import html
import json
import re
from pathlib import Path

HERE = Path(__file__).parent
REPO = Path(__file__).resolve().parent.parent
studies = (HERE / "studies.html").read_text(encoding="utf-8")
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
    {"id": "contact_detail", "study": "contact", "tab": "Contact", "legend": "S, Mises", "unit": "MPa",
     "model": "Roller on plate · steel, R = 50 mm, 501 N/mm · section through the contact",
     "lines": ["Solver: CalculiX 2.22 · surface-to-surface penalty contact",
               "Peak contact pressure +6.092e+02 · Hertz exact +6.067e+02",
               "Highest stress 0.41 mm below the surface, where Hertz puts it"]},
    {"id": "bolted_joint", "study": "bolted_joint", "tab": "Joint", "legend": "CPRESS", "unit": "MPa",
     "model": "Bolted joint · two 6 mm steel plates, M8 at 15 kN, half model mirrored",
     "lines": ["Solver: CalculiX 2.22 · C3D8I, surface-to-surface contact with friction",
               "Contact pressure on the bottom plate after clamping, before any side load",
               "Peak 162 MPa at the hole · contact patch 21.1 mm across"]},
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
               "A 30 mm slice of the plane-strain section · coolant left to right",
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
               "Within 0.9 % of an independent Timoshenko beam model"]},
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
    ("bolted_joint", "16", "struct", "New · Friction contact", "Bolted joint, slip and opening", "Fails narrowly: once the joint settles it slips at 2.39 kN, 4.4 % short of the 2.5 kN it must carry. A 15.6 kN preload fixes it, and it stays closed to 13.1 kN.", "fail", "CalculiX"),
    ("strap_proof", "14", "struct", "New · Plasticity", "Strap proof test, notch plasticity", "A 15 kN proof test strains the hole edge to 0.58 %, inside a 1 % limit, and leaves −77 MPa of compression behind, which helps fatigue.", "pass", "CadQuery · Gmsh · CalculiX"),
    ("strut", "13", "struct", "New · Stability", "Strut buckling, with an imperfect strut", "The longest acceptable strut is about 587 mm. The bow costs 4 to 7 % of the buckling load, so a buckling check alone would overstate the capacity.", "pass", "CalculiX"),
    ("contact", "10", "struct", "Contact", "Roller-on-plate contact, nonlinear FEA", "A track roller carrying 500 N/mm. The contact pressure peaks at 609 MPa against a 650 MPa limit, and the shear under the surface reaches 184 MPa against 200. The CalculiX model lands within 0.4 % of the exact Hertz solution.", "pass", "Gmsh · CalculiX"),
    ("fea", "01", "struct", "Structures", "Cantilever bracket, 3D FEA", "Passes with room to spare at 0.953 mm and 150 MPa.", "pass", "FreeCAD · Gmsh · CalculiX"),
    ("strap", "02", "struct", "Structures", "Cable hole in a strap, CAD to FEA", "The hole can go up to about 16.7 mm. 16 mm passes at 117 MPa and 18 mm fails.", "pass", "CadQuery · Gmsh · CalculiX"),
    ("fatigue", "03", "struct", "Fatigue", "Strap fatigue life, chained analysis", "Lasts easily, and could be rated to 7.8 kN cyclic for 3 × 10⁷ cycles.", "pass", "CalculiX · Python"),
    ("modal", "04", "struct", "Vibration", "Bracket arm modal analysis", "7 mm thick puts the first mode at 261.7 Hz and the weight at 206 g.", "pass", "CadQuery · Gmsh · CalculiX"),
    ("cold_plate", "15", "fluid", "New · Multiphysics", "Cold plate, the full thermal chain", "Passes on all three counts, from the coolant flow through the plate's conduction to its thermal stress: 40.99 °C, a 7.20 K coolant rise and 46.8 MPa.", "pass", "OpenFOAM · CalculiX"),
    ("cfd", "05", "fluid", "CFD", "Coolant channel pressure budget", "Fails. It needs 33.4 Pa against a 30 Pa budget, and no gap size fixes it.", "fail", "OpenFOAM"),
    ("thermal", "06", "fluid", "Heat transfer", "Heat-sink fin temperature", "The tip sits at 73.2 °C, and still 65.9 °C with every input at its worst.", "pass", "CalculiX"),
    ("heat", "11", "fluid", "Heat transfer", "Cold-plate channel heat transfer", "Passes, verified: the wall peaks at 44.03 °C against 45, and the coolant warms 7.2 K. A finer mesh study was needed to settle the peak.", "pass", "OpenFOAM"),
    ("suspension", "07", "vehicle", "Vehicle dynamics", "Quarter car, ride and road holding", "600 to 1000 N·s/m works at 18 km/h. At 36 km/h the wheel leaves the road.", "mixed", "SciPy · OpenModelica"),
    ("cad", "08", "geom", "Geometry", "Parametric mounting plate", "Only the 9 mm (M8 clearance) hole meets both the weight and edge-distance rules.", "pass", "CadQuery"),
    ("baseline", "09", "workflow", "Workflow", "Mass-spring-damper baseline", "All 72 checks pass, and the two tools agree to a few parts per million.", "pass", "SciPy · OpenModelica"),
]
VERDICT = {"pass": "Passes", "fail": "Fails", "mixed": "Depends on speed", "held": "One result on hold"}
cards_html = "\n".join(
    f'''      <a class="card" href="#{k}" data-study="{k}" data-group="{g}">
        <span class="thumb"><img src="v2/th_{k}.webp" alt="" loading="lazy" width="800" height="500"></span>
        <span class="card-body">
          <span class="meta"><span class="no">{n}</span><span>{html.escape(d.replace("New · ", "").replace("Featured · ", ""))}</span></span>
          <span class="card-title">{html.escape(t)}</span>
          <span class="card-foot"><span class="v v-{v}">{VERDICT[v]}</span><span class="tools">{tools}</span></span>
        </span>
      </a>''' for k, n, g, d, t, a, v, tools in CARDS)

# load-step frames for the viewer's slider (scripts/make_study_renders.py --frames)
_fr = HERE / "v2" / "frames.json"
for v in VP:
    f = json.loads(_fr.read_text(encoding="utf-8")).get(v["study"]) if _fr.exists() else None
    if f:
        v["frames"] = f["frames"]
        v["frames_main"] = f["main"]

# the viewer follows the gallery's order
order = [c[0] for c in CARDS]
VP.sort(key=lambda v: order.index(v["study"]))
assert [v["study"] for v in VP] == order, "every study needs exactly one viewer entry"

term_html = "".join(
    f'<span class="t-row"><span class="t-id">{cid}</span><span class="t-{st.lower()}">{st}</span><span class="t-num">{val}</span><span class="t-tol">tol {tol}</span></span>'
    for cid, st, val, tol in term_lines)

# gallery thumbnail for study 11: the wall and bulk temperature panel of its response plot
th_heat = HERE / "v2" / "th_heat.webp"
if not th_heat.exists():
    from PIL import Image
    src = Image.open(HERE / "v2" / "heat_response.webp").convert("RGB").crop((10, 80, 725, 535))
    src.thumbnail((760, 470), Image.LANCZOS)
    canvas = Image.new("RGB", (800, 500), (252, 252, 251))
    canvas.paste(src, ((800 - src.width) // 2, (500 - src.height) // 2))
    canvas.save(th_heat, "WEBP", quality=88)


def study_panels(text: str) -> str:
    """Each study sheet becomes a closed <details>, hidden until its card is chosen: the summary keeps its
    head (label and title) and adds the verdict and the one-line answer; the body opens on a click or a
    link to the study. The optimiser's panel points to its featured section."""
    answers = {c[0]: c for c in CARDS}
    text = re.sub(r'\n  <h2 class="discipline">[^<]*</h2>\n', "\n", text)
    pat = re.compile(r'  <section class="study" id="(\w+)">\s*<div class="study-head">(.*?)</div>(.*?)\n  </section>', re.S)
    panels = {}
    for m in pat.finditer(text):
        k, head, body = m.group(1), m.group(2), m.group(3)
        c = answers[k]
        panels[k] = (f'  <details class="study pick" id="{k}" data-study="{k}" hidden>\n    <summary class="study-head">{head}'
                     f'<span class="v v-{c[6]}">{VERDICT[c[6]]}</span><span class="study-sum">{html.escape(c[5])}</span>'
                     f'<span class="study-toggle"></span></summary>\n'
                     f'    <div class="study-body">{body}\n{extras.evidence_html(k)}    </div>\n  </details>')
    assert len(panels) == text.count('<section class="study"'), "every study sheet must become a panel"
    c = answers["bracket_opt"]
    panels["bracket_opt"] = (f'  <div class="study pick" id="pick-bracket_opt" data-study="bracket_opt" hidden>\n'
                             f'    <div class="study-head"><span class="label">Study 12 · {c[7]}</span><h2>{html.escape(c[4])}</h2>'
                             f'<span class="v v-{c[6]}">{VERDICT[c[6]]}</span><span class="study-sum">{html.escape(c[5])}</span>'
                             f'<a class="study-toggle-link" href="#bracket_opt">Read the full study, just below ↓</a></div>\n  </div>')
    missing = [c[0] for c in CARDS if c[0] not in panels]
    assert not missing, f"no write-up for {missing}"
    return "\n".join(panels[c[0]] for c in CARDS)

def featured_with_evidence() -> str:
    """The featured study gets the same evidence line as the others, once its files are committed."""
    text = (HERE / "featured.html").read_text(encoding="utf-8")
    ev = extras.evidence_html("bracket_opt")
    end = text.rindex("  </section>")
    return text[:end] + ev + text[end:] if ev else text


WORDS = {15: ("fifteen", "Fifteen"), 16: ("sixteen", "Sixteen"), 17: ("seventeen", "Seventeen"),
         18: ("eighteen", "Eighteen")}
import extras
import make_og
facts = extras.repo_facts()
make_og.make(facts)
gdata = extras.grader_data()
gcheck = extras.check_js_against_python(gdata)
grader_body, grader_js = extras.grader_html(gdata)

page = (HERE / "v2_template.html").read_text(encoding="utf-8")
page = (page.replace("{{EXTRA_CSS}}", extras.CSS)
            .replace("{{STUDY_COUNT_WORD}}", WORDS[len(CARDS)][0])
            .replace("{{STUDY_COUNT_TITLE}}", WORDS[len(CARDS)][1])
            .replace("{{STUDY_COUNT}}", str(len(CARDS)))
            .replace("{{MEMO_URL}}", extras.gh(extras.MEMO))
            .replace("{{CODE_FACTS}}", extras.code_facts(facts))
            .replace("{{GRADER}}", grader_body)
            .replace("{{GRADER_JS}}", grader_js)
            .replace("{{REQS}}", extras.reqs_html())
            .replace("{{CHECKS}}", f"{facts['checks']:,}")
            .replace("{{RUNS}}", str(facts["runs"])))
page = (page.replace("{{VP_JSON}}", json.dumps(VP, ensure_ascii=False))
            .replace("{{CARDS}}", cards_html)
            .replace("{{TERMINAL}}", term_html)
            .replace("{{FEATURED}}", featured_with_evidence())
            .replace("{{PICKS}}", study_panels(studies))
            .replace("{{CAPS}}", extras.CAPS)
            .replace("{{VIEWER3D_JS}}", (HERE / "viewer3d.js").read_text(encoding="utf-8")))
(HERE / "index.html").write_text(page, encoding="utf-8")
assert "{{" not in page, page[page.index("{{"):page.index("{{") + 40]
# every link target must be unique: a repeated id sends "#id" links to whichever comes first
ids = re.findall(r'\sid="([^"]+)"', page)
dupes = sorted({i for i in ids if ids.count(i) > 1})
assert not dupes, f"duplicate ids on the page: {dupes}"
missing = sorted(set(re.findall(r'href="#([^"]+)"', page)) - set(ids))
assert not missing, f"links to ids that don't exist: {missing}"
# an unclosed brace makes the browser drop every style rule after it, silently
css = page[page.index("<style>"):page.index("</style>")]
depth = 0
for line_no, line in enumerate(css.splitlines(), 1):
    depth += line.count("{") - line.count("}")
    assert depth >= 0, f"stray closing brace in the page styles, line {line_no}"
assert depth == 0, "unclosed brace in the page styles"
print("written", len(page) // 1024, "KB;", len(term_lines), "terminal lines;", facts,
      f"; page grader matches Python on {gcheck['checked']} answers")
