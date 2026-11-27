"""Fan rotor critical speeds and unbalance response (study G). Runs in the ROSS environment (~/.venvs/ross, ROSS 3.1).

usage: <ross python> fan_rotor.py params.json out.json

Rotor: solid steel shaft (diameter d, bearing span L, n Timoshenko elements with rotary inertia and gyroscopic
terms), one rigid disc (outer 400 mm, width 25 mm, bored to the shaft) at mid-span, two equal linear bearings
(stiffness kb in x and y, damping cb) at the shaft ends.

Writes: the forward and backward natural frequencies against speed (Campbell), the critical speeds (ROSS's own
intersection search, with whirl direction), the disc's unbalance response over the operating range with API 684's
unbalance U = 6350 W / N_max (g mm; W the rotor mass in kg, N_max in rpm), and three closed-form references computed
on companion models: Jeffcott (massless shaft, rigid supports), the bare shaft on rigid supports (Euler-Bernoulli
pinned-pinned), and the Jeffcott rotor on the case's bearings (series springs).
"""

from __future__ import annotations

import json
import math
import sys
import time
import warnings

warnings.filterwarnings("ignore")

import numpy as np  # noqa: E402
import ross as rs  # noqa: E402

RPM = 2 * math.pi / 60
RIGID = 1e13  # N/m, "rigid" support for the reference models
# optional detail (study 23 part 2): a hub bonded to the shaft under the disc (the shaft elements under it take the
# hub's diameter; the disc's bore is the hub's), and smaller bearing journals at both ends
OPTIONAL = ("hub_diameter_m", "hub_length_m", "journal_diameter_m", "journal_length_m")


def diameters(p) -> list[float]:
    """Each shaft element's outer diameter: the shaft's, the hub's under the hub, the journal's at the ends. The
    hub and journal lengths must be whole numbers of elements (the element nodes fall on their ends)."""
    n, L, d = int(p["n_elements"]), float(p["bearing_span_m"]), float(p["shaft_diameter_m"])
    le = L / n
    out = [d] * n
    for key_d, key_l, where in (("journal_diameter_m", "journal_length_m", "ends"),
                                ("hub_diameter_m", "hub_length_m", "middle")):
        dd, ll = float(p.get(key_d, 0) or 0), float(p.get(key_l, 0) or 0)
        if dd <= 0:
            continue
        k = ll / le
        if abs(k - round(k)) > 1e-9 or round(k) < 1:
            raise ValueError(f"{key_l} {ll} is not a whole number of {le} m elements")
        k = round(k)
        idx = (list(range(k)) + list(range(n - k, n))) if where == "ends" else \
            list(range(n // 2 - k // 2, n // 2 + (k - k // 2)))
        if where == "middle" and k % 2:
            raise ValueError("the hub must span an even number of elements (centred on the disc's node)")
        for i in idx:
            out[i] = dd
    return out


def build(p, *, kb=None, cb=None, disc=True, shaft_rho=None):
    steel = rs.Material(name="steel_shaft", rho=float(p["density_kg_per_m3"]), E=float(p["youngs_modulus_Pa"]),
                        Poisson=float(p["poisson_ratio"]))
    shaft_mat = steel if shaft_rho is None else rs.Material(name="massless_shaft", rho=shaft_rho,
                                                             E=float(p["youngs_modulus_Pa"]),
                                                             Poisson=float(p["poisson_ratio"]))
    n, L, d = int(p["n_elements"]), float(p["bearing_span_m"]), float(p["shaft_diameter_m"])
    if n % 2:
        raise ValueError("n_elements must be even (the disc sits on the mid-span node)")
    shaft = [rs.ShaftElement(L=L / n, idl=0.0, odl=di, material=shaft_mat, shear_effects=True, rotary_inertia=True,
                             gyroscopic=True) for di in diameters(p)]
    bore = float(p.get("hub_diameter_m", 0) or 0) or d
    disks = [rs.DiskElement.from_geometry(n=n // 2, material=steel, width=float(p["disc_width_m"]), i_d=bore,
                                          o_d=float(p["disc_diameter_m"]))] if disc else []
    k = float(p["bearing_stiffness_N_per_m"]) if kb is None else kb
    c = float(p["bearing_damping_Ns_per_m"]) if cb is None else cb
    bearings = [rs.BearingElement(n=0, kxx=k, cxx=c, scale_factor=0.5),
                rs.BearingElement(n=n, kxx=k, cxx=c, scale_factor=0.5)]
    return rs.Rotor(shaft, disks, bearings)


def main(pfile, ofile):
    p = json.loads(open(pfile, encoding="utf-8").read())
    t0 = time.time()
    rotor = build(p)
    n_max = float(p["speed_max_rpm"])
    speeds = np.linspace(0.0, float(p["campbell_max_rpm"]), int(p["campbell_points"]))
    camp = rotor.run_campbell(speeds * RPM, frequencies=int(p["modes"]))
    wd = np.asarray(camp.wd) / RPM          # (speeds, modes), rpm
    whirl = np.asarray(camp.whirl_values)   # 0 forward, 1 backward, 0.5 mixed
    # critical speeds: where each mode's damped frequency crosses the 1x line (wd = running speed), linear between
    # Campbell points; whirl from the nearer point (0 forward, 1 backward, 0.5 mixed)
    crit = []
    for j in range(wd.shape[1]):
        f = wd[:, j] - speeds
        for i in np.nonzero(np.sign(f[:-1]) * np.sign(f[1:]) < 0)[0]:
            s_c = speeds[i] - f[i] * (speeds[i + 1] - speeds[i]) / (f[i + 1] - f[i])
            w_c = whirl[i, j] if abs(s_c - speeds[i]) <= abs(s_c - speeds[i + 1]) else whirl[i + 1, j]
            crit.append({"rpm": float(s_c), "mode": j, "whirl": "forward" if w_c < 0.25 else
                         "backward" if w_c > 0.75 else "mixed"})
    crit.sort(key=lambda c: c["rpm"])
    # ROSS's own search (Newton on each mode, its default speed range) as a cross-check
    try:
        cs = rotor.run_critical_speed(num_modes=int(p["modes"]))
        ross_crit = [{"rpm": float(w / RPM), "whirl": str(wh).lower()}
                     for w, wh in zip(np.atleast_1d(cs._wn), np.atleast_1d(cs.whirl_direction))]
    except RuntimeError as e:
        ross_crit = [{"error": str(e)[:200]}]

    W = float(rotor.m)
    U_gmm = 6350.0 * W / n_max
    resp_speeds = np.linspace(float(p["speed_min_rpm"]), n_max, int(p["response_points"]))
    disc_node = int(p["n_elements"]) // 2
    ur = rotor.run_unbalance_response(node=[disc_node], unbalance_magnitude=[U_gmm * 1e-6], unbalance_phase=[0.0],
                                      speed_range=resp_speeds * RPM)
    # disc displacement amplitude (0-peak) in x and y over the speeds
    resp = np.asarray(ur.forced_resp)       # (dofs, speeds); 6 dof per node in ROSS 3
    ndof = rotor.number_dof
    amp_x = np.abs(resp[ndof * disc_node + 0, :])
    amp_y = np.abs(resp[ndof * disc_node + 1, :])

    # closed-form references on companion models (the uniform rotor: the closed forms know no hub or journals)
    p = {k: v for k, v in p.items() if k not in OPTIONAL}
    d, L, E = float(p["shaft_diameter_m"]), float(p["bearing_span_m"]), float(p["youngs_modulus_Pa"])
    I = math.pi * d ** 4 / 64
    jeff = build(p, kb=RIGID, cb=0.0, shaft_rho=1e-6)
    m_disc = float(jeff.disk_elements[0].m)
    ks = 48 * E * I / L ** 3
    jeff_ross = float(jeff.run_modal(speed=0).wn[0] / RPM)
    jeff_cf = math.sqrt(ks / m_disc) / RPM
    kb = float(p["bearing_stiffness_N_per_m"])
    ser = build(p, cb=0.0, shaft_rho=1e-6)
    ser_ross = float(ser.run_modal(speed=0).wn[0] / RPM)
    ser_cf = math.sqrt(1 / (1 / ks + 1 / (2 * kb)) / m_disc) / RPM
    bare = build(p, kb=RIGID, cb=0.0, disc=False)
    bare_ross = float(bare.run_modal(speed=0).wn[0] / RPM)
    rho = float(p["density_kg_per_m3"])
    bare_cf = (math.pi / L) ** 2 * math.sqrt(E * I / (rho * math.pi * d ** 2 / 4)) / RPM

    out = {"rotor_mass_kg": W, "disc_mass_kg": float(rotor.disk_elements[0].m), "unbalance_g_mm": U_gmm,
           "campbell_rpm": speeds.tolist(), "campbell_wd_rpm": wd.tolist(), "campbell_whirl": whirl.tolist(),
           "critical_speeds": crit, "ross_critical_speeds": ross_crit, "response_rpm": resp_speeds.tolist(), "disc_amp_x_m": amp_x.tolist(),
           "disc_amp_y_m": amp_y.tolist(),
           "ref": {"jeffcott_ross_rpm": jeff_ross, "jeffcott_cf_rpm": jeff_cf, "series_ross_rpm": ser_ross,
                   "series_cf_rpm": ser_cf, "bare_ross_rpm": bare_ross, "bare_cf_rpm": bare_cf,
                   "shaft_stiffness_N_per_m": ks},
           "frequency_0rpm_hz": [float(v) / (2 * math.pi) for v in rotor.run_modal(speed=0).wn[:4]],
           "ross_version": rs.__version__, "wall_s": time.time() - t0}
    open(ofile, "w", encoding="utf-8").write(json.dumps(out))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
