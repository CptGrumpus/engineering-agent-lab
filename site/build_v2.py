"""Assemble the v2 portfolio page: new frame + the existing case-study sections."""
import html
import json
import re
from pathlib import Path

HERE = Path(__file__).parent
REPO = Path(r"c:\Users\mrstego\projects\engineering-agent-lab")
old = (HERE / "index_v1.html").read_text(encoding="utf-8")
CONTACT = (HERE / "contact_section.html").read_text(encoding="utf-8")
studies = old[old.index('  <h2 class="discipline">Structures and vibration</h2>'):old.index("  <footer>")]
i0 = old.index('<section class="caps" aria-labelledby="caps-title">')
caps = old[old.index('<div class="table-wrap">', i0):old.index("</section>", i0)]
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
    ("contact", "10", "struct", "New · Contact", "Roller-on-plate contact, nonlinear FEA", "A track roller carries 500 N/mm. Peak contact pressure 609 MPa against a 650 MPa limit, shear below the surface 184 MPa against 200. CalculiX contact matches the exact Hertz solution to 0.4 %.", "pass", "Gmsh · CalculiX"),
    ("fea", "01", "struct", "Structures", "Cantilever bracket, 3D FEA", "Yes: 0.953 mm and 150 MPa, mesh uncertainty 0.02 %.", "pass", "FreeCAD · Gmsh · CalculiX"),
    ("strap", "02", "struct", "Structures", "Cable hole in a strap, CAD to FEA", "Largest hole about 16.7 mm: 16 passes at 117 MPa, 18 fails.", "pass", "CadQuery · Gmsh · CalculiX"),
    ("fatigue", "03", "struct", "Fatigue", "Strap fatigue life, chained analysis", "Lasts by a wide margin; rated to 7.8 kN cyclic for 3 × 10⁷ cycles.", "pass", "CalculiX · Python"),
    ("modal", "04", "struct", "Vibration", "Bracket arm modal analysis", "7 mm: first mode 261.7 Hz at 206 g, clear of the engine order.", "pass", "CadQuery · Gmsh · CalculiX"),
    ("cfd", "05", "fluid", "CFD", "Coolant channel pressure budget", "No: needs 33.4 Pa against a 30 Pa budget. No gap size fixes it.", "fail", "OpenFOAM"),
    ("thermal", "06", "fluid", "Heat transfer", "Heat-sink fin temperature", "Yes: tip at 73.2 °C, still 65.9 °C with every input at its worst.", "pass", "CalculiX"),
    ("suspension", "07", "vehicle", "Vehicle dynamics", "Quarter car, ride and road holding", "600 to 1000 N·s/m at 18 km/h. At 36 km/h the wheel leaves the road.", "mixed", "SciPy · OpenModelica"),
    ("cad", "08", "geom", "Geometry", "Parametric mounting plate", "Only the 9 mm (M8 clearance) hole meets weight and edge rules.", "pass", "CadQuery"),
    ("baseline", "09", "workflow", "Workflow", "Mass-spring-damper baseline", "All 72 checks pass; two tools agree to parts per million.", "pass", "SciPy · OpenModelica"),
]
VERDICT = {"pass": "Answer delivered", "fail": "Design fails, with the fix", "mixed": "Pass and fail regimes"}
cards_html = "\n".join(
    f'''      <a class="card{' featured' if k == 'contact' else ''}" href="#{k}" data-group="{g}">
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

def fig(src, alt, cap):
    return ("\n    " + f'<figure><div class="plate"><img src="{src}" alt="{alt}" loading="lazy"></div>'
            f'<figcaption>{cap}</figcaption></figure>')


def after_head(text, sid, html):
    import re as _re
    m = _re.search(rf'(<section class="study" id="{sid}">\s*<div class="study-head">.*?</div>)', text, flags=_re.S)
    assert m, sid
    return text[:m.end()] + html + text[m.end():]


studies = after_head(studies, "fatigue", fig("img/render_fatigue.png", "Cyclic stress amplitude on the strap",
    "The cyclic stress amplitude for the 0 to 5 kN service cycle, highest at the sides of the hole where a crack would start."))
studies = after_head(studies, "cfd", fig("img/render_duct.png", "Velocity over the passage cross-section",
    "Velocity over the passage cross-section from the 3D check: flat across most of the width, falling to zero at the side walls. The volume under this surface equals the flow rate, which the render check confirms."))
studies = after_head(studies, "suspension", fig("img/anim_quarter_car.gif", "Animation of the quarter car crossing the bump",
    "Drawn from the simulation at 36 km/h and 600 N·s/m: the wheel leaves the road twice, and the tire load and body acceleration trace beside it."))
studies = after_head(studies, "baseline", fig("img/anim_msd.gif", "Animation of the mass-spring-damper at three damping ratios",
    "The same step force at three damping ratios, drawn from the runs, with the exact solution dotted underneath."))
page = (HERE / "v2_template.html").read_text(encoding="utf-8")
page = (page.replace("{{VP_JSON}}", json.dumps(VP, ensure_ascii=False))
            .replace("{{TABS}}", tabs_html)
            .replace("{{CARDS}}", cards_html)
            .replace("{{TERMINAL}}", term_html)
            .replace("{{STUDIES}}", studies.replace('  <section class="study" id="modal">',
                                                    CONTACT + "\n" + '  <section class="study" id="modal">', 1))
            .replace("{{CAPS}}", caps.replace(
                '<td><a href="#fea">1</a>, <a href="#strap">2</a></td></tr>',
                '<td><a href="#fea">1</a>, <a href="#strap">2</a></td></tr>\n          <tr><td>Contact: nonlinear surface-to-surface contact, contact pressure and subsurface stress, verified against Hertz</td><td>Gmsh, CalculiX</td><td><a href="#contact">10</a></td></tr>', 1)))
(HERE / "index.html").write_text(page, encoding="utf-8")
print("written", len(page) // 1024, "KB;", len(term_lines), "terminal lines")
