"""Study C: random vibration of the clamped bracket arm (study 4's 7 mm arm) under a base acceleration PSD.

Model:     cadquery_ccx_random (models/fea/bracket_random.py): CadQuery -> Gmsh C3D10 -> CalculiX *FREQUENCY (modes,
           modal stresses, participation factors); the random response by modal superposition in Python, one axis at
           a time (x, y, z), with modal damping acting on the relative velocity.
Responses: tip-centre relative displacement; root stresses by surface extrapolation (0.4 t and 1.0 t from the clamp,
           the IIW hot-spot rule, applied mode by mode, since extrapolation is linear) on the top face and the side
           face; von Mises rms by Segalman's quadratic form (the expected value of the von Mises square); fatigue on
           the root's axial stress (sigma_xx) by Dirlik and by Steinberg's three bands, Miner's sum over the three
           axes, an EN 1993-1-9 S-N curve (detail category a parameter).
Checks:    CalculiX's own harmonic base-motion response against the Python modal sum (with CalculiX's absolute-damping
           term) at every CalculiX frequency; Miles' equation for mode 1; effective mass >= 90 % per axis; the PSD
           integral on two frequency grids; the surface-extrapolated root stress against the beam formula M c / I with
           M from the rotational participation factors; mesh GCI on the requirement metrics (run level).
"""

from __future__ import annotations

import importlib.util
import math
import re
import subprocess
import tempfile
from pathlib import Path

import numpy as np

from harness.backend_base import Backend, failed
from harness.calculix import read_dat_frequency, read_frd
from harness.checks import check
from harness.convergence import describe, discretization_uncertainty
from harness.study import Study

WRITER = "models/fea/bracket_random.py"
G = 9806.65                        # mm/s^2
AXES = ("x", "y", "z")
COMPS = ("SXX", "SYY", "SZZ", "SXY", "SYZ", "SZX")


def _load_writer(path: Path):
    spec = importlib.util.spec_from_file_location("bracket_random_saved", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_W = _load_writer(Path(__file__).resolve().parent.parent / WRITER)
PARAMS = _W.PARAMS + ("psd_g2_per_Hz", "f_low_Hz", "f_high_Hz", "duration_per_axis_s", "yield_MPa",
                      "detail_category_MPa", "clearance_mm")


def _p(params, k):
    return float(params[k])


# ----------------------------------------------------------------------------------------------- CalculiX output
def read_participation(dat: Path) -> np.ndarray:
    """PARTICIPATION FACTORS table of a frequency step: (n_modes, 6) [x, y, z, rx, ry, rz] (rotations about the
    global axes through the origin, here the centre of the clamped face)."""
    lines = Path(dat).read_text(encoding="latin-1").splitlines()
    k = next(i for i, ln in enumerate(lines) if "P A R T I C I P A T I O N   F A C T O R S" in ln)
    rows = []
    for ln in lines[k + 1:]:
        p = ln.split()
        if len(p) == 7 and p[0].isdigit():
            rows.append([float(v) for v in p[1:]])
        elif rows and ln.strip() and not p[0].isdigit():
            break
    return np.array(rows)


def read_harmonic_tip(dat: Path) -> list[dict]:
    """The steady-state steps' TIP displacements: per step {"f_Hz", "re" (n, 3), "im" (n, 3)}; CalculiX prints a real
    and an imaginary block at each frequency, in that order."""
    text = Path(dat).read_text(encoding="latin-1")
    steps = re.split(r"\n\s+S T E P\s+(\d+)\s*\n", text)
    out = []
    for body in steps[2::2]:
        if "displacements (vx,vy,vz) for set TIP" not in body or "E I G E N" in body:
            continue
        blocks = re.findall(r"displacements \(vx,vy,vz\) for set TIP and time\s+(\S+)\s*\n\s*\n\s*\d+\s+(\S+)\s+(\S+)\s+(\S+)",
                            body)
        f = np.array([float(b[0]) for b in blocks])
        v = np.array([[float(x) for x in b[1:]] for b in blocks])
        out.append({"f_Hz": f[0::2], "re": v[0::2], "im": v[1::2]})
    return out


# ------------------------------------------------------------------------------------------- random response
def modal_coords(wn: np.ndarray, gamma: np.ndarray, zeta: float, w: np.ndarray,
                 absolute_damping: bool = False) -> np.ndarray:
    """Modal coordinates per unit base acceleration, (n_modes, n_freq): q = -Gamma / (wn^2 - w^2 + 2 j zeta wn w).
    absolute_damping adds CalculiX's extra forcing 2 j zeta wn Gamma / w (its modal damping acts on the absolute
    velocity under *BASE MOTION), to reproduce its harmonic output."""
    wn, gamma, w = np.asarray(wn)[:, None], np.asarray(gamma)[:, None], np.asarray(w)[None, :]
    num = -gamma + (2j * zeta * wn * gamma / w if absolute_damping else 0.0)
    return num / (wn ** 2 - w ** 2 + 2j * zeta * wn * w)


def freq_grid(fn: np.ndarray, zeta: float, f_lo: float, f_hi: float, n_log: int = 400, n_res: int = 80) -> np.ndarray:
    """Log grid over the band plus dense points across +-5 half-power bandwidths of each mode inside it."""
    f = [np.geomspace(f_lo, f_hi, n_log)]
    for fi in fn:
        if f_lo <= fi <= f_hi:
            bw = 2 * zeta * fi
            f.append(fi + np.linspace(-5, 5, n_res) * bw)
    f = np.unique(np.concatenate(f))
    return f[(f >= f_lo) & (f <= f_hi)]


def integrate(y: np.ndarray, f: np.ndarray) -> float:
    return float(np.trapezoid(y, f))


def vm_mean_square(s: np.ndarray, S: np.ndarray, f: np.ndarray) -> float:
    """E[sigma_vm^2] of a Gaussian stress process: s (6, n_f) complex transfer per unit base acceleration (xx, yy, zz,
    xy, yz, zx), S the base PSD. sigma_vm^2 = s^T Q s, so its mean is the integral of trace(Q Re(s s^H)) S."""
    Q = np.array([[1, -.5, -.5, 0, 0, 0], [-.5, 1, -.5, 0, 0, 0], [-.5, -.5, 1, 0, 0, 0],
                  [0, 0, 0, 3, 0, 0], [0, 0, 0, 0, 3, 0], [0, 0, 0, 0, 0, 3]], dtype=float)
    dens = np.einsum("af,ab,bf->f", s.conj(), Q, s).real
    return integrate(dens * S, f)


def miles_tip_rms(phi_gamma: float, fn: float, zeta: float, S: float) -> float:
    """Relative displacement rms of one mode under a flat base PSD S, integrated 0 to infinity:
    |phi Gamma| sqrt(S / (8 zeta wn^3)) (S per Hz; Miles' equation divided by wn^2)."""
    wn = 2 * math.pi * fn
    return abs(phi_gamma) * math.sqrt(S / (8 * zeta * wn ** 3))


# ----------------------------------------------------------------------------------------------------- fatigue
def ec3_cycles(drange: np.ndarray, dsc: float) -> np.ndarray:
    """EN 1993-1-9 direct-stress S-N curve, detail category dsc (stress range at 2e6 cycles): slope 3 to 5e6, slope
    5 to 1e8, no damage below the cut-off (0.549 dsc). Returns the cycles to failure (inf below the cut-off)."""
    d = np.asarray(drange, dtype=float)
    dD, dL = dsc * (2 / 5) ** (1 / 3), dsc * (2 / 5) ** (1 / 3) * (5 / 100) ** (1 / 5)
    with np.errstate(divide="ignore"):
        n3 = 2e6 * (dsc / d) ** 3
        n5 = 5e6 * (dD / d) ** 5
    return np.where(d >= dD, n3, np.where(d >= dL, n5, np.inf))


def spectral_moments(G_f: np.ndarray, f: np.ndarray) -> tuple[float, float, float, float]:
    return tuple(integrate(f ** k * G_f, f) for k in (0, 1, 2, 4))


def steinberg_damage(m: tuple, T: float, dsc: float) -> float:
    """Three-band: 68.3 % of the zero up-crossings at a 1 sigma amplitude, 27.1 % at 2 sigma, 4.33 % at 3 sigma."""
    m0, _, m2, _ = m
    s, nu0 = math.sqrt(m0), math.sqrt(m2 / m0)
    return float(sum(frac * nu0 * T / ec3_cycles(np.array([2 * k * s]), dsc)[0]
                     for k, frac in ((1, 0.683), (2, 0.271), (3, 0.0433))))


def dirlik_pdf(srange: np.ndarray, m: tuple) -> np.ndarray:
    """Dirlik's probability density of stress ranges from the spectral moments m0, m1, m2, m4."""
    m0, m1, m2, m4 = m
    xm = m1 / m0 * math.sqrt(m2 / m4)
    g = m2 / math.sqrt(m0 * m4)
    D1 = 2 * (xm - g ** 2) / (1 + g ** 2)
    R = (g - xm - D1 ** 2) / (1 - g - D1 + D1 ** 2)
    D2 = (1 - g - D1 + D1 ** 2) / (1 - R)
    D3 = 1 - D1 - D2
    Qd = 1.25 * (g - D3 - D2 * R) / D1
    Z = np.asarray(srange) / (2 * math.sqrt(m0))
    return (D1 / Qd * np.exp(-Z / Qd) + D2 * Z / R ** 2 * np.exp(-Z ** 2 / (2 * R ** 2))
            + D3 * Z * np.exp(-Z ** 2 / 2)) / (2 * math.sqrt(m0))


def dirlik_damage(m: tuple, T: float, dsc: float, n: int = 4000) -> float:
    m0, _, m2, m4 = m
    s = np.linspace(1e-9, 14 * math.sqrt(m0), n)      # ranges to 7 sigma amplitude
    return float(math.sqrt(m4 / m2) * T * integrate(dirlik_pdf(s, m) / ec3_cycles(s, dsc), s))


# ------------------------------------------------------------------------------------------------- the backend
class CadQueryCalculiXRandom(Backend):
    sources = (WRITER,)

    def __init__(self):
        from studies.cantilever import find_freecadcmd

        bin_dir = find_freecadcmd().parent
        self.gmsh, self.ccx = bin_dir / "gmsh.exe", bin_dir / "ccx.exe"
        self._versions: dict = {}

    def prepare(self, source_dir=None, log_dir=None):
        import cadquery

        self.writer = _load_writer(self.source_path(WRITER, source_dir))
        g = subprocess.run([str(self.gmsh), "--version"], capture_output=True, text=True, timeout=60)
        c = subprocess.run([str(self.ccx), "-v"], capture_output=True, text=True, timeout=60)
        self._versions = {"cadquery": cadquery.__version__, "gmsh": (g.stdout + g.stderr).strip().splitlines()[-1],
                          "CalculiX": (c.stdout.strip().splitlines() or ["?"])[-1]}

    def solve(self, params, numerics, tolerance_scale=1.0):
        work = Path(tempfile.mkdtemp(prefix="bracket_random_"))
        keep = ("arm.step", "mesh.geo", "job.inp", "job.sta", "gmsh.log", "ccx.log", "modal_basis.npz")

        def files():
            return {n: work / n for n in keep if (work / n).exists()}

        try:
            volume = self.writer.build_step(params, work / "arm.step")
            self.writer.write_geo(params, work / "mesh.geo")
            g = subprocess.run([str(self.gmsh), "mesh.geo", "-3", "-format", "inp", "-o", "mesh.inp"],
                               cwd=work, capture_output=True, text=True, timeout=1800)
            (work / "gmsh.log").write_text(g.stdout + g.stderr, encoding="utf-8")
            if g.returncode != 0 or not (work / "mesh.inp").exists():
                return failed(f"gmsh failed (exit {g.returncode})") | {"files": files(), "cleanup": work}
            info = self.writer.write_deck(params, work / "mesh.inp", work / "job.inp", _p(params, "f_low_Hz"),
                                          _p(params, "f_high_Hz"), int(numerics.get("harmonic_points", 40)))
            c = subprocess.run([str(self.ccx), "-i", "job"], cwd=work, capture_output=True, text=True,
                               timeout=float(numerics.get("solver_timeout_s", 7200)))
            (work / "ccx.log").write_text(c.stdout[-20000:] + c.stderr, encoding="utf-8")
            if c.returncode != 0 or not (work / "job.frd").exists():
                return failed(f"CalculiX failed (exit {c.returncode}); see ccx.log") | {"files": files(),
                                                                                        "cleanup": work}
            res = random_response(params, numerics, work / "job.dat", work / "job.frd", info)
        except Exception as e:  # noqa: BLE001
            return failed(f"{type(e).__name__}: {e}") | {"files": files(), "cleanup": work}
        out, series = res
        out |= info | {"volume_mm3": volume}
        return {"success": True, "message": (f"{len(out['frequency_Hz'])} modes ({out['frequency_Hz'][0]:.1f} Hz "
                                             f"first); 3 sigma von Mises {out['stress_3sigma_MPa']:.1f} MPa, tip "
                                             f"{out['tip_disp_3sigma_mm']:.3f} mm"),
                "nfev": None, "series": series, "outputs": out, "files": files(), "cleanup": work}

    def tool_versions(self):
        return self._versions


def _face_interp(xy: np.ndarray, vals: np.ndarray, pts: np.ndarray) -> np.ndarray:
    from scipy.interpolate import LinearNDInterpolator

    r = LinearNDInterpolator(xy, vals)(pts)
    if np.isnan(r).any():
        raise ValueError("a hot-spot reading point fell outside the face mesh")
    return r


def random_response(params: dict, numerics: dict, dat: Path, frd_path: Path, info: dict) -> tuple[dict, dict]:
    L, b, h = _p(params, "length_mm"), _p(params, "width_mm"), _p(params, "thickness_mm")
    zeta, S0 = _p(params, "damping_ratio"), _p(params, "psd_g2_per_Hz") * G ** 2
    f_lo, f_hi, T, dsc = _p(params, "f_low_Hz"), _p(params, "f_high_Hz"), _p(params, "duration_per_axis_s"), \
        _p(params, "detail_category_MPa")
    fr = read_dat_frequency(dat)
    fn = np.asarray(fr["frequency_Hz"])
    wn = 2 * np.pi * fn
    Gam = read_participation(dat)
    if len(Gam) != len(fn):
        raise ValueError("participation table and eigenvalues differ in length")
    frd = read_frd(frd_path)
    o = np.argsort(frd["nodes"])
    ids, xyz = frd["nodes"][o], frd["coords"][o]
    nmode = len(fn)
    disp = [blk for name, blk in frd["blocks"] if name == "DISP"][:nmode]
    strs = [blk for name, blk in frd["blocks"] if name == "STRESS"][:nmode]
    tip = int(info["tip_node"])
    phi_tip = np.array([[blk[c][np.flatnonzero(blk["ids"] == tip)[0]] for c in ("D1", "D2", "D3")] for blk in disp])

    # hot-spot reading points: top face (z = h/2) across the width, side face (y = b/2) through the thickness
    def face(mask_fn, cols):
        m = mask_fn(xyz)
        return np.flatnonzero(m), xyz[m][:, cols]
    top_idx, top_xy = face(lambda p: np.isclose(p[:, 2], h / 2, atol=1e-6) & (p[:, 0] < 4 * h), [0, 1])
    side_idx, side_xz = face(lambda p: np.isclose(p[:, 1], b / 2, atol=1e-6) & (p[:, 0] < 4 * h), [0, 2])
    ys = np.linspace(-b / 2, b / 2, 11) * 0.999
    zs = np.linspace(-h / 2, h / 2, 5) * 0.999
    pts_top = [np.column_stack([np.full_like(ys, a * h), ys]) for a in (0.4, 1.0)]
    pts_side = [np.column_stack([np.full_like(zs, a * h), zs]) for a in (0.4, 1.0)]
    # modal stress at every node, in node-id order: (n_nodes, n_modes * 6)
    allS = np.zeros((len(ids), nmode * 6))
    for i, blk in enumerate(strs):
        oo = np.argsort(blk["ids"])
        if not np.array_equal(blk["ids"][oo], ids):
            raise ValueError("stress block nodes differ from the mesh")
        for c, comp in enumerate(COMPS):
            allS[:, i * 6 + c] = blk[comp][oo]

    def hotspot(idx, xy2, pts):
        s04, s10 = (_face_interp(xy2, allS[idx], p) for p in pts)
        hs = 1.67 * s04 - 0.67 * s10                         # IIW linear extrapolation to the clamp line
        return hs.reshape(len(pts[0]), nmode, 6).transpose(0, 2, 1)   # (n_points, 6, n_modes)
    hs_modes = np.concatenate([hotspot(top_idx, top_xy, pts_top), hotspot(side_idx, side_xz, pts_side)])
    hs_where = [f"top y={y:+.2f}" for y in ys / 0.999] + [f"side z={z:+.2f}" for z in zs / 0.999]
    # the modal basis: everything the response needs, for reuse without CalculiX (study H)
    np.savez(Path(dat).parent / "modal_basis.npz", frequency_Hz=fn, participation=Gam, phi_tip=phi_tip,
             hotspot_modal_stress=hs_modes, hotspot_points=np.array(hs_where))

    Iy, Iz = b * h ** 3 / 12, h * b ** 3 / 12
    out = {"frequency_Hz": fn.tolist(), "participation": Gam.tolist(),
           "effective_mass": np.asarray(fr["effective_mass"]).tolist(),
           "total_effective_mass": np.asarray(fr["total_effective_mass"]).tolist(), "hotspot_points": hs_where}
    grids = {"base": freq_grid(fn, zeta, f_lo, f_hi, int(numerics.get("n_log", 400)), int(numerics.get("n_res", 80))),
             "fine": freq_grid(fn, zeta, f_lo, f_hi, 2 * int(numerics.get("n_log", 400)),
                               2 * int(numerics.get("n_res", 80)))}
    series = {"f_Hz": grids["base"]}
    per_axis, dmg_dirlik, dmg_stein = {}, np.zeros(len(hs_where)), np.zeros(len(hs_where))
    for a, ax in enumerate(AXES):
        res = {}
        for gname, f in grids.items():
            w = 2 * np.pi * f
            q = modal_coords(wn, Gam[:, a], zeta, w)                        # (n_modes, n_f)
            u = phi_tip.T @ q                                               # (3, n_f) relative tip displacement
            tip_ms = float(sum(integrate(np.abs(u[k]) ** 2 * S0, f) for k in range(3)))
            s = np.einsum("pcm,mf->pcf", hs_modes, q)                       # (n_points, 6, n_f)
            vm_ms = np.array([vm_mean_square(s[k], S0, f) for k in range(len(hs_where))])
            sxx_psd = np.abs(s[:, 0, :]) ** 2 * S0                          # (n_points, n_f)
            My, Mz = (wn ** 2 * Gam[:, 4]) @ q, (wn ** 2 * Gam[:, 5]) @ q
            res[gname] = {"tip_rms": math.sqrt(tip_ms), "vm_rms": np.sqrt(vm_ms), "sxx_psd": sxx_psd, "f": f,
                          "nom_top_rms": math.sqrt(integrate(np.abs(My) ** 2 * S0, f)) * (h / 2) / Iy,
                          "nom_side_rms": math.sqrt(integrate(np.abs(Mz) ** 2 * S0, f)) * (b / 2) / Iz,
                          "sxx_rms": np.sqrt([integrate(sxx_psd[k], f) for k in range(len(hs_where))]), "u": u}
        r, rf = res["base"], res["fine"]
        mom = [spectral_moments(r["sxx_psd"][k], r["f"]) for k in range(len(hs_where))]
        dD = np.array([dirlik_damage(m, T, dsc) for m in mom])
        dS = np.array([steinberg_damage(m, T, dsc) for m in mom])
        dmg_dirlik += dD
        dmg_stein += dS
        k_top_c = len(ys) // 2                                              # top face, centre line
        k_side_c = len(ys) + len(zs) // 2                                   # side face, mid-thickness
        per_axis[ax] = {"tip_rms_mm": r["tip_rms"], "vm_rms_max_MPa": float(r["vm_rms"].max()),
                        "vm_rms_where": hs_where[int(np.argmax(r["vm_rms"]))],
                        "sxx_rms_top_centre_MPa": float(r["sxx_rms"][k_top_c]),
                        "sxx_rms_side_centre_MPa": float(r["sxx_rms"][k_side_c]),
                        "nominal_top_rms_MPa": r["nom_top_rms"], "nominal_side_rms_MPa": r["nom_side_rms"],
                        "grid_change_tip": abs(rf["tip_rms"] - r["tip_rms"]) / max(r["tip_rms"], 1e-300),
                        "grid_change_vm": float(np.max(np.abs(rf["vm_rms"] - r["vm_rms"])
                                                       / np.maximum(r["vm_rms"], 1e-300))),
                        "dirlik_damage_max": float(dD.max()), "steinberg_damage_max": float(dS.max()),
                        "zero_upcrossings_Hz": float(math.sqrt(mom[int(np.argmax(r["vm_rms"]))][2]
                                                               / mom[int(np.argmax(r["vm_rms"]))][0]))}
        series[f"tip_psd_{ax}_mm2_per_Hz"] = np.sum(np.abs(r["u"]) ** 2, axis=0) * S0
        series[f"sxx_psd_{ax}_MPa2_per_Hz"] = r["sxx_psd"][int(np.argmax(r["vm_rms"]))]
    out["per_axis"] = per_axis
    out["stress_3sigma_MPa"] = 3 * max(v["vm_rms_max_MPa"] for v in per_axis.values())
    out["tip_disp_3sigma_mm"] = 3 * max(v["tip_rms_mm"] for v in per_axis.values())
    out["damage_dirlik"] = float(dmg_dirlik.max())
    out["damage_steinberg"] = float(dmg_stein.max())
    out["damage_where"] = hs_where[int(np.argmax(dmg_dirlik))]
    # Miles, mode 1 (flapwise, z)
    k1 = 0
    out["miles_tip_rms_mm"] = miles_tip_rms(phi_tip[k1, 2] * Gam[k1, 2], fn[k1], zeta, S0)
    f = grids["fine"]
    q1 = modal_coords(wn[:1], Gam[:1, 2], zeta, 2 * np.pi * f)
    out["mode1_tip_rms_mm"] = math.sqrt(integrate(np.abs(phi_tip[k1, 2] * q1[0]) ** 2 * S0, f))
    # CalculiX's harmonic response (absolute displacement, absolute damping) against the modal sum
    harm = read_harmonic_tip(dat)
    errs = []
    for a, hstep in enumerate(harm[:3]):
        w = 2 * np.pi * hstep["f_Hz"]
        qa = modal_coords(wn, Gam[:, a], zeta, w, absolute_damping=True)
        u = phi_tip.T @ qa
        u[a] -= 1 / w ** 2                                                  # plus the base's own motion
        ccx = hstep["re"].T + 1j * hstep["im"].T
        errs.append(float(np.max(np.abs(u - ccx)) / np.max(np.abs(ccx))))
    out["harmonic_max_rel_error"] = errs
    out["harmonic_steps"] = len(harm)
    return out, series


# --------------------------------------------------------------------------------------------------- the study
class BracketRandomStudy(Study):
    name = "bracket_random"
    models = {"cadquery_ccx_random": CadQueryCalculiXRandom}
    metrics = frozenset({"stress_3sigma_MPa", "damage_dirlik", "tip_disp_3sigma_mm", "first_frequency_Hz"})
    param_names = PARAMS
    series_file = "response_psd.csv"
    compare_description = "max relative difference over the response PSD columns"

    def derive(self, params):
        L, b, h = _p(params, "length_mm"), _p(params, "width_mm"), _p(params, "thickness_mm")
        if min(L, b, h) <= 0 or int(params["n_modes"]) < 6:
            raise ValueError("positive dimensions and at least 6 modes")
        return {"base_grms_g": math.sqrt(_p(params, "psd_g2_per_Hz") * (_p(params, "f_high_Hz") - _p(params, "f_low_Hz"))),
                "stress_limit_MPa": _p(params, "yield_MPa") / 1.5}

    def compute_metrics(self, series, params, case, outputs=None):
        return {"stress_3sigma_MPa": outputs["stress_3sigma_MPa"], "damage_dirlik": outputs["damage_dirlik"],
                "tip_disp_3sigma_mm": outputs["tip_disp_3sigma_mm"], "first_frequency_Hz": outputs["frequency_Hz"][0]}

    def verify_point(self, case, point, pdir: Path, series, backend):
        tol = case["verification"]
        p, out = point["parameters"], point["solver_outputs"]
        eff = np.array(out["effective_mass"]).sum(axis=0)[:3] / np.array(out["total_effective_mass"])[:3]
        pa = out["per_axis"]
        nom_err_top = abs(pa["z"]["sxx_rms_top_centre_MPa"] / pa["z"]["nominal_top_rms_MPa"] - 1)
        nom_err_side = abs(pa["y"]["sxx_rms_side_centre_MPa"] / pa["y"]["nominal_side_rms_MPa"] - 1)
        fn = np.array(out["frequency_Hz"])
        checks = [
            check("harmonic_vs_calculix", "max over the 3 axes and CalculiX's frequencies of |modal sum - CalculiX "
                  "harmonic tip displacement| / max |CalculiX| (modal sum with CalculiX's absolute damping and the base "
                  "motion added)", max(out["harmonic_max_rel_error"]) if out["harmonic_steps"] == 3 else float("inf"),
                  tol["harmonic_rel_tol"]),
            check("miles_mode1", "|mode-1 tip rms integrated over the band / Miles' closed form - 1|",
                  abs(out["mode1_tip_rms_mm"] / out["miles_tip_rms_mm"] - 1), tol["miles_rel_tol"]),
            check("effective_mass", "1 - least effective-mass fraction over x, y, z (modes kept)",
                  1 - float(eff.min()), 1 - tol["effective_mass_min"]),
            check("modes_cover_band", "highest mode kept / (1.5 x the band's top frequency), must be >= 1 "
                  "(reported as 1 / that)", (1.5 * _p(p, "f_high_Hz")) / float(fn[-1]), 1.0),
            check("psd_grid", "max over axes of the change in tip rms and hot-spot von Mises rms when the frequency "
                  "grid is doubled", max(max(v["grid_change_tip"], v["grid_change_vm"]) for v in pa.values()),
                  tol["grid_rel_tol"]),
            check("root_stress_vs_beam", "max of |surface-extrapolated root sigma_xx rms / beam M c / I - 1| on the "
                  "top centre (z axis) and the side centre (y axis); M from the rotational participation factors "
                  "(model form: the clamp's Poisson restraint, shear lag)", max(nom_err_top, nom_err_side),
                  tol["beam_rel_tol"]),
        ]
        rv_figure(pdir / "response.png", series, out, p, title=point["label"])
        return checks

    def verify_run_level(self, case, manifest, points):
        if case.get("sweep", {}).get("parameter") != "element_size_mm":
            return [], {}
        tol = case["verification"]
        done = sorted((pt for pt in manifest["points"] if pt["status"] == "completed"),
                      key=lambda pt: pt["parameters"]["element_size_mm"])
        if len(done) < 3:
            return [check("mesh_convergence_gci", "needs >= 3 completed mesh levels", float("inf"), 0.0)], {}
        fine = done[:3]
        hs = tuple(float(pt["parameters"]["element_size_mm"]) for pt in fine)
        checks, detail = [], {"meshes_used": [pt["label"] for pt in fine]}
        for m in ("stress_3sigma_MPa", "tip_disp_3sigma_mm"):
            u = discretization_uncertainty(hs, tuple(pt["metrics"][m] for pt in fine), design_order=2,
                                           noise_floor=float(tol.get("mesh_noise_rel", 1e-5)))
            detail[m] = u
            checks.append(check(f"discretization_{m}", f"relative discretization uncertainty of {m}, {describe(u)}",
                                u["uncertainty"], tol["gci_max"]) | {"metric": m})
        return checks, detail


def rv_figure(path, series, out, p, *, title):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    from harness.plotting import SERIES_1, SERIES_2, SURFACE, TEXT, _style

    f = np.asarray(series["f_Hz"])
    fig, ax = plt.subplots(1, 2, figsize=(12, 4.2), facecolor=SURFACE)
    cols = {"x": TEXT, "y": SERIES_2, "z": SERIES_1}
    for axn in AXES:
        ax[0].loglog(f, np.maximum(np.asarray(series[f"tip_psd_{axn}_mm2_per_Hz"]), 1e-30), color=cols[axn], lw=1.2,
                     label=f"{axn}: rms {out['per_axis'][axn]['tip_rms_mm'] * 1e3:.1f} um")
        ax[1].loglog(f, np.maximum(np.asarray(series[f"sxx_psd_{axn}_MPa2_per_Hz"]), 1e-30), color=cols[axn], lw=1.2,
                     label=f"{axn}: von Mises rms {out['per_axis'][axn]['vm_rms_max_MPa']:.1f} MPa")
    ax[0].set_xlabel("frequency (Hz)")
    ax[0].set_ylabel("tip relative displacement PSD (mm^2/Hz)")
    ax[1].set_xlabel("frequency (Hz)")
    ax[1].set_ylabel("root sigma_xx PSD at the hot spot (MPa^2/Hz)")
    for a in ax:
        a.legend(frameon=False, fontsize=8)
        _style(a)
    fig.suptitle(f"{title}: 3 sigma von Mises {out['stress_3sigma_MPa']:.1f} MPa, tip {out['tip_disp_3sigma_mm']:.3f} mm, "
                 f"damage {out['damage_dirlik']:.2e} (Dirlik)", fontsize=10, color=TEXT)
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)


STUDY = BracketRandomStudy()
