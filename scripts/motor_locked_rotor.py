"""Emulate ORNL's locked-rotor test from a motor torque run's saved instantaneous torque (study 7).

usage: python scripts/motor_locked_rotor.py <run dir of a pyleecan_femm_load case>

ORNL (TM-2004/185) fixes the stator currents (Ia, -Ia/2, -Ia/2: a current vector along phase a) and turns the locked
shaft, reporting the largest torque over shaft angle, which includes the torque ripple. The model's sweep holds the
current angle gamma while the rotor turns and saves the torque at 24 rotor positions for each gamma. For each gamma the
saved phase currents give the rotor position at which the current vector lies along +a: those (gamma, position) pairs
lie on one line, the locked-rotor path. Torque along it: a periodic spline in position (60 electrical degrees, the slot
ripple) and a cubic spline in gamma; the maximum is the model's counterpart of ORNL's value.
"""
import json, glob, sys
import numpy as np
from scipy.interpolate import CubicSpline
R = sys.argv[1]
w_deg = 360 * 1000 / 60 * 4                  # electrical degrees per second at 1000 rpm, 4 pole pairs
ornl = {35.355: 74, 53.033: 118, 70.711: 154, 88.388: 199, 106.066: 221, 141.421: 286, 176.777: 337}
for f in sorted(glob.glob(R + "/points/*/point.json"), key=lambda f: float(f.split("-")[-1].split("/")[0].split("\\")[0])):
    d = json.load(open(f)); I = float(d["parameters"]["current_rms_A"]); ops = d["solver_outputs"]["ops"]
    g = np.array([o["gamma_deg"] for o in ops])
    pos_star = []
    for o in ops:                             # rotor electrical angle at which the current vector lies along +a
        t = np.array(o["current_time_s"]); i = np.array(o["current_A"])
        psi = np.degrees(np.unwrap(np.arctan2(np.sqrt(3) / 2 * (i[:, 1] - i[:, 2]), i[:, 0] - (i[:, 1] + i[:, 2]) / 2)))
        th = w_deg * t
        # psi rises linearly with time: solve psi(th) = 0 mod 360
        a, b = np.polyfit(th, psi, 1)
        target = 360 * np.ceil((0 - b) / 360)
        pos_star.append(((target - b) / a) % 360)
    pos_star = np.array(pos_star)
    path = (pos_star + g) % 60                # constant if the rotor turns against gamma one for one
    path2 = (pos_star - g) % 60
    Tm = np.array([o["torque_Nm"] for o in ops])[:, :8]
    per = [CubicSpline(np.arange(9) * 7.5, np.append(Tm[i], Tm[i, 0]), bc_type="periodic") for i in range(len(g))]
    use = path if np.ptp(np.unwrap(np.radians(path * 6)) ) < np.ptp(np.unwrap(np.radians(path2 * 6))) else path2
    sgn = -1 if use is path else +1           # position = c - gamma (sgn -1) or c + gamma (+1)
    c = float(np.degrees(np.angle(np.mean(np.exp(1j * np.radians(use * 6))))) / 6) % 60
    gg = np.linspace(0, 70, 1401)
    T_lr = np.array([CubicSpline(g, [s((c + sgn * x) % 60) for s in per])(x) for x in gg])
    o = ornl[round(I, 3)]; k = T_lr.argmax()
    mean = float(np.mean(np.array([op["torque_Nm"] for op in ops]), axis=1).max())
    print(f"{I*np.sqrt(2):5.0f} A peak: path offset spread {np.ptp(np.unwrap(np.radians(use*6)))/6*180/np.pi:5.2f} deg; mean {mean:6.1f}; "
          f"locked-rotor max {T_lr[k]:6.1f} N m at gamma {gg[k]:4.1f}; ORNL {o}: mean {100*(mean/o-1):+5.1f} %, locked rotor {100*(T_lr[k]/o-1):+5.1f} %")
