"""Build v2 page assets: transparent viewport renders + uniform card thumbnails + scene metadata."""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))
from make_renders import beauty  # noqa: E402

OUT = Path(__file__).parent / "v2"
B = REPO / "build" / "render"


def rgba(scene):
    a = (np.clip(beauty(B / f"{scene}.npz"), 0, 1) * 255).astype(np.uint8)
    return Image.fromarray(a, "RGBA")


def crop_alpha(im, thr=40, pad=0.04):
    a = np.asarray(im)[..., 3]
    ys, xs = np.nonzero(a > thr)
    x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
    p = int(pad * max(x1 - x0, y1 - y0))
    return im.crop((max(0, x0 - p), max(0, y0 - p), min(im.width, x1 + p), min(im.height, y1 + p)))


def fit(im, w, h, bg=None):
    im = im.copy()
    im.thumbnail((w, h), Image.LANCZOS)
    canvas = Image.new("RGBA", (w, h), bg or (0, 0, 0, 0))
    canvas.alpha_composite(im, ((w - im.width) // 2, (h - im.height) // 2))
    return canvas


meta = {}
checks = json.loads((REPO / "portfolio/img/renders.json").read_text(encoding="utf-8"))
flat = {e["scene"]: e for v in checks.values() for e in v}
for scene in ("cantilever", "strap_detail", "fin", "mode1", "mode4", "strap", "mode3", "cad_plate",
              "contact_detail", "duct", "fatigue"):
    im = rgba(scene)
    im = crop_alpha(im, thr=60, pad=0.10)
    im.thumbnail((1400, 900), Image.LANCZOS)
    im.save(OUT / f"vp_{scene}.webp", quality=90, method=6)
    m = json.loads((B / f"{scene}.json").read_text(encoding="utf-8"))
    e = flat.get(scene, {})
    meta[scene] = {k: m.get(k) for k in ("field", "units", "vmin", "vmax", "bands", "band_colors", "title",
                                          "caption", "data_min", "data_max")}
    meta[scene]["volume"] = e.get("volume_check")
    meta[scene]["color"] = e.get("color_check")
    meta[scene]["seconds"] = e.get("seconds")
(OUT / "scenes.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")

# card thumbnails 800x500
thumbs = {
    "fea": ("render", "cantilever"), "strap": ("render", "strap_detail"), "modal": ("render", "mode3"),
    "thermal": ("render", "fin"), "cad": ("render", "cad_plate"),
    "fatigue": ("render", "fatigue"), "contact": ("render", "contact_detail"), "cfd": ("render", "duct"),
    "suspension": ("gif", REPO / "portfolio/img/anim_quarter_car.gif"),
    "baseline": ("gif", REPO / "portfolio/img/anim_msd.gif"),
}
for key, (kind, src) in thumbs.items():
    if kind == "render":
        im = crop_alpha(rgba(src), thr=60, pad=0.06)
        fit(im, 800, 500).save(OUT / f"th_{key}.webp", quality=88, method=6)
    elif kind == "gif":
        im = Image.open(src); im.seek(22 if "quarter" in str(src) else 12)
        fit(im.convert("RGBA"), 800, 500, bg=(252, 252, 251, 255)).save(OUT / f"th_{key}.webp", quality=88, method=6)
    elif src is not None and Path(src).exists():
        im = Image.open(src).convert("RGBA")
        a = np.asarray(im.convert("L")); ys, xs = np.nonzero(a < 235)
        im = im.crop((xs.min(), ys.min(), xs.max() + 1, ys.max() + 1))
        if key == "cfd":   # wide, thin field plot: keep the flow region, drop the axis labels
            im = im.crop((int(0.06 * im.width), int(0.08 * im.height), int(0.86 * im.width), int(0.82 * im.height)))
        fit(im, 800, 500, bg=(252, 252, 251, 255)).save(OUT / f"th_{key}.webp", quality=86, method=6)
    else:
        print("no source for", key)
for f in sorted(OUT.iterdir()):
    print(f.name, f.stat().st_size // 1024, "KB")
