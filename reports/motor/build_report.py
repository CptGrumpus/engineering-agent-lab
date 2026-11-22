"""Study 7 (2004 Toyota Prius motor) HTML reports, kept apart from the main dashboard.

usage: .venv/Scripts/python.exe reports/motor/build_report.py [artifact-index-path]

Reads the motor cases (their header comments are the study's written record: predictions before each run, results
after), the runs they produced (report.json, verification.json, manifest.json, point.json, figures), and the two
machine definitions (Pyleecan's bundled Toyota_Prius.json and ours, models/motor/Toyota_Prius_ORNL.json). Writes
self-contained pages (figures embedded) to reports/motor/: index.html, geometry.html, open-circuit.html.

Numbers that came from scratch runs (not harness runs) are typed in below with the BACKLOG entry they come from.
"""

from __future__ import annotations

import base64
import html
import json
import math
import re
import sys
import tomllib
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))

from models.motor.build_prius_ornl import CHANGES, IN, SOURCE  # noqa: E402  (plain data; Pyleecan imported lazily)
from studies.motor_em import pyleecan_python  # noqa: E402

CASES = ["motor_prius_oc_mesh", "motor_prius_oc_mesh_r1", "motor_prius_ornl_oc_mesh"]
ORNL_THERMAL = "https://info.ornl.gov/sites/publications/Files/Pub57487.pdf"
ORNL_DESIGN = "https://info.ornl.gov/sites/publications/Files/Pub57348.pdf"
E = html.escape


# --------------------------------------------------------------------------- data

def case_record(name):
    path = REPO / "cases" / f"{name}.toml"
    text = path.read_text(encoding="utf-8")
    header = []
    for line in text.splitlines():
        if not line.startswith("#"):
            break
        header.append(line[2:] if line.startswith("# ") else line[1:])
    return {"name": name, "path": path, "header": "\n".join(header), "toml": tomllib.loads(text)}


def latest_run(name):
    runs = sorted(p for p in (REPO / "runs").glob(f"*_{name}") if re.fullmatch(r"\d{8}-\d{6}_" + re.escape(name), p.name))
    return runs[-1] if runs else None


def load_run(name):
    d = latest_run(name)
    if d is None:
        return None
    r = {"dir": d, "id": d.name}
    for f in ("report", "verification", "manifest"):
        p = d / f"{f}.json"
        r[f] = json.loads(p.read_text(encoding="utf-8").replace("Infinity", "1e999")) if p.exists() else None
    r["points"] = []
    for pd in sorted((d / "points").glob("p*")):
        pj = pd / "point.json"
        if pj.exists():
            pt = json.loads(pj.read_text(encoding="utf-8"))
            ck = pd / "checks.json"
            pt["checks"] = json.loads(ck.read_text(encoding="utf-8"))["checks"] if ck.exists() else []
            pt["dir"] = pd
            r["points"].append(pt)
    r["complete"] = r["report"] is not None
    return r


def machine_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def pyleecan_machine_path():
    py = pyleecan_python()
    return py.parent.parent / "Lib" / "site-packages" / "pyleecan" / "Data" / "Machine" / "Toyota_Prius.json"


def dig(d, path):
    for k in path.split("."):
        d = d[k]
    return d


# --------------------------------------------------------------------------- html helpers

def img64(path, alt, cls="plate"):
    if not Path(path).exists():
        return f'<p class="muted">Figure not available yet: {E(Path(path).name)}</p>'
    b = base64.b64encode(Path(path).read_bytes()).decode()
    return f'<img class="{cls}" alt="{E(alt)}" src="data:image/png;base64,{b}">'


def fmt(x, nd=4):
    if x is None:
        return "–"
    if isinstance(x, str):
        return E(x)
    if not math.isfinite(x):
        return "no estimate"
    if x != 0 and (abs(x) < 1e-3 or abs(x) >= 1e5):
        return f"{x:.2e}"
    return f"{x:.{nd}g}"


def pill(status):
    s = str(status).upper()
    cls = "pass" if s.startswith("PASS") else "fail" if s.startswith("FAIL") else "warn"
    return f'<span class="pill {cls}">{E(str(status))}</span>'


def table(head, rows, cls=""):
    th = "".join(f"<th>{h}</th>" for h in head)
    tr = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows)
    return f'<div class="tablewrap"><table class="{cls}"><thead><tr>{th}</tr></thead><tbody>{tr}</tbody></table></div>'


CSS = """
:root {
  /* Layout: a single reading column (about 72ch) with full-width tables and figures; a slim page bar on top. */
  --bg: #eef1f5; --surface: #ffffff; --ink: #0e1621; --ink-2: #4a5666; --ink-3: #6e7c8c; --rule: #d5dce5;
  --accent: #2346c4; --accent-soft: #e4e9fb; --plate: #fcfcfb;
  --pass: #157447; --pass-bg: #e0f1e7; --fail: #b0381a; --fail-bg: #fbe6df; --warn: #855f00; --warn-bg: #f9efd6;
  --s1: #2346c4; --s2: #c9461a; --grid: #e3e8ee;
  --font-display: "Archivo", "Arial Narrow", system-ui, sans-serif;
  --font-body: "Source Sans 3", "Segoe UI", system-ui, -apple-system, sans-serif;
  --font-data: "JetBrains Mono", ui-monospace, "Cascadia Mono", Consolas, monospace;
  --radius: 4px;
}
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) {
  --bg: #0b1016; --surface: #121a24; --ink: #e8edf3; --ink-2: #a2b0bf; --ink-3: #7d8b9b; --rule: #233041;
  --accent: #8fa9ff; --accent-soft: #1b2645; --plate: #fcfcfb;
  --pass: #7fd6a2; --pass-bg: #14301f; --fail: #ff9b7b; --fail-bg: #3a1e16; --warn: #e9c46a; --warn-bg: #33290f;
  --s1: #6f8cf0; --s2: #e0683a; --grid: #1f2a38; color-scheme: dark; } }
:root[data-theme="dark"] {
  --bg: #0b1016; --surface: #121a24; --ink: #e8edf3; --ink-2: #a2b0bf; --ink-3: #7d8b9b; --rule: #233041;
  --accent: #8fa9ff; --accent-soft: #1b2645; --plate: #fcfcfb;
  --pass: #7fd6a2; --pass-bg: #14301f; --fail: #ff9b7b; --fail-bg: #3a1e16; --warn: #e9c46a; --warn-bg: #33290f;
  --s1: #6f8cf0; --s2: #e0683a; --grid: #1f2a38; color-scheme: dark; }
* { box-sizing: border-box; }
body { background: var(--bg); color: var(--ink); font: 17px/1.55 var(--font-body); margin: 0; }
.bar { background: var(--surface); border-bottom: 1px solid var(--rule);
  padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px)); }
.bar-in { max-width: 1040px; margin: 0 auto; display: flex; flex-wrap: wrap; gap: 6px 22px; align-items: baseline; padding-block: 12px; }
.brand { font: 700 15px/1 var(--font-display); letter-spacing: .02em; color: var(--ink); text-decoration: none; }
.bar nav { display: flex; flex-wrap: wrap; gap: 4px 18px; }
.bar nav a { color: var(--ink-2); text-decoration: none; font-size: 15px; }
.bar nav a[aria-current="page"] { color: var(--accent); font-weight: 600; }
main { max-width: 1040px; margin: 0 auto; padding-block: 28px 64px;
  padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px)); }
.col { max-width: 72ch; }
h1 { font: 760 clamp(30px, 5vw, 44px)/1.08 var(--font-display); font-stretch: 88%; margin: 6px 0 14px; text-wrap: balance; }
h2 { font: 700 25px/1.2 var(--font-display); font-stretch: 92%; margin: 46px 0 10px; text-wrap: balance;
  padding-top: 18px; border-top: 1px solid var(--rule); }
h3 { font: 650 19px/1.3 var(--font-display); margin: 28px 0 8px; text-wrap: balance; }
.eyebrow { font: 600 12px/1 var(--font-data); letter-spacing: .09em; text-transform: uppercase; color: var(--ink-3); }
.lede { font-size: 20px; color: var(--ink-2); }
p, li { max-width: 72ch; }
a { color: var(--accent); }
code, .mono { font-family: var(--font-data); font-size: .86em; }
.muted { color: var(--ink-3); }
.facts { display: grid; grid-template-columns: repeat(auto-fit, minmax(210px, 1fr)); gap: 12px; margin: 22px 0; }
.fact { background: var(--surface); border: 1px solid var(--rule); border-radius: var(--radius); padding: 14px 16px; min-width: 0; }
.fact .k { font: 600 12px/1.2 var(--font-data); letter-spacing: .06em; text-transform: uppercase; color: var(--ink-3); }
.fact .v { font: 700 24px/1.25 var(--font-display); margin-top: 6px; }
.fact .n { font-size: 14px; color: var(--ink-2); margin-top: 4px; }
.sealed { border-left: 3px solid var(--warn); }
.tablewrap { overflow-x: auto; margin: 12px 0 18px; border: 1px solid var(--rule); border-radius: var(--radius); background: var(--surface); }
table { border-collapse: collapse; width: 100%; font-size: 15px; }
th, td { text-align: left; padding: 8px 12px; border-bottom: 1px solid var(--rule); vertical-align: top; }
th { font: 600 12px/1.3 var(--font-data); letter-spacing: .05em; text-transform: uppercase; color: var(--ink-3); background: var(--surface); }
tr:last-child td { border-bottom: 0; }
td.num, table.num td:not(:first-child) { font-family: var(--font-data); font-size: 14px; font-variant-numeric: tabular-nums; white-space: nowrap; }
.pill { display: inline-block; font: 600 12px/1 var(--font-data); padding: 4px 7px; border-radius: 3px; white-space: nowrap; }
.pill.pass { color: var(--pass); background: var(--pass-bg); }
.pill.fail { color: var(--fail); background: var(--fail-bg); }
.pill.warn { color: var(--warn); background: var(--warn-bg); }
figure { margin: 18px 0 26px; }
img.plate { display: block; width: 100%; max-width: 100%; background: var(--plate); border: 1px solid var(--rule); border-radius: var(--radius); }
figcaption { font-size: 14px; color: var(--ink-2); margin-top: 8px; max-width: 80ch; }
details { background: var(--surface); border: 1px solid var(--rule); border-radius: var(--radius); margin: 12px 0; }
summary { cursor: pointer; padding: 10px 14px; font-weight: 600; }
summary:focus-visible, a:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
details pre { margin: 0; padding: 4px 16px 16px; overflow-x: auto; font: 13px/1.5 var(--font-data); white-space: pre-wrap; color: var(--ink-2); }
.callout { background: var(--accent-soft); border-radius: var(--radius); padding: 14px 18px; margin: 18px 0; max-width: 80ch; }
.callout p { margin: 6px 0; }
.chart { background: var(--surface); border: 1px solid var(--rule); border-radius: var(--radius); padding: 14px 14px 8px; overflow-x: auto; position: relative; }
.chart svg { display: block; width: 100%; min-width: 520px; height: auto; }
.chart text { fill: var(--ink-2); font: 12px var(--font-data); }
.chart .t-ink { fill: var(--ink); }
.chart .grid { stroke: var(--grid); stroke-width: 1; }
.chart .axis { stroke: var(--rule); stroke-width: 1; }
.legend { display: flex; flex-wrap: wrap; gap: 6px 18px; font-size: 14px; color: var(--ink-2); margin: 0 0 6px; }
.legend i { display: inline-block; width: 18px; height: 3px; border-radius: 2px; vertical-align: middle; margin-right: 6px; }
.tip { position: absolute; pointer-events: none; background: var(--ink); color: var(--surface); font: 12px/1.35 var(--font-data);
  padding: 6px 8px; border-radius: 3px; max-width: 280px; }
.dot { cursor: default; }
.dot:hover, .dot:focus { stroke-width: 4; outline: none; }
ol.timeline { list-style: none; padding: 0; margin: 12px 0; display: grid; gap: 10px; }
ol.timeline li { display: grid; grid-template-columns: 7.5em 1fr; gap: 12px; max-width: 90ch; }
ol.timeline time { font: 13px/1.6 var(--font-data); color: var(--ink-3); }
@media (max-width: 560px) { ol.timeline li { grid-template-columns: 1fr; gap: 0; } body { font-size: 16px; } }
@media (prefers-reduced-motion: reduce) { * { transition: none !important; } }
"""

TIP_JS = """
<script>
document.querySelectorAll('.chart').forEach(function (box) {
  var tip = document.createElement('div'); tip.className = 'tip'; tip.hidden = true; box.appendChild(tip);
  function show(e) { var d = e.target.closest('.dot'); if (!d) return; tip.textContent = d.getAttribute('data-tip');
    tip.hidden = false; var b = box.getBoundingClientRect(), r = d.getBoundingClientRect();
    var x = r.left - b.left + box.scrollLeft + 12, y = r.top - b.top - 8;
    tip.style.left = Math.min(x, box.scrollWidth - 290) + 'px'; tip.style.top = Math.max(0, y) + 'px'; }
  box.addEventListener('mouseover', show); box.addEventListener('focusin', show);
  box.addEventListener('mouseout', function () { tip.hidden = true; }); box.addEventListener('focusout', function () { tip.hidden = true; });
});
</script>
"""

PAGES = [("index.html", "Overview"), ("geometry.html", "Design inputs"), ("open-circuit.html", "Open circuit")]


def page(fname, title, body, description, full=True):
    nav = "".join(f'<a href="{f}"{" aria-current=\"page\"" if f == fname else ""}>{E(t)}</a>' for f, t in PAGES)
    doc = f"""<title>{E(title)}</title>
<meta name="claude:viewport-fit-sides" content="cover">
<meta name="description" content="{E(description)}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wdth,wght@62..125,400..800&family=JetBrains+Mono:wght@400;500;600&family=Source+Sans+3:ital,wght@0,400;0,600;1,400&display=swap">
<style>{CSS}</style>
<header class="bar"><div class="bar-in"><a class="brand" href="index.html">Prius motor study</a><nav>{nav}</nav></div></header>
<main>
{body}
</main>
{TIP_JS}
"""
    if not full:  # the artifact host wraps the main page in its own document skeleton
        return doc
    head, rest = doc.split("<header", 1)
    return ('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
            f'{head}</head>\n<body>\n<header{rest}</body>\n</html>\n')


# --------------------------------------------------------------------------- charts (inline SVG, theme tokens)

def line_chart(series, *, xlabel, ylabel, xticks, xpos, ylim, yticks, width=760, height=330, extra=""):
    """series: [{name, color_var, points: [(xval, y, tip)], label}]; xpos maps an x value to 0..1."""
    L, R, T, B = 64, 150, 16, 46
    W, H = width - L - R, height - T - B
    y0, y1 = ylim
    X = lambda v: L + xpos(v) * W  # noqa: E731
    Y = lambda v: T + (1 - (v - y0) / (y1 - y0)) * H  # noqa: E731
    g = []
    for t in yticks:
        g.append(f'<line class="grid" x1="{L}" x2="{L + W}" y1="{Y(t):.1f}" y2="{Y(t):.1f}"/>'
                 f'<text x="{L - 8}" y="{Y(t) + 4:.1f}" text-anchor="end">{t:g}</text>')
    for v, lab in xticks:
        g.append(f'<text x="{X(v):.1f}" y="{T + H + 20}" text-anchor="middle">{E(lab)}</text>')
    g.append(f'<line class="axis" x1="{L}" x2="{L + W}" y1="{T + H}" y2="{T + H}"/>')
    g.append(f'<text x="{L + W / 2:.1f}" y="{height - 6}" text-anchor="middle">{E(xlabel)}</text>')
    g.append(f'<text transform="translate(14 {T + H / 2:.1f}) rotate(-90)" text-anchor="middle">{E(ylabel)}</text>')
    for s in series:
        pts = s["points"]
        if len(pts) > 1:
            d = " ".join(f"{X(x):.1f},{Y(y):.1f}" for x, y, _ in pts)
            g.append(f'<polyline points="{d}" fill="none" stroke="var({s["color_var"]})" stroke-width="2" '
                     f'stroke-linejoin="round" stroke-linecap="round"/>')
        for x, y, tip in pts:
            fill = f"var({s['color_var']})" if not s.get("hollow") else "var(--surface)"
            g.append(f'<circle class="dot" tabindex="0" cx="{X(x):.1f}" cy="{Y(y):.1f}" r="5" fill="{fill}" '
                     f'stroke="{"var(--surface)" if not s.get("hollow") else "var(" + s["color_var"] + ")"}" '
                     f'stroke-width="2" data-tip="{E(tip)}"><title>{E(tip)}</title></circle>')
        if s.get("label") and pts:
            x, y, _ = pts[-1]
            g.append(f'<text class="t-ink" x="{X(x) + 12:.1f}" y="{Y(y) + 4 + s.get("label_dy", 0):.1f}">{E(s["label"])}</text>')
    g.append(extra)
    legend = "".join(f'<span><i style="background:var({s["color_var"]})"></i>{E(s["name"])}</span>' for s in series
                     if s.get("legend", True))
    return (f'<div class="chart"><div class="legend">{legend}</div><svg viewBox="0 0 {width} {height}" role="img" '
            f'aria-label="{E(ylabel)} against {E(xlabel)}">{"".join(g)}</svg></div>')


# --------------------------------------------------------------------------- shared numbers

def finest(run):
    pts = [p for p in run["points"] if p.get("status") == "completed"]
    return max(pts, key=lambda p: float(p["parameters"]["mesh_fineness"])) if pts else None


def run_checks(run):
    v = run.get("verification") or {}
    return v.get("run_checks", []), v.get("run_check_detail", {})


def point_pass(pt):
    return sum(c["status"] == "PASS" for c in pt["checks"]), len(pt["checks"])


# --------------------------------------------------------------------------- page: overview

def build_index(cases, runs, full=True):
    r0, r1, r2 = (runs[c] for c in CASES)
    f0, f1, f2 = (finest(r) if r else None for r in (r0, r1, r2))
    emf = lambda p: p["metrics"]["back_emf_LL_rms_per_krpm_V"] if p else None  # noqa: E731
    ornl_done = r2 is not None and r2["complete"]

    ledger = [
        ("19:14", "Smoke solve, Pyleecan machine", 107.253, "case motor_prius_oc_mesh, smoke test (fineness 1)"),
        ("19:45", "First mesh study, finest mesh", emf(f0), f"run {r0['id']} (fineness 4)" if r0 else ""),
        ("19:49", "Mesh study revision 1, finest mesh", emf(f1), f"run {r1['id']} (fineness 8), GCI 0.01 %" if r1 else ""),
        ("21:45", "ORNL Fig. 21 radii only (air gap 0.775 mm)", 106.591, "scratch run, fineness 4 (BACKLOG)"),
    ]
    if f2:
        ledger.append(("21:50", "Our machine: ORNL radii and slot", emf(f2),
                       f"run {r2['id']} (fineness {f2['parameters']['mesh_fineness']:g})"
                       + ("" if ornl_done else ", run still going")))
    ys = [v for _, _, v, _ in ledger if v]
    lo, hi = math.floor(min(ys) - 0.6), math.ceil(max(ys) + 0.6)
    n = len(ledger)
    pts = [(i, v, f"{t}  {lab}: {v:.2f} V ({src})") for i, (t, lab, v, src) in enumerate(ledger) if v]
    chart = line_chart(
        [{"name": "Blind back-EMF prediction", "color_var": "--s1", "points": pts, "legend": False,
          "label": f"{pts[-1][1]:.1f} V"}],
        xlabel="revision of the prediction (time on 2026-11-21)", ylabel="V rms line-to-line per 1000 rpm",
        xticks=[(i, t) for i, (t, *_rest) in enumerate(ledger)], xpos=lambda i: (i + 0.3) / (n - 0.4),
        ylim=(lo, hi), yticks=[v for v in range(lo, hi + 1)], height=300)
    ledger_rows = [[f'<span class="mono">{t}</span>', E(lab), f'<span class="mono">{v:.3f} V</span>' if v else "–",
                    f'<span class="muted">{E(src)}</span>'] for t, lab, v, src in ledger]

    current = emf(f2) if ornl_done else emf(f1)
    status_rows = [
        ["Design inputs: stator, rotor, slot", "ORNL/TM-2005/33 Fig. 21, read from the PDF's vector text and outline",
         pill("PASS") + " rebuilt and compared", '<a href="geometry.html">Design inputs</a>'],
        ["Design inputs: magnet pockets, materials", "Still Pyleecan's: no dimensioned source in hand", pill("OPEN"), ""],
        ["Electromagnetics, open circuit", "FEMM via Pyleecan; phase symmetry, winding theory, zero cogging mean, mesh GCI",
         pill("PASS") + " verified", '<a href="open-circuit.html">Open circuit</a>'],
        ["Electromagnetics, torque against current", "FEMM via Pyleecan, dq current sweep, power balance", pill("NOT STARTED"), ""],
        ["Efficiency map", "Copper and iron losses on the torque-speed plane", pill("NOT STARTED"), ""],
        ["Rotor bridge stress at overspeed", "CalculiX, plane stress, centrifugal load", pill("NOT STARTED"), ""],
        ["Thermal network", "Lumped network checked against CalculiX on a stator section", pill("NOT STARTED"), ""],
        ["Blind comparison with ORNL test data", "Opened only after every prediction above is written down", pill("SEALED"), ""],
    ]

    body = f"""
<div class="col">
<div class="eyebrow">Study 7 · electric machine · 2004 Toyota Prius traction motor</div>
<h1>Prius motor study</h1>
<p class="lede">Can an open-source toolchain (Pyleecan and FEMM for the electromagnetics, CalculiX for the rotor, later
a thermal network) predict a production traction motor well enough for early design screening? The test case is the
2004 Prius motor, which Oak Ridge National Laboratory (ORNL) took apart and measured.</p>
</div>

<div class="facts">
  <div class="fact"><div class="k">Machine</div><div class="v">48 slots · 8 poles</div><div class="n">Interior V magnets, 83.8 mm stack, 50 kW, 400 N m to base speed</div></div>
  <div class="fact"><div class="k">Back-EMF, current prediction</div><div class="v">{fmt(current, 4)} V</div><div class="n">rms line-to-line per 1000 rpm at 20 °C{"" if ornl_done else " (our rebuilt machine's run is still going)"}</div></div>
  <div class="fact"><div class="k">REQ-M1, uncontrolled generator</div><div class="v">{pill("FAIL")} ≈ {fmt(f2["metrics"]["back_emf_LL_peak_at_max_speed_V"] if f2 else f1["metrics"]["back_emf_LL_peak_at_max_speed_V"], 4)} V</div><div class="n">Line-to-line peak at 6000 rpm against the 500 V bus</div></div>
  <div class="fact sealed"><div class="k">ORNL performance data</div><div class="v">Sealed</div><div class="n">No test value has been opened. Only design drawings and text have been read.</div></div>
</div>

<h2>The question and the limits</h2>
<div class="col">
<p>Two kinds of answer come out of this study, and they are kept apart.</p>
<ul>
<li><b>Design checks</b> come from our own models with internal verification only: does the rated peak torque fit
inside the current limit, does the rotor bridge stay under the lamination's yield at overspeed, and does the open-circuit
voltage at top speed stay under the bus voltage (REQ-M1).</li>
<li><b>Validation</b> compares our predictions with ORNL's measurements, once, at the end. The limits were agreed
before any data was seen:</li>
</ul>
</div>
{table(["Quantity", "Agreed limit", "Status"], [
        ["Back-EMF constant", "within 5 %", pill("SEALED") + " prediction written"],
        ["Peak torque at several currents", "within 10 %", pill("SEALED") + " not yet predicted"],
        ["Efficiency at sample points", "within 2 percentage points", pill("SEALED") + " not yet predicted"],
    ])}
<div class="col">
<p>The limits may change only before the ORNL data is opened, and only with a written reason. After that, any change is
a documented revision that keeps the earlier verdict. Otherwise the comparison would say nothing.</p>
</div>

<h2>How the blind prediction has moved</h2>
<div class="col"><p>Every change below came from the model or its design inputs (mesh, then the dimensions from ORNL's
drawing), never from test data. Each one was written into the case file before the run that tested it.</p></div>
{chart}
{table(["Time", "What changed", "Back-EMF", "Evidence"], ledger_rows)}

<h2>Work breakdown</h2>
{table(["Piece", "Method and checks", "Status", "Report"], status_rows)}

<h2>Toolchain</h2>
<div class="col">
<ul>
<li><b>Pyleecan</b> (GitHub master 1e940df, in its own Python 3.14 environment) builds the machine and drives FEMM.
SciDataTool comes from GitHub master too, because the PyPI release still calls <code>numpy.string_</code>.</li>
<li><b>FEMM 4.2</b> (x64, 22 Oct 2023 build) solves 2D magnetostatics. Checked first on a 100 A wire, where
B = μ<sub>0</sub>I / (2πr) holds exactly: 0.1-0.5 % on FEMM's default mesh.</li>
<li><b>The harness</b> (this repository) runs each case, checks every point, runs the mesh study, and keeps the
inputs, hashes and tool versions with every run.</li>
</ul>
</div>

<h2>Timeline, 2026-11-21</h2>
<ol class="timeline">
<li><time>afternoon</time><span>Feasibility: Pyleecan master installs on Python 3.14; FEMM 4.2 installed and scriptable; the wire check passes.</span></li>
<li><time>evening</time><span>Framing and validation limits agreed. Design inputs spot-checked against ORNL's 2004 design report (stack 3.3 in exactly; series winding; ratings).</span></li>
<li><time>19:14</time><span>First FEMM solve through Pyleecan. Blind prediction about 107 V per 1000 rpm.</span></li>
<li><time>19:45</time><span>Open-circuit mesh study: REQ-M1 verified fail (1028 V), but the flux linkage converged at order 0.19.</span></li>
<li><time>19:49</time><span>Revision 1 drops the coarsest mesh: order 1.95, GCI 0.01 %, prediction 107.0 V.</span></li>
<li><time>20:15</time><span>ORNL/TM-2005/33 Fig. 21 found: a dimensioned stator and rotor drawing.</span></li>
<li><time>21:45</time><span>The drawing's radii widen the air gap from 0.750 to 0.775 mm: back-EMF −0.41 %.</span></li>
<li><time>21:49</time><span>The drawing's slot is much narrower than Pyleecan's (145 against 218 mm²). Our machine definition is committed with its sources.</span></li>
<li><time>21:50</time><span>Open-circuit mesh study on our machine{" verified: back-EMF 108.0 V per 1000 rpm (+1.4 %), REQ-M1 fail at 1004 V. Our machine becomes the design input." if ornl_done else " started."}</span></li>
</ol>

<p class="muted">Generated from the case files and runs by <code>reports/motor/build_report.py</code>.</p>
"""
    return page("index.html", "Prius Motor Study", body, "Study 7 overview: question, blind protocol, status and predictions.",
                full)


# --------------------------------------------------------------------------- page: design inputs

def build_geometry():
    ours = machine_json(REPO / "models/motor/Toyota_Prius_ORNL.json")
    pyl_path = pyleecan_machine_path()
    pyl = machine_json(pyl_path) if pyl_path.exists() else None
    rows = []
    for path, attr, inches, note in CHANGES:
        key = f"{path}.{attr}"
        new = dig(ours, key) * 1e3
        old = dig(pyl, key) * 1e3 if pyl else None
        diff = "" if not old else f"{100 * (new - old) / old:+.1f} %"
        flag = abs(new - old) / old > 0.01 if old else False
        rows.append([f'<code>{E(key)}</code>', f"{inches:.4g} in", f"{new:.3f}", f"{old:.3f}" if old is not None else "–",
                     f"<b>{diff}</b>" if flag else diff, E(note)])
    gap_o = (ours["stator"]["Rint"] - ours["rotor"]["Rext"]) * 1e3
    gap_p = (pyl["stator"]["Rint"] - pyl["rotor"]["Rext"]) * 1e3 if pyl else None

    mapping = [
        ["W0", "slot opening at the bore", "0.076 in", "Labelled directly."],
        ["H0", "tooth-tip height", "0.040 in", "Labelled directly."],
        ["H1", "height of a sloped shoulder (wedge)", "0", "The inset shows a flat step from the opening to the slot body."],
        ["W1", "slot width just above the tooth tip", "0.124 in",
         "The inset's arrows sit about 0.3 in up a tapered slot, so the label alone is ambiguous. The main view's outline "
         "gives 0.1246 in just above the shoulder, which is where W1 is defined."],
        ["W2", "width where the round end starts", "0.222 in", "The round end is taken as a full semicircle, so W2 is its diameter."],
        ["R1", "radius of the round end", "0.111 in", "Follows from the same assumption: W2 / 2."],
        ["H2", "depth of the slot body", "1.280 in",
         "1.320 in spans the bore to the end of the round (the main view confirms: slot end 1.32 in outside the bore). "
         "Pyleecan's depth is H0 + H1 + H2, so H2 = 1.320 − 0.040."],
    ]
    outline = [
        ["3.19", "0.0760", "0.344", "opening (labelled 0.076 in)"],
        ["3.25", "0.1246", "0.300", "just above the shoulder (labelled 0.124 in; tooth labelled 0.300 in)"],
        ["3.50", "0.1459", "0.312", "slot body, widening linearly"],
        ["3.80", "0.1714", "0.326", ""],
        ["4.00", "0.1884", "0.335", ""],
        ["4.35", "0.2182", "0.351", "near the start of the round end (labelled ø0.222 in)"],
        ["4.52", "0.0184", "–", "the round end closes: slot end at about 4.51 in, so depth 1.32 in"],
    ]

    body = f"""
<div class="col">
<div class="eyebrow">Study 7 · design inputs</div>
<h1>Building the machine from published dimensions</h1>
<p class="lede">The model started from Pyleecan's bundled <code>Toyota_Prius.json</code>. To make the inputs ours,
we rebuilt the stator, rotor and slot from ORNL's published drawing and compared them with Pyleecan's file dimension by
dimension. Where they disagree, the published source wins and the difference is recorded.</p>
</div>

<div class="facts">
  <div class="fact"><div class="k">Radii</div><div class="v">within 0.012 mm</div><div class="n">Stator OD and bore, rotor OD and ID agree with Pyleecan's file</div></div>
  <div class="fact"><div class="k">Air gap</div><div class="v">{gap_o:.3f} mm</div><div class="n">Pyleecan's file: {fmt(gap_p, 3)} mm (3 % narrower)</div></div>
  <div class="fact"><div class="k">Slot area</div><div class="v">145 mm²</div><div class="n">Pyleecan's file: 218 mm². Its slot is 50 % larger than the drawing's.</div></div>
  <div class="fact"><div class="k">Tooth at the bore</div><div class="v">7.4 mm</div><div class="n">Pyleecan's file: 5.6 mm</div></div>
</div>

<h2>Sources</h2>
{table(["Document", "What was used", "What was not opened"], [
        [f'<a href="{ORNL_THERMAL}">ORNL/TM-2005/33</a>, <i>Report on Toyota Prius Motor Thermal Management</i> (FY 2005)',
         "Fig. 21, a dimensioned stator and rotor schematic (report page 25, PDF page 32). Its text: 9 conductor bundles per slot.",
         "Pages 20-30 hold test data and stay closed."],
        [f'<a href="{ORNL_DESIGN}">ORNL/TM-2004/137</a>, Hsu, Ayers, Coomer (July 2004), design report',
         "Stack 3.3 in (83.82 mm, an exact match), series winding on the 2004 model, 200-500 V boosted bus, 50 kW and 400 N m to base speed, 0.014 in laminations, slot fill 0.84.",
         "No performance data was read."],
        ["ORNL/TM-2006/423 and ORNL/TM-2004/247 rev. (test reports)", "Only filtered searches for design terms, which found no dimensions in their text.",
         "All of their measured performance: this is the blind validation data."],
        ["Pyleecan <code>Toyota_Prius.json</code> (master 1e940df)", "Starting point; magnets, materials and winding kept.", ""],
    ])}

<h2>Dimension by dimension</h2>
<div class="col"><p>Each row is applied by <code>models/motor/build_prius_ornl.py</code>, which writes
<code>models/motor/Toyota_Prius_ORNL.json</code>. The harness copies that file into each run's inputs and records its
SHA-256. Bold differences exceed 1 %.</p></div>
{table(["Parameter", "Drawing", "Ours (mm)", "Pyleecan (mm)", "Difference", "How the drawing gives it"], rows, "num")}

<h2>How the drawing was read</h2>
<div class="col">
<p>Fig. 21's labels are vector text, so <code>page.get_text()</code> (PyMuPDF) gives them exactly. The slot inset gives
the depth, the opening, the tooth tip, one slot width and the round end. Because the inset's arrows are placed loosely
on a tapered slot, the main view's vector outline was measured too:</p>
<ol>
<li>Collect the line segments of the stator outline.</li>
<li>Fit a circle to the tooth faces and scale it to the labelled 6.375 in bore.</li>
<li>Intersect the outline with circles of increasing radius. The gaps between crossings are slot and tooth widths.</li>
</ol>
</div>
{table(["Radius (in)", "Slot width (in)", "Tooth width (in)", "Reading"], outline, "num")}
<div class="col"><p>The inset and the main view agree, including the drawing's own 0.300 in tooth label. The drawing is
self-consistent, so it replaces Pyleecan's slot.</p></div>

<h2>From the drawing to Pyleecan's slot parameters</h2>
<div class="col"><p>Pyleecan describes this slot as a <code>SlotW11</code>: a tapered slot with a round end, set by seven
numbers. The drawing was read to fill exactly those seven; anything the slot type cannot represent was left out.</p></div>
{table(["Parameter", "Meaning", "Value", "Judgement"], mapping)}

<figure>
{img64(REPO / "portfolio/img/motor_slot_vs_ornl_fig21.png", "Slot outline overlay: ORNL drawing, our machine and Pyleecan's file")}
<figcaption>Our slot (blue) drawn by Pyleecan from the seven parameters, over the drawing's vector outline (black) and
Pyleecan's original slot (orange, dashed). Our slot follows the drawing along both sides and the round end. The drawing
sits about 0.015 in (about 0.3 pt on the page) radially outside both, equally at the tooth face and the slot end: that
is the circle fit's error, not a shape difference, so the absolute depth comes from the labelled 1.320 in. The small
notches at the shoulder (probably for slot wedges) cannot be represented by SlotW11 and are left out.</figcaption>
</figure>

<h2>Why the slot matters</h2>
<div class="col">
<p>The verified open-circuit run on Pyleecan's machine gives an air-gap field fundamental of 0.893 T. Spread over a
tooth at the bore, that is about 1.70 T in Pyleecan's 5.55 mm tooth, past the knee of the M400-50A steel, and about
1.27 T in the drawing's 7.40 mm tooth. Under load the difference grows, so it matters more for torque than for
back-EMF.</p>
</div>

<h2>Still Pyleecan's</h2>
<div class="col">
<ul>
<li><b>Magnet pockets</b> (HoleM50). Fig. 21 draws them but gives no dimensions, apart from two red labels, 0.060 in and
0.056 in, that look like the bridges beside the magnets. Pyleecan's bridge is 1.5 mm (0.059 in), close, but what the
labels measure is not certain.</li>
<li><b>Magnet material</b>: generic NdFeB, Br 1.24 T at 20 °C, recoil permeability 1.05.</li>
<li><b>Lamination material</b>: M400-50A, a 0.5 mm grade. The real laminations are 0.36 mm (0.014 in), which matters for
iron loss and efficiency more than for the field.</li>
<li><b>Winding</b>: 9 turns per coil, one parallel path, consistent with the 9 conductor bundles per slot in ORNL's text.</li>
</ul>
</div>
<p class="muted">Generated by <code>reports/motor/build_report.py</code>.</p>
"""
    return page("geometry.html", "Prius Design Inputs", body, "Study 7: the Prius machine rebuilt from ORNL's drawing.")


# --------------------------------------------------------------------------- page: open circuit

RUN_NOTES = {
    "motor_prius_oc_mesh": "Pyleecan's machine, mesh fineness 1 / 2 / 4. REQ-M1 verified fail. The flux linkage converged "
                           "at an order of only 0.19, too low to trust its extrapolation.",
    "motor_prius_oc_mesh_r1": "Same machine, fineness 2 / 4 / 8: dropping the coarsest mesh (bridges under one element) "
                              "recovered order 1.95 and a GCI of 0.01 %. REQ-M1 is withheld on this run only because the "
                              "peak's tiny mesh-to-mesh noise defeats the GCI; the earlier run verified it.",
    "motor_prius_ornl_oc_mesh": "Our machine rebuilt from ORNL Fig. 21 (air gap 0.775 mm, the drawing's slot), fineness "
                                "2 / 4 / 8. The back-EMF rose 1.4 % against the radii-only machine, less than the 2-6 % "
                                "predicted, while the peak at 6000 rpm fell 2.3 % because the narrower slots cut the "
                                "harmonics. REQ-M1 is verified fail on this run. This machine is now the design input, and "
                                "108.0 V per 1000 rpm is the blind prediction.",
}


def run_section(case, run):
    name = case["name"]
    t = case["toml"]
    head = f'<h3 id="{name}">{E(name)}</h3><p>{E(RUN_NOTES.get(name, t["case"]["description"]))}</p>'
    if run is None:
        return head + '<p class="muted">No run yet.</p>'
    rows = []
    for pt in run["points"]:
        m, so = pt.get("metrics", {}), pt.get("solver_outputs", {})
        ok, n = point_pass(pt)
        rows.append([f'{float(pt["parameters"]["mesh_fineness"]):g}', fmt(m.get("lambda1_Wb"), 6),
                     fmt(m.get("back_emf_LL_rms_per_krpm_V"), 6), fmt(m.get("back_emf_LL_peak_at_max_speed_V"), 5),
                     fmt(m.get("mean_torque_Nm"), 3), fmt(m.get("torque_ripple_pp_Nm"), 3),
                     f'{so.get("wall_s", 0):.0f} s', pill(f"{ok}/{n} PASS") if n and ok == n else pill(f"{ok}/{n}")])
    pts_table = table(["Mesh fineness", "λ₁ (Wb)", "Back-EMF (V/krpm)", "Peak at 6000 rpm (V)", "Mean torque (N m)",
                       "Cogging p-p (N m)", "Solve", "Checks"], rows, "num")
    rc, detail = run_checks(run)
    rc_rows = [[f'<code>{E(c["id"])}</code>', E(c["description"]), fmt(c["value"], 3), fmt(c["tolerance"], 3),
                pill(c["status"])] for c in rc]
    rc_table = table(["Run-level check", "Description", "Value", "Limit", "Status"], rc_rows) if rc_rows else \
        '<p class="muted">Run-level checks appear when the run finishes.</p>'
    req = ""
    if run["report"]:
        verdicts = {pt["label"]: pt["requirements"][0]["verdict"] for pt in run["report"]["points"] if pt.get("requirements")}
        req = "<p>REQ-M1 verdicts: " + ", ".join(f'{E(k.split("_", 1)[1])} {pill(v)}' for k, v in verdicts.items()) + "</p>"
    f = finest(run)
    figs = ""
    if (run["dir"] / "sweep.png").exists():
        figs += f'<figure>{img64(run["dir"] / "sweep.png", "Requirement metric across the mesh sweep")}<figcaption>REQ-M1 metric across the mesh sweep (harness figure).</figcaption></figure>'
    if f is not None:
        figs += (f'<figure>{img64(f["dir"] / "response.png", "Flux linkage and air-gap field")}<figcaption>Finest mesh: '
                 "the three phase flux linkages over one electrical period with the winding-theory fundamental (dashed), "
                 "and the radial air-gap flux density at t = 0.</figcaption></figure>")
    man = run.get("manifest") or {}
    env = man.get("environment", {})
    git = env.get("git", {})
    prov = (f'<p class="muted mono">run {E(run["id"])} · case sha256 {E(str(man.get("case_sha256", ""))[:12])} · '
            f'git {E(str(git.get("commit", ""))[:7])}{" (uncommitted changes)" if git.get("dirty") else ""} · '
            f'{E(", ".join(f"{k} {v}" for k, v in env.get("tools", {}).items()))}</p>') if man else \
        f'<p class="muted mono">run {E(run["id"])} (still running)</p>'
    record = f'<details><summary>Case record: predictions before the run, results after</summary><pre>{E(case["header"])}</pre></details>'
    return head + pts_table + rc_table + req + figs + record + prov


def build_open_circuit(cases, runs):
    def series(run_names, var, label, dy=0):
        pts = {}
        for rn in run_names:
            r = runs[rn]
            if not r:
                continue
            for pt in r["points"]:
                if pt.get("status") == "completed":
                    k = float(pt["parameters"]["mesh_fineness"])
                    v = pt["metrics"]["back_emf_LL_rms_per_krpm_V"]
                    pts[k] = (k, v, f"fineness {k:g}: {v:.3f} V ({r['id']})")
        return {"name": label, "color_var": var, "points": [pts[k] for k in sorted(pts)], "label": label.split(" (")[0],
                "label_dy": dy}

    s_pyl = series(["motor_prius_oc_mesh", "motor_prius_oc_mesh_r1"], "--s1", "Pyleecan's machine (2 runs)", -2)
    s_orn = series(["motor_prius_ornl_oc_mesh"], "--s2", "Our machine (ORNL Fig. 21)", 4)
    scratch = {"name": "ORNL radii only, Pyleecan's slot (scratch)", "color_var": "--ink-3", "hollow": True,
               "points": [(4.0, 106.591, "fineness 4: 106.591 V (scratch run, BACKLOG 21:45)")], "label": "radii only"}
    ys = [y for s in (s_pyl, s_orn, scratch) for _, y, _ in s["points"]]
    lo, hi = math.floor(min(ys) - 0.4), math.ceil(max(ys) + 0.4)
    step = 0.5 if hi - lo <= 4 else 1
    yt = [lo + i * step for i in range(int((hi - lo) / step) + 1)]
    chart = line_chart([s_pyl, s_orn, scratch], xlabel="mesh fineness (Pyleecan Kmesh_fineness, log scale)",
                       ylabel="back-EMF, V rms LL per 1000 rpm",
                       xticks=[(1, "1"), (2, "2"), (4, "4"), (8, "8")], xpos=lambda v: (math.log2(v) + 0.25) / 3.5,
                       ylim=(lo, hi), yticks=yt)

    checks_rows = [
        ["Phase symmetry", "Spread of the three phases' fundamental flux linkage, over the mean", "≤ 1e-3",
         "A wrong winding or periodicity breaks the balance."],
        ["Phase shift", "Largest departure of the phase shifts from 120°", "≤ 0.5°", "Same, for the winding layout."],
        ["Winding theory", "Flux linkage from FEMM's air-gap field, 2 N k<sub>w1</sub> B<sub>1</sub> R L / p, against FEMM's integral over the coils",
         "≤ 2 %", "An independent second route to the same number. Model-form differences (mid-gap sampling, slot openings, leakage) keep it near 0.5 %."],
        ["Open-circuit torque", "Mean torque with no current, over the rated 400 N m", "≤ 1e-3", "No net torque can come from magnets alone."],
        ["Time resolution", "At least 48 steps per electrical period", "validity", "Settled in the prototype: 48 and 96 steps agree."],
        ["Mesh convergence (run level)", "GCI on the flux linkage and on the requirement metric, three meshes", "≤ 1 %",
         "A failed GCI withholds the requirement verdict on that run."],
    ]

    sections = "".join(run_section(c, runs[c["name"]]) for c in cases)
    r2 = runs["motor_prius_ornl_oc_mesh"]
    body = f"""
<div class="col">
<div class="eyebrow">Study 7 · electromagnetics · no current</div>
<h1>Open-circuit electromagnetics</h1>
<p class="lede">With no current in the windings, the magnets alone set the flux linkage. That gives the back-EMF
constant (the blind prediction for ORNL) and answers REQ-M1: if the inverter stops switching at top speed, does the
motor's own voltage stay under the 500 V bus?</p>
</div>

<div class="callout">
<p><b>REQ-M1 fails, about twice over.</b> The line-to-line back-EMF peak at 6000 rpm is about 1000-1030 V against the
500 V bus. That is expected for an interior-magnet design: above base speed the drive depends on field weakening, and a
fault at top speed needs protection. The flux-linkage harmonics add 9.5 % to the peak over the fundamental on our
machine, and 13 % on Pyleecan's, whose wider slots make the field less sinusoidal.</p>
</div>

<h2>Method</h2>
<div class="col">
<ul>
<li>2D magnetostatic FEMM solves through Pyleecan, at 1000 rpm over one electrical period in 48 steps, using the
machine's angular and time periodicity.</li>
<li>λ<sub>1</sub> is the mean fundamental amplitude of the three phase flux linkages. The back-EMF constant is
√3 ω<sub>e</sub> λ<sub>1</sub> / √2 at 1000 rpm, with 4 pole pairs.</li>
<li>The peak at 6000 rpm is the largest |e<sub>ab</sub>| from a spectral derivative of φ<sub>a</sub> − φ<sub>b</sub>,
harmonics included, scaled by the speed ratio.</li>
<li>Mesh fineness divides all of Pyleecan's FEMM mesh sizes (at fineness 1: air gap 0.25 mm, rotor iron 1.94 mm,
magnets 3.9 mm, teeth 4.3 mm, yoke 4.8 mm).</li>
</ul>
</div>

<h2>Checks on every point</h2>
{table(["Check", "What is compared", "Limit", "Why"], checks_rows)}

<h2>Back-EMF across the mesh studies</h2>
<div class="col"><p>Both machines change by under 0.05 % between fineness 4 and 8. The step between them is the
design-input correction: the wider air gap alone lowers the back-EMF 0.41 % (hollow marker), then the drawing's narrower
slot raises it 1.4 %, because the wider teeth saturate less.</p></div>
{chart}

<h2>Runs</h2>
{sections}

<p class="muted">Generated by <code>reports/motor/build_report.py</code>{"" if (r2 and r2["complete"]) else "; the last run was still going when this page was built"}.</p>
"""
    return page("open-circuit.html", "Prius Open Circuit", body, "Study 7: open-circuit electromagnetics of the Prius motor.")


def main():
    cases = [case_record(c) for c in CASES]
    runs = {c: load_run(c) for c in CASES}
    (OUT / "index.html").write_text(build_index(cases, runs), encoding="utf-8")
    if len(sys.argv) > 1:  # also write the artifact's main page (no document skeleton) to the given path
        Path(sys.argv[1]).write_text(build_index(cases, runs, full=False), encoding="utf-8")
    (OUT / "geometry.html").write_text(build_geometry(), encoding="utf-8")
    (OUT / "open-circuit.html").write_text(build_open_circuit(cases, runs), encoding="utf-8")
    for f, _ in PAGES:
        print(f"wrote {OUT / f} ({(OUT / f).stat().st_size / 1e3:.0f} kB)")


if __name__ == "__main__":
    main()
