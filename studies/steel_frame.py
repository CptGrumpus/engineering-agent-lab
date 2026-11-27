"""Steel frame study: a single-bay equipment-platform portal to AISC 360-22 (LRFD) by the direct analysis method.

Model:     aisc_portal_frame (validation/aisc_frame.py on validation/frame2d.py: exact second order by stability
           functions; member strengths by validation/aisc360.py; sections from validation/aisc_shapes_subset.json)
Load cases (factored, the client's): gravity w_u on the beam with notional loads N = 0.002 Y (C2-1); gravity with the
           lateral load H_u (notional loads added there too only if the second-order drift ratio exceeds 1.7,
           C2.2b(d)). 80 % stiffness, tau_b checked (C2.3). Service: the beam's live-load deflection (nominal
           stiffness, first order) and the frame's drift under the service lateral load with the service live load on
           the beam (nominal stiffness, second order).
Reference: Example C.1A of the AISC v16.0 Design Examples rerun on every point (the analysis); three Design Examples
           (E.1D, F.1-3B, H.1B: the member checks); Kleinlogel's closed forms for the fixed-base portal (first order);
           the B1-B2 amplified first-order analysis of Appendix 8 beside the exact second-order moments; equilibrium.
Run-level: none (the analysis is exact at its nodes; segment refinement is a point check)
"""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np

from harness.backend_base import Backend, failed
from harness.checks import check
from harness.study import Study
from validation import aisc360 as A
from validation.aisc_frame import portal, tau_b
from validation.frame2d import Frame

PARAMS = ("frame_height_m", "bay_span_m", "column_shape", "beam_shape", "youngs_modulus_MPa", "yield_strength_MPa",
          "base", "factored_gravity_kN_per_m", "factored_lateral_kN", "service_live_kN_per_m", "service_lateral_kN",
          "beam_unbraced_length_m", "column_unbraced_length_weak_m")
# optional (study 28 part 2; absent or 0 / "": rigid knees, no slip, no connection check): knee_stiffness_ratio,
# knee_slip_mrad, knee_connection
SOURCES = ("validation/frame2d.py", "validation/aisc_frame.py", "validation/aisc360.py",
           "validation/aisc_shapes_subset.json", "validation/aisc_connections.py", "validation/flange_plated.py")
KIP_IN, KIP = 112984.829, 4448.2216          # N mm per kip-in, N per kip
N_SEG = 8          # members per column and per beam: moments sampled at 1/8 points (Cb needs the quarter points)


def _member_checks(r, col, beam, E, Fy, H, L, Lb_beam, Lc_col_weak):
    """H1 ratios and shear ratios of both columns and the beam for one analysed load case (N-mm units)."""
    f = r["frame"]
    ends = f.end_forces
    out = {}
    for name, idx in (("left_column", range(0, N_SEG)), ("right_column", range(N_SEG, 2 * N_SEG)),
                      ("beam", range(2 * N_SEG, 3 * N_SEG))):
        idx = list(idx)
        sec, length = (beam, L) if name == "beam" else (col, H)
        m_nodes = [ends[idx[0]][2]] + [-ends[i][5] for i in idx]          # moment at each 1/8 point, end to end
        m_abs = [abs(m) for m in m_nodes]
        Mr, Vr = max(m_abs), max(max(abs(ends[i][1]), abs(ends[i][4])) for i in idx)
        Pr = max(f.axial[i] for i in idx)                                 # compression positive
        if name == "beam":
            Lb, Lcx, Lcy = Lb_beam, L, Lb_beam
        else:
            Lb, Lcx, Lcy = Lc_col_weak, H, Lc_col_weak
        q = N_SEG // 4                                                    # Cb over the unbraced length = the member
        cb = A.cb(Mr, m_abs[q], m_abs[2 * q], m_abs[3 * q]) if Lb >= length - 1e-9 else 1.0
        pc = A.compression(sec, E, Fy, Lcx, Lcy)
        fl = A.flexure(sec, E, Fy, Lb, cb)
        sh = A.shear(sec, E, Fy)
        h1 = A.interaction(max(Pr, 0.0), pc["phiPn"], Mr, fl["phiMn"])
        pns = Fy * (pc["Ae"] if pc["elements"]["web"]["slender"] or pc["elements"]["flange"]["slender"] else sec["A"])
        out[name] = {"Pr_kN": Pr / 1e3, "Mr_kNm": Mr / 1e6, "Vr_kN": Vr / 1e3, "Cb": cb, "phiPn_kN": pc["phiPn"] / 1e3,
                     "phiMn_kNm": fl["phiMn"] / 1e6, "flexure_regime": fl["regime"], "phiVn_kN": sh["phiVn"] / 1e3,
                     "H1_equation": h1["equation"], "H1_ratio": h1["ratio"], "shear_ratio": Vr / sh["phiVn"],
                     "alpha_Pr_over_Pns": max(Pr, 0.0) / pns, "web_slender_in_compression":
                         pc["elements"]["web"]["slender"], "moments_kNm": [m / 1e6 for m in m_nodes]}
    return out


def _knee_checks(r, design: str, col_shape: str, beam_shape: str) -> dict:
    """validation/flange_plated.checks at both knees of one analysed load case (N-mm in, kip-in to the checks)."""
    from validation import flange_plated as fpc

    g = fpc.DESIGNS[design]
    col, beam = A.shape(col_shape), A.shape(beam_shape)
    out = {}
    for k, side in enumerate(("left", "right")):
        Mu = abs(r["beam_end_moments"][k]) / KIP_IN
        Vu, Pu, Vc = abs(r[side]["N"]) / KIP, abs(r["beam_N"]) / KIP, abs(r[side]["V_base"]) / KIP
        rows = fpc.checks(beam, col, g, Mu, Vu, Pu, Vc)
        worst = max(rows, key=lambda x: x["ratio"])
        out[side] = {"Mu_kNm": Mu * KIP_IN / 1e6, "Vu_kN": Vu * KIP / 1e3, "Pu_kN": Pu * KIP / 1e3,
                     "max_ratio": worst["ratio"], "governing": worst["id"],
                     "checks": {x["id"]: round(x["ratio"], 4) for x in rows}}
    return out


def _b1b2(col, beam, E, H, L, w, H_lat, base, springs=None):
    """Appendix 8 approximate second-order analysis (80 % stiffness, as used with the direct analysis method): the
    first-order 'no translation' case (sway held at the beam) and 'lateral translation' case (the holding force
    reversed, plus the lateral loads); B2 = 1 / (1 - P_story / P_e,story), P_e,story = R_M H_L L / Delta_H with R_M
    0.85 (all columns in the moment frame); B1 = C_m / (1 - P_r / P_e1) >= 1 per column, C_m = 0.6 - 0.4 M1 / M2.
    Returns B1, B2, Cm and the amplified column-top moment of the more loaded (right) column, kN m."""
    Es = 0.8 * E

    def frame(hold):                                   # nt: gravity, sway held; lt: lateral loads only
        f = Frame()
        a, b, c, d = f.node(0, 0), f.node(0, H), f.node(L, H), f.node(L, 0)
        f.member(a, b, Es, col["A"], col["Ix"])
        f.member(b, c, Es, beam["A"], beam["Ix"], w=-w if hold else 0.0, spring_i=springs[0] if springs else None,
                 spring_j=springs[1] if springs else None)
        f.member(d, c, Es, col["A"], col["Ix"])
        f.support(a, rz=base != "pinned"); f.support(d, rz=base != "pinned")
        if hold:
            f.support(b, ux=True, uy=False, rz=False)
        return f, b, c

    f, b, c = frame(True)
    f.solve()
    hold = f.reactions[3 * b]                          # force the restraint applies, +x
    m_nt = -f.end_forces[2][5]                         # right column top
    m_nt_base = f.end_forces[2][2]
    p_nt = f.axial[2]
    f, b, c = frame(False)
    f.load(b, fx=H_lat - hold)
    f.solve()
    m_lt = -f.end_forces[2][5]
    drift = (f.U[3 * b] + f.U[3 * c]) / 2
    p_story = w * L
    pe_story = 0.85 * abs(H_lat - hold) * H / abs(drift) if drift else float("inf")
    b2 = 1 / (1 - p_story / pe_story)
    pe1 = math.pi ** 2 * Es * col["Ix"] / H ** 2
    m1, m2 = sorted((m_nt_base, m_nt), key=abs)
    # AISC's M1 / M2 is positive in reverse curvature; with internal (sagging-positive) signs, reverse curvature means
    # end moments of opposite sign, so the AISC ratio is -(m1 / m2) here
    cm = 0.6 - 0.4 * (-(m1 / m2))
    b1 = max(1.0, cm / (1 - p_nt / pe1))
    return {"B1": b1, "B2": b2, "Cm": cm, "M_amplified_kNm": abs(b1 * m_nt + b2 * m_lt) / 1e6,
            "M_nt_kNm": m_nt / 1e6, "M_lt_kNm": m_lt / 1e6}


class PythonSteelFrame(Backend):
    sources = SOURCES

    def solve(self, params, numerics, tolerance_scale=1.0):
        try:
            E, Fy = float(params["youngs_modulus_MPa"]), float(params["yield_strength_MPa"])
            H, L = 1e3 * float(params["frame_height_m"]), 1e3 * float(params["bay_span_m"])
            col, beam = A.to_si(A.shape(params["column_shape"])), A.to_si(A.shape(params["beam_shape"]))
            base = params["base"]
            w_u = float(params["factored_gravity_kN_per_m"])                 # kN/m = N/mm
            H_u = 1e3 * float(params["factored_lateral_kN"])
            Lb_beam = 1e3 * float(params["beam_unbraced_length_m"])
            Lc_weak = 1e3 * float(params["column_unbraced_length_weak_m"])
            kw = dict(H=H, L=L, E=E, col=col, beam=beam, base=base, n_col=N_SEG, n_beam=N_SEG)
            # semi-rigid knees: the spring k = ratio x EI / L of the beam (nominal; x 0.8 in the DAM cases), and a
            # bolt-slip rotation before it engages (study 28 part 2)
            kr = params.get("knee_stiffness_ratio")
            knee = {}
            if kr not in (None, "", 0, 0.0):
                knee = {"knee_k": float(kr) * E * beam["Ix"] / L,
                        "knee_slip": 1e-3 * float(params.get("knee_slip_mrad", 0.0) or 0.0)}
            kw |= knee
            notional = 0.002 * 1.0 * w_u * L                                  # C2-1, alpha 1.0 (LRFD)
            first = portal(w=w_u, H_left=notional, stiffness_factor=0.8, second_order=False, **kw)
            second = portal(w=w_u, H_left=notional, stiffness_factor=0.8, second_order=True, **kw)
            ratio = second["drift"] / first["drift"]
            cases = {"gravity_notional": (second, notional, 0.0),
                     "gravity_lateral": (portal(w=w_u, H_left=H_u + (notional if ratio > 1.7 else 0.0),
                                                stiffness_factor=0.8, second_order=True, **kw),
                                         notional if ratio > 1.7 else 0.0, H_u)}
            checks_by_case, eq = {}, {}
            for name, (r, n_load, lat) in cases.items():
                checks_by_case[name] = _member_checks(r, col, beam, E, Fy, H, L, Lb_beam, Lc_weak)
                R = r["frame"].reactions
                eq[name] = max(abs(R[1::3].sum() - w_u * L) / (w_u * L), abs(R[0::3].sum() + n_load + lat) / (w_u * L))
            w_live = float(params["service_live_kN_per_m"])
            live = portal(w=w_live, stiffness_factor=1.0, second_order=False, **kw)
            ends_uy = (live["frame"].U[3 * N_SEG + 1] + live["frame"].U[3 * (2 * N_SEG) + 1]) / 2
            live_defl = abs(live["beam_mid_uy"] - ends_uy)
            serv = portal(w=w_live, H_left=1e3 * float(params["service_lateral_kN"]), stiffness_factor=1.0,
                          second_order=True, **kw)
            serv1 = portal(w=w_live, H_left=1e3 * float(params["service_lateral_kN"]), stiffness_factor=1.0,
                           second_order=False, **kw)
            b1b2 = _b1b2(col, beam, E, H, L, w_u, H_u, base,
                         springs=cases["gravity_lateral"][0]["knee_springs"])
            seg = portal(w=w_u, H_left=H_u, stiffness_factor=0.8, second_order=True, H=H, L=L, E=E, col=col,
                         beam=beam, base=base, n_col=2, n_beam=2, **knee)
            design = params.get("knee_connection")
            knees = ({c_: _knee_checks(r, design, params["column_shape"], params["beam_shape"])
                      for c_, (r, _, _) in cases.items()} if design else None)
        except Exception as e:  # noqa: BLE001 - recorded as the point's failure
            return failed(f"{type(e).__name__}: {e}")
        gl = cases["gravity_lateral"][0]
        series = {"position_along_member": np.linspace(0, 1, N_SEG + 1)}
        for case_name, mc in checks_by_case.items():
            for member, d in mc.items():
                series[f"M_kNm_{case_name}_{member}"] = np.asarray(d["moments_kNm"])
        outputs = {"member_checks": checks_by_case, "drift_ratio_2nd_1st": ratio, "notional_load_kN": notional / 1e3,
                   "notional_in_lateral_case": ratio > 1.7, "equilibrium_rel": eq, "live_deflection_mm": live_defl,
                   "service_drift_mm": max(abs(serv["drift"]), abs(serv1["drift"])),
                   "service_drift_first_order_mm": abs(serv1["drift"]),
                   "b1b2": b1b2,
                   "exact_right_column_top_kNm": abs(gl["right"]["M_top"]) / 1e6,
                   "segment_check_right_top_kNm": abs(seg["right"]["M_top"]) / 1e6,
                   "frame_dims_mm": [H, L],
                   "knee": None if not knee else {"k_nominal_Nmm_per_rad": knee["knee_k"],
                                                  "slip_rad": knee["knee_slip"],
                                                  "springs_Nmm_per_rad": {c_: r["knee_springs"] for c_, (r, _, _)
                                                                          in cases.items()},
                                                  "rotations_rad": {c_: r["knee_rotations"] for c_, (r, _, _)
                                                                    in cases.items()}},
                   "knee_connection": knees}
        worst = max((d["H1_ratio"], c, m) for c, mc in checks_by_case.items() for m, d in mc.items())
        return {"success": True, "message": f"max H1 {worst[0]:.3f} ({worst[2]}, {worst[1]}); drift ratio {ratio:.3f}",
                "nfev": None, "series": series, "outputs": outputs}


def _kleinlogel_check(params):
    """First-order fixed-base portal against Kleinlogel's closed forms (rigid axially, as the closed forms assume):
    UDL knee moment w l^2 / (6 (k + 2)); lateral base moment H h (3k + 1) / (2 (6k + 1)); k = (Ib / l) / (Ic / h)."""
    E = float(params["youngs_modulus_MPa"])
    H, L = 1e3 * float(params["frame_height_m"]), 1e3 * float(params["bay_span_m"])
    col, beam = A.to_si(A.shape(params["column_shape"])), A.to_si(A.shape(params["beam_shape"]))
    w, Hl = float(params["factored_gravity_kN_per_m"]), 1e3 * float(params["factored_lateral_kN"])
    k = (beam["Ix"] / L) / (col["Ix"] / H)
    errs = []
    for ww, hh, want, pick in ((w, 0.0, w * L * L / (6 * (k + 2)), lambda e: -e[0][5]),
                               (0.0, Hl, Hl * H * (3 * k + 1) / (2 * (6 * k + 1)), lambda e: e[0][2])):
        f = Frame()
        a, b, c, d = f.node(0, 0), f.node(0, H), f.node(L, H), f.node(L, 0)
        f.member(a, b, E, col["A"] * 1e6, col["Ix"]); f.member(b, c, E, beam["A"] * 1e6, beam["Ix"], w=-ww)
        f.member(d, c, E, col["A"] * 1e6, col["Ix"])
        f.support(a); f.support(d); f.load(b, fx=hh); f.solve()
        errs.append(abs(abs(pick(f.end_forces)) - want) / want)
    return max(errs)


def _benchmarks():
    """The analysis and the member checks against the AISC Design Examples (largest relative miss)."""
    s = A.shape
    misses = []
    for so, drift, mc in ((False, 0.181, 124), (True, 0.290, 127)):
        r = portal(H=240.0, L=360.0, E=29000.0, col=s("W12X65"), beam=s("W18X40"), w=0.2, P_tops=(36.0, 36.0),
                   H_left=0.576, base="pinned", stiffness_factor=0.8, second_order=so, P_leaning=144.0)
        misses += [abs(r["drift"] - drift) / drift / 2, abs(abs(r["right"]["M_top"]) / 12 - mc) / mc]   # drift: 2 %
    misses.append(abs(A.compression(s("W14X90"), 29000.0, 50.0, 360.0, 180.0)["phiPn"] - 927) / 927)
    misses.append(abs(A.flexure(s("W18X50"), 29000.0, 50.0, 210.0, 1.30)["phiMn"] / 12 - 288) / 288)
    misses.append(abs(A.interaction(400, 1130, 250, 642, 80.0, 311)["ratio"] - 0.929) / 0.929)
    return max(misses)


class SteelFrameStudy(Study):
    name = "steel_frame"
    models = {"aisc_portal_frame": PythonSteelFrame}
    metrics = frozenset({"max_interaction_ratio", "column_interaction_max", "beam_interaction_max",
                         "shear_ratio_max", "live_deflection_mm", "service_drift_mm", "drift_ratio_2nd_1st",
                         "max_connection_ratio"})
    param_names = PARAMS
    series_file = "moment_diagrams.csv"

    def compute_metrics(self, series, params, case, outputs=None):
        mc = outputs["member_checks"]
        h1 = {(c, m): d["H1_ratio"] for c, ms in mc.items() for m, d in ms.items()}
        return {"max_interaction_ratio": max(h1.values()),
                "column_interaction_max": max(v for (c, m), v in h1.items() if m != "beam"),
                "beam_interaction_max": max(v for (c, m), v in h1.items() if m == "beam"),
                "shear_ratio_max": max(d["shear_ratio"] for ms in mc.values() for d in ms.values()),
                "live_deflection_mm": outputs["live_deflection_mm"], "service_drift_mm": outputs["service_drift_mm"],
                "drift_ratio_2nd_1st": outputs["drift_ratio_2nd_1st"]} | (
            {"max_connection_ratio": max(k["max_ratio"] for c in outputs["knee_connection"].values()
                                         for k in c.values())} if outputs.get("knee_connection") else {})

    def verify_point(self, case, point, pdir: Path, series, backend):
        tol = case["verification"]
        out, p = point["solver_outputs"], point["parameters"]
        b = out["b1b2"]
        alpha = max(d["alpha_Pr_over_Pns"] for ms in out["member_checks"].values() for d in ms.values())
        return [
            check("benchmarks_aisc", "largest relative miss against the AISC Design Examples: C.1A drift (scaled to its "
                  "2 % tolerance) and moments, E.1D, F.1-3B, H.1B", _benchmarks(), tol["benchmark_rel_tol"]),
            check("closed_form_portal", "first-order knee moment (UDL) and base moment (lateral) against Kleinlogel's "
                  "closed forms, axially rigid", _kleinlogel_check(p), tol["closed_form_rel_tol"]),
            check("equilibrium", "largest |sum of reactions + applied loads| / total gravity, both load cases",
                  max(out["equilibrium_rel"].values()), tol["equilibrium_rel_tol"]),
            check("b1b2_vs_exact", "|Appendix 8 B1-B2 amplified moment - exact second-order moment| / exact, right "
                  "column top, gravity + lateral", abs(b["M_amplified_kNm"] - out["exact_right_column_top_kNm"])
                  / out["exact_right_column_top_kNm"], tol["b1b2_rel_tol"]),
            check("segments", "right column top moment with 2 against 8 members per span (exact at nodes: should "
                  "agree to round-off)", abs(out["segment_check_right_top_kNm"] - out["exact_right_column_top_kNm"])
                  / out["exact_right_column_top_kNm"], tol["segment_rel_tol"]),
            check("tau_b", "largest alpha Pr / Pns (C2.3: tau_b = 1 and the 0.8 reduction alone apply up to 0.5)",
                  alpha, 0.5, kind="validity"),
            check("drift_ratio", "second- to first-order drift ratio (Commentary C1 recommends at most 2.5; above 1.7 "
                  "notional loads go into every load case)", out["drift_ratio_2nd_1st"], 2.5, kind="validity"),
        ]


STUDY = SteelFrameStudy()
