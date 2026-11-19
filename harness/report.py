"""Requirements-compliance report: requirement -> result -> check -> evidence file."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from harness.case import OPERATORS, load_case
from harness.runio import read_json, write_json


def _verdict(passed: bool | None, verification: str) -> str:
    if passed is None:
        return "NO RESULT"
    base = "PASS" if passed else "FAIL"
    return base if verification == "PASS" else f"{base} (unverified)"


def evaluate(case: dict, manifest: dict, verification: dict | None) -> dict:
    ver_by_label = {p["label"]: p for p in (verification or {}).get("points", [])}
    points = []
    for pt in manifest["points"]:
        ver = ver_by_label.get(pt["label"], {"status": "NOT_RUN", "checks": []})
        reqs = []
        for r in case["requirements"]:
            value = pt.get("metrics", {}).get(r["metric"])
            passed = None if value is None else bool(OPERATORS[r["operator"]](value, r["limit"]))
            margin = None
            if value is not None:
                margin = r["limit"] - value if r["operator"] in ("<=", "<") else value - r["limit"]
            reqs.append({
                "id": r["id"], "text": r["text"], "metric": r["metric"], "operator": r["operator"],
                "limit": r["limit"], "units": r["units"], "value": value, "margin": margin,
                "verdict": _verdict(passed, ver["status"]),
            })
        points.append({
            "label": pt["label"], "parameters": pt["parameters"], "derived": pt.get("derived"),
            "simulation_status": pt["status"], "verification_status": ver["status"],
            "checks": ver.get("checks", []), "requirements": reqs,
        })
    return {"points": points}


def _fmtv(v):
    return f"{v:.4g}" if isinstance(v, (int, float)) else str(v)


def _fmt(v, digits=4):
    if v is None:
        return "-"
    return f"{v:.{digits}g}"


def build_report(run_dir: str | Path) -> Path:
    run_dir = Path(run_dir)
    case, _, _ = load_case(run_dir / "inputs" / "case.toml")
    manifest = read_json(run_dir / "manifest.json")
    ver_path = run_dir / "verification.json"
    verification = read_json(ver_path) if ver_path.exists() else None
    result = evaluate(case, manifest, verification)
    result["run_id"] = manifest["run_id"]
    result["generated_utc"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    result["verification_status"] = verification["status"] if verification else "NOT_RUN"
    write_json(run_dir / "report.json", result)

    env = manifest["environment"]
    sweep = case.get("sweep", {}).get("parameter")
    reqs = case["requirements"]
    L = []
    L.append(f"# Engineering review report: {case['case']['name']}")
    L.append("")
    L.append(f"- **Run:** `{manifest['run_id']}`" + (f" (rerun of `{manifest['rerun_of']}`)"
                                                       if manifest.get("rerun_of") else ""))
    L.append(f"- **Generated:** {result['generated_utc']}")
    L.append(f"- **Case file SHA-256:** `{manifest['case_sha256']}`")
    git = env.get("git", {})
    L.append(f"- **Environment:** Python {env['python']}, "
             + ", ".join(f"{k} {v}" for k, v in env["packages"].items())
             + f"; {env['platform']}")
    tools = env.get("tools") or {}
    if tools:
        L.append("- **Tools:** " + "; ".join(f"{k} {v}" for k, v in tools.items()))
    L.append(f"- **Code version:** git `{git.get('commit') or 'none'}`"
             + (" (uncommitted changes present)" if git.get("dirty") else ""))
    L.append(f"- **Simulation status:** {manifest['status']}")
    L.append(f"- **Verification status:** {result['verification_status']}")
    L.append("")
    if result["verification_status"] != "PASS":
        L.append("> **Warning:** verification did not pass for every point. Requirement verdicts "
                 "marked *(unverified)* are not supported by evidence and must not be used for "
                 "acceptance.")
        L.append("")

    L.append("## Scope")
    L.append("")
    L.append(case["case"]["description"])
    L.append("")
    L.append("**Assumptions**")
    L.append("")
    L.extend(f"- {a}" for a in case["case"].get("assumptions", []))
    L.append("")

    L.append("## Requirements")
    L.append("")
    L.append("| ID | Requirement | Metric | Limit |")
    L.append("|---|---|---|---|")
    for r in reqs:
        L.append(f"| {r['id']} | {r['text']} | `{r['metric']}` | {r['operator']} {r['limit']:g} "
                 f"{r['units']} |")
    L.append("")

    L.append("## Summary across points")
    L.append("")
    head = ["Point"] + ([sweep] if sweep else []) + [r["id"] for r in reqs] + ["Checks"]
    L.append("| " + " | ".join(head) + " |")
    L.append("|" + "---|" * len(head))
    for pt in result["points"]:
        row = [pt["label"]]
        if sweep:
            row.append(f"{pt['parameters'][sweep]:g}")
        for rq in pt["requirements"]:
            row.append(f"{_fmt(rq['value'])} {rq['units']}: **{rq['verdict']}**")
        n_pass = sum(c["status"] == "PASS" for c in pt["checks"])
        row.append(f"{n_pass}/{len(pt['checks'])} {pt['verification_status']}")
        L.append("| " + " | ".join(row) + " |")
    L.append("")

    run_checks = (verification or {}).get("run_checks", [])
    if run_checks:
        L.append("## Run-level checks")
        L.append("")
        L.append("Checks that use several points together (for example mesh convergence).")
        L.append("")
        L.append("| Check | Description | Value | Tolerance | Status |")
        L.append("|---|---|---|---|---|")
        for c in run_checks:
            L.append(f"| {c['id']} | {c['description']} | {c['value']:.3g} | "
                     f"{c['tolerance']:.3g} | {c['status']} |")
        L.append("")

    rows = [(pt["parameters"][sweep], {rq["metric"]: rq["value"] for rq in pt["requirements"]},
             {rq["metric"]: rq["verdict"] for rq in pt["requirements"]})
            for pt in result["points"] if sweep and pt["simulation_status"] == "completed"]
    if len(rows) >= 2 and all(isinstance(r[0], (int, float)) for r in rows):
        from harness.plotting import sweep_figure
        sweep_figure(run_dir / "sweep.png", sweep, rows, reqs,
                     f"{case['case']['name']}: requirement metrics vs {sweep}")
        L.append("![Requirement metrics across the sweep](sweep.png)")
        L.append("")

    L.append("## Point details")
    for pt in result["points"]:
        rel = f"points/{pt['label']}"
        L.append("")
        L.append(f"### {pt['label']}")
        L.append("")
        params = ", ".join(f"{k} = {_fmtv(v)}" for k, v in pt["parameters"].items())
        L.append(f"Parameters: {params}")
        if pt["derived"]:
            derived = ", ".join(f"{k} = {_fmtv(v)}" for k, v in pt["derived"].items())
            L.append("")
            L.append(f"Derived: {derived}")
        L.append("")
        L.append("| Requirement | Result | Limit | Margin | Verdict | Evidence |")
        L.append("|---|---|---|---|---|---|")
        for rq in pt["requirements"]:
            L.append(f"| {rq['id']} | {_fmt(rq['value'])} {rq['units']} | {rq['operator']} "
                     f"{rq['limit']:g} | {_fmt(rq['margin'], 3)} | **{rq['verdict']}** | "
                     f"[point.json]({rel}/point.json) |")
        L.append("")
        if pt["checks"]:
            L.append("| Check | Description | Value | Tolerance | Status |")
            L.append("|---|---|---|---|---|")
            for c in pt["checks"]:
                kind = " (validity)" if c.get("kind") == "validity" else ""
                L.append(f"| {c['id']}{kind} | {c['description']} | {c['value']:.2e} | "
                         f"{c['tolerance']:.0e} | {c['status']} |")
            for fig in sorted((run_dir / "points" / pt["label"]).glob("*.png")):
                L.append("")
                L.append(f"![{pt['label']} {fig.stem}]({rel}/{fig.name})")
        else:
            L.append(f"No verification checks recorded (status: {pt['verification_status']}).")

    for xc_path in sorted(run_dir.glob("cross_check_*.json")):
        xc = read_json(xc_path)
        L.append("")
        L.append(f"## Cross-tool check against `{xc['against']}` ({xc.get('against_model')})")
        L.append("")
        measure = xc.get("measure", "max |x - x_other| / (F/k)")
        L.append(f"Status: **{xc['status']}** (tolerance: {measure} <= "
                 f"{xc['tolerance']:g}). Evidence: [{xc_path.name}]({xc_path.name})")
        L.append("")
        req_metrics = [r["metric"] for r in reqs]
        L.append("| Point | Max rel. diff | " + " | ".join(f"{m} diff" for m in req_metrics)
                 + " | Status |")
        L.append("|" + "---|" * (len(req_metrics) + 3))
        for pt in xc["points"]:
            m = pt.get("metrics", {})
            cells = [f"{m.get(k, {}).get('diff', float('nan')):.2e}" for k in req_metrics]
            L.append(f"| {pt['label']} | {pt.get('max_rel_diff', float('nan')):.2e} | "
                     + " | ".join(cells) + f" | {pt['status']} |")

    L.append("")
    L.append("## Limitations")
    L.append("")
    L.extend(f"- {x}" for x in case["case"].get("limitations", []))
    L.append("- A converged solver run that matches an analytical reference shows that the "
             "equations were solved correctly. It does not show that the equations represent "
             "real hardware.")
    L.append("")
    L.append("## Engineering acceptance")
    L.append("")
    L.append("Pending human review. This report does not accept or reject the design.")
    L.append("")

    out = run_dir / "report.md"
    out.write_text("\n".join(L), encoding="utf-8")
    return out
