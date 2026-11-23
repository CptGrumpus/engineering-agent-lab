"""Build our 2004 Prius machine definition from published dimensions (study 7 geometry rebuild). Pyleecan environment.

usage: <pyleecan python> models/motor/build_prius_ornl.py [--steel GRADE] [--out PATH]
  --steel M330-35A (default) writes models/motor/Toyota_Prius_ORNL.json; any other grade writes
  models/motor/Toyota_Prius_ORNL_<GRADE>.json. Prints the table of changes.

Source of every dimension changed here: ORNL/TM-2005/33, "Report on Toyota Prius Motor Thermal Management" (FY 2005),
Fig. 21 "Schematic of Prius motor stator and rotor", report page 25 (PDF page 32),
https://info.ornl.gov/sites/publications/Files/Pub57487.pdf. Only that figure was read: the report's test-data pages
stay closed so that the ORNL performance comparison remains blind.

How the drawing was read (2026-11-21): the labels are vector text (PyMuPDF get_text). The slot inset gives the depth
1.320 in (bore to the end of the round), the opening 0.076 in, the tooth tip 0.040 in, the slot width 0.124 in and the
round end 0.222 in diameter. The main view's vector outline, scaled by fitting a circle to the bore (6.375 in), agrees:
0.076 in at the bore, 0.125 in just above the tooth tip widening linearly to 0.218 in at r = 4.35 in, slot end at
r = 4.51 in (depth 1.32 in), tooth 0.300 in near the bore (the drawing's own "0.300" label).

Rotor and magnets (ROTOR_CHANGES, MAGNET_CHANGES), checked 2026-11-21 late evening:
- Fig. 21 draws each pole's V pocket as a vector outline. The figure is stretched 1.1 % in x against y in the PDF (its
  rotor OD outline is an ellipse, x/y 1.0114); corrected by scaling x and y separately to the labelled 6.314 in OD.
  Measured on all 8 poles: arm angle to tangential 17.4 deg (sd 0.13; Pyleecan 17.46), pocket thickness 6.80 mm
  (sd 0.03; Pyleecan 6.50), outer apex 10.65 mm below the OD (Pyleecan H0 10.96), inner apex 17.76 mm (Pyleecan
  17.78). So the inner edge is Pyleecan's and the extra thickness is on the air-gap side: H0 = 10.65, H3 = 6.80, and
  W0 = 41.21 mm to keep the arm angle. In HoleM50 the magnet fills the pocket thickness (6.80 mm).
- Bridge 1.45 mm: ORNL/TM-2004/120 (PM Motor Parametric Design Analyses, July 2004), Table 5.3 and Fig. 5.2, which
  marks this dimension as "Bridge"; Fig. 21's red label 0.056 in (1.42 mm) agrees. Pyleecan: H1 = 1.5 mm.
- Magnet material: ORNL/TM-2004/137 (design report) Fig. 14, ORNL's measured B-H line of a Prius magnet sample
  (opened by the user's decision, 2026-11-21; a material property, not motor performance), digitized from 906 pixels
  of ORNL's fitted line: Br 1.243 T (12.43 kG at H = 0, an extrapolation: the measured points span -7.2 to -4.7 kOe),
  recoil permeability 1.129, Hcb -876 kA/m. Pyleecan: Br 1.24 T, 1.05. Temperature not stated: taken as 20 C.
- Not adopted: TM-2004/120's magnet 19.24 x 5.31 mm (MagWid 38.48 mm for the pair) and Br 1.12 T. A 5.31 mm magnet
  in the drawing's 6.78 mm pocket would need a different hole model; the size change nets about -0.4 % on back-EMF
  (scratch sensitivity), and 1.12 T matches 1.24 T at about 120 C with the material's -0.1 %/K, so it is probably a
  hot value. Recorded as alternatives.

Laminations (LAMINATIONS, user's decision 2026-11-22 ~00:40): one stand-in grade for every property, M330-35A. ORNL
gives the thickness (0.014 in = 0.36 mm, ORNL/TM-2004/137) but not the grade; M330-35A is a standard 0.35 mm EN 10106
grade with full public data, mid-range in its class. Its B-H curve, density, resistivity and modulus replace the
M400-50A (0.5 mm) that came with Pyleecan's file and was never chosen. Runs before 2026-11-22 used M400-50A; it stays
available as --steel M400-50A, the "inherited steel" side of the sensitivity. FEMM's magnetostatic solve reads only
the B-H points (Pyleecan passes no lamination thickness or stacking factor), so the B-H curve is the change that moves
the results. The curve above 1.8 T is our extrapolation (see _tail): the datasheet stops at 1.8 T, and only regions
driven harder than that (tooth tips at high current) depend on it.

What stays Pyleecan's: the magnet width (18.9 mm) and the V's other parameters, the winding (9 turns per coil; the thermal report's text gives 9 conductor bundles per slot) and the stack (83.82 mm =
3.3 in, which ORNL's 2004 design report ORNL/TM-2004/137 confirms).
"""

from __future__ import annotations

import argparse
import csv
import math
from os.path import join
from pathlib import Path

IN = 0.0254
SOURCE = "ORNL/TM-2005/33 Fig. 21"
HERE = Path(__file__).resolve().parent
OUT = HERE / "Toyota_Prius_ORNL.json"
DEFAULT_STEEL = "M330-35A"
MU0 = 4e-7 * math.pi

# (object path, attribute, value in inches, how the drawing gives it)
CHANGES = [
    ("stator", "Rext", 10.600 / 2, "stator OD 10.600 in"),
    ("stator", "Rint", 6.375 / 2, "stator bore 6.375 in"),
    ("rotor", "Rext", 6.314 / 2, "rotor OD 6.314 in"),
    ("rotor", "Rint", 4.356 / 2, "rotor ID 4.356 in"),
    ("shaft", "Drsh", 4.356, "shaft diameter = rotor ID 4.356 in"),
    ("stator.slot", "W0", 0.076, "slot opening 0.076 in"),
    ("stator.slot", "H0", 0.040, "tooth tip height 0.040 in"),
    ("stator.slot", "H1", 0.0, "flat shoulder under the tooth tip (inset)"),
    ("stator.slot", "W1", 0.124, "slot width 0.124 in at the shoulder (main view 0.1246 in)"),
    ("stator.slot", "W2", 0.222, "round end 0.222 in diameter"),
    ("stator.slot", "R1", 0.222 / 2, "round end radius = 0.222 in / 2"),
    ("stator.slot", "H2", 1.320 - 0.040, "slot depth 1.320 in minus the tooth tip 0.040 in (SlotW11: depth = H0 + H1 + H2)"),
]


# rotor pocket (HoleM50): (object path, attribute, value in metres, source label, how it was obtained)
ROTOR_CHANGES = [
    ("rotor.hole.0", "H3", 6.80e-3, "6.80 mm", "Fig. 21 pocket thickness, measured from the vector outline on 8 poles (sd 0.03 mm) after correcting the figure's 1.1 % x/y stretch; the magnet fills it in HoleM50"),
    ("rotor.hole.0", "H0", 10.65e-3, "10.65 mm", "Fig. 21 outer apex depth below the rotor OD (8 poles, sd 0.03 mm, stretch corrected); the inner apex then sits at 17.78 mm, as drawn (17.76)"),
    ("rotor.hole.0", "H1", 1.45e-3, "1.45 mm", "ORNL/TM-2004/120 Table 5.3 'Bridge' (Fig. 21 red label 0.056 in = 1.42 mm)"),
    ("rotor.hole.0", "W0", 41.206e-3, "41.21 mm", "solved so the arm stays at Fig. 21's 17.4 deg to tangential (8 poles, sd 0.13 deg) with H0 and H1 above (HoleM50 ties the arm angle to H0, H1 and W0)"),
]
# magnet material, both magnets of the pole: (attribute of mat_type.mag, value, source label, how it was obtained)
MAGNET_CHANGES = [
    ("Brm20", 1.243, "1.243 T", "ORNL/TM-2004/137 Fig. 14, measured line of a Prius magnet sample, digitized (B at H = 0)"),
    ("mur_lin", 1.129, "1.129", "ORNL/TM-2004/137 Fig. 14, slope of the same line"),
]


def _tail(h_last, b_last, js, h_points):
    """B-H points above the datasheet's last point: the polarization J = B - mu0 H approaches the saturation value js
    as J = js - (js - J_last) (H_last / H). With js = 2.0 T this joins M330-35A's last segment with a continuous slope
    (k = 1.01 from the 1.7-1.8 T secant). js 2.0 T: the textbook saturation polarization of iron with about 3 % Si
    (2.03 T at 3.2 % Si), the alloy range of 0.35 mm non-oriented grades. An assumption, not datasheet data."""
    j_last = b_last - MU0 * h_last
    return [(h, js - (js - j_last) * h_last / h + MU0 * h) for h in h_points]


def _csv_rows(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(line for line in f if not line.startswith("#")))


def _m330_35a(js=2.0):
    """M330-35A, Tata Steel 'Typical data' sheet (Oct 2009), models/motor/materials/M330-35A_tata_2009.csv. js: the
    saturation polarization of the extrapolated tail (2.0 T; 2.05 T only for the tail sensitivity case)."""
    csv_name = "M330-35A_tata_2009.csv"
    rows = _csv_rows(HERE / "materials" / csv_name)
    bh = [(0.0, 0.0)] + [(float(r["H_50Hz_A_per_m"]), float(r["B_T"])) for r in rows if r["H_50Hz_A_per_m"]]
    h_last, b_last = bh[-1]
    bh += _tail(h_last, b_last, js, [12e3, 15e3, 20e3, 30e3, 45e3, 70e3, 100e3, 150e3, 220e3, 300e3])
    return {
        "name": "M330-35A" if js == 2.0 else f"M330-35A (tail Js {js:g} T)",
        "path": csv_name,
        "bh": bh,
        "bh_source": (f"Tata Steel M330-35A typical data (Oct 2009), H at 50 Hz, 0.1-{b_last:.1f} T; above {b_last:.1f} T "
                      f"extrapolated (build_prius_ornl._tail, saturation polarization {js:g} T)"),
        "Wlam": 0.35e-3,  # EN 10106 nominal thickness (ORNL: 0.36 mm)
        "rho": 7650.0,  # kg/m^3, EN 10106 conventional density for M330-35A
        "elec_rho": 0.42e-6,  # ohm m, Tata sheet (42 uOhm cm)
        "Ex": 200e9,  # Pa, Tata sheet, rolling direction (210 GPa transverse)
    }


TAIL_H = [12e3, 15e3, 20e3, 30e3, 45e3, 70e3, 100e3, 150e3, 220e3, 300e3]


def _m250_35a():
    """M250-35A, Tata Steel 'Typical data' sheet (June 2008), models/motor/materials/M250-35A_tata_2008.csv. Bracketing
    grade (lower loss, higher Si: lower permeability above 1.3 T than M330-35A)."""
    csv_name = "M250-35A_tata_2008.csv"
    rows = _csv_rows(HERE / "materials" / csv_name)
    bh = [(0.0, 0.0)] + [(float(r["H_50Hz_A_per_m"]), float(r["B_T"])) for r in rows if r["H_50Hz_A_per_m"]]
    h_last, b_last = bh[-1]
    bh += _tail(h_last, b_last, 2.0, TAIL_H)  # 1.7-1.8 T secant gives k = 1.17 here; the k = 1 form is kept for all
    return {
        "name": "M250-35A",
        "path": csv_name,
        "bh": bh,
        "bh_source": (f"Tata Steel M250-35A typical data (June 2008), H at 50 Hz, 0.1-{b_last:.1f} T; above {b_last:.1f} T "
                      "extrapolated (build_prius_ornl._tail, saturation polarization 2.0 T)"),
        "Wlam": 0.35e-3,
        "rho": 7600.0,  # kg/m^3, EN 10106 conventional density for M250-35A (not on the sheet)
        "elec_rho": 0.55e-6,  # ohm m, Tata sheet (55 uOhm cm)
        "Ex": 185e9,  # Pa, Tata sheet, rolling direction (200 GPa transverse)
    }


def _powercore_190y390():
    """thyssenkrupp powercore traction 035-190Y390 (Aug 2025), models/motor/materials/powercore_035-190Y390_tk_2025.csv.
    Bracketing grade (high strength). The sheet gives the polarization J, so B = J + mu0 H."""
    csv_name = "powercore_035-190Y390_tk_2025.csv"
    rows = _csv_rows(HERE / "materials" / csv_name)
    bh = [(0.0, 0.0)] + [(float(r["H_50Hz_A_per_m"]), float(r["J_T"]) + MU0 * float(r["H_50Hz_A_per_m"]))
                         for r in rows if r["H_50Hz_A_per_m"]]
    h_last, b_last = bh[-1]
    bh += _tail(h_last, b_last, 2.0, TAIL_H)
    return {
        "name": "powercore 035-190Y390",
        "path": csv_name,
        "bh": bh,
        "bh_source": (f"thyssenkrupp powercore 035-190Y390 typical data (Aug 2025), J at 50 Hz, 0.5-1.8 T, B = J + mu0 H; "
                      f"above B = {b_last:.3f} T extrapolated (build_prius_ornl._tail, saturation polarization 2.0 T)"),
        "Wlam": 0.35e-3,
        "rho": 7600.0,  # kg/m^3, on the sheet
        "elec_rho": None,  # not on the sheet: Pyleecan's value is kept (unused by the magnetostatic solve)
        "Ex": None,  # not on the sheet: Pyleecan's value is kept (the overspeed stress does not depend on E)
    }


# lamination grades: name -> function returning the data. Grades without an entry keep Pyleecan's file data (only
# M400-50A, which came with it).
LAMINATIONS = {"M330-35A": _m330_35a, "M250-35A": _m250_35a, "190Y390": _powercore_190y390,
               # sensitivity of the deep-saturation tail (user's decision 2026-11-22 morning): M330-35A with Js 2.05 T
               "M330-35A-Js205": lambda: _m330_35a(js=2.05)}


def _set_lamination(m, grade):
    """Replace both laminations' material with the given grade; returns rows for the table."""
    if grade == "M400-50A":
        return []
    data = LAMINATIONS[grade]()
    bh = data["bh"]
    hs, bs = [h for h, _ in bh], [b for _, b in bh]
    if any(b2 <= b1 for b1, b2 in zip(bs, bs[1:])) or any(h2 <= h1 for h1, h2 in zip(hs, hs[1:])):
        raise ValueError(f"{grade}: B-H curve not strictly increasing")
    import numpy as np
    from pyleecan.Classes.ImportMatrixVal import ImportMatrixVal

    rows = []
    for lam in (m.stator, m.rotor):
        mat = lam.mat_type
        old_name = mat.name
        mat.name, mat.path = data["name"], data["path"]
        mat.mag.BH_curve = ImportMatrixVal(value=np.array(bh))
        mat.mag.Wlam = data["Wlam"]
        # mur_lin is used only by linear models; take the curve's secant at 1.0 T
        mat.mag.mur_lin = float(1.0 / np.interp(1.0, bs, hs) / MU0)
        mat.struct.rho = data["rho"]
        if data["Ex"] is not None:
            mat.struct.Ex = data["Ex"]
        if data["elec_rho"] is not None:
            mat.elec.rho = data["elec_rho"]
        rows.append((f"{'stator' if lam is m.stator else 'rotor'}.mat_type", old_name, data["name"], data["bh_source"]))
    return rows


def _materials(m):
    yield m.stator.mat_type
    yield m.rotor.mat_type
    if m.shaft and m.shaft.mat_type:
        yield m.shaft.mat_type
    for hole in m.rotor.hole:
        for mag in (hole.get_magnet_dict().values()):          # HoleM50 or HoleUD (revision 4)
            if mag is not None:
                yield mag.mat_type
    w = m.stator.winding
    if w and w.conductor:
        for k in ("cond_mat", "ins_mat"):
            if getattr(w.conductor, k, None):
                yield getattr(w.conductor, k)


def _get(m, path):
    for part in path.split("."):
        m = m[int(part)] if part.isdigit() else getattr(m, part)
    return m


DESIGN_MAGNET = {"width": 19.24e-3, "thickness": 5.31e-3,
                 "source": "ORNL/TM-2004/120 Table 5.3: magnet width 38.48 mm for the pair (19.24 each), thickness 5.31 mm"}
PLACEMENTS = ("outer", "centre", "inner")
# Study 7 revision 5 (client data pack, validation/motor_ornl/CLIENT_DATA.md): the magnet as measured on the hardware
CLIENT_MAGNET = {"width": 18.9e-3, "thickness": 6.5e-3, "length": 83.1e-3,
                 "source": "ORNL/TM-2010/253 Table 2.7 (2004 Prius): one magnet 83.1 x 18.9 x 6.5 mm, 10.2 cm3, 77 g"}
CLIENT_MAGNET_MATERIAL = [
    ("Brm20", 1.255, "1.255 T", "ORNL/TM-2010/253 Fig. 2.72, 2004 Prius motor magnet, hysteresisgraph, 12.55 kG at 20 C"),
    ("alpha_Br", -0.0010, "-0.10 %/C", "ORNL/TM-2010/253 Fig. 2.72: 12.55 kG at 20 C to about 10.9 kG at 150 C"),
    ("mur_lin", 1.129, "1.129", "ORNL/TM-2004/137 Fig. 14, slope of the measured line (unchanged)"),
]


def design_magnet(m, placement: str, spec: dict = DESIGN_MAGNET, tag: str = "study 7 revision 4") -> list:
    """Study 7 revision 4: the magnet at its design size inside the drawn pocket. Sets HoleM50's magnet width (W4) to
    the design width, converts the hole to HoleUD, and replaces each magnet rectangle (pocket thickness H3) by a
    design-thickness magnet plus air strip(s): against the outer (air-gap side) face, centred, or against the inner
    face. The magnetization directions are kept (HoleM50's). Returns rows for the change table."""
    from pyleecan.Classes.Segment import Segment
    from pyleecan.Classes.SurfLine import SurfLine
    from pyleecan.Functions.labels import HOLEM_LAB, HOLEV_LAB

    if placement not in PLACEMENTS:
        raise ValueError(f"placement must be one of {PLACEMENTS}")
    hole = m.rotor.hole[0]
    rows = [("rotor.hole.0.W4", hole.W4, spec["width"], f"{spec['width'] * 1e3:.2f} mm: {spec['source']}")]
    hole.W4 = spec["width"]
    hole.check()
    H, t = hole.H3, spec["thickness"]
    if not 0 < t < H:
        raise ValueError(f"design magnet thickness {t} must be inside the pocket thickness {H}")
    a = {"outer": 0.0, "centre": (H - t) / 2, "inner": H - t}[placement]
    pd = hole._comp_point_coordinate()

    def rect(p1, p2, p3, p4, label):
        pts = [p1, p2, p3, p4]
        lines = [Segment(pts[i], pts[(i + 1) % 4]) for i in range(4)]
        return SurfLine(line_list=lines, label=label, point_ref=sum(pts) / 4)

    ud = hole.convert_to_UD()
    new = []
    for s in ud.surf_list:
        if HOLEM_LAB not in s.label:
            new.append(s)
            continue
        pts = [ln.get_begin() for ln in s.get_lines()]
        z8b, z8c, z4 = pd["Z8b"], pd["Z8c"], pd["Z4"]
        if sum(p.imag for p in pts) > 0:                                        # the mirrored magnet (magnet_1)
            z8b, z8c, z4 = z8b.conjugate(), z8c.conjugate(), z4.conjugate()
        if min(abs(p - z8c) for p in pts) > 1e-9 or min(abs(p - z4) for p in pts) > 1e-9:
            raise RuntimeError(f"magnet surface {s.label} does not match HoleM50's corner points")
        u = (z4 - z8c) / abs(z4 - z8c)                                         # unit vector into the rotor
        if abs(abs(z4 - z8c) - H) > 1e-9:
            raise RuntimeError("pocket thickness from the corners differs from H3")
        new.append(rect(z8b + a * u, z8c + a * u, z8c + (a + t) * u, z8b + (a + t) * u, s.label))
        if a > 0:
            new.append(rect(z8b, z8c, z8c + a * u, z8b + a * u, s.label.replace(HOLEM_LAB, HOLEV_LAB) + "-strip-out"))
        if a + t < H - 1e-12:
            new.append(rect(z8b + (a + t) * u, z8c + (a + t) * u, z8c + H * u, z8b + H * u,
                            s.label.replace(HOLEM_LAB, HOLEV_LAB) + "-strip-in"))
    ud.surf_list = new
    m.rotor.hole[0] = ud
    rows.append(("rotor.hole.0 (HoleUD)", H, t, f"{t * 1e3:.2f} mm magnet in the {H * 1e3:.2f} mm pocket, placed "
                 f"{placement}; air strip {(H - t) * 1e3:.2f} mm: {spec['source']} ({tag})"))
    return rows


def build(steel=DEFAULT_STEEL, out=None, br=None, magnet=None, client_magnet=None, airgap_mm=None):
    if magnet and client_magnet:
        raise ValueError("--design-magnet and --client-magnet are alternatives")
    if steel != "M400-50A" and steel not in LAMINATIONS:
        raise ValueError(f"unknown lamination grade {steel}; known: M400-50A, {', '.join(LAMINATIONS)}")
    stem = "Toyota_Prius_ORNL" + ("" if steel == DEFAULT_STEEL else f"_{steel}") + (
        "" if br is None else f"_Br{br:.4f}".replace(".", "p")) + ("" if magnet is None else f"_mag531{magnet}") + (
        "" if client_magnet is None else f"_rev5{client_magnet}") + ("" if airgap_mm is None else f"_gap{airgap_mm:.3f}".replace(".", "p"))
    out = Path(out) if out else (OUT if stem == "Toyota_Prius_ORNL" else HERE / f"{stem}.json")
    from pyleecan.definitions import DATA_DIR
    from pyleecan.Functions.load import load

    m = load(join(DATA_DIR, "Machine", "Toyota_Prius.json"))
    rows = []
    for path, attr, inches, note in CHANGES:
        obj = _get(m, path)
        old, new = getattr(obj, attr), inches * IN
        setattr(obj, attr, new)
        rows.append((f"{path}.{attr}", old, new, note))
    for path, attr, value, label, note in ROTOR_CHANGES:
        obj = _get(m, path)
        old = getattr(obj, attr)
        setattr(obj, attr, value)
        rows.append((f"{path}.{attr}", old, value, f"{label}: {note}"))
    if airgap_mm is not None:
        # the bore stays the drawing's; the rotor OD moves, and the pocket (H0, H1 measured from the OD) moves with it
        old = m.rotor.Rext
        m.rotor.Rext = m.stator.Rint - airgap_mm * 1e-3
        rows.append(("rotor.Rext", old, m.rotor.Rext, f"air gap {airgap_mm:.3f} mm (ORNL/TM-2010/253 Table 2.7 states "
                     "0.730 mm; the drawing's bore and OD give 0.775 mm)"))
    mags = [mag for hole in m.rotor.hole for mag in (hole.magnet_0, hole.magnet_1)]
    if client_magnet is not None and br is not None:
        raise ValueError("--br (calibration) is not combined with the client data")
    changes = CLIENT_MAGNET_MATERIAL if client_magnet is not None else MAGNET_CHANGES if br is None else [
        (a, br, f"{br:.4f} T", "POST-TEST CALIBRATION (study 7, hypothesis A): remanence scaled so the open-circuit "
         "back-EMF matches ORNL's routine back-EMF test; not a design input") if a == "Brm20" else (a, v, l, n)
        for a, v, l, n in MAGNET_CHANGES]
    for attr, value, label, note in changes:
        old = {getattr(mag.mat_type.mag, attr) for mag in mags}
        if len(old) != 1:
            raise ValueError(f"the magnets disagree on {attr}: {old}")
        for mag in mags:
            setattr(mag.mat_type.mag, attr, value)
        rows.append((f"magnets.mat_type.mag.{attr}", old.pop(), value, f"{label}: {note}"))
    if magnet is not None:
        rows += design_magnet(m, magnet)
    if client_magnet is not None:
        rows += design_magnet(m, client_magnet, CLIENT_MAGNET, "study 7 revision 5, client data")
        for hole in m.rotor.hole:                     # 83.1 mm: recorded; FEMM's 2D solve uses the stack length
            for mag in hole.get_magnet_dict().values():
                mag.Lmag = CLIENT_MAGNET["length"]
    rows += _set_lamination(m, steel)
    m.name = stem
    m.desc = (f"2004 Toyota Prius: Pyleecan's Toyota_Prius.json with the stator, rotor and slot dimensions of {SOURCE}, "
              "the pocket thickness from the same figure, the bridge from ORNL/TM-2004/120 and the magnet B-H line from "
              f"ORNL/TM-2004/137 Fig. 14, laminations {steel} (see models/motor/build_prius_ornl.py); magnet width "
              "and winding unchanged.")
    m.stator.slot.check()
    m.rotor.hole[0].check()
    # Pyleecan's bundled file carries absolute material paths from its authors' computer; keep the file
    # names only, so no personal path is committed (tests/test_privacy.py)
    for mat in {id(x): x for x in _materials(m)}.values():
        if mat.path and ("/" in mat.path or "\\" in mat.path):
            mat.path = mat.path.replace("\\", "/").rsplit("/", 1)[-1]
    m.save(str(out))
    return m, rows, out


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--steel", default=DEFAULT_STEEL, help=f"lamination grade (default {DEFAULT_STEEL})")
    ap.add_argument("--out", help="output path (default: see the module docstring)")
    ap.add_argument("--br", type=float, help="post-test calibration only: magnet remanence at 20 C (T), replacing the "
                    "design value; writes Toyota_Prius_ORNL_Br<value>.json")
    ap.add_argument("--design-magnet", choices=PLACEMENTS, help="study 7 revision 4: the design magnet (19.24 x 5.31 mm, "
                    "TM-2004/120) in the drawn pocket, placed against its outer face, centred or against its inner face; "
                    "writes Toyota_Prius_ORNL_mag531<placement>.json")
    ap.add_argument("--client-magnet", choices=PLACEMENTS, help="study 7 revision 5: the measured magnet (18.9 x 6.5 mm, "
                    "ORNL/TM-2010/253) and its measured material (1.255 T at 20 C, -0.10 %%/C) in the drawn pocket; writes "
                    "Toyota_Prius_ORNL_rev5<placement>[_gap<mm>].json")
    ap.add_argument("--airgap-mm", type=float, help="air gap (mm): the rotor OD moves, the bore stays")
    args = ap.parse_args()
    m, rows, out = build(args.steel, args.out, args.br, args.design_magnet, args.client_magnet, args.airgap_mm)
    print("| Parameter | Pyleecan file | Ours | Difference | Source |")
    print("|---|---|---|---|---|")
    for name, old, new, note in rows:
        if isinstance(new, str):
            print(f"| {name} | {old} | {new} | | {note} |")
            continue
        diff = "" if not old else f"{100 * (new - old) / old:+.1f} %"
        k, u = (1, "") if name.startswith("magnets.") else (1e3, " mm")
        print(f"| {name} | {k * old:.3f}{u} | {k * new:.3f}{u} | {diff} | {note} |")
    s = m.stator.slot
    print(f"\nair gap {1e3 * (m.stator.Rint - m.rotor.Rext):.4f} mm; slot depth H0+H1+H2 {1e3 * (s.H0 + s.H1 + s.H2):.3f} mm; "
          f"slot area {1e6 * s.comp_surface():.1f} mm^2, active {1e6 * s.comp_surface_active():.1f} mm^2")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
