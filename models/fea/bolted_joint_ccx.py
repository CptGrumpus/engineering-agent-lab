"""Preloaded bolted joint: two clamped plates with friction contact, then a side load to slip.

Half model (symmetry plane y = 0, the side load acts along x) of the clamped region around one
bolt: two circular steel plates, outer diameter D_A, hole d_h, thicknesses t1 (top) and t2
(bottom), stacked with the interface at z = 0. Structured polar hex mesh written here (r graded
from the hole, a node ring at the washer radius d_W / 2), C3D8I elements; node and element
numbers are offset by 1 000 000 for the bottom plate.

Bolt: represented by its clamp force, a uniform pressure on the washer annuli (top face of the
top plate, bottom face of the bottom plate), equal and opposite: F_V / 2 on the half model.
Interface: CalculiX surface-to-surface penalty contact (linear pressure-overclosure), Coulomb
friction mu with a stick slope; the slave surface (top plate) is adjusted onto the master so the
contact is closed from the start.

Supports: y = 0 plane held in y (symmetry); bottom plate outer rim held in x; top plate outer
rim held in x in step 1 and pushed along x in step 2; one unloaded node on the bottom plate's
outer rim held in z (the clamp forces balance, so its reaction is zero).
Steps: 1 preload; 2 rim displacement ramped to slip_displacement_mm in equal increments, the
reaction of the top rim printed every increment; contact pressure at the end of step 1.
"""

from __future__ import annotations

import numpy as np

PARAMS = ("plate_outer_diameter_mm", "hole_diameter_mm", "washer_diameter_mm", "top_thickness_mm",
          "bottom_thickness_mm", "youngs_modulus_MPa", "poisson_ratio", "preload_N", "friction_coefficient",
          "element_size_mm", "contact_stiffness_factor", "stick_slope_factor", "slip_displacement_mm",
          "slip_increments")
OFFSET = 1_000_000


class JointMesh:
    def __init__(self, p: dict):
        s = float(p["element_size_mm"])
        self.rh, self.rw, self.R = (float(p[k]) / 2 for k in ("hole_diameter_mm", "washer_diameter_mm",
                                                              "plate_outer_diameter_mm"))
        n1 = max(2, round((self.rw - self.rh) / s))
        # outer ring: geometric grading so the first element matches the washer-ring size
        h0 = (self.rw - self.rh) / n1
        n2 = max(4, round(np.log(1 + (self.R - self.rw) * 0.15 / h0) / np.log(1.15)))
        g = 1.15
        grow = h0 * g ** np.arange(n2)
        grow *= (self.R - self.rw) / grow.sum()
        self.r = np.concatenate([self.rh + h0 * np.arange(n1 + 1), self.rw + np.cumsum(grow)])
        self.r[-1] = self.R
        self.i_w = n1                                         # node ring at the washer radius
        self.nt = 2 * max(6, round(np.pi * self.rw / s / 2))  # elements over the half circle
        self.th = np.pi * np.arange(self.nt + 1) / self.nt
        self.t1, self.t2 = float(p["top_thickness_mm"]), float(p["bottom_thickness_mm"])
        self.nz1 = max(2, round(self.t1 / s))
        self.nz2 = max(2, round(self.t2 / s))
        self.nr = len(self.r) - 1

    def z(self, plate):
        return (self.t1 * np.arange(self.nz1 + 1) / self.nz1 if plate == "top"
                else -self.t2 + self.t2 * np.arange(self.nz2 + 1) / self.nz2)

    def nid(self, plate, i, j, k):
        off = 0 if plate == "top" else OFFSET
        return off + 1 + i + (self.nr + 1) * (j + (self.nt + 1) * k)

    def eid(self, plate, i, j, k):
        off = 0 if plate == "top" else OFFSET
        return off + 1 + i + self.nr * (j + self.nt * k)

    def nz(self, plate):
        return self.nz1 if plate == "top" else self.nz2

    def nodes(self, plate):
        out = []
        for k, z in enumerate(self.z(plate)):
            for j, t in enumerate(self.th):
                for i, r in enumerate(self.r):
                    out.append((self.nid(plate, i, j, k), r * np.cos(t), r * np.sin(t), z))
        return out

    def elements(self, plate):
        out = {}
        for k in range(self.nz(plate)):
            for j in range(self.nt):
                for i in range(self.nr):
                    n = lambda a, b, c: self.nid(plate, a, b, c)
                    out[self.eid(plate, i, j, k)] = [n(i, j, k), n(i + 1, j, k), n(i + 1, j + 1, k), n(i, j + 1, k),
                                                     n(i, j, k + 1), n(i + 1, j, k + 1), n(i + 1, j + 1, k + 1),
                                                     n(i, j + 1, k + 1)]
        return out


def _rows(ids, per=12):
    ids = list(ids)
    return [", ".join(str(v) for v in ids[s:s + per]) for s in range(0, len(ids), per)]


def write_deck(p: dict, m: JointMesh) -> str:
    E, nu = float(p["youngs_modulus_MPa"]), float(p["poisson_ratio"])
    FV, mu = float(p["preload_N"]), float(p["friction_coefficient"])
    h_el = float(p["element_size_mm"])
    K = float(p["contact_stiffness_factor"]) * E / h_el
    lam = float(p["stick_slope_factor"]) * E / h_el
    # washer pressure from the meshed face areas (flat quads with chord edges: the polygonal annulus
    # is sin(dtheta)/dtheta smaller than the true one, 0.4 % at 1 mm), so the half model carries
    # exactly F_V / 2
    a_mesh = sum(0.5 * (m.r[i + 1] ** 2 - m.r[i] ** 2) * np.sin(m.th[j + 1] - m.th[j])
                 for j in range(m.nt) for i in range(m.i_w))
    pw = float(FV / 2 / a_mesh)
    out = ["*HEADING", "Preloaded bolted joint, half model, friction contact", "*NODE, NSET=NALL"]
    for plate in ("top", "bottom"):
        out += [f"{n}, {x:.12e}, {y:.12e}, {z:.12e}" for n, x, y, z in m.nodes(plate)]
    for plate in ("top", "bottom"):
        out += [f"*ELEMENT, TYPE=C3D8I, ELSET=E{plate.upper()}"]
        out += [f"{e}, " + ", ".join(str(v) for v in n) for e, n in m.elements(plate).items()]
    sym = [m.nid(pl, i, j, k) for pl in ("top", "bottom") for k in range(m.nz(pl) + 1) for j in (0, m.nt)
           for i in range(m.nr + 1)]
    rim = {pl: [m.nid(pl, m.nr, j, k) for k in range(m.nz(pl) + 1) for j in range(m.nt + 1)] for pl in ("top", "bottom")}
    top_washer = [m.nid("top", i, j, m.nz1) for j in range(m.nt + 1) for i in range(m.i_w + 1)]
    bot_washer = [m.nid("bottom", i, j, 0) for j in range(m.nt + 1) for i in range(m.i_w + 1)]
    iface_line = [m.nid("top", i, 0, 0) for i in range(m.nr + 1)]
    out += ["*NSET, NSET=NSYM"] + _rows(sym) + ["*NSET, NSET=NRIMTOP"] + _rows(rim["top"])
    out += ["*NSET, NSET=NRIMBOT"] + _rows(rim["bottom"]) + ["*NSET, NSET=NWASHTOP"] + _rows(top_washer)
    out += ["*NSET, NSET=NWASHBOT"] + _rows(bot_washer) + ["*NSET, NSET=NIFACE"] + _rows(iface_line)
    # z support on an unloaded node (outer rim): a node under the nut pressure carried 41 N
    out += ["*NSET, NSET=NZFIX", str(m.nid("bottom", m.nr, 0, 0))]
    out += ["*SURFACE, NAME=SSLAVE, TYPE=ELEMENT"]
    out += [f"{m.eid('top', i, j, 0)}, S1" for j in range(m.nt) for i in range(m.nr)]
    out += ["*SURFACE, NAME=SMASTER, TYPE=ELEMENT"]
    out += [f"{m.eid('bottom', i, j, m.nz2 - 1)}, S2" for j in range(m.nt) for i in range(m.nr)]
    out += ["*MATERIAL, NAME=STEEL", "*ELASTIC", f"{E!r}, {nu!r}",
            "*SOLID SECTION, ELSET=ETOP, MATERIAL=STEEL", "*SOLID SECTION, ELSET=EBOTTOM, MATERIAL=STEEL",
            "*CONTACT PAIR, INTERACTION=SI, TYPE=SURFACE TO SURFACE, ADJUST=1.e-6", "SSLAVE, SMASTER",
            "*SURFACE INTERACTION, NAME=SI", "*SURFACE BEHAVIOR, PRESSURE-OVERCLOSURE=LINEAR", f"{K!r}, 1.0",
            "*FRICTION", f"{mu!r}, {lam!r}",
            "*BOUNDARY", "NSYM, 2, 2, 0.", "NRIMBOT, 1, 1, 0.", "NRIMTOP, 1, 1, 0.", "NZFIX, 3, 3, 0."]
    dload = [f"{m.eid('top', i, j, m.nz1 - 1)}, P2, {pw!r}" for j in range(m.nt) for i in range(m.i_w)]
    dload += [f"{m.eid('bottom', i, j, 0)}, P1, {pw!r}" for j in range(m.nt) for i in range(m.i_w)]
    ctrl = ["*CONTROLS, PARAMETERS=FIELD", "1.e-7, 1.e-5"]
    out += ["*STEP, NLGEOM=NO, INC=1000", "*STATIC", "0.1, 1.0, 1.e-6, 0.25"] + ctrl + ["*DLOAD"] + dload
    out += ["*NODE PRINT, NSET=NWASHTOP, FREQUENCY=1000", "U", "*NODE PRINT, NSET=NWASHBOT, FREQUENCY=1000", "U",
            "*NODE PRINT, NSET=NZFIX, TOTALS=ONLY, FREQUENCY=1000", "RF",
            "*CONTACT FILE, FREQUENCY=1000", "CSTR",
            "*END STEP"]
    n = int(p["slip_increments"])
    out += ["*STEP, NLGEOM=NO, INC=1000", "*STATIC, DIRECT", f"{1.0 / n!r}, 1.0"] + ctrl
    out += ["*BOUNDARY", f"NRIMTOP, 1, 1, {float(p['slip_displacement_mm'])!r}"]
    out += ["*NODE PRINT, NSET=NRIMTOP, TOTALS=ONLY, FREQUENCY=1", "RF",
            "*NODE PRINT, NSET=NRIMBOT, TOTALS=ONLY, FREQUENCY=1", "RF",
            "*END STEP"]
    return "\n".join(out) + "\n"
