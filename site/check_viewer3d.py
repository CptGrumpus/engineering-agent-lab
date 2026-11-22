"""Check the page's interactive 3D view the same way the Blender renders are checked.

Serves docs/ locally, opens every page in headless Chrome (check_viewer3d.mjs), turns on the 3D view
on each study page and, for every result with a mesh, takes a lit and an unlit frame from four angles. Each pair then goes
through the render pipeline's own checks (scripts/make_renders.py): the unlit frame's part pixels must
be legend colours (99.5 %, away from anti-aliased edges), and the lit frame must read as the right band (check_legibility, the same 2 %
limit). Fails on any page error. Needs node and Chrome; run after build_v2.py and export_docs.py:

    .venv\\Scripts\\python.exe site\\check_viewer3d.py
"""
from __future__ import annotations

import base64
import functools
import http.server
import io
import json
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
sys.path.insert(0, str(REPO / "scripts"))
sys.path.insert(0, str(HERE))
import make_mesh3d  # noqa: E402
import make_renders as mr  # noqa: E402

CHROME = Path("C:/Program Files/Google/Chrome/Application/chrome.exe")


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def on_legend(flat_png: Path, band_colors) -> float:
    """Fraction of the unlit frame's part pixels that are legend colours, as in the render's colour check,
    except that the browser anti-aliases band boundaries (Blender's check pass is not anti-aliased): a
    pixel counts only where it and its four neighbours have the same colour and full opacity."""
    a = np.asarray(Image.open(flat_png).convert("RGBA")).astype(int)
    rgb, op = a[..., :3], a[..., 3] == 255
    same = np.zeros(op.shape, bool)
    c = rgb[1:-1, 1:-1]
    same[1:-1, 1:-1] = (op[1:-1, 1:-1] & op[:-2, 1:-1] & op[2:, 1:-1] & op[1:-1, :-2] & op[1:-1, 2:]
                        & np.all(c == rgb[:-2, 1:-1], -1) & np.all(c == rgb[2:, 1:-1], -1)
                        & np.all(c == rgb[1:-1, :-2], -1) & np.all(c == rgb[1:-1, 2:], -1))
    ref = np.round(np.asarray(band_colors)[:, :3] * 255)
    px = rgb[same]
    return float((np.abs(px[:, None, :] - ref[None]).max(-1).min(-1) <= mr.COLOR_TOL).mean())


def main() -> int:
    handler = functools.partial(Quiet, directory=str(REPO / "docs"))
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        pages = json.loads((REPO / "docs" / "pages.json").read_text(encoding="utf-8"))
        out = subprocess.run(["node", str(HERE / "check_viewer3d.mjs"), f"http://127.0.0.1:{srv.server_port}/",
                              str(CHROME), ",".join(pages["viewer"]), ",".join(pages["all"])],
                             capture_output=True, text=True, timeout=1500, check=True).stdout
    finally:
        srv.shutdown()
    res = json.loads(out)
    ok = not res["errors"]
    for e in res["errors"]:
        print("page error:", e)
    tmp = Path(tempfile.mkdtemp())
    missing = set(make_mesh3d.SCENES) - set(res["frames"])
    if missing:
        print("no 3D frames for:", ", ".join(sorted(missing)))
        ok = False
    for vid, views in res["frames"].items():
        meta = json.loads((REPO / "site/v2/scenes.json").read_text(encoding="utf-8"))[vid]
        for k, v in enumerate(views):
            stem = tmp / f"{vid}{k}"
            for kind, key in (("beauty", "lit"), ("flat", "flat")):
                Image.open(io.BytesIO(base64.b64decode(v[key].split(",", 1)[1]))).save(f"{stem}_{kind}.png")
            stem.with_suffix(".json").write_text(json.dumps({"band_colors": meta["band_colors"]}), encoding="utf-8")
            col = on_legend(Path(f"{stem}_flat.png"), meta["band_colors"])
            leg = mr.check_legibility(stem.with_suffix(".npz"))
            good = col >= mr.COLOR_PASS and leg["passed"]
            ok &= good
            print(f"{vid:12s} view {k}: {col:.2%} on the legend (limit {mr.COLOR_PASS:.1%}), "
                  f"{leg['misread']:.2%} misread (limit {leg['limit']:.0%}) {'ok' if good else 'FAIL'}")
    print("3D view checks", "passed" if ok else "FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
