"""Looping gallery thumbnails, played while a card is hovered or focused.

    .venv\\Scripts\\python.exe site\\make_thumb_loops.py

Studies with load-step frames (v2/frames.json, written by scripts/make_study_renders.py --frames) get a
loop built from those same frames, fitted to the 800 x 500 thumbnail: every frame in it has already
passed the render checks. Studies with an existing animation use it as it is (LOOPS below). Writes
v2/loops.json, which build_v2.py reads to give each card its loop.
"""
from __future__ import annotations

import json
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
V2 = HERE / "v2"

# studies whose loop is an existing animation (published path)
LOOPS = {"modal": "img/bracket_modes.webp", "suspension": "img/anim_quarter_car.webp", "baseline": "img/anim_msd.webp"}


def fit(im: Image.Image) -> Image.Image:
    im = im.convert("RGBA")
    im.thumbnail((800, 500), Image.LANCZOS)
    canvas = Image.new("RGBA", (800, 500), (0, 0, 0, 0))
    canvas.alpha_composite(im, ((800 - im.width) // 2, (500 - im.height) // 2))
    return canvas


def main() -> dict:
    out = dict(LOOPS)
    frames = json.loads((V2 / "frames.json").read_text(encoding="utf-8"))
    for name, f in frames.items():
        ims = [fit(Image.open(HERE / fr["img"])) for fr in f["frames"]]
        main_k = f["main"]
        durations = [140] * len(ims)
        durations[main_k] = 900                         # hold on the main result
        durations[-1] = max(durations[-1], 900)         # and at the end before looping
        path = V2 / f"loop_{name}.webp"
        ims[0].save(path, save_all=True, append_images=ims[1:], duration=durations, loop=0, quality=80, method=6)
        out[name] = f"v2/loop_{name}.webp"
        print(name, len(ims), "frames", path.stat().st_size // 1024, "KB")
    (V2 / "loops.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    return out


if __name__ == "__main__":
    main()
