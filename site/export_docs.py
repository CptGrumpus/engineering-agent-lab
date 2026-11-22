"""Export the built page to docs/ for GitHub Pages (the public copy of the dashboard).

    .venv\\Scripts\\python.exe site\\build_v2.py && .venv\\Scripts\\python.exe site\\export_docs.py

Writes docs/index.html with a full HTML document around the page, and copies every image the
page references into docs/img and docs/v2. It fails if a referenced file can't be found, so the
public page never ships with a broken image.
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
DOCS = REPO / "docs"

# where each published folder's files come from, in order of preference
SOURCES = {"img": [REPO / "portfolio" / "img", DOCS / "img"], "v2": [HERE / "v2"]}

HEAD = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="description" content="Sixteen open-source simulation studies, each checked against an independent reference, with a live grader demo and every requirement in one table.">
<meta property="og:type" content="website">
<meta property="og:url" content="https://cptgrumpus.github.io/engineering-agent-lab/">
<meta property="og:title" content="Simulation, proof attached">
<meta property="og:description" content="Sixteen open-source simulation studies, from FEA, CFD and coupled multiphysics to an optimisation loop. Every result is checked against an independent reference before it's called a pass or a fail.">
<meta property="og:image" content="https://cptgrumpus.github.io/engineering-agent-lab/v2/og_card.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="A machined clevis bracket rendered with its stress contours, beside the page headline and its counts of studies, checks and runs">
<meta name="twitter:card" content="summary_large_image">
"""
OG_CARD = "v2/og_card.png"      # referenced by absolute URL in the head, so copied explicitly


def main() -> int:
    page = (HERE / "index.html").read_text(encoding="utf-8")
    refs = sorted(set(re.findall(r'(?:src|href)="((?:img|v2)/[^"#?]+)"', page)) |
                  set(re.findall(r'"(?:img|mesh)": "((?:img|v2)/[^"]+)"', page)) | {OG_CARD})
    missing = []
    for ref in refs:
        folder, name = ref.split("/", 1)
        src = next((d / name for d in SOURCES[folder] if (d / name).exists()), None)
        if src is None:
            missing.append(ref)
            continue
        dst = DOCS / ref
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.resolve() != dst.resolve():
            shutil.copyfile(src, dst)
    if missing:
        raise SystemExit("missing files for the public page: " + ", ".join(missing))
    # the page source starts with <title>; it goes inside <head>, the rest into <body>
    title_end = page.index("</title>") + len("</title>")
    head_extra, body = page[:title_end], page[title_end:]
    style_end = body.index("</style>") + len("</style>")
    doc = HEAD + head_extra + body[:style_end] + "\n</head>\n<body>\n" + body[style_end:] + "\n</body>\n</html>\n"
    (DOCS / "index.html").write_text(doc, encoding="utf-8")
    (DOCS / ".nojekyll").touch()
    print(f"docs/index.html written; {len(refs)} referenced files in place")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
