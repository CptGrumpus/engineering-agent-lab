"""Page additions: the 30-second summary, the live grader demo, and the requirements table.

The grader demo takes its criteria straight from tasks/*/grader.py (the within/equals calls are
recorded while grading the reference answer), grades every preset answer with the Python grader,
and checks the page's JavaScript grader against the Python one on random answers using node.
"""
from __future__ import annotations

import html
import importlib.util
import json
import random
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
TASKS = REPO / "tasks"


# --------------------------------------------------------------------------- summary
EXTRA_RUNS = ("20261120-225322_bracket_opt", "20261120-225744_bracket_opt_confirm")   # study 12

# --------------------------------------------------------------------------- evidence links
REPO_URL = "https://github.com/CptGrumpus/engineering-agent-lab"
MEMO = "portfolio/deliverables/coolant-channel-memo.md"
# page key -> the study's write-up in portfolio/, which lists the runs it rests on
STUDY_DOCS = {
    "fea": "01-cantilever-bracket", "cantilever_opt": "01b-cantilever-optimisation", "strap": "02-strap-cable-hole", "fatigue": "03-strap-fatigue",
    "modal": "04-bracket-modal", "cfd": "05-coolant-channel", "thermal": "06-heat-sink-fin",
    "suspension": "07-quarter-car", "cad": "08-mounting-plate", "baseline": "09-mass-spring-damper",
    "contact": "10-roller-contact", "heat": "11-cold-plate-heat-transfer", "bracket_opt": "12-bracket-optimisation",
    "strut": "13-strut-buckling", "strap_proof": "14-strap-proof-plasticity", "cold_plate": "15-cold-plate-thermal-chain",
    "bolted_joint": "16-bolted-joint-slip", "pv_nozzle": "18-pressure-vessel-nozzle",
    "pipe": "19-turbulent-pipe-friction", "motor": "20-prius-traction-motor",
}
_RUN = re.compile(r"runs/(\d{8}-(\d{2})(\d{2})\d{2}_[A-Za-z0-9_]+)")
_tracked: set[str] | None = None


def tracked(path: str) -> bool:
    """True if the file is committed, so a link to it on GitHub resolves."""
    global _tracked
    if _tracked is None:
        _tracked = set(subprocess.run(["git", "ls-files"], cwd=REPO, capture_output=True, text=True,
                                      check=True).stdout.splitlines())
    return path in _tracked


def gh(path: str) -> str:
    return f"{REPO_URL}/blob/main/{path}"


def evidence(key: str) -> dict | None:
    """The study's write-up and each run report it cites, on the public repository. Only committed files
    are linked, so the site never points at a file GitHub doesn't have."""
    doc = f"portfolio/{STUDY_DOCS[key]}.md"
    if not tracked(doc):
        return None
    runs = sorted(set(m.group(1) for m in _RUN.finditer((REPO / doc).read_text(encoding="utf-8"))))
    runs = [r for r in runs if tracked(f"runs/{r}/report.md")]
    names = [r.split("_", 1)[1] for r in runs]
    links = [(name if names.count(name) == 1 else f"{name} · {r[9:11]}:{r[11:13]}", gh(f"runs/{r}/report.md"))
             for r, name in zip(runs, names)]
    return {"doc": gh(doc), "memo": gh(MEMO) if key == "cfd" and tracked(MEMO) else None, "runs": links}


def repo_facts() -> dict:
    files = subprocess.run(["git", "ls-files", "*.py"], cwd=REPO, capture_output=True, text=True,
                           check=True).stdout.split()
    lines = sum(len((REPO / f).read_text(encoding="utf-8").splitlines()) for f in files)
    py = REPO / ".venv" / "Scripts" / "python.exe"
    # count only tests in committed files: the page says they run on every push
    tests = [f for f in files if f.startswith("tests/") and f.rsplit("/", 1)[-1].startswith("test_")]
    out = subprocess.run([str(py), "-m", "pytest", "--collect-only", "-q", *tests], cwd=REPO,
                         capture_output=True, text=True).stdout
    m = re.search(r"(\d+) tests? collected", out)
    assert m, out[-500:]
    # checks and saved runs: every committed run with a verification record, plus runs listed in
    # EXTRA_RUNS that the page already presents but that have not been committed yet
    ver = set(subprocess.run(["git", "ls-files", "runs/*/verification.json"], cwd=REPO, capture_output=True,
                             text=True, check=True).stdout.split())
    ver |= {f"runs/{r}/verification.json" for r in EXTRA_RUNS if (REPO / "runs" / r / "verification.json").exists()}
    checks = sum(len(pt.get("checks", [])) for f in ver
                 for pt in json.loads((REPO / f).read_text(encoding="utf-8")).get("points", []))
    return {"py_files": len(files), "py_lines": lines, "tests": int(m.group(1)), "checks": checks, "runs": len(ver)}


def code_facts(facts: dict) -> str:
    k = facts["py_lines"] // 1000
    return (f"It's all Python, about {k},000 lines across {facts['py_files']} files: the harness that runs and checks "
            f"everything, the models, the independent reference solutions and the graders, with {facts['tests']} "
            f"automated tests that run on every push.")


# --------------------------------------------------------------------------- grader demo
def _load(name):
    spec = importlib.util.spec_from_file_location(f"page_grader_{name}", TASKS / name / "grader.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _criteria(mod) -> list[dict]:
    """Record the grader's own within/equals calls while it grades the reference answer."""
    calls, w0, e0 = [], mod.within, mod.equals

    def w(answer, key, ref, rel=None, abs_=None):
        calls.append({"key": key, "kind": "num", "ref": ref, "rel": rel, "abs": abs_})
        return w0(answer, key, ref, rel=rel, abs_=abs_)

    def e(answer, key, ref):
        calls.append({"key": key, "kind": "bool", "ref": ref})
        return e0(answer, key, ref)

    mod.within, mod.equals = w, e
    try:
        r = mod.grade(dict(mod.REFERENCE))
        assert r["passed"]
    finally:
        mod.within, mod.equals = w0, e0
    # a criterion the grader checks with its own helper (a named choice) is described in CHOICES; its rule
    # is checked against the Python grader like every other criterion
    order = [c["criterion"] for c in r["criteria"]]
    rec = {c["key"]: c for c in calls}
    for k in order:
        if k not in rec:
            rec[k] = {"key": k, "kind": "choice", **CHOICES[k]}
    assert len(rec) == len(order), "a criterion the page grader can't describe"
    return [rec[k] for k in order]


# choice criteria: the options offered on the page, the reference, and the grader's acceptance rule
# (trimmed, lower case; passes if it starts with one of `prefix` or equals one of `exact`)
CHOICES = {
    "pq_governing_surface": {"ref": "inner", "options": ["inner", "outer"], "prefix": ["inner"], "exact": ["s = 0", "s=0"]},
}


LABELS = {
    "contact_half_width_mm": ("Contact half-width", "mm", 4),
    "peak_contact_pressure_MPa": ("Peak contact pressure", "MPa", 1),
    "max_subsurface_shear_MPa": ("Max subsurface shear", "MPa", 1),
    "max_shear_depth_mm": ("Depth of max shear", "mm", 4),
    "pressure_limit_met": ("Pressure limit met?", "", 0),
    "shear_limit_met": ("Shear limit met?", "", 0),
    "coolant_rise_K": ("Coolant rise", "K", 3),
    "peak_wall_temperature_C": ("Peak wall temperature", "°C", 2),
    "nusselt_at_end_of_heating": ("Nusselt number, end of heating", "", 3),
    "wall_limit_met": ("Wall limit met?", "", 0),
    "tip_deflection_mm": ("Tip deflection", "mm", 3),
    "root_bending_stress_MPa": ("Root bending stress", "MPa", 1),
    "deflection_limit_met": ("Deflection limit met?", "", 0),
    "stress_limit_met": ("Stress limit met?", "", 0),
    "peak_fe_stress_is_singular": ("FE peak stress is an artifact?", "", 0),
    "tip_drop_mm": ("Drop of the free edge", "mm", 2),
    "tip_pull_in_mm": ("Pull-in towards the wall", "mm", 2),
    "bending_modulus_MPa": ("Bending modulus used", "MPa", 2),
    "clearance_met": ("Clears the belt?", "", 0),
    "pl_MPa": ("PL, local membrane", "MPa", 2),
    "pq_MPa": ("P + Q, membrane plus bending", "MPa", 2),
    "pq_governing_surface": ("Surface where P + Q governs", "", 0),
    "pl_limit_met": ("PL limit met?", "", 0),
    "pq_limit_met": ("P + Q limit met?", "", 0),
}


def _presets_hertz(ref):
    s = ((210000 / (2 * (1 - 0.09))) / 210000) ** 0.5          # sqrt(E*/E)
    a, p0 = ref["contact_half_width_mm"] * s, ref["peak_contact_pressure_MPa"] / s
    return [
        ("Hertz line contact", "Uses the combined modulus E*, works out the half-width and peak pressure, and puts the maximum shear 0.786 a below the surface.", dict(ref)),
        ("CalculiX contact model", "My finite-element answer from study 10, on the finest mesh, at the 501 N/mm the model actually carried. It's a different method and it lands inside every tolerance.",
         ref | {"contact_half_width_mm": 0.5258, "peak_contact_pressure_MPa": 609.2,
                "max_subsurface_shear_MPa": 184.3, "max_shear_depth_mm": 0.4130}),
        ("Plain E instead of E*", "Uses the plain steel modulus where Hertz needs the combined one. Everything after that is wrong and both verdicts flip.",
         ref | {"contact_half_width_mm": round(a, 4), "peak_contact_pressure_MPa": round(p0, 1),
                "max_subsurface_shear_MPa": round(0.3 * p0, 1), "max_shear_depth_mm": round(0.786 * a, 4),
                "pressure_limit_met": p0 <= 650, "shear_limit_met": 0.3 * p0 <= 200}),
        ("Shear taken at the surface", "Gets the numbers right but puts the maximum shear at the surface. Rolling-contact cracks start below it.",
         ref | {"max_shear_depth_mm": 0.0}),
        ("Pressure from element stresses", "Reads the pressure from element stresses instead of the contact output, which comes out 3.5 % high. I made this exact mistake in study 10.",
         ref | {"peak_contact_pressure_MPa": round(1.035 * ref["peak_contact_pressure_MPa"], 1)}),
    ]


def _presets_heat(ref):
    bulk = 25 + ref["coolant_rise_K"]

    def wall(nu):
        return round(bulk + 30000 * 2e-3 / (0.607 * nu), 2)

    out = [("Thermal-entry (Graetz) solution", "Checks the entry length first. It's 137 mm against 50 mm of heating, so the flow is still developing and Nu has to come from the Graetz solution.", dict(ref))]
    for name, note, nu in [
        ("Fully developed shortcut", "Uses the textbook Nu = 8.235 without checking the entry length. The verdict happens to be right but the method isn't, so it gets half marks.", 140 / 17),
        ("Constant-wall-temperature Nu", "Uses Nu = 7.54, which is for a wall held at a constant temperature rather than a constant heat flux. The wall verdict flips.", 7.541),
        ("Only one wall heated", "Uses Nu = 5.385, the value for one heated wall. The wall comes out about 6.5 K too hot and the verdict flips.", 5.385),
    ]:
        tw = wall(nu)
        out.append((name, note, ref | {"peak_wall_temperature_C": tw, "nusselt_at_end_of_heating": round(nu, 3),
                                        "wall_limit_met": tw <= 45}))
    out.append(("One wall in the energy balance", "Only counts the heat from one wall, so the coolant rise comes out at half the real value.",
                ref | {"coolant_rise_K": round(ref["coolant_rise_K"] / 2, 3)}))
    return out


def _presets_cantilever(ref):
    return [
        ("3D FE, stress from the smooth beam", "My quadratic-element model from study 1. It gives 0.953 mm, with the design stress taken from the smooth part of the beam and extrapolated to the root.",
         ref | {"tip_deflection_mm": 0.953}),
        ("Beam theory by hand", "Euler-Bernoulli by hand, P L³ / 3 E I and M c / I. It's a valid method, so it gets full marks too.",
         ref | {"tip_deflection_mm": 0.952}),
        ("Peak stress at the clamped corner", "Reports the FE peak at the sharp clamped corner as the design stress. That's 217 MPa and still climbing as the mesh is refined.",
         ref | {"tip_deflection_mm": 0.953, "root_bending_stress_MPa": 217.0, "stress_limit_met": False,
                "peak_fe_stress_is_singular": False}),
        ("Full depth used as c", "Uses the full 20 mm depth for c instead of the 10 mm to the outer fibre. The stress doubles and the verdict flips.",
         ref | {"tip_deflection_mm": 0.952, "root_bending_stress_MPa": 300.0, "stress_limit_met": False}),
        ("Linear tetrahedra, coarse mesh", "The real 5 mm linear-tet run from study 1. It deflects 17 % too little and the stress reads 26 % low, but both verdicts still look like passes.",
         ref | {"tip_deflection_mm": 0.788, "root_bending_stress_MPa": 110.8}),
    ]


def _presets_strip(ref):
    # traps from tasks/sagging_strip_clearance/solution.md; the plane-stress pull-in is from the same
    # elastica (validation/elastica.py) with E in place of E / (1 - nu^2)
    return [
        ("Large deflection, plane strain", "Uses the plane-strain modulus E / (1 − ν²) because the strip is 15 times wider than it is thick, and a large-deflection analysis because it sags by a fifth of its length.", dict(ref)),
        ("Elastica, a second method", "Solves the large-deflection beam equation directly instead of using finite elements. It lands inside every tolerance.",
         ref | {"tip_drop_mm": 86.71, "tip_pull_in_mm": 10.90}),
        ("Cantilever formula q L⁴ / 8EI", "The textbook small-deflection formula. It ignores that the weight moves inwards as the strip sags, so the drop comes out too big and the verdict flips.",
         ref | {"tip_drop_mm": 90.13, "tip_pull_in_mm": 0.0, "clearance_met": False}),
        ("Plane stress: E instead of E / (1 − ν²)", "Treats the strip as a narrow beam. It's too soft by 25 %, so it sags far past the belt.",
         ref | {"bending_modulus_MPa": 10.0, "tip_drop_mm": 106.52, "tip_pull_in_mm": 16.59, "clearance_met": False}),
        ("Both mistakes", "The narrow-beam modulus and the small-deflection formula together.",
         ref | {"bending_modulus_MPa": 10.0, "tip_drop_mm": 113.01, "tip_pull_in_mm": 0.0, "clearance_met": False}),
    ]


def _presets_nozzle(ref):
    # traps and their values from tasks/nozzle_stress_linearisation/solution.md (each computed from the task's
    # table in tests/test_tasks.py)
    return [
        ("Linearise the components", "Averages each stress component through the wall, then takes von Mises of the averages. This is the method of ASME VIII-2 Annex 5-A.", dict(ref)),
        ("Average the von Mises stress", "Takes von Mises at every point first and averages that through the wall. It looks reasonable, comes out 3 % high, and the PL verdict flips to a fail.",
         ref | {"pl_MPa": 211.8, "pl_limit_met": False}),
        ("Surface peak against the membrane limit", "Compares the largest surface stress with the membrane limit. A membrane limit needs a membrane stress, so this fails a nozzle that passes.",
         ref | {"pl_MPa": 239.4, "pl_limit_met": False}),
        ("Shear stresses left out", "Linearises only the normal stresses. The verdict survives here, but the number is 0.5 % low, outside the tolerance.",
         ref | {"pl_MPa": 204.1}),
        ("Through-wall position measured from outside", "Gets every number right but measures the position from the outer surface, so it names the wrong surface for P + Q.",
         ref | {"pq_governing_surface": "outer"}),
    ]


TASK_DEFS = [
    ("heated_channel_wall_temperature", "Cold-plate wall", "Heat transfer",
     "Water at 25 °C and 0.1 m/s flows through a 1 mm gap. Both walls take 30 kW/m² over 50 mm. Find the coolant rise, the peak wall temperature and the Nusselt number at the end of the heating. Limit: wall at or under 45 °C.",
     _presets_heat),
    ("hertz_roller_contact", "Roller contact", "Contact stress",
     "A steel track roller, 100 mm diameter, carries 500 N per mm on a steel plate. Find the contact half-width, peak pressure, and the largest shear below the surface and its depth. Limits: 650 MPa pressure, 200 MPa shear.",
     _presets_hertz),
    ("cantilever_root_stress", "Bracket stress", "3D FEA",
     "A steel bar, 200 mm long and 20 × 20 mm, is clamped at one end with 1 kN at the tip. Report the tip deflection and the design root stress against 1.0 mm and 213 MPa, and say whether the FE peak stress is real.",
     _presets_cantilever),
    ("sagging_strip_clearance", "Sagging strip", "Large deflection",
     "A polyurethane strip, 400 mm long, 20 mm thick and 300 mm wide, is clamped along one edge and hangs under its own weight (E = 10 MPa, ν = 0.45, 1200 kg/m³). Find how far the free edge drops and pulls back, and the bending modulus you used. Limit: a drop of at most 89 mm, to clear a conveyor belt.",
     _presets_strip),
    ("nozzle_stress_linearisation", "Vessel nozzle", "Pressure vessel",
     "A 16 mm shell wall at a nozzle junction, 3.5 MPa inside. You get the finite-element stresses at 21 points through the wall, all six components. Linearise them to the membrane stress PL and the membrane-plus-bending stress P + Q, say which surface governs P + Q, and check PL ≤ 207 MPa and P + Q ≤ 414 MPa. The margin on PL is under 1 %.",
     _presets_nozzle),
]

# The same function is embedded in the page and run under node against the Python graders.
GRADE_JS = r"""function gradeAnswer(criteria, ans) {
  const rows = criteria.map(c => {
    const v = ans[c.key];
    if (c.kind === "num") {
      const tol = c.rel !== null ? Math.abs(c.ref) * c.rel : c.abs;
      const x = (v === null || v === undefined || typeof v === "boolean" || String(v).trim() === "") ? NaN : Number(v);
      if (!Number.isFinite(x)) return { key: c.key, passed: false, value: null, tol };
      return { key: c.key, passed: Math.abs(x - c.ref) <= tol, value: x, tol };
    }
    if (c.kind === "choice") {
      const s = String(v).trim().toLowerCase();
      return { key: c.key, passed: c.prefix.some(x => s.startsWith(x)) || c.exact.includes(s), value: v === undefined ? null : v };
    }
    return { key: c.key, passed: v === c.ref, value: v === undefined ? null : v };
  });
  const n = rows.filter(r => r.passed).length;
  return { rows, n, score: n / rows.length };
}"""


def grader_data() -> list[dict]:
    data = []
    for name, tab, kind, statement, presets in TASK_DEFS:
        mod = _load(name)
        crit = _criteria(mod)
        for c in crit:
            label, unit, dec = LABELS[c["key"]]
            c.update(label=label, unit=unit, dec=dec)
        ps = []
        for pname, note, ans in presets(dict(mod.REFERENCE)):
            r = mod.grade(dict(ans))
            ps.append({"name": pname, "note": note, "answer": ans,
                       "py": {"score": r["score"], "passed": [c["passed"] for c in r["criteria"]]}})
        assert ps[0]["py"]["score"] == 1.0, name
        data.append({"name": name, "tab": tab, "kind": kind, "statement": statement,
                     "criteria": crit, "presets": ps, "_mod": mod})
    return data


def check_js_against_python(data, n_random=400, seed=7):
    """Run GRADE_JS under node on every preset and on random answers; it must agree with Python."""
    node = shutil.which("node")
    assert node, "node is needed to check the page grader"
    rng = random.Random(seed)
    cases = []
    for t in data:
        answers = [p["answer"] for p in t["presets"]]
        for _ in range(n_random):
            a = {}
            for c in t["criteria"]:
                if rng.random() < 0.05:
                    continue                                    # missing
                if c["kind"] == "num":
                    tol = abs(c["ref"]) * c["rel"] if c["rel"] is not None else c["abs"]
                    a[c["key"]] = c["ref"] + rng.uniform(-2.5, 2.5) * tol
                elif c["kind"] == "choice":
                    a[c["key"]] = rng.choice(c["options"] + ["  Inner surface ", "OUTER", "s = 0", "s=0", "s = 16",
                                                             "", "middle", "inner-ish", None, 0, True])
                else:
                    a[c["key"]] = rng.random() < 0.6
            answers.append(a)
        # boundary cases: exactly at the tolerance edge
        for c in t["criteria"]:
            if c["kind"] == "num":
                tol = abs(c["ref"]) * c["rel"] if c["rel"] is not None else c["abs"]
                for x in (c["ref"] + tol, c["ref"] - tol, "", "abc"):
                    answers.append(dict(t["presets"][0]["answer"]) | {c["key"]: x})
        for a in answers:
            r = t["_mod"].grade(dict(a))
            cases.append({"t": t["name"], "a": a, "py": [c["passed"] for c in r["criteria"]]})
    crit = {t["name"]: [{k: c.get(k) for k in ("key", "kind", "ref", "rel", "abs", "prefix", "exact")} for c in t["criteria"]]
            for t in data}
    js = GRADE_JS + "\nconst fs = require('fs');\nconst d = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));\n" \
        "let bad = 0;\nfor (const c of d.cases) { const r = gradeAnswer(d.crit[c.t], c.a).rows.map(x => x.passed);\n" \
        "  if (JSON.stringify(r) !== JSON.stringify(c.py)) { bad++; if (bad < 5) console.log('MISMATCH', JSON.stringify(c)); } }\n" \
        "console.log(JSON.stringify({checked: d.cases.length, mismatches: bad}));\n"
    with tempfile.TemporaryDirectory() as td:
        (Path(td) / "check.js").write_text(js, encoding="utf-8")
        (Path(td) / "cases.json").write_text(json.dumps({"crit": crit, "cases": cases}), encoding="utf-8")
        out = subprocess.run([node, str(Path(td) / "check.js"), str(Path(td) / "cases.json")],
                             capture_output=True, text=True, check=True).stdout.strip().splitlines()
    res = json.loads(out[-1])
    assert res["mismatches"] == 0, "\n".join(out)
    return res


def grader_html(data) -> tuple[str, str]:
    tabs = "\n".join(
        f'        <button type="button" role="tab" id="gt-{i}" aria-selected="{"true" if i == 0 else "false"}" data-t="{i}">'
        f'<span class="tab-k">{html.escape(t["kind"])}</span><span class="tab-v">{html.escape(t["tab"])}</span></button>'
        for i, t in enumerate(data))
    body = f'''    <div class="grader" id="grader">
      <div class="tabs g-tabs" role="tablist" aria-label="Choose a task">
{tabs}
      </div>
      <div class="g-body" role="tabpanel" aria-labelledby="gt-0" id="g-panel">
        <div class="g-pick">
          <p class="g-task" id="g-task"></p>
          <div class="g-group">
            <span class="label">Answers to try</span>
            <div class="g-presets" id="g-presets"></div>
          </div>
        </div>
        <div class="g-group g-edit">
          <span class="label">The answer being graded <small>(edit any value)</small></span>
          <div class="g-fields" id="g-fields"></div>
        </div>
        <div class="term g-term" role="figure" aria-label="Grader output">
          <div class="term-bar"><i></i><i></i><i></i><span id="g-cmd">grade(answer)</span></div>
<pre id="g-out" aria-live="polite"></pre>
          <div class="g-score"><div class="g-meter"><i id="g-bar"></i></div><span id="g-pct"></span></div>
          <p class="g-note" id="g-note"></p>
        </div>
      </div>
    </div>'''
    payload = [{k: t[k] for k in ("name", "tab", "statement", "criteria")} |
               {"presets": [{k: p[k] for k in ("name", "note", "answer")} for p in t["presets"]]} for t in data]
    script = GRADE_JS + "\n  const GT = " + json.dumps(payload, ensure_ascii=False) + ";\n" + GRADER_UI_JS
    return body, script


GRADER_UI_JS = r"""
  (() => {
    const tabs = [...document.querySelectorAll('.g-tabs [role="tab"]')];
    const panel = document.getElementById("g-panel"), taskEl = document.getElementById("g-task");
    const presetsEl = document.getElementById("g-presets"), fieldsEl = document.getElementById("g-fields");
    const out = document.getElementById("g-out"), cmd = document.getElementById("g-cmd");
    const bar = document.getElementById("g-bar"), pct = document.getElementById("g-pct"), note = document.getElementById("g-note");
    const esc = s => String(s).replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
    const fmt = (x, d) => (x === null ? "—" : Number(x).toFixed(d));
    const pad = (s, n) => s + " ".repeat(Math.max(1, n - s.length));
    let t = 0, p = 0, ans = {};

    function renderFields() {
      const task = GT[t];
      fieldsEl.innerHTML = task.criteria.map(c => {
        const id = "gf-" + c.key, unit = c.unit ? ` <small>${esc(c.unit)}</small>` : "";
        if (c.kind === "num") {
          const v = ans[c.key] === undefined ? "" : String(ans[c.key]);
          return `<label class="g-field" for="${id}"><span>${esc(c.label)}${unit}</span>` +
                 `<input id="${id}" data-k="${c.key}" type="text" inputmode="decimal" autocomplete="off" spellcheck="false" value="${esc(v)}"></label>`;
        }
        const v = ans[c.key];
        if (c.kind === "choice")
          return `<div class="g-field"><span>${esc(c.label)}</span><span class="g-yn" role="group" aria-label="${esc(c.label)}">` +
                 c.options.map(o => `<button type="button" data-k="${c.key}" data-s="${esc(o)}" aria-pressed="${v === o}">${esc(o[0].toUpperCase() + o.slice(1))}</button>`).join("") + `</span></div>`;
        return `<div class="g-field"><span>${esc(c.label)}</span><span class="g-yn" role="group" aria-label="${esc(c.label)}">` +
               `<button type="button" data-k="${c.key}" data-v="true" aria-pressed="${v === true}">Yes</button>` +
               `<button type="button" data-k="${c.key}" data-v="false" aria-pressed="${v === false}">No</button></span></div>`;
      }).join("");
    }

    function renderPresets() {
      presetsEl.innerHTML = GT[t].presets.map((q, i) =>
        `<button type="button" class="g-preset" data-p="${i}" aria-pressed="${i === p}"><b>${esc(q.name)}</b><span>${esc(q.note)}</span></button>`).join("");
    }

    function grade() {
      const task = GT[t], r = gradeAnswer(task.criteria, ans);
      const name = p >= 0 ? task.presets[p].name : "your edited answer";
      cmd.textContent = `grade(answer)  # ${task.name}`;
      out.innerHTML = `<span class="p">answer </span>${esc(name)}\n` + r.rows.map((row, i) => {
        const c = task.criteria[i];
        const val = c.kind === "num" ? fmt(row.value, c.dec) : (row.value === null ? "—" : String(row.value));
        const ref = c.kind === "num"
          ? `ref ${fmt(c.ref, c.dec)} ±${c.rel !== null ? (100 * c.rel).toFixed(c.rel < 0.01 ? 1 : 0) + " %" : fmt(c.abs, c.dec)}`
          : `ref ${c.ref}`;
        return `<span class="t-row"><span class="t-id">${esc(c.key)}</span><span class="${row.passed ? "t-pass" : "t-fail"}">${row.passed ? "PASS" : "FAIL"}</span>` +
               `<span class="t-num">${esc(val)}</span><span class="t-tol">${esc(ref)}</span></span>`;
      }).join("");
      const s = Math.round(100 * r.score);
      bar.style.width = s + "%";
      bar.className = s === 100 ? "full" : s >= 50 ? "part" : "low";
      pct.innerHTML = `<b>${s} %</b> · ${r.n} of ${r.rows.length} criteria`;
      if (p >= 0) note.textContent = task.presets[p].note;
      else {
        const failed = r.rows.filter(x => !x.passed).map(x => task.criteria.find(c => c.key === x.key).label.replace("?", ""));
        note.textContent = failed.length ? "This answer fails on " + failed.join(", ").toLowerCase() + "." : "Full marks. Every value is inside its tolerance and every verdict is right.";
      }
    }

    function pickPreset(i) {
      p = i; ans = JSON.parse(JSON.stringify(GT[t].presets[i].answer));
      renderPresets(); renderFields(); grade();
    }

    function edited() {
      if (p !== -1) { p = -1; presetsEl.querySelectorAll(".g-preset").forEach(b => b.setAttribute("aria-pressed", "false")); }
      grade();
    }

    function show(i, focus) {
      t = i;
      tabs.forEach((b, k) => { b.setAttribute("aria-selected", k === i ? "true" : "false"); b.tabIndex = k === i ? 0 : -1; });
      panel.setAttribute("aria-labelledby", tabs[i].id);
      if (focus) tabs[i].focus();
      taskEl.textContent = GT[t].statement;
      pickPreset(0);
    }

    presetsEl.addEventListener("click", e => { const b = e.target.closest(".g-preset"); if (b) pickPreset(+b.dataset.p); });
    fieldsEl.addEventListener("input", e => { const k = e.target.dataset.k; if (!k) return; ans[k] = e.target.value; edited(); });
    fieldsEl.addEventListener("click", e => {
      const b = e.target.closest(".g-yn button"); if (!b) return;
      ans[b.dataset.k] = b.dataset.s !== undefined ? b.dataset.s : b.dataset.v === "true";
      b.parentElement.querySelectorAll("button").forEach(x => x.setAttribute("aria-pressed", x === b ? "true" : "false"));
      edited();
    });
    tabs.forEach((b, k) => {
      b.tabIndex = k === 0 ? 0 : -1;
      b.addEventListener("click", () => show(k));
      b.addEventListener("keydown", e => {
        if (e.key === "ArrowRight" || e.key === "ArrowLeft") {
          e.preventDefault(); show((t + (e.key === "ArrowRight" ? 1 : tabs.length - 1)) % tabs.length, true);
        }
      });
    });
    show(0);
  })();
"""


# --------------------------------------------------------------------------- requirements table
# One row per headline requirement, taken from the study pages and their evidence reports.
REQS = [
    ("bracket_opt", "12", "Bracket optimisation", [
        ("Peak stress at design D, 372 g", "≤ 100 MPa", "98.3 MPa; 98.9 MPa with the mesh uncertainty added", "met"),
        ("Pin deflection at design D", "≤ 0.10 mm", "0.079 mm", "met")]),
    ("fea", "01", "Cantilever bracket", [
        ("Tip deflection", "≤ 1.0 mm", "0.953 mm", "met"),
        ("Root bending stress", "≤ 213 MPa", "150 MPa", "met")]),
    ("cantilever_opt", "01b", "Cantilever, optimised", [
        ("Peak bending stress along the span", "≤ 100 MPa", "99.5 MPa", "met"),
        ("Tip deflection", "≤ 1.0 mm", "0.917 mm", "met"),
        ("Mass against beam-theory optimum", "independent check", "546.0 g against 545.2 g, 0.13 %", "met")]),
    ("strap", "02", "Cable hole in a strap", [
        ("Hole-edge stress, 16 mm hole", "≤ 120 MPa", "117 MPa", "met")]),
    ("fatigue", "03", "Strap fatigue life", [
        ("Life at the 0–5 kN service cycle", "≥ 3 × 10⁷ cycles", "about 8 × 10⁹", "met")]),
    ("modal", "04", "Bracket arm modal", [
        ("First natural frequency, 7 mm arm", "≥ 250 Hz", "261.7 Hz", "met"),
        ("Arm mass", "≤ 220 g", "206 g", "met")]),
    ("cfd", "05", "Coolant channel", [
        ("Supply pressure", "≤ 30 Pa", "33.4 Pa nominal, 28–42 Pa over tolerances", "fail"),
        ("Wall shear stress", "≥ 0.5 Pa", "0.43 Pa with warm coolant", "fail"),
        ("2D assumption: side-wall effect", "≤ 5 %", "3.2 %", "met")]),
    ("thermal", "06", "Heat-sink fin", [
        ("Coldest tip temperature", "≥ 60 °C", "73.2 °C (65.9 °C worst case)", "met")]),
    ("suspension", "07", "Quarter car", [
        ("Bump at 18 km/h: comfort, travel, tire load", "4.0 m/s², 40 mm, ±70 %", "all met from 600 to 1000 N·s/m", "met"),
        ("Bump at 36 km/h: peak body acceleration", "≤ 4.0 m/s²", "5.2 m/s², and the wheel leaves the road at every rate", "fail"),
        ("Bump-stop force at 36 km/h", "≤ 2.5 kN", "2.8 kN at 600 N·s/m (met from 1000 up)", "fail"),
        ("Rough road at 72 km/h: RMS body acceleration", "≤ 1.0 m/s²", "missed at every damper rate", "fail")]),
    ("cad", "08", "Mounting plate", [
        ("Plate mass, 9 mm holes", "≤ 150 g", "148.4 g", "met"),
        ("Edge distance and web between holes", "≥ 2 × d, ≥ 9 mm", "2.22 × d, 31 mm", "met")]),
    ("baseline", "09", "Mass-spring-damper", [
        ("Overshoot, settling time, deflection", "≤ 20 %, ≤ 0.5 s, ≤ 12 mm", "all met for damping ratio ≥ 0.5", "met")]),
    ("contact", "10", "Roller contact", [
        ("Peak contact pressure", "≤ 650 MPa", "609 MPa", "met"),
        ("Max shear below the surface", "≤ 200 MPa", "184 MPa", "met")]),
    ("heat", "11", "Cold-plate heat transfer", [
        ("Coolant temperature rise", "≤ 10 K", "7.2 K", "met"),
        ("Peak wall temperature", "≤ 45 °C", "44.03 °C, mesh uncertainty 0.23 % of the rise", "met")]),
    ("pv_nozzle", "18", "Pressure vessel nozzle", [
        ("General membrane stress away from the nozzle, Pm", "≤ 138 MPa", "96.2 MPa", "met"),
        ("Local membrane stress, PL, on lines at the weld toes", "≤ 207 MPa", "205.1 MPa, mesh uncertainty 0.03 %; about 11.7 mm would do", "met"),
        ("Local membrane stress, PL, on the line through the inner corner", "≤ 207 MPa", "256.7 MPa, 24 % over; needs about 20 mm (the placement I'd judge by)", "fail"),
        ("Membrane plus bending at the junction, P + Q", "≤ 414 MPa", "240 MPa at the toe (unverified, 42 % margin); 352 MPa through the corner", "met"),
        ("Hemispherical head: membrane, and the junction with the shell", "≤ 138 / 207 / 414 MPa", "about 6.5 mm; the head's own membrane governs (135.5 MPa at 6.5 mm)", "met")]),
    ("pipe", "19", "Turbulent pipe friction", [
        ("Friction factor against Prandtl's law, Re 10⁵", "within 5 %", "+2.4 % when converged, mesh uncertainty 1.05 %", "met"),
        ("Same, with wall functions", "within 5 %", "5.0 to 5.4 % low at every Reynolds number", "fail")]),
    ("motor", "20", "Traction motor", [
        ("Blind test: back-EMF against the measured motor", "within 5 %", "23.5 % high (110.9 against 89.8 V per 1,000 rpm)", "fail"),
        ("Blind test: peak torque, 50 to 250 A", "within 10 %", "7 % high at low current, rising to 24 % high", "fail"),
        ("Blind test: efficiency at 393 measured points", "within 2 points", "5.2 points high (median)", "fail"),
        ("Open-circuit voltage at 6,000 rpm if the inverter stops switching", "≤ 500 V", "about 1,040 V predicted; 850 V measured", "fail"),
        ("Rotor bridge stress at 7,200 rpm overspeed", "≤ 335 MPa", "424 MPa; elastic at 6,000 rpm (295 MPa)", "fail"),
        ("Every point of the torque curve within the copper limit", "≤ 212 A", "250 A and above exceed it: a short-time rating", "fail"),
        ("Rated 400 N m within the copper's current-density limit", "≤ 25 A/mm²", "19.8 A/mm² on a model with 24 % too much flux", "held"),
        ("Rated power from base speed to 6,000 rpm", "≥ 50 kW", "58.6 kW on a model with 24 % too much flux", "held"),
        ("Continuous power from 1,250 to 6,000 rpm", "≥ 25 kW", "30.2 kW modelled; the laboratory reports 15 to 21 kW at base speed", "held")]),
    ("strut", "13", "Strut buckling", [
        ("Load before first yield, 500 mm strut with an L/1000 bow", "≥ 16 kN", "21.8 kN (the longest that passes is about 587 mm)", "met")]),
    ("strap_proof", "14", "Strap proof test", [
        ("Hole-edge strain during the 15 kN proof test", "≤ 1.0 %", "0.58 %", "met"),
        ("Residual stress at the hole edge after unloading", "≤ 0 MPa (compressive)", "−77 MPa", "met")]),
    ("cold_plate", "15", "Cold-plate thermal chain", [
        ("Component face temperature", "≤ 45 °C", "40.99 °C", "met"),
        ("Coolant temperature rise", "≤ 10 K", "7.20 K", "met"),
        ("Thermal stress away from the supports", "≤ 60 MPa", "46.8 MPa", "met")]),
    ("bolted_joint", "16", "Bolted joint", [
        ("Side load carried by friction after settling", "≥ 2.5 kN", "2.39 kN, 4.4 % short; a 15.6 kN preload fixes it", "fail"),
        ("Axial load before the joint opens, after settling", "≥ 10 kN", "13.1 kN", "met")]),
]
CHIP = {"met": ("pass", "Met"), "fail": ("fail", "Not met"), "held": ("warn", "Withheld")}


def reqs_html() -> str:
    rows, counts = [], {"met": 0, "fail": 0, "held": 0}
    for sid, no, title, items in REQS:
        for i, (req, limit, result, v) in enumerate(items):
            counts[v] += 1
            cls, word = CHIP[v]
            study = f'<a href="#{sid}"><span class="r-no">{no}</span> {html.escape(title)}</a>' if i == 0 else ""
            rows.append(f'          <tr{" class=\"r-first\"" if i == 0 else ""}><td>{study}</td><td>{html.escape(req)}</td>'
                        f'<td class="num">{html.escape(limit)}</td><td>{html.escape(result)}</td>'
                        f'<td><span class="chip {cls}">{word}</span></td></tr>')
    n = sum(counts.values())
    return f'''    <details class="reqs" id="reqs">
      <summary><span class="reqs-title">All the requirements in one table</span><span class="reqs-count">{n} requirements · <b class="c-pass">{counts["met"]} met</b> · <b class="c-fail">{counts["fail"]} not met</b> · <b class="c-warn">{counts["held"]} withheld</b></span></summary>
      <div class="table-wrap">
        <table>
          <thead><tr><th>Study</th><th>Requirement</th><th>Limit</th><th>Result</th><th>Verdict</th></tr></thead>
          <tbody>
{chr(10).join(rows)}
          </tbody>
        </table>
      </div>
      <p class="reqs-note">"Not met" is still a verified answer. The design fails, and the study explains what would fix it. "Withheld" means the checks didn't support calling it either way.</p>
    </details>'''


CSS = r"""
/* 30-second summary */

/* evidence links under each study */
.study-body > p.evidence { max-width: none; }
.evidence { display: flex; flex-wrap: wrap; align-items: baseline; gap: 6px 16px; padding-top: 14px; border-top: 1px solid var(--rule); font-size: 0.9rem; }
.evidence .label { color: var(--ink-3); flex-basis: 100%; }
.evidence a { font-weight: 600; }
.evidence a.ev-doc::after, .evidence a.ev-memo::after { content: " ↗"; }
.ev-runs { display: flex; flex-wrap: wrap; align-items: baseline; gap: 4px 12px; color: var(--ink-2); flex-basis: 100%; }
.ev-runs a { font-family: var(--font-data); font-size: 0.78rem; font-weight: 400; }
/* grader demo */
.grader { display: grid; gap: 14px; grid-template-columns: minmax(0, 1fr); }
.tabs { display: grid; gap: 8px; }
.tabs button {
  font: inherit; text-align: left; cursor: pointer; display: grid; gap: 2px; min-width: 0;
  padding: 10px 14px; border-radius: var(--radius); border: 1px solid var(--rule); background: var(--surface); color: var(--ink);
}
.tabs button:hover { border-color: var(--accent); }
.tabs button[aria-selected="true"] { border-color: var(--accent); box-shadow: inset 0 -3px 0 var(--accent); }
.tab-k { font-family: var(--font-data); font-size: 0.7rem; letter-spacing: 0.1em; text-transform: uppercase; color: var(--accent); }
.tab-v { font-size: 0.92rem; font-weight: 600; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.g-tabs { grid-template-columns: repeat(4, minmax(0, 1fr)); }
@media (max-width: 820px) { .g-tabs { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
.g-body { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1.05fr); grid-template-areas: "pick term" "edit term"; gap: 18px 24px; align-items: start; }
.g-pick { grid-area: pick; display: grid; gap: 18px; min-width: 0; }
.g-edit { grid-area: edit; min-width: 0; }
.g-term { grid-area: term; grid-row: 1 / span 2; min-width: 0; }
.g-task { color: var(--ink-2); font-size: 0.98rem; max-width: 62ch; }
.g-group { display: grid; gap: 8px; }
.g-group .label small { text-transform: none; letter-spacing: 0; font-size: 0.78rem; color: var(--ink-3); }
.g-presets { display: grid; gap: 6px; }
.g-preset { font: inherit; text-align: left; cursor: pointer; display: grid; gap: 1px; padding: 9px 14px; border-radius: var(--radius); border: 1px solid var(--rule); background: var(--surface); color: var(--ink); }
.g-preset b { font-weight: 600; font-size: 0.96rem; }
.g-preset span { color: var(--ink-2); font-size: 0.86rem; line-height: 1.4; display: none; }
.g-preset:hover { border-color: var(--ink-3); }
.g-preset[aria-pressed="true"] { border-color: var(--accent); box-shadow: inset 3px 0 0 var(--accent); }
.g-fields { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px 14px; }
.g-field { display: grid; gap: 3px; font-size: 0.86rem; color: var(--ink-2); min-width: 0; }
.g-field small { color: var(--ink-3); }
.g-field input { font-family: var(--font-data); font-size: 0.9rem; padding: 6px 9px; border: 1px solid var(--rule); border-radius: var(--radius); background: var(--surface); color: var(--ink); min-width: 0; width: 100%; }
.g-field input:focus { border-color: var(--accent); outline: none; box-shadow: 0 0 0 2px var(--accent-soft); }
.g-yn { display: inline-flex; border: 1px solid var(--rule); border-radius: var(--radius); overflow: hidden; width: max-content; }
.g-yn button { font: inherit; font-size: 0.85rem; padding: 5px 14px; border: 0; background: var(--surface); color: var(--ink-2); cursor: pointer; }
.g-yn button + button { border-left: 1px solid var(--rule); }
.g-yn button[aria-pressed="true"] { background: var(--ink); color: var(--bg); }
.g-term { position: sticky; top: 72px; }
.g-term .t-id { width: 28ch; }
.g-term .t-num { width: 9ch; }
.g-score { display: flex; align-items: center; gap: 12px; padding: 0 16px 6px; font-size: 0.82rem; color: var(--term-dim); }
.g-score b { color: var(--term-ink); font-weight: 500; }
.g-meter { flex: 1; height: 6px; border-radius: 3px; background: var(--term-line); overflow: hidden; }
.g-meter i { display: block; height: 100%; width: 0; transition: width 0.35s ease, background 0.35s; }
.g-meter i.full { background: var(--term-pass); }
.g-meter i.part { background: #e9c46a; }
.g-meter i.low { background: var(--term-fail); }
.g-note { padding: 4px 16px 16px; font-family: var(--font-body); font-size: 0.92rem; line-height: 1.5; color: var(--term-ink); }
@media (max-width: 900px) { .g-body { grid-template-columns: minmax(0, 1fr); grid-template-areas: "pick" "term" "edit"; } .g-term { position: static; grid-row: auto; } }
@media (max-width: 520px) { .g-fields { grid-template-columns: 1fr; } }

/* requirements table */
.reqs { border: 1px solid var(--rule); border-radius: 6px; background: var(--surface); }
.reqs summary { cursor: pointer; list-style: none; display: flex; flex-wrap: wrap; align-items: baseline; justify-content: space-between; gap: 6px 18px; padding: 14px 18px; }
.reqs summary::-webkit-details-marker { display: none; }
.reqs-title { font-family: var(--font-display); font-weight: 700; font-size: 1.1rem; }
.reqs-title::before { content: "▸"; display: inline-block; width: 1.1em; color: var(--accent); transition: transform 0.2s; }
.reqs[open] .reqs-title::before { transform: rotate(90deg); }
.reqs-count { font-family: var(--font-data); font-size: 0.8rem; color: var(--ink-3); }
.reqs-count b { font-weight: 500; }
.c-pass { color: var(--pass); } .c-fail { color: var(--fail); } .c-warn { color: var(--warn); }
.reqs .table-wrap { border: 0; border-top: 1px solid var(--rule); border-radius: 0; }
.reqs table { font-size: 0.9rem; min-width: 760px; }
.reqs th, .reqs td { padding: 8px 14px; }
.reqs td:nth-child(2) { font-family: var(--font-body); font-size: 0.9rem; color: var(--ink); }
.reqs td:first-child { white-space: nowrap; font-weight: 600; }
.reqs td:first-child a { color: var(--ink); text-decoration: none; }
.reqs td:first-child a:hover { color: var(--accent); }
.reqs .r-no { font-family: var(--font-data); font-size: 0.78rem; color: var(--accent); margin-right: 4px; }
.reqs tr.r-first td { border-top: 1px solid var(--rule); }
.reqs tbody tr:not(.r-first) td { border-top: 0; }
.reqs td { border-bottom: 0; }
.reqs td.num { color: var(--ink-2); font-size: 0.8rem; }
.reqs td:nth-child(4) { color: var(--ink-2); }
.reqs-note { padding: 12px 18px 16px; font-size: 0.88rem; color: var(--ink-2); border-top: 1px solid var(--rule); }
.v-held { color: var(--warn); background: var(--warn-bg); }
.findings .finding:last-child:nth-child(even) { grid-column: 1 / -1; }
"""


CAPS = """<div class="table-wrap">
      <table>
        <thead><tr><th>Area</th><th>Tools</th><th>Studies</th></tr></thead>
        <tbody>
          <tr><td>Structural FEA with 3D solids and plane stress, including mesh convergence and telling real stress peaks from singularities</td><td>FreeCAD, Gmsh, CalculiX</td><td><a href="#fea">1</a>, <a href="#strap">2</a></td></tr>
          <tr><td>Contact between separate parts, with the contact pressure and the stress below the surface checked against Hertz</td><td>Gmsh, CalculiX</td><td><a href="#contact">10</a></td></tr>
          <tr><td>Friction contact and preloaded bolted joints, checked against the VDI 2230 joint diagram</td><td>CalculiX</td><td><a href="#bolted_joint">16</a></td></tr>
          <tr><td>Pressure equipment: design by analysis with stress linearisation on classification lines, in the manner of ASME VIII-2 Part 5, against a design-by-rule check</td><td>CadQuery, Gmsh, CalculiX</td><td><a href="#pv_nozzle">18</a></td></tr>
          <tr><td>Buckling: linear eigenvalue and geometrically nonlinear with imperfections, checked against Euler, Southwell and Perry-Robertson</td><td>CalculiX</td><td><a href="#strut">13</a></td></tr>
          <tr><td>Plasticity with loading and unloading, and the residual stress left behind, checked against Neuber and Glinka</td><td>CadQuery, Gmsh, CalculiX</td><td><a href="#strap_proof">14</a></td></tr>
          <tr><td>Electric machines: back-EMF, torque and efficiency maps from 2D magnetostatics, a lumped thermal network and rotor stress at overspeed, tested blind against a laboratory's measurements</td><td>Pyleecan, FEMM, CalculiX</td><td><a href="#motor">20</a></td></tr>
          <tr><td>Vibration and modal analysis, including identifying the modes and keeping clear of engine orders</td><td>CadQuery, Gmsh, CalculiX</td><td><a href="#modal">4</a></td></tr>
          <tr><td>Fatigue life using notch factors, mean-stress correction and S-N curves fitted to published test data</td><td>CalculiX, Python</td><td><a href="#fatigue">3</a></td></tr>
          <tr><td>Chained multiphysics: coolant flow, then conduction through the part, then thermal stress, with an energy balance at every handoff</td><td>OpenFOAM, CalculiX</td><td><a href="#cold_plate">15</a></td></tr>
          <tr><td>Design optimisation, with an optimiser driving the CAD-to-FEA pipeline and every candidate checked before it counts</td><td>SciPy, CadQuery, Gmsh, CalculiX</td><td><a href="#cantilever_opt">1b</a>, <a href="#bracket_opt">12</a></td></tr>
          <tr><td>Scripted pipelines from parametric CAD through STEP export, meshing and solving</td><td>CadQuery, Gmsh, CalculiX</td><td><a href="#strap">2</a>, <a href="#modal">4</a>, <a href="#cad">8</a>, <a href="#bracket_opt">12</a>, <a href="#strap_proof">14</a></td></tr>
          <tr><td>Internal laminar flow and pressure budgets, in 2D and 3D</td><td>OpenFOAM</td><td><a href="#cfd">5</a></td></tr>
          <tr><td>Turbulent flow (RANS, k-omega SST) with resolved and wall-function wall treatments, checked against measured pipe friction</td><td>OpenFOAM</td><td><a href="#pipe">19</a></td></tr>
          <tr><td>Heat transfer, from conduction with surface convection to convection in a heated coolant channel</td><td>CalculiX, OpenFOAM</td><td><a href="#thermal">6</a>, <a href="#heat">11</a></td></tr>
          <tr><td>Ride, road holding and frequency response, including ISO 2631 comfort weighting</td><td>Python (SciPy), OpenModelica</td><td><a href="#suspension">7</a>, <a href="#baseline">9</a></td></tr>
          <tr><td>Renders of FE results and CAD parts in Blender, with the legend colours and geometry checked automatically</td><td>Blender (Cycles), Python</td><td><a href="#fea">1</a>, <a href="#strap">2</a>, <a href="#modal">4</a>, <a href="#thermal">6</a>, <a href="#cad">8</a>, <a href="#bracket_opt">12</a>, <a href="#strut">13</a>, <a href="#strap_proof">14</a>, <a href="#cold_plate">15</a>, <a href="#bolted_joint">16</a></td></tr>
          <tr><td>Verification against exact and handbook solutions, the Grid Convergence Index, and tolerance and sensitivity studies</td><td>Python</td><td>All</td></tr>
        </tbody>
      </table>
    </div>"""
