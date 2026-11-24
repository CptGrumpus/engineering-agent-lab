"""Study 7, 18 % diagnosis step 4, item 1: the model's rotor pockets and magnets against the client's lamination drawing
(ORNL/TM-2005/33 Fig. 21, page 32 of Pub57487.pdf, sha256 179407ecf90a), and where the drawn magnet stops put each magnet.

Two steps (PyMuPDF lives in the system Python, matplotlib and scipy in the project venv):
    python scripts/motor_drawing_stops.py extract <Pub57487.pdf> <out dir>
    .venv/Scripts/python.exe scripts/motor_drawing_stops.py measure <out dir> build/elmer/rev5centre.json

extract: the blue (rotor) outline of the page as line segments (Bezier curves as their control polygons), in points.
measure: centre and aspect from an ellipse fit to the rotor OD (6.314 in), segments in mm about the rotor centre; the
best rotation of the model's pocket outline onto the drawing; for every magnet, the distance from each end to the
nearest drawn line inside its thickness band (the stop); writes drawing_stops.json and overlay_pole.png.
"""
import json
import math
import sys

import numpy as np


def extract(pdf, out):
    import fitz
    p = fitz.open(pdf)[31]
    segs = []
    for d in p.get_drawings():
        if d.get("color") == (0.0, 0.0, 1.0):
            for it in d["items"]:
                if it[0] == "l":
                    segs.append((it[1].x, it[1].y, it[2].x, it[2].y))
                elif it[0] == "c":
                    q = [it[1], it[2], it[3], it[4]]
                    segs += [(a.x, a.y, b.x, b.y) for a, b in zip(q[:-1], q[1:])]
    np.save(f"{out}/raw_segs.npy", np.array(segs, float))
    print(len(segs), "segments")


def measure(out, geo_path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from scipy.spatial import cKDTree
    S = np.load(f"{out}/raw_segs.npy")
    P = np.vstack([S[:, :2], S[:, 2:]])
    c0 = np.array([219.137, 228.907])                    # rough centre, refined by the fit
    od = P[np.hypot(*(P - c0).T) > 0.985 * np.hypot(*(P - c0).T).max()]
    A, B, C, D = np.linalg.lstsq(np.column_stack([od[:, 0] ** 2, od[:, 1] ** 2, od[:, 0], od[:, 1]]),
                                 np.ones(len(od)), rcond=None)[0]
    cx, cy = -C / (2 * A), -D / (2 * B)
    F = 1 + A * cx * cx + B * cy * cy
    ax_, by_ = math.sqrt(F / A), math.sqrt(F / B)
    kx, ky = 6.314 / 2 * 25.4 / ax_, 6.314 / 2 * 25.4 / by_
    X = (S[:, [0, 2]] - cx) * kx
    Y = -(S[:, [1, 3]] - cy) * ky
    dense = np.vstack([np.column_stack([np.linspace(x1, x2, max(2, int(math.hypot(x2 - x1, y2 - y1) / 0.02))),
                                        np.linspace(y1, y2, max(2, int(math.hypot(x2 - x1, y2 - y1) / 0.02)))])
                       for (x1, x2), (y1, y2) in zip(X, Y)])
    geo = json.load(open(geo_path))
    outline = {"magnet": [], "void": []}
    for s in geo["surfaces"]:
        if s["kind"] in outline:
            pts = []
            for ln in s["loops"][0]:
                if ln["kind"] == "seg":
                    pts += [ln["b"], ln["e"]]
                else:
                    c = complex(*ln["c"]); z0 = complex(*ln["b"]) - c
                    pts += [[(c + z0 * complex(math.cos(t), math.sin(t))).real,
                             (c + z0 * complex(math.cos(t), math.sin(t))).imag]
                            for t in np.linspace(0, ln["angle"], 12)]
            outline[s["kind"]].append((s, np.array(pts) * 1e3))
    tree = cKDTree(dense)
    void_pts = np.vstack([q for _, q in outline["void"]])
    best = min(((deg, float(np.median(tree.query(void_pts @ np.array(
        [[math.cos(math.radians(deg)), math.sin(math.radians(deg))],
         [-math.sin(math.radians(deg)), math.cos(math.radians(deg))]]))[0])))
                for deg in np.arange(-2, 2.001, 0.05)), key=lambda x: x[1])
    rot = math.radians(best[0])
    Rm = np.array([[math.cos(rot), -math.sin(rot)], [math.sin(rot), math.cos(rot)]])
    ends = {"+": [], "-": []}
    for s, _ in outline["magnet"]:
        V = (np.array([ln["b"] for ln in s["loops"][0]]) * 1e3) @ Rm.T
        c = V.mean(0)
        e = [V[(i + 1) % len(V)] - V[i] for i in range(len(V))]
        L = [float(np.hypot(*v)) for v in e]
        u = e[int(np.argmax(L))] / max(L)
        n = np.array([-u[1], u[0]])
        half_len, half_t = 0.5 * max(L), 0.5 * min(L)
        sv, hv = (dense - c) @ u, (dense - c) @ n
        for sign, key in ((1, "+"), (-1, "-")):
            band = (np.abs(hv) < 0.8 * half_t) & (sign * sv > half_len - 1.0) & (sign * sv < half_len + 6)
            ends[key].append(float((sign * sv[band]).min() - half_len) if band.any() else None)
    res = {"drawing": "ORNL/TM-2005/33 Fig. 21 (Pub57487.pdf p. 32)", "aspect_x_over_y": ax_ / by_,
           "model_rotation_deg": best[0], "pocket_outline_median_distance_mm": best[1],
           "magnet_end_to_stop_mm": ends}
    for key, g in ends.items():
        g = np.array([x for x in g if x is not None])
        res[f"end_{key}_median_mm"] = float(np.median(g))
        res[f"end_{key}_range_mm"] = [float(g.min()), float(g.max())]
    json.dump(res, open(f"{out}/drawing_stops.json", "w"), indent=1)
    print(json.dumps({k: v for k, v in res.items() if k != "magnet_end_to_stop_mm"}, indent=1))
    fig, ax = plt.subplots(figsize=(10, 6.5))
    for (x1, x2), (y1, y2) in zip(X, Y):
        ax.plot([x1, x2], [y1, y2], color="#1f4fd1", lw=0.8)
    for kind, col in (("void", "#e08a00"), ("magnet", "#d1301f")):
        for _, q in outline[kind]:
            q = q @ Rm.T
            ax.plot(*q.T, color=col, lw=0.9)
    ax.set_xlim(-13, 47); ax.set_ylim(50, 82); ax.set_aspect("equal")
    ax.set_xlabel("mm"); ax.set_ylabel("mm")
    ax.set_title("Blue: client drawing (TM-2005/33 Fig. 21). Orange: model pockets. Red: model magnets (revision 5)",
                 fontsize=9)
    fig.tight_layout()
    fig.savefig(f"{out}/overlay_pole.png", dpi=120)


if __name__ == "__main__":
    if sys.argv[1] == "extract":
        extract(sys.argv[2], sys.argv[3])
    else:
        measure(sys.argv[2], sys.argv[3])
