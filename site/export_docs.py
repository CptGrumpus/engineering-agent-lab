"""Put every image the built site references into docs/ (the public copy, served by GitHub Pages).

    .venv\\Scripts\\python.exe site\\build_v2.py && .venv\\Scripts\\python.exe site\\export_docs.py

build_v2.py writes the pages (docs/*.html) and the shared stylesheet and scripts (docs/assets/). This script
reads every page, copies each image, mesh or frame it references into docs/img and docs/v2, and fails if
one can't be found, so the public site never ships with a broken image.
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
DOCS = REPO / "docs"
SITE_URL = "https://cptgrumpus.github.io/engineering-agent-lab/"

# where each published folder's files come from, in order of preference
SOURCES = {"img": [REPO / "portfolio" / "img", DOCS / "img"], "v2": [HERE / "v2"]}


def main() -> int:
    refs = set()
    pages = sorted(DOCS.glob("*.html"))
    for page in pages:
        text = page.read_text(encoding="utf-8")
        refs |= set(re.findall(r'(?:src|href|data-loop)="((?:img|v2)/[^"#?]+)"', text))
        refs |= set(re.findall(r'"(?:img|mesh)": "((?:img|v2)/[^"]+)"', text))
        # preview cards are referenced by absolute address in the head
        refs |= set(re.findall(r'content="' + re.escape(SITE_URL) + r'((?:img|v2)/[^"]+)"', text))
    missing = []
    for ref in sorted(refs):
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
        raise SystemExit("missing files for the public site: " + ", ".join(missing))
    (DOCS / ".nojekyll").touch()
    print(f"{len(pages)} pages in docs/; {len(refs)} referenced files in place")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
