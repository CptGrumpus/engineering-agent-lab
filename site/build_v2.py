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
    {"id": "bracket_opt", "tab": "Optimised", "legend": "S, Mises", "unit": "MPa",
     "model": "Optimised bracket · steel taper 26.0 → 8.7 mm, 200 × 20 mm, 1 kN at the tip",
     "lines": ["Solver: CalculiX 2.22 · C3D10 · candidate 27 of 32, chosen by COBYLA",
               "Deformation scale factor: +2.500e+01",
               "Peak bending stress 99.5 MPa against 100 · 546 g, 30 % lighter than the straight bar"]},
    {"id": "cantilever", "tab": "Stress", "legend": "S, Mises", "unit": "MPa",
     "model": "Cantilever bracket · steel, 200 × 20 × 20 mm, 1 kN at the tip",
     "lines": ["Solver: CalculiX 2.22 · C3D10 · 5 758 surface nodes",
               "Deformation scale factor: +2.500e+01",
               "Range capped at the 150 MPa beam-theory stress; the clamp corners are singular"]},
    {"id": "contact_detail", "tab": "Contact", "legend": "S, Mises", "unit": "MPa",
     "model": "Roller on plate · steel, R = 50 mm, 501 N/mm · section through the contact",
     "lines": ["Solver: CalculiX 2.22 · surface-to-surface penalty contact",
               "Peak contact pressure +6.092e+02 · Hertz exact +6.067e+02",
               "Highest stress 0.41 mm below the surface, where Hertz puts it"]},
    {"id": "fatigue", "tab": "Fatigue", "legend": "S11 amplitude", "unit": "MPa",
     "model": "Strap with a 16 mm hole · 160 × 40 × 4 mm, 0 → 5 kN cyclic",
     "lines": ["Solver: CalculiX 2.22 · plane stress, quarter model mirrored",
               "Peak amplitude +5.85e+01 at the sides of the hole",
               "Life about 8 × 10⁹ cycles against 3 × 10⁷ required"]},
    {"id": "fin", "tab": "Thermal", "legend": "NT11", "unit": "°C",
     "model": "Heat-sink fin · 6061-T6, 40 × 20 × 2 mm, h = 25 W/m²K",
     "lines": ["Solver: CalculiX 2.22 · steady heat transfer",
               "Tip 73.2 °C against a 60 °C minimum",
               "Energy balance: base heat in equals convection out"]},
    {"id": "duct", "tab": "Flow", "legend": "U, axial", "unit": "m/s",
     "model": "Coolant passage · 20 × 1 mm, water at 0.1 m/s mean, Re 199",
     "lines": ["Solver: OpenFOAM 14 · 3D laminar, quarter section mirrored",
               "Height = velocity; gap direction drawn 5× wider",
               "Pressure gradient within 0.03 % of the exact rectangular-duct solution"],
     "check_text": "Render check: the volume under the surface equals the imposed flow rate to {err} · {col} of pixels on the legend"},
    {"id": "mode1", "tab": "Modal", "legend": "U, Magnitude", "unit": "normalised",
     "model": "Bracket arm · steel, 150 × 25 × 7 mm, clamped",
     "lines": ["Solver: CalculiX 2.22 · *FREQUENCY, mode 1 of 4",
               "261.7 Hz flapwise · requirement ≥ 250 Hz (engine 2nd order + 25 %)",
               "Within 0.9 % of an independent Timoshenko beam model"]},
]
for v in VP:
    s = scenes[v["id"]]
    vol, col = s["volume"], s["color"]
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
    ("bracket_opt", "12", "struct", "New · Design automation", "Bracket optimisation loop, driven by the agent", "The agent searched 32 designs and found a tapered bracket that is 30 % lighter than the straight bar it started from, at 546 g and inside both limits. Every candidate went through the full set of checks, and an independent beam-theory optimum agrees within 0.13 %.", "pass", "CadQuery · Gmsh · CalculiX · SciPy"),
    ("contact", "10", "struct", "Contact", "Roller-on-plate contact, nonlinear FEA", "A track roller carrying 500 N/mm. The contact pressure peaks at 609 MPa against a 650 MPa limit, and the shear under the surface reaches 184 MPa against 200. The CalculiX model lands within 0.4 % of the exact Hertz solution.", "pass", "Gmsh · CalculiX"),
    ("fea", "01", "struct", "Structures", "Cantilever bracket, 3D FEA", "Passes with room to spare at 0.953 mm and 150 MPa.", "pass", "FreeCAD · Gmsh · CalculiX"),
    ("strap", "02", "struct", "Structures", "Cable hole in a strap, CAD to FEA", "The hole can go up to about 16.7 mm. 16 mm passes at 117 MPa and 18 mm fails.", "pass", "CadQuery · Gmsh · CalculiX"),
    ("fatigue", "03", "struct", "Fatigue", "Strap fatigue life, chained analysis", "Lasts easily, and could be rated to 7.8 kN cyclic for 3 × 10⁷ cycles.", "pass", "CalculiX · Python"),
    ("modal", "04", "struct", "Vibration", "Bracket arm modal analysis", "7 mm thick puts the first mode at 261.7 Hz and the weight at 206 g.", "pass", "CadQuery · Gmsh · CalculiX"),
    ("cfd", "05", "fluid", "CFD", "Coolant channel pressure budget", "Fails. It needs 33.4 Pa against a 30 Pa budget, and no gap size fixes it.", "fail", "OpenFOAM"),
    ("thermal", "06", "fluid", "Heat transfer", "Heat-sink fin temperature", "The tip sits at 73.2 °C, and still 65.9 °C with every input at its worst.", "pass", "CalculiX"),
    ("heat", "11", "fluid", "Heat transfer", "Cold-plate channel heat transfer", "The coolant warms 7.2 K, verified. The wall stays under 45 °C, but I haven't pinned down its mesh uncertainty yet.", "held", "OpenFOAM"),
    ("suspension", "07", "vehicle", "Vehicle dynamics", "Quarter car, ride and road holding", "600 to 1000 N·s/m works at 18 km/h. At 36 km/h the wheel leaves the road.", "mixed", "SciPy · OpenModelica"),
    ("cad", "08", "geom", "Geometry", "Parametric mounting plate", "Only the 9 mm (M8 clearance) hole meets both the weight and edge-distance rules.", "pass", "CadQuery"),
    ("baseline", "09", "workflow", "Workflow", "Mass-spring-damper baseline", "All 72 checks pass, and the two tools agree to a few parts per million.", "pass", "SciPy · OpenModelica"),
]
VERDICT = {"pass": "Passes", "fail": "Fails", "mixed": "Depends on speed", "held": "One result on hold"}
cards_html = "\n".join(
    f'''      <a class="card" href="#{k}" data-group="{g}">
        <span class="thumb"><img src="v2/th_{k}.webp" alt="" loading="lazy" width="800" height="500"></span>
        <span class="card-body">
          <span class="meta"><span class="no">{n}</span><span>{d}</span></span>
          <span class="card-title">{html.escape(t)}</span>
          <span class="card-answer">{html.escape(a)}</span>
          <span class="card-foot"><span class="v v-{v}">{VERDICT[v]}</span><span class="tools">{tools}</span></span>
        </span>
      </a>''' for k, n, g, d, t, a, v, tools in CARDS)

tabs_html = "\n".join(
    f'<button type="button" role="tab" id="tab-{v["id"]}" aria-controls="vp" aria-selected="{"true" if i == 0 else "false"}" data-i="{i}">'
    f'<span class="tab-k">{v["tab"]}</span><span class="tab-v">{html.escape(v["model"].split(" · ")[0])}</span></button>'
    for i, v in enumerate(VP))

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


def collapse_studies(text: str) -> str:
    """Each study sheet becomes a closed <details>: the summary keeps its head (label and title) and
    adds the gallery card's one-line answer; the body opens on a click or a link to the study."""
    answers = {c[0]: c[5] for c in CARDS}
    pat = re.compile(r'  <section class="study" id="(\w+)">\s*<div class="study-head">(.*?)</div>(.*?)\n  </section>', re.S)

    def rep(m):
        k, head, body = m.group(1), m.group(2), m.group(3)
        summ = html.escape(answers.get(k, ""))
        return (f'  <details class="study" id="{k}">\n    <summary class="study-head">{head}'
                f'<span class="study-sum">{summ}</span><span class="study-toggle"></span></summary>\n'
                f'    <div class="study-body">{body}\n{extras.evidence_html(k)}    </div>\n  </details>')

    out, n = pat.subn(rep, text)
    assert n == text.count('<section class="study"'), "every study sheet must collapse"
    return out

def featured_with_evidence() -> str:
    """The featured study gets the same evidence line as the others, once its files are committed."""
    text = (HERE / "featured.html").read_text(encoding="utf-8")
    ev = extras.evidence_html("bracket_opt")
    end = text.rindex("  </section>")
    return text[:end] + ev + text[end:] if ev else text


import extras
import make_og
facts = extras.repo_facts()
make_og.make(facts)
gdata = extras.grader_data()
gcheck = extras.check_js_against_python(gdata)
grader_body, grader_js = extras.grader_html(gdata)

page = (HERE / "v2_template.html").read_text(encoding="utf-8")
page = (page.replace("{{EXTRA_CSS}}", extras.CSS)
            .replace("{{TLDR}}", extras.summary_html(facts))
            .replace("{{GRADER}}", grader_body)
            .replace("{{GRADER_JS}}", grader_js)
            .replace("{{REQS}}", extras.reqs_html())
            .replace("{{CHECKS}}", f"{facts['checks']:,}")
            .replace("{{RUNS}}", str(facts["runs"])))
page = (page.replace("{{VP_JSON}}", json.dumps(VP, ensure_ascii=False))
            .replace("{{TABS}}", tabs_html)
            .replace("{{CARDS}}", cards_html)
            .replace("{{TERMINAL}}", term_html)
            .replace("{{FEATURED}}", featured_with_evidence())
            .replace("{{STUDIES}}", collapse_studies(studies))
            .replace("{{CAPS}}", extras.CAPS))
(HERE / "index.html").write_text(page, encoding="utf-8")
assert "{{" not in page, page[page.index("{{"):page.index("{{") + 40]
print("written", len(page) // 1024, "KB;", len(term_lines), "terminal lines;", facts,
      f"; page grader matches Python on {gcheck['checked']} answers")
