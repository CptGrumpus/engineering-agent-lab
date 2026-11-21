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
<meta name="description" content="Twelve open-source simulation studies, each checked against an independent reference, with a live grader demo and every requirement in one table.">
"""


def main() -> int:
    page = (HERE / "index.html").read_text(encoding="utf-8")
    refs = sorted(set(re.findall(r'(?:src|href)="((?:img|v2)/[^"#?]+)"', page)) |
                  set(re.findall(r'"img": "((?:img|v2)/[^"]+)"', page)))
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
