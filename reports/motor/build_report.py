"""Study 7 (2004 Toyota Prius motor) HTML reports, kept apart from the main dashboard.

usage: .venv/Scripts/python.exe reports/motor/build_report.py [artifact-index-path]

Reads the motor cases (their header comments are the study's written record: predictions before each run, results
after), the runs they produced (report.json, verification.json, manifest.json, point.json, figures), and the two
machine definitions (Pyleecan's bundled Toyota_Prius.json and ours, models/motor/Toyota_Prius_ORNL.json). Writes
self-contained pages (figures embedded) to reports/motor/: index.html, geometry.html, open-circuit.html, torque.html.

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

from models.motor.build_prius_ornl import CHANGES, IN, MAGNET_CHANGES, ROTOR_CHANGES, SOURCE  # noqa: E402  (plain data; Pyleecan imported lazily)
from studies.motor_em import pyleecan_python  # noqa: E402

CASES = ["motor_prius_oc_mesh", "motor_prius_oc_mesh_r1", "motor_prius_ornl_oc_mesh", "motor_prius_ornl_oc_mesh_r1",
         "motor_prius_ornl_oc_mesh_r2", "motor_prius_ornl_oc_mesh_r3"]
TORQUE_CASES = ["motor_prius_torque_mesh", "motor_prius_torque_current", "motor_prius_torque_current_r1"]
#: the lamination bracket (user's decision 2026-11-22 ~00:40): the final machine on two other grades
BRACKET_OC = ["motor_prius_ornl_oc_m250", "motor_prius_ornl_oc_y390"]
BRACKET_TQ = ["motor_prius_torque_m250", "motor_prius_torque_y390"]
ORNL_THERMAL = "https://info.ornl.gov/sites/publications/Files/Pub57487.pdf"
ORNL_DESIGN = "https://info.ornl.gov/sites/publications/Files/Pub57348.pdf"
#: copper per slot after the 2026-11-22 correction: ORNL's 0.84 fill is on the squares of the insulated wires, so the
#: bare copper is Pyleecan's 13 strands of 0.912 mm per turn x 9 turns (76.4 mm^2), not 0.84 x 143.0 = 120.1 mm^2
COPPER_MM2_PER_SLOT, TURNS_PER_SLOT, J_LIMIT = 76.4, 9, 25.0
I_LIMIT = J_LIMIT * COPPER_MM2_PER_SLOT / TURNS_PER_SLOT  # 212 A rms
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
        d = d[int(k)] if k.isdigit() else d[k]
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
  --s1: #2346c4; --s2: #c9461a; --s3: #1a7f5a; --grid: #e3e8ee;
  --font-display: "Archivo", "Arial Narrow", system-ui, sans-serif;
  --font-body: "Source Sans 3", "Segoe UI", system-ui, -apple-system, sans-serif;
  --font-data: "JetBrains Mono", ui-monospace, "Cascadia Mono", Consolas, monospace;
  --radius: 4px;
}
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) {
  --bg: #0b1016; --surface: #121a24; --ink: #e8edf3; --ink-2: #a2b0bf; --ink-3: #7d8b9b; --rule: #233041;
  --accent: #8fa9ff; --accent-soft: #1b2645; --plate: #fcfcfb;
  --pass: #7fd6a2; --pass-bg: #14301f; --fail: #ff9b7b; --fail-bg: #3a1e16; --warn: #e9c46a; --warn-bg: #33290f;
  --s1: #6f8cf0; --s2: #e0683a; --s3: #45c08f; --grid: #1f2a38; color-scheme: dark; } }
:root[data-theme="dark"] {
  --bg: #0b1016; --surface: #121a24; --ink: #e8edf3; --ink-2: #a2b0bf; --ink-3: #7d8b9b; --rule: #233041;
  --accent: #8fa9ff; --accent-soft: #1b2645; --plate: #fcfcfb;
  --pass: #7fd6a2; --pass-bg: #14301f; --fail: #ff9b7b; --fail-bg: #3a1e16; --warn: #e9c46a; --warn-bg: #33290f;
  --s1: #6f8cf0; --s2: #e0683a; --s3: #45c08f; --grid: #1f2a38; color-scheme: dark; }
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

PAGES = [("index.html", "Overview"), ("geometry.html", "Design inputs"), ("open-circuit.html", "Open circuit"),
         ("torque.html", "Torque"), ("efficiency.html", "Efficiency")]


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
        if len(pts) > 1 and not s.get("dots_only"):
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


def bracket_table(runs):
    """One row per lamination grade: back-EMF, torque at 100 and 300 A, and the overspeed verdict by comparison."""
    def emf(rn):
        r = runs.get(rn)
        f = finest(r) if r and r["complete"] else None
        return f'{f["metrics"]["back_emf_LL_rms_per_krpm_V"]:.2f}' if f else "running" if r else "queued"

    def torque(rn, amps):
        r = runs.get(rn)
        if not r:
            return "queued"
        for pt in r["points"]:
            if pt.get("status") == "completed" and float(pt["parameters"]["current_rms_A"]) == amps:
                return f'{pt["metrics"]["torque_mtpa_Nm"]:.1f}'
        return "running"

    rows = [
        ["M400-50A (0.50 mm)", "Pyleecan's inherited curve, never chosen", emf("motor_prius_ornl_oc_mesh_r2"),
         torque("motor_prius_torque_current", 100.0), torque("motor_prius_torque_current", 300.0), "–", "–"],
        ["<b>M330-35A</b> (0.35 mm)", "<b>the stand-in: the blind prediction</b>", emf("motor_prius_ornl_oc_mesh_r3"),
         torque("motor_prius_torque_current_r1", 100.0), torque("motor_prius_torque_current_r1", 300.0),
         "335", pill("FAIL") + " run"],
        ["M250-35A (0.35 mm)", "lower-loss bracket", emf("motor_prius_ornl_oc_m250"),
         torque("motor_prius_torque_m250", 100.0), torque("motor_prius_torque_m250", 300.0),
         "455 typical", pill("PASS") + " by comparison, margin 7 %"],
        ["powercore 035-190Y390 (0.35 mm)", "high-strength bracket", emf("motor_prius_ornl_oc_y390"),
         torque("motor_prius_torque_y390", 100.0), torque("motor_prius_torque_y390", 300.0),
         "390 guaranteed, 407 typical", pill("FAIL") + " by comparison"],
    ]
    return table(["Laminations", "Role", "Back-EMF (V/krpm)", "Torque at 100 A (N m)", "Torque at 300 A (N m)",
                  "Yield (MPa)", "REQ-M4: 424 MPa at 7200 rpm"], rows)


BRACKET_TEXT = """<div class="col"><p>ORNL gives the lamination thickness (0.36 mm) but not the grade, so the final machine
was also run on two other 0.35 mm grades. The back-EMF moves by 0.13 % across the three and the torque by under 2 %,
far inside the agreed 5 % and 10 % limits: the unknown grade does not limit the blind comparison. Each grade's
predictions were written before its run; they are in the case records on the open-circuit and torque pages.</p>
<p>The overspeed stress (424 MPa in the bridge at 7200 rpm) is the same for every grade: it does not depend on the
modulus, and the densities differ by 0.7 %. So only the yield changes the verdict. M250-35A, the lower-loss grade, is
also the strongest of the three on typical values.</p></div>
"""


# --------------------------------------------------------------------------- page: overview

def build_index(cases, runs, full=True):
    r0, r1, r2, r3, r4, r5 = (runs[c] for c in CASES)
    f0, f1, f2, f3, f4, f5 = (finest(r) if r else None for r in (r0, r1, r2, r3, r4, r5))
    emf = lambda p: p["metrics"]["back_emf_LL_rms_per_krpm_V"] if p else None  # noqa: E731
    ornl_done = r2 is not None and r2["complete"]
    done = [(r, f) for r, f in ((r5, f5), (r4, f4), (r3, f3), (r2, f2), (r1, f1)) if r is not None and r["complete"] and f]
    latest_run, latest_pt = done[0]
    tm, tc = runs.get("motor_prius_torque_mesh"), runs.get("motor_prius_torque_current")
    tc1 = runs.get("motor_prius_torque_current_r1")
    so = runs.get("motor_prius_rotor_overspeed_mesh")

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
    for tstamp, lab, r, f in (("22:36", "Rotor and magnets sourced (pocket grown inward)", r3, f3),
                              ("01:37*", "Pocket placed as drawn (final machine; inherited M400-50A steel)", r4, f4),
                              ("01:47*", "Laminations M330-35A, the stand-in steel (final machine)", r5, f5)):
        if f:
            ledger.append((tstamp, lab, emf(f), f"run {r['id']} (fineness {f['parameters']['mesh_fineness']:g})"
                           + ("" if r["complete"] else ", run still going")))
    ys = [v for _, _, v, _ in ledger if v]
    lo, hi = math.floor(min(ys) - 0.6), math.ceil(max(ys) + 0.6)
    n = len(ledger)
    pts = [(i, v, f"{t}  {lab}: {v:.2f} V ({src})") for i, (t, lab, v, src) in enumerate(ledger) if v]
    chart = line_chart(
        [{"name": "Blind back-EMF prediction", "color_var": "--s1", "points": pts, "legend": False,
          "label": f"{pts[-1][1]:.1f} V"}],
        xlabel="revision of the prediction (time on 2026-11-21; * the next morning)", ylabel="V rms line-to-line per 1000 rpm",
        xticks=[(i, t) for i, (t, *_rest) in enumerate(ledger)], xpos=lambda i: (i + 0.3) / (n - 0.4),
        ylim=(lo, hi), yticks=[v for v in range(lo, hi + 1)], height=300)
    ledger_rows = [[f'<span class="mono">{t}</span>', E(lab), f'<span class="mono">{v:.3f} V</span>' if v else "–",
                    f'<span class="muted">{E(src)}</span>'] for t, lab, v, src in ledger]

    current = emf(latest_pt)

    def torque_status(r):
        if r is None:
            return pill("QUEUED")
        if not r["complete"]:
            return pill("RUNNING")
        return pill(r["report"]["verification_status"]) + " verification"
    def eff_status(runs):
        r = runs.get("motor_prius_efficiency_r1") or runs.get("motor_prius_efficiency")
        return torque_status(r)

    status_rows = [
        ["Design inputs: stator, rotor, slot", "ORNL/TM-2005/33 Fig. 21, read from the PDF's vector text and outline",
         pill("PASS") + " rebuilt and compared", '<a href="geometry.html">Design inputs</a>'],
        ["Design inputs: magnet pockets, bridge, magnet material",
         "Fig. 21 pocket outline (stretch corrected), ORNL/TM-2004/120 bridge, ORNL/TM-2004/137 Fig. 14 magnet B-H line",
         pill("PASS") + " sourced", '<a href="geometry.html#rotor">Design inputs</a>'],
        ["Design inputs: lamination steel",
         "ORNL gives 0.36 mm but no grade: M330-35A (0.35 mm, Tata typical data) as the single stand-in for every property; "
         "bracketed by M250-35A and powercore 035-190Y390 (see the lamination bracket below)",
         pill("PASS") + " stand-in chosen", '<a href="geometry.html#steel">Design inputs</a>'],
        ["Design inputs: magnet width", "Still Pyleecan's (18.9 mm)", pill("OPEN"), ""],
        ["Electromagnetics, open circuit", "FEMM via Pyleecan; phase symmetry, winding theory, zero cogging mean, mesh GCI",
         pill("PASS") + " verified", '<a href="open-circuit.html">Open circuit</a>'],
        ["Design limit: copper current density (REQ-M2, REQ-M3)",
         "25 A/mm² on 76.4 mm² of bare copper per slot: 212 A rms (corrected from 333 A on 2026-11-22, before any test "
         "data was opened)", pill("PASS") + " REQ-M2: 400 N m at 168 A, 19.8 A/mm² · " + pill("FAIL")
         + " REQ-M3 from 250 A", '<a href="torque.html">Torque</a>'],
        ["Electromagnetics, torque against current: mesh study at 333 A (the limit as first computed)",
         "Current-angle sweep, MTPA; power balance, current amplitude, symmetry, GCI", torque_status(tm),
         '<a href="torque.html">Torque</a>'],
        ["Electromagnetics, torque against current: 50-350 A curve, inherited M400-50A steel", "Same checks at every current",
         torque_status(tc), '<a href="torque.html">Torque</a>'],
        ["Electromagnetics, torque against current: 50-350 A curve, M330-35A (the blind prediction)",
         "Same checks at every current", torque_status(tc1), '<a href="torque.html">Torque</a>'],
        ["Efficiency map", "dq look-up tables (FEMM) at 20 and 80 °C magnets; lowest-loss current under the 500 V bus "
         "and 212 A limits; checks against the open-circuit and torque studies and on the map's own interpolation",
         eff_status(runs), '<a href="efficiency.html">Efficiency</a>'],
        ["Rotor bridge stress at overspeed (REQ-M4)", "CalculiX, plane stress, centrifugal and magnet loads, 7200 rpm; "
         "linearized bridge stress against M330-35A's yield (335 MPa)",
         (torque_status(so) + ": REQ-M4 fail, 424 MPa") if so and so["complete"] else torque_status(so), ""],
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
  <div class="fact"><div class="k">Back-EMF, current prediction</div><div class="v">{fmt(current, 4)} V</div><div class="n">rms line-to-line per 1000 rpm at 20 °C, run {E(latest_run["id"][:15])}</div></div>
  <div class="fact"><div class="k">REQ-M1, uncontrolled generator</div><div class="v">{pill("FAIL")} ≈ {fmt(latest_pt["metrics"]["back_emf_LL_peak_at_max_speed_V"], 4)} V</div><div class="n">Line-to-line peak at 6000 rpm against the 500 V bus</div></div>
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
        ["Peak torque at several currents", "within 10 %",
         pill("SEALED") + (" prediction written" if tc1 and tc1["complete"] else " stand-in steel curve still running")],
        ["Efficiency at sample points", "within 2 percentage points",
         pill("SEALED") + (" prediction written" if (runs.get("motor_prius_efficiency_r1") or {}).get("complete")
                           else " first map written; revision running")],
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

<h2>Lamination bracket</h2>
{BRACKET_TEXT}
{bracket_table(runs)}

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
<li><time>22:15</time><span>Decision: the ORNL data stays sealed until the whole study is complete.</span></li>
<li><time>22:20</time><span>Magnet pockets: Fig. 21 draws each pole's V as a vector outline; ORNL/TM-2004/120 gives the bridge and a magnet size. A scratch sensitivity shows remanence dominates (1.12 T would cut back-EMF 11 %).</span></li>
<li><time>22:30</time><span>Decision: open the design report's Fig. 14 only (ORNL's measured B-H line of a Prius magnet sample). Br 1.243 T, recoil permeability 1.129.</span></li>
<li><time>22:40</time><span>Fig. 21 found stretched 1.1 % in x; corrected, the pocket's extra thickness sits on the air-gap side. Torque study added; evidence runs queued overnight.</span></li>
</ol>
<h3>2026-11-22</h3>
<ol class="timeline">
<li><time>00:08</time><span>Torque mesh study at 333 A: 608 N m, spread 0.055 % but the GCI withheld (mesh noise). REQ-M2 passes, unverified.</span></li>
<li><time>00:30</time><span>Rotor overspeed check (CalculiX): 424 MPa linearized in the bridge at 7200 rpm against a 335 MPa yield. REQ-M4 verified fail; elastic at 6000 rpm (295 MPa).</span></li>
<li><time>00:40</time><span>Decision: one stand-in lamination steel, M330-35A, for every property; bracket the unknown grade with a lower-loss and a high-strength grade; a material trade study after validation.</span></li>
<li><time>01:36</time><span>Torque curve on the inherited M400-50A steel verified: 115-622 N m from 50 to 350 A rms, 400 N m at about 171 A.</span></li>
<li><time>01:37</time><span>Open circuit on the final machine (M400-50A), then the same machine and the torque curve on M330-35A, queued.</span></li>
<li><time>01:46</time><span>Open circuit on the final machine with M400-50A: 109.7 V per 1000 rpm (+1.1 % on revision 1, above the predicted +0.2 %).</span></li>
<li><time>01:56</time><span>The same machine on M330-35A: 110.9 V per 1000 rpm (+1.1 %, predicted +1.0 to +3.5 %), the new blind back-EMF prediction. REQ-M1 fails at 1040 V; its mesh uncertainty is withheld (anomalous convergence order), the verdict is not in doubt.</span></li>
<li><time>03:20</time><span>Torque curve on M330-35A verified, the blind torque prediction: 119-606 N m from 50 to 350 A rms, 400 N m at about 168 A. Against M400-50A: +3.0 % at 50 A, changing sign near 240 A, −2.5 % at 350 A, because above 1.8 T our M330-35A curve is extrapolated. Bracket runs (M250-35A, 190Y390) started.</span></li>
<li><time>03:32</time><span>Bracket, open circuit on M250-35A: 111.0 V per 1000 rpm, +0.13 % (predicted −0.35 %: wrong sign).</span></li>
<li><time>03:56</time><span>Bracket, torque on M250-35A: −1.8 % at 100 A, −1.0 % at 300 A.</span></li>
<li><time>04:05</time><span>Bracket, open circuit on 190Y390: 111.0 V per 1000 rpm, +0.12 %. The three grades span 0.13 % in back-EMF.</span></li>
<li><time>04:29</time><span>Bracket, torque on 190Y390: −0.9 % at 100 A, −0.6 % at 300 A. Across the three grades the torque spans 1.8 % at 100 A and 1.0 % at 300 A, the stand-in M330-35A at the top: the unknown grade does not limit the blind comparison.</span></li>
<li><time>09:16</time><span>B-H tail sensitivity, saturation polarization 2.05 T instead of 2.0: back-EMF −0.35 %.</span></li>
<li><time>09:20</time><span>Correction: ORNL's 0.84 slot fill is on the squares of the insulated wires, so the bare copper is 76.4 mm² per slot, not 120.1. The 25 A/mm² limit is 212 A rms, not 333. REQ-M2 still passes (margin about 19 %); REQ-M3 now fails from 250 A. Torques unchanged.</span></li>
<li><time>09:42</time><span>Tail sensitivity, torque: +1.75 % at 300 A, +1.96 % at 350 A. The high-current prediction carries about ±2 % from the unmeasured deep-saturation tail; it stays on 2.0 T.</span></li>
<li><time>12:06</time><span>dq look-up table, magnets at 20 °C (169 FEMM solves): verified; the dq torque equation within 0.37 % of FEMM's torque.</span></li>
<li><time>13:34</time><span>The same table with magnets at 80 °C: open-circuit flux −7.0 % against Br's −6 % (the saturated bridges keep their leakage flux); torque −5.1 to −5.4 % at id = 0.</span></li>
<li><time>13:38</time><span>First efficiency map: peak 97.4 % cold, 97.0 % hot; rated 50 kW holds to 6000 rpm (58.6 / 53.7 kW). Not verified: the 25 A table does not resolve light load at high speed. Low-current tables (6.25 A steps) started.</span></li>
</ol>

<h2>Blind protocol log</h2>
<div class="col">
<p>Everything that touched ORNL material, in order. "Sealed" means not opened by anyone working on the study.</p>
</div>
{table(["When", "What", "Effect on the blind comparison"], [
        ["evening", "ORNL/TM-2004/137 design report and ORNL/TM-2005/33 Fig. 21 read for design content", "None: design data"],
        ["22:20", "ORNL/TM-2004/120 read with a line filter. Values from its Tables 5.4-5.5 slipped through because their labels are abbreviations or sit on separate lines. They are ORNL's lumped-parameter <b>model</b> results, not measurements, at operating points that were not identified.",
         "Recorded in full. The measured data stays sealed. The torque cases declare it as prior knowledge. Extraction is whitelist-only from here on."],
        ["22:30", "ORNL/TM-2004/137 Fig. 14 opened by the user's decision: ORNL's measured B-H line of a magnet sample", "A material input, like a datasheet; not motor performance"],
        ["2026-11-22 09:20", "ORNL/TM-2004/137, the winding paragraph re-read by whitelist (the slot-fill definition and the conductor description)", "None: design text. It corrected our copper area (see the timeline)."],
        ["sealed", "ORNL/TM-2004/137 Fig. 13 (measured no-load air-gap flux density); ORNL/TM-2004/247 and ORNL/TM-2006/423 (test reports); ORNL/TM-2005/33 pages 20-30", "Opened only when the study is complete"],
    ])}

<p class="muted">Generated from the case files and runs by <code>reports/motor/build_report.py</code>.</p>
"""
    return page("index.html", "Prius Motor Study", body, "Study 7 overview: question, blind protocol, status and predictions.",
                full)


# --------------------------------------------------------------------------- page: design inputs

def rotor_section(ours, pyl):
    rows = []
    for path, attr, value, label, note in ROTOR_CHANGES:
        key = f"{path}.{attr}"
        old = dig(pyl, key) * 1e3 if pyl else None
        new = dig(ours, key) * 1e3
        rows.append([f"<code>{E(key)}</code>", f"{new:.3f} mm", f"{old:.3f} mm" if old is not None else "–",
                     f"{100 * (new - old) / old:+.1f} %" if old else "", E(note)])
    for attr, value, label, note in MAGNET_CHANGES:
        key = f"rotor.hole.0.magnet_0.mat_type.mag.{attr}"
        old = dig(pyl, key) if pyl else None
        new = dig(ours, key)
        rows.append([f"<code>magnet {E(attr)}</code>", f"{new:.4g}", f"{old:.4g}" if old is not None else "–",
                     f"{100 * (new - old) / old:+.1f} %" if old else "", E(note)])
    pocket = [
        ["Arm angle to tangential", "17.4° (sd 0.13°)", "17.46°", "kept (W0 re-solved so it stays 17.4° with the new H0)"],
        ["Pocket thickness", "6.80 mm (sd 0.03)", "6.50 mm", "adopted"],
        ["Outer apex depth below the OD", "10.65 mm (sd 0.03)", "10.96 mm", "adopted (H0)"],
        ["Inner apex depth below the OD", "17.76 mm", "17.78 mm", "follows: 17.78 mm with H0 and H3 above"],
    ]
    sens = [
        ["Pocket and magnet 6.78 mm (Fig. 21)", "+0.42 %"], ["Magnet 5.31 mm thick (ORNL/TM-2004/120)", "−2.38 %"],
        ["Magnet 19.24 mm wide (ORNL/TM-2004/120)", "+2.01 %"], ["Br 1.12 T (ORNL/TM-2004/120)", "<b>−11.3 %</b>"],
    ]
    conflicts = [
        ["Radial distance to the slot end", "116.5 mm (TM-2004/120 Rad2)", "114.5 mm (Fig. 21: bore + 1.320 in)",
         "Fig. 21 kept: a dimensioned drawing whose inset and outline agree. Pyleecan's file had 115.2 mm."],
        ["Magnet size", "19.24 × 5.31 mm (TM-2004/120)", "pocket 6.80 mm thick (Fig. 21)",
         "Magnet fills the drawn pocket; TM-2004/120's size recorded as an alternative (net about −0.4 %)."],
        ["Remanence", "1.12 T (TM-2004/120 Table 5.4)", "1.243 T (TM-2004/137 Fig. 14, measured)",
         "Fig. 14 adopted. 1.12 T matches 1.24 T at about 120 °C with −0.1 %/K, so it is probably a hot value."],
        ["Stack length", "83.57 mm (TM-2004/120)", "83.82 mm = 3.3 in (TM-2004/137)", "3.3 in kept."],
    ]
    return f"""
<h2 id="rotor">Rotor pockets and magnets</h2>
<div class="col">
<p>Fig. 21 also draws each pole's V-shaped magnet pocket as a vector outline: two magnet seats in one bent pocket,
separated only by stop notches, with the elbow on the pole axis. The figure is not dimensioned there, so the outline
was measured. One correction came first: the figure is stretched 1.1 % horizontally in the PDF (its rotor outline is an
ellipse, x/y = 1.0114), so x and y were scaled separately to the labelled 6.314 in diameter. Measured on all 8 poles:</p>
</div>
{table(["Pocket feature", "Fig. 21 (8 poles)", "Pyleecan's file", "Use"], pocket, "num")}
<div class="col"><p>The inner edge matches Pyleecan's; the extra thickness is on the air-gap side.</p></div>
<figure>
{img64(REPO / "portfolio/img/motor_pocket_vs_ornl_fig21.png", "Pocket overlay: ORNL drawing, our machine and Pyleecan's file")}
<figcaption>One pole's pocket: the drawing's vector outline (black, stretch corrected), our pocket (blue) and Pyleecan's
(orange, dashed). Our pocket follows both edges of the drawing; Pyleecan's outer edge sits 0.3 mm inside it.</figcaption>
</figure>

<h3>Magnet material</h3>
<div class="col">
<p>A scratch sensitivity showed which magnet input matters. Changing one at a time from the stator-rebuilt machine
(108.09 V per 1000 rpm at fineness 4):</p>
</div>
{table(["Change", "Back-EMF"], sens, "num")}
<div class="col">
<p>Remanence dominates: the 1.12 T in ORNL/TM-2004/120 would move the back-EMF more than twice the 5 % validation
limit. The only Prius-specific source was Fig. 14 of the 2004 design report, ORNL's measured B-H line of a Prius magnet
sample against other magnets. It is a material property, not motor performance, but it is ORNL-measured, so opening it
was the user's decision (22:30). Only that figure was rendered; the measured air-gap flux density (Fig. 13) above it on
the same page stayed out of the crop.</p>
<p>Digitized from 906 pixels of ORNL's fitted line: <b>Br 1.243 T</b> (the line extrapolated to H = 0; the measured
points span −7.2 to −4.7 kOe), <b>recoil permeability 1.129</b>, Hcb −876 kA/m. Pyleecan's generic 1.24 T was right;
its permeability of 1.05 was not. The temperature is not stated, so 20 °C is assumed.</p>
</div>

<h3>Every rotor and magnet change</h3>
{table(["Parameter", "Ours", "Pyleecan", "Difference", "Source"], rows, "num")}

<h3>Where sources disagree</h3>
{table(["Quantity", "One source", "Other source", "Decision"], conflicts)}
"""


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

{rotor_section(ours, pyl)}

<h2>Why the slot matters</h2>
<div class="col">
<p>The verified open-circuit run on Pyleecan's machine gives an air-gap field fundamental of 0.893 T. Spread over a
tooth at the bore, that is about 1.70 T in Pyleecan's 5.55 mm tooth, past the knee of the steel, and about
1.27 T in the drawing's 7.40 mm tooth. Under load the difference grows, so it matters more for torque than for
back-EMF.</p>
</div>

<h2>Still Pyleecan's</h2>
<div class="col">
<ul>
<li><b>Magnet width</b>: 18.9 mm. ORNL/TM-2004/120 gives 19.24 mm with a 5.31 mm thickness, which does not fit the
drawn 6.80 mm pocket in this pocket model; together they would move the back-EMF about −0.4 %.</li>
<li><b>Winding</b>: 9 turns per coil, one parallel path, consistent with the 9 conductor bundles per slot in ORNL's text.</li>
</ul>
</div>
<h2 id="steel">Lamination steel</h2>
<div class="col">
<p>ORNL's design report gives the lamination thickness, 0.014 in (0.36 mm), but not the grade, and Toyota probably
used a supplier's own 0.35 mm grade. Until 2026-11-22 the electromagnetics used the M400-50A curve (0.5 mm) that came
with Pyleecan's file and was never chosen. Now one stand-in grade serves every property: <b>M330-35A</b>, a standard
0.35 mm EN 10106 grade with full public data, mid-range in its class (Tata Steel typical data, 2009: B-H at 50 Hz to
1.8 T, losses to 2500 Hz, yield 315-335 MPa). The aim is the closest guess to what Toyota used, not the best steel.</p>
<ul>
<li><b>Above 1.8 T</b> the datasheets stop. The curve continues with the polarization approaching 2.0 T as 1/H,
joined with a continuous slope: our assumption, which matters only in the tooth tips at high current.</li>
<li><b>The bracket</b>: M250-35A (lower loss, Tata 2008; less permeable above 1.3 T) and thyssenkrupp powercore
035-190Y390 (high strength, 2025: yield 390 MPa guaranteed, 407 typical). The blind predictions become ranges.</li>
<li><b>Field needed</b> at 1.3 T: 242 A/m for M330-35A against 950 A/m for the inherited M400-50A curve; at 1.5 T,
1027 against 2450. That is why the back-EMF and torque move when the steel changes.</li>
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
    "motor_prius_ornl_oc_mesh_r1": "Rotor and magnets from published sources: pocket 6.78 mm (grown inward, later "
                                   "corrected), bridge 1.45 mm, magnet Br 1.243 T and recoil permeability 1.129 from "
                                   "ORNL's Fig. 14.",
    "motor_prius_ornl_oc_mesh_r2": "Final machine: the pocket placed as drawn (outer apex 10.65 mm, 6.80 mm thick), still "
                                   "on Pyleecan's inherited M400-50A steel: the other side of the steel sensitivity.",
    "motor_prius_ornl_oc_mesh_r3": "Final machine with M330-35A laminations, the study's stand-in steel. Its finest-mesh "
                                   "back-EMF is the blind prediction.",
    "motor_prius_ornl_oc_m250": "Lamination bracket: the final machine on M250-35A, the lower-loss grade. +0.13 % on "
                                "M330-35A, against a predicted -0.35 %: below 1.15 T, where most of the open-circuit iron "
                                "runs, this grade needs less field, not more.",
    "motor_prius_ornl_oc_y390": "Lamination bracket: the final machine on powercore 035-190Y390, the high-strength grade. "
                                "+0.12 % on M330-35A (predicted -0.1 %), for the same reason.",
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
    s_orn = series(["motor_prius_ornl_oc_mesh"], "--s2", "Our machine, stator rebuilt (ORNL Fig. 21)", 4)
    final = "motor_prius_ornl_oc_mesh_r2" if runs.get("motor_prius_ornl_oc_mesh_r2") else "motor_prius_ornl_oc_mesh_r1"
    s_fin = series([final], "--accent", "Our machine, rotor and magnets sourced (M400-50A)", -6)
    s_m330 = series(["motor_prius_ornl_oc_mesh_r3"], "--s3", "Final machine, M330-35A steel (the prediction)", -6)
    scratch = {"name": "ORNL radii only, Pyleecan's slot (scratch)", "color_var": "--ink-3", "hollow": True,
               "points": [(4.0, 106.591, "fineness 4: 106.591 V (scratch run, BACKLOG 21:45)")], "label": "radii only"}
    all_series = [s_pyl, s_orn, s_fin, scratch] + ([s_m330] if s_m330["points"] else [])
    ys = [y for s in all_series for _, y, _ in s["points"]]
    lo, hi = math.floor(min(ys) - 0.4), math.ceil(max(ys) + 0.4)
    step = 0.5 if hi - lo <= 4 else 1
    yt = [lo + i * step for i in range(int((hi - lo) / step) + 1)]
    chart = line_chart(all_series, xlabel="mesh fineness (Pyleecan Kmesh_fineness, log scale)",
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
    r2 = runs["motor_prius_ornl_oc_mesh_r3"] or runs["motor_prius_ornl_oc_mesh_r2"]
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


TORQUE_NOTES = {
    "motor_prius_torque_m250": "Lamination bracket: M250-35A at 100 and 300 A. -1.8 % and -1.0 % on M330-35A; the gap "
                               "is largest at 100 A, where the loaded teeth sit at 1.4-1.6 T and this grade needs up to "
                               "1.8 times the field.",
    "motor_prius_torque_y390": "Lamination bracket: powercore 035-190Y390 at 100 and 300 A. -0.9 % and -0.6 % on "
                               "M330-35A, the same pattern as M250-35A.",
    "motor_prius_torque_mesh": "Mesh study at 333 A rms, the 25 A/mm² copper limit as first computed (corrected to "
                               "212 A, see the callout above), fineness 2 / 4 / 8. At 333 A the corrected current "
                               "density is 39 A/mm².",
    "motor_prius_torque_current": "The MTPA torque curve from 50 to 350 A rms at fineness 4, on Pyleecan's inherited "
                                  "M400-50A steel: the other side of the steel sensitivity.",
    "motor_prius_torque_current_r1": "The same curve with M330-35A laminations, the study's stand-in steel: the blind "
                                     "prediction of torque against current. It sits 3 % above the M400-50A curve at 50 A "
                                     "and 2.5 % below it at 350 A, the sign changing near 240 A: at high current the "
                                     "teeth run above 1.8 T, where M330-35A's curve is our extrapolation, not data.",
}


def torque_section(case, run):
    name = case["name"]
    head = f'<h3 id="{name}">{E(name)}</h3><p>{E(TORQUE_NOTES.get(name, case["toml"]["case"]["description"]))}</p>'
    record = f'<details><summary>Case record: predictions before the run, results after</summary><pre>{E(case["header"])}</pre></details>'
    if run is None:
        return head + '<p class="muted">Queued: no run yet.</p>' + record
    rows = []
    for pt in run["points"]:
        m, p = pt.get("metrics", {}), pt["parameters"]
        ok, n = point_pass(pt)
        rows.append([f'{float(p["current_rms_A"]):g}', f'{float(p["mesh_fineness"]):g}',
                     fmt(TURNS_PER_SLOT * float(p["current_rms_A"]) / COPPER_MM2_PER_SLOT, 3), fmt(m.get("torque_mtpa_Nm"), 5),
                     fmt(m.get("mtpa_angle_deg"), 3), fmt(m.get("torque_per_amp_Nm_per_A"), 4),
                     fmt(m.get("torque_ripple_pp_at_mtpa_Nm"), 3),
                     f'{pt.get("solver_outputs", {}).get("wall_s", 0):.0f} s',
                     pill(f"{ok}/{n} PASS") if n and ok == n else pill(f"{ok}/{n}")])
    pts_table = table(["Current (A rms)", "Mesh", "J, bare copper (A/mm²)", "MTPA torque (N m)", "Angle (°)", "N m per A",
                       "Ripple p-p (N m)", "Solve", "Checks"], rows, "num")
    rc, _ = run_checks(run)
    rc_table = table(["Run-level check", "Description", "Value", "Limit", "Status"],
                     [[f'<code>{E(c["id"])}</code>', E(c["description"]), fmt(c["value"], 3), fmt(c["tolerance"], 3),
                       pill(c["status"])] for c in rc]) if rc else ""
    req = ""
    if run["report"]:
        req = "<p>Requirement verdicts: " + ", ".join(
            f'{E(pt["label"].split("_", 1)[1])} {pill(pt["requirements"][0]["verdict"])}'
            for pt in run["report"]["points"] if pt.get("requirements")) + "</p>"
    figs = ""
    pick = max((pt for pt in run["points"] if pt.get("status") == "completed"),
               key=lambda pt: (float(pt["parameters"]["mesh_fineness"]), float(pt["parameters"]["current_rms_A"])),
               default=None)
    if pick is not None:
        figs = (f'<figure>{img64(pick["dir"] / "response.png", "Torque against current angle")}<figcaption>{E(pick["label"])}: '
                "mean torque against current angle with the MTPA point, and the torque over one electrical period at the "
                "best sampled angle.</figcaption></figure>")
    prov = f'<p class="muted mono">run {E(run["id"])}' + ("" if run["complete"] else " (still running)") + "</p>"
    return head + pts_table + rc_table + req + figs + record + prov


def build_torque(tcases, runs):
    def curve(r, steel):
        if not r:
            return []
        return [(float(pt["parameters"]["current_rms_A"]), pt["metrics"]["torque_mtpa_Nm"],
                 f'{steel}, {float(pt["parameters"]["current_rms_A"]):g} A rms: {pt["metrics"]["torque_mtpa_Nm"]:.1f} N m at '
                 f'{pt["metrics"]["mtpa_angle_deg"]:.1f} deg') for pt in r["points"] if pt.get("status") == "completed"]

    chart = ""
    pts = curve(runs.get("motor_prius_torque_current"), "M400-50A")
    pts1 = curve(runs.get("motor_prius_torque_current_r1"), "M330-35A")
    if pts or pts1:
        series = []
        if pts:
            series.append({"name": "M400-50A (inherited)", "color_var": "--s1", "points": pts,
                           "label": f"M400-50A {pts[-1][1]:.0f} N m", "label_dy": 8})
        if pts1:
            series.append({"name": "M330-35A (stand-in, the prediction)", "color_var": "--s2", "points": pts1,
                           "label": f"M330-35A {pts1[-1][1]:.0f} N m", "label_dy": -8})
        for rn, steel, var in (("motor_prius_torque_m250", "M250-35A", "--s3"),
                               ("motor_prius_torque_y390", "190Y390", "--ink-3")):
            bp = curve(runs.get(rn), steel)
            if bp:
                series.append({"name": f"{steel} (bracket, 100 / 300 A)", "color_var": var, "points": bp,
                               "hollow": True, "dots_only": True})
        if True:
            ymax = max(500, math.ceil(max(y for _, y, _ in pts + pts1) / 100) * 100)
            X0, X1 = 0, 375
            L, Rr, T, B, Wd, Hd = 64, 150, 16, 46, 760, 330
            W, H = Wd - L - Rr, Hd - T - B
            xlim = L + (I_LIMIT - X0) / (X1 - X0) * W
            y400 = T + (1 - 400 / ymax) * H
            extra = (f'<line x1="{L}" x2="{L + W}" y1="{y400:.1f}" y2="{y400:.1f}" stroke="var(--ink-3)" stroke-width="1"/>'
                     f'<text x="{L + 6}" y="{y400 - 6:.1f}">rated 400 N m</text>'
                     f'<line x1="{xlim:.1f}" x2="{xlim:.1f}" y1="{T}" y2="{T + H}" stroke="var(--ink-3)" stroke-width="1"/>'
                     f'<text x="{xlim - 6:.1f}" y="{T + 14}" text-anchor="end">25 A/mm² limit, {I_LIMIT:.0f} A</text>')
            chart = line_chart(series,
                               xlabel="phase current (A rms)", ylabel="MTPA torque (N m)",
                               xticks=[(v, str(v)) for v in range(0, 376, 50)], xpos=lambda v: (v - X0) / (X1 - X0),
                               ylim=(0, ymax), yticks=list(range(0, ymax + 1, 100)), extra=extra)
    checks_rows = [
        ["Power balance", "Mean of Σ i·dφ/dt over one period against mean torque × mechanical speed, at every angle", "≤ 2 %",
         "Energy conservation in a lossless magnetostatic model: an independent route to FEMM's stress-tensor torque. "
         "Pyleecan's flux-linkage sign is opposite to the motor convention; the check applies it explicitly."],
        ["Current amplitude", "Imposed phase-current fundamental against √2 × the requested rms", "≤ 1e-3",
         "Pyleecan's dq currents are rms; a peak/rms mix-up would be a factor √2."],
        ["Phase symmetry under load", "Spread of the three phases' fundamental flux linkage", "≤ 2e-3", "Winding and periodicity under load."],
        ["MTPA bracketed", "Maximum torque inside the angle sweep", "validity", "Otherwise the parabola extrapolates."],
        ["Mesh convergence (run level)", "GCI on the MTPA torque, three meshes", "≤ 1 %", "At the most saturated current."],
    ]
    sections = "".join(torque_section(c, runs.get(c["name"])) for c in tcases)
    body = f"""
<div class="col">
<div class="eyebrow">Study 7 · electromagnetics · under load</div>
<h1>Torque against current</h1>
<p class="lede">How much torque does the motor make per amp, and does it reach its rated 400 N m within a copper
current-density limit? Each point sweeps the current angle and takes the maximum torque per amp (MTPA).</p>
</div>

<div class="callout">
<p><b>Assumed design limit:</b> 25 A/mm² rms in the copper, a common short-time limit for an oil-cooled traction
motor. With 76.4 mm² of bare copper per slot (13 strands of 0.912 mm per turn, 9 turns) that is <b>212 A rms</b>.
No published inverter current rating is used: searching for one risks ORNL's measured torque-current data.</p>
<p><b>Corrected on 2026-11-22, before any test data was opened.</b> The first version applied ORNL's 0.84 slot fill
to the whole slot (120.1 mm², 333 A). ORNL defines that fill on the <i>squares</i> of the insulated wires; the bare
copper is about 0.59 of the slot, 1.57 times less. Torques are unchanged; only the current-density verdicts move:
REQ-M2 still passes (400 N m at about 168 A, 19.8 A/mm², margin about 19 % instead of 52 %), and REQ-M3 now fails
from 250 A. The mesh study below still runs at 333 A, the limit as first computed.</p>
<p><b>Prior knowledge declared:</b> the 400 N m rating, and ORNL lumped-parameter model values seen in the filter
incident (see the overview's blind protocol log).</p>
</div>

<h2>Method</h2>
<div class="col">
<ul>
<li>Pyleecan's dq currents are rms. At current I the angle γ runs from the q axis towards negative d:
I<sub>d</sub> = −I sin γ, I<sub>q</sub> = I cos γ, from 0 to 70° in 8 steps.</li>
<li>At each angle one FEMM simulation over one electrical period (48 steps) gives the torque and the phase flux
linkages; the MTPA torque comes from a parabola through the best three angles.</li>
<li>1000 rpm, below base speed, so no voltage limit applies.</li>
</ul>
</div>

<h2>Checks on every point</h2>
{table(["Check", "What is compared", "Limit", "Why"], checks_rows)}

<h2>MTPA torque against current</h2>
{chart or '<p class="muted">The curve appears when the 50-350 A run has points.</p>'}
<h3>Lamination bracket</h3>
{bracket_table(runs)}
<div class="col"><p>The two steels differ by at most 3 %. M330-35A needs less field below 1.7 T, so it gives more torque
at low current. Above about 240 A the teeth saturate past 1.8 T, the top of Tata Steel's table. There our M330-35A curve
is extrapolated (saturation polarization 2.0 T), and it carries less flux than Pyleecan's M400-50A curve. The prediction
above 200 A therefore rests on a stated assumption about deep saturation.</p></div>

<h2>Runs</h2>
{sections}

<p class="muted">Generated by <code>reports/motor/build_report.py</code>.</p>
"""
    return page("torque.html", "Prius Torque Curve", body, "Study 7: torque against current of the Prius motor.")


# --------------------------------------------------------------------------- page: efficiency map

EFF_CASES = ["motor_prius_efficiency", "motor_prius_efficiency_r1"]
LUT_CASES = ["motor_prius_lut_mesh", "motor_prius_lut_cold", "motor_prius_lut_hot", "motor_prius_lut_cold_lowiq",
             "motor_prius_lut_hot_lowiq"]
EFF_NOTES = {
    "motor_prius_efficiency": "First map, on the 25 A tables. Not verified: below 30 N m at 4000-6000 rpm the best "
                              "operating point uses only 2-5 A of q-axis current, inside the table's first cell, and the "
                              "map there moved by up to 10 points between the half and the full table.",
    "motor_prius_efficiency_r1": "The tables gain rows at 6.25 A steps below 50 A of q-axis current, and the map itself "
                                 "is checked: the map from the half table against the map from the full one.",
    "motor_prius_lut_mesh": "Mesh study for the tables: fineness 2 within 0.4 % of 8 on torque and iron loss.",
    "motor_prius_lut_cold": "dq table, magnets at 20 °C: id 0 to −300 A, iq 0 to 300 A in 25 A steps (169 FEMM solves).",
    "motor_prius_lut_hot": "The same table with magnets at 80 °C.",
    "motor_prius_lut_cold_lowiq": "Supplementary rows at iq 6.25-43.75 A (cold). The 25 A row, computed again, is "
                                  "bit-identical to the main table.",
    "motor_prius_lut_hot_lowiq": "Supplementary rows at iq 6.25-43.75 A (hot).",
}


def eff_metrics_table(run):
    from studies.motor_efficiency import REF_POINTS  # noqa: PLC0415

    pts = [pt for pt in run["points"] if pt.get("status") == "completed"]
    names = [pt["label"].split("_", 1)[1] for pt in pts]
    rows = [["Peak efficiency"] + [f'{pt["metrics"]["peak_efficiency_pct"]:.2f} % at {pt["metrics"]["peak_efficiency_speed_rpm"]:.0f} rpm, '
                                   f'{pt["metrics"]["peak_efficiency_torque_Nm"]:.0f} N m' for pt in pts]]
    for n, t in REF_POINTS:
        rows.append([f"{n} rpm, {t} N m"] + [f'{pt["metrics"][f"efficiency_{n}rpm_{t}Nm_pct"]:.2f} %' for pt in pts])
    rows.append(["Lowest power at 212 A, base speed to 6000 rpm (REQ-M5 ≥ 50 kW)"]
                + [f'{pt["metrics"]["min_power_rated_speed_range_kW"]:.1f} kW' for pt in pts])
    rows.append(["400 N m reachable at 212 A up to"] + [f'{pt["metrics"]["base_speed_rated_torque_rpm"]:.0f} rpm' for pt in pts])
    rows.append(["Phase resistance"] + [f'{pt["solver_outputs"]["phase_resistance_ohm"] * 1e3:.1f} mΩ' for pt in pts])
    return table(["Quantity"] + [E(n) for n in names], rows, "num")


def eff_section(case, run):
    name = case["name"]
    head = f'<h3 id="{name}">{E(name)}</h3><p>{E(EFF_NOTES.get(name, case["toml"]["case"]["description"]))}</p>'
    record = f'<details><summary>Case record: predictions before the run, results after</summary><pre>{E(case["header"])}</pre></details>'
    if run is None:
        return head + '<p class="muted">Queued: no run yet.</p>' + record
    if not run["complete"]:
        return head + f'<p class="muted mono">run {E(run["id"])} (still running)</p>' + record
    body = ""
    if name.startswith("motor_prius_efficiency"):
        body += eff_metrics_table(run)
        rows = []
        for pt in run["points"]:
            for c in pt["checks"]:
                rows.append([E(pt["label"].split("_", 1)[1]), f'<code>{E(c["id"])}</code>', E(c["description"]),
                             fmt(c["value"], 3), fmt(c["tolerance"], 3), pill(c["status"])])
        body += table(["Scenario", "Check", "Description", "Value", "Limit", "Status"], rows)
    else:
        ok = sum(1 for pt in run["points"] if point_pass(pt)[0] == point_pass(pt)[1])
        body += f'<p>{ok} of {len(run["points"])} columns pass every check; verification {pill(run["report"]["verification_status"])}.</p>'
    req = ""
    if run["report"] and name.startswith("motor_prius_efficiency"):
        req = "<p>Requirement verdicts: " + ", ".join(
            f'{E(pt["label"].split("_", 1)[1])} {pill(pt["requirements"][0]["verdict"])}'
            for pt in run["report"]["points"] if pt.get("requirements")) + "</p>"
    prov = f'<p class="muted mono">run {E(run["id"])}, verification {E(run["report"]["verification_status"])}</p>'
    return head + body + req + record + prov


def build_efficiency(runs):
    ecases = [case_record(c) for c in EFF_CASES]
    lcases = [case_record(c) for c in LUT_CASES]
    best = runs.get("motor_prius_efficiency_r1")
    if not (best and best["complete"]):
        best = runs.get("motor_prius_efficiency")
    figs = ""
    if best and best["complete"]:
        for pt in best["points"]:
            figs += (f'<figure>{img64(pt["dir"] / "response.png", "Efficiency map")}<figcaption>{E(pt["label"])}: '
                     "motor-only efficiency over speed and torque, with the torque limit at the 212 A design current. "
                     f'Run {E(best["id"])}.</figcaption></figure>')
    sections = "".join(eff_section(c, runs.get(c["name"])) for c in ecases)
    lut_sections = "".join(eff_section(c, runs.get(c["name"])) for c in lcases)
    body = f"""
<div class="col">
<div class="eyebrow">Study 7 · efficiency</div>
<h1>Efficiency map</h1>
<p class="lede">How efficient is the motor across its torque-speed range, and does it hold its rated 50 kW from base
speed to 6000 rpm within the 500 V bus and the 212 A copper limit? The map comes from look-up tables of FEMM solves,
searched for the lowest-loss current at every operating point.</p>
</div>

<div class="callout">
<p><b>Framing (user's decision, 2026-11-22):</b> motor only, copper and iron loss; no mechanical, magnet eddy-current,
AC copper or inverter loss, so these efficiencies are upper bounds on what a dynamometer would measure. Two corners of a
temperature band: cold (everything at 20 °C) and hot (windings 100 °C, magnets 80 °C). Bus 500 V; design current
212 A rms.</p>
<p><b>Blind:</b> no ORNL efficiency value has been opened. The sample points are chosen to span the plane, not taken
from any ORNL test plan.</p>
</div>

<h2>Method</h2>
<div class="col">
<ul>
<li><b>dq tables.</b> At each d-axis current, one FEMM run per q-axis current over one electrical period at 1000 rpm
gives the mean torque, the dq flux linkages and the iron-loss coefficients of P = A f + B f² + C f<sup>1.5</sup>.
One table per magnet temperature.</li>
<li><b>The search.</b> The tables are interpolated (cubic) onto a 1 A grid. At each speed and torque, the feasible
current with the least copper plus iron loss is chosen, under the voltage limit V<sub>dc</sub>/√6 (204 V phase rms,
the resistive drop included) and the current limit.</li>
<li><b>Copper.</b> 72 series turns per phase, 8.49 mm² of bare copper per turn, end connections estimated from the
geometry: 59.6 mΩ per phase at 20 °C, 78.4 mΩ at 100 °C.</li>
</ul>
</div>

<h2>Result</h2>
{figs or '<p class="muted">The maps appear when the efficiency run has finished.</p>'}

<h2>Runs</h2>
{sections}

<h2>The tables behind the map</h2>
{lut_sections}

<p class="muted">Generated by <code>reports/motor/build_report.py</code>.</p>
"""
    return page("efficiency.html", "Prius Efficiency Map", body, "Study 7: motor-only efficiency map of the Prius motor.")


def main():
    cases = [case_record(c) for c in CASES]
    tcases = [case_record(c) for c in TORQUE_CASES]
    bcases = [case_record(c) for c in BRACKET_OC]
    btcases = [case_record(c) for c in BRACKET_TQ]
    runs = {c: load_run(c) for c in CASES + TORQUE_CASES + BRACKET_OC + BRACKET_TQ + EFF_CASES + LUT_CASES
            + ["motor_prius_rotor_overspeed_mesh"]}
    (OUT / "index.html").write_text(build_index(cases, runs), encoding="utf-8")
    if len(sys.argv) > 1:  # also write the artifact's main page (no document skeleton) to the given path
        Path(sys.argv[1]).write_text(build_index(cases, runs, full=False), encoding="utf-8")
    (OUT / "geometry.html").write_text(build_geometry(), encoding="utf-8")
    (OUT / "open-circuit.html").write_text(build_open_circuit(cases + bcases, runs), encoding="utf-8")
    (OUT / "torque.html").write_text(build_torque(tcases + btcases, runs), encoding="utf-8")
    (OUT / "efficiency.html").write_text(build_efficiency(runs), encoding="utf-8")
    for f, _ in PAGES:
        print(f"wrote {OUT / f} ({(OUT / f).stat().st_size / 1e3:.0f} kB)")


if __name__ == "__main__":
    main()
