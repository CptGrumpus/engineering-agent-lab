"""Cut the round field map out of the motor's published figure, on a transparent background, for mock-up B's hero.

A mock-up shortcut: it only crops and masks site/v2/fig_motor_field.webp, so it shows nothing the figure doesn't.
In the real build, scripts/make_field_map.py should export this view itself.
"""
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
im = Image.open(HERE.parent / "v2" / "fig_motor_field.webp").convert("RGB")
a = np.asarray(im).astype(int)
h, w, _ = a.shape
# the stator's coloured disc: saturated pixels in the left half of the figure
sat = (a.max(axis=2) - a.min(axis=2)) > 60
sat[:, w // 2:] = False
cols = np.where(sat.sum(axis=0) > 0.02 * h)[0]
rows = np.where(sat.sum(axis=1) > 0.02 * w)[0]
x0, x1, y0, y1 = cols.min(), cols.max(), rows.min(), rows.max()
# the enlarged pole beside it reaches into the left half, so the width is no guide: take the diameter from the
# height and the centre from the disc's left edge, then check the disc's right edge is where that puts it
r = (y1 - y0) / 2
cx, cy = x0 + r, (y0 + y1) / 2
top = int(np.argmax(sat[:, int(cx)]))             # the disc's top, on the centre's column
left = int(np.argmax(sat[int(cy), :]))            # and its left edge, on the centre's row
edge = int(np.argmax(sat[int(cy - 0.7071 * r) + 6, :]))   # a third point, on the 45 degree chord
assert abs(top - y0) < 0.02 * r and abs(left - x0) < 0.02 * r, ("not a disc", x0, left, y0, top)
assert abs(edge - (cx - 0.7071 * r)) < 0.03 * r, ("not a disc", edge, cx - 0.7071 * r)
box = tuple(int(v) for v in (cx - r, cy - r, cx + r, cy + r))
cut = im.crop(box).convert("RGBA")
mask = Image.new("L", cut.size, 0)
ImageDraw.Draw(mask).ellipse((2, 2, cut.size[0] - 3, cut.size[1] - 3), fill=255)
c = np.asarray(cut).astype(int)
yy, xx = np.mgrid[:c.shape[0], :c.shape[1]]
# a label's white box overlaps the disc's rim. The figure is one pole solved and repeated, so the field a quarter
# turn away is the same field: fill the box from there
box_px = (c[:, :, :3].min(axis=2) > 236) & (np.hypot(xx - r, yy - r) > 0.8 * r) & (np.asarray(mask) > 0)
if box_px.any():
    by, bx = np.where(box_px)
    sl = (slice(max(by.min() - 4, 0), by.max() + 5), slice(max(bx.min() - 4, 0), bx.max() + 5))
    assert cut.size[0] == cut.size[1]
    turned = np.rot90(np.asarray(cut))
    inside = np.asarray(mask)[sl] > 0             # past the rim both are paper, and the mask drops it anyway
    assert (turned[sl][:, :, :3].min(axis=2) <= 236)[inside].all(), "the quarter-turn patch has a label in it too"
    patched = np.asarray(cut).copy()
    patched[sl] = turned[sl]
    cut = Image.fromarray(patched)
    c = patched.astype(int)
# the shaft bore is drawn in the figure's paper colour: make it see-through
bore = (c[:, :, :3].min(axis=2) > 236) & (np.hypot(xx - r, yy - r) < 0.5 * r)
m = np.asarray(mask).copy()
m[bore] = 0
cut.putalpha(Image.fromarray(m))
(HERE / "img").mkdir(exist_ok=True)
cut.save(HERE / "img" / "motor_field_cut.webp", quality=92)
print("disc", box, "->", cut.size)
