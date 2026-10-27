"""P-13 op amp offset at the demodulator (vos in series with IN+ of U2 and U4).

Reads sim-runs/P13_vos/P13_vos.csd. The run used lia_v3_fast.cir with vampl = 0.2 V
(as circuits/lia_v3_fast_P10a0.cir), 0.15 s, output capacitors 1 uF (tau = 10 ms),
.STEP PARAM vos LIST -25u 0 25u (sorted, see docs/simulation-quirks.md), probes
V(VX), V(VY). The step values are matched by section.step_value.

Sign: the netlist has "V_VOSX N00695 N00695P {vos}". In SPICE, V(N00695) - V(N00695P)
= vos, so the op amp input N00695P sits at the switch output minus vos. In both
switch states the output then shifts by -2 vos (with R1 = R2). The entry expected
+2 vos. The check below therefore uses -2 vos from the netlist and reports the
entry value as well.

Settled value: time-weighted trapezoid mean over the last 20 whole periods of 517 Hz
(38.68 ms, from 111.32 ms to 150 ms), on raw PSpice points with interpolated ends.
The settling bias is removed with the P-08 model (V_ss = (m - 2.5 V F) / (1 - F)).

Model offset at vos = 0: the residual of the measured VX against the ideal value
(2.5 V - 2A/pi) and of VY against the P-08 model (ideal Y timing error of 0.18 deg,
126 ns lag and slew term, see docs/sim-results/P-08.md). The residual is also given
as an equivalent input offset, residual / (-2).

Run from the project root:
    python docs/sim-results/scripts/P-13_vos.py
"""

import math
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools"))
from csdf import read_csdf  # noqa: E402

CSD = ROOT / "sim-runs/P13_vos/P13_vos.csd"
PLOT = ROOT / "docs/sim-results/plots/P-13_vos.png"

F = 517.0
T = 1.0 / F
A = 0.2                  # Vampl, V
MID = 2.5                # reference, V
T_DELAY_Y = 482.6e-6     # Y reference delay, s
N_PER = 20
TAU = 10e3 * 1e-6        # R3 x C1 = 10 kOhm x 1 uF
PASS_LIMIT_UV = 2.0      # entry pass limit, uV

# P-08 model constants (docs/sim-results/P-08.md)
D_DEG = 360.0 * (T / 4 - T_DELAY_Y) / T     # 0.1785 deg
DELTA_DEG = 360.0 * 126e-9 / T              # 126 ns constant lag, 0.0234 deg
C_SLEW = 0.457e-3 / 2.0 ** 2                # V per V^2, from 0.457 mV at 2 V


def k_amp(a):
    return 2.0 * a / math.pi


def ideal_vx(a):
    return MID - k_amp(a)


def model_vy(a):
    return MID - k_amp(a) * math.sin(math.radians(D_DEG - DELTA_DEG)) + C_SLEW * a * a


def window_mean(t, y, t0, t1):
    inside = (t > t0) & (t < t1)
    tt = np.concatenate(([t0], t[inside], [t1]))
    yy = np.concatenate(([np.interp(t0, t, y)], y[inside], [np.interp(t1, t, y)]))
    return float(np.trapezoid(yy, tt) / (t1 - t0))


def settle_factor(t0, tw, tau):
    return (tau / tw) * (1 - math.exp(-tw / tau)) * math.exp(-t0 / tau)


def settled(sec):
    t = sec.x
    tend = float(t[-1])
    tw = N_PER * T
    t0 = tend - tw
    tp0 = t0 - tw
    f = settle_factor(t0, tw, TAU)
    out = {"vos": sec.step_value, "F": f, "points": len(t)}
    for name, key in (("V(VX)", "vx"), ("V(VY)", "vy")):
        y = sec[name]
        m = window_mean(t, y, t0, tend)
        prior = window_mean(t, y, tp0, t0)
        out[key + "_raw"] = m
        out[key + "_dprior"] = m - prior
        out[key] = (m - MID * f) / (1 - f)
    out["t0"] = t0
    out["t_end"] = tend
    return out


def main():
    secs = read_csdf(str(CSD))
    res = [settled(s) for s in secs]
    res.sort(key=lambda r: r["vos"])
    by = {round(r["vos"], 9): r for r in res}
    zero = by[0.0]

    print(f"Window: {N_PER} periods = {N_PER*T*1e3:.4f} ms, from {zero['t0']*1e3:.4f} ms to "
          f"{zero['t_end']*1e3:.4f} ms. Settling factor F = {zero['F']:.4e}.")
    print("Sections (sorted by vos): " + ", ".join(f"{r['vos']*1e6:+.0f} uV: {r['points']} points"
                                                   for r in res))
    print()

    print("Settled means (V) and settling check")
    print(f"{'vos (uV)':>10}{'VX (V)':>14}{'VY (V)':>14}{'dVX raw (mV)':>14}{'dVY raw (mV)':>14}")
    for r in res:
        print(f"{r['vos']*1e6:>10.1f}{r['vx']:>14.7f}{r['vy']:>14.7f}"
              f"{r['vx_dprior']*1e3:>14.5f}{r['vy_dprior']*1e3:>14.5f}")
    print()

    print("Offset response relative to vos = 0 (uV). Netlist gives -2 vos; the entry expects +2 vos.")
    print(f"{'vos (uV)':>10}{'dVX (uV)':>12}{'dVY (uV)':>12}{'-2 vos (uV)':>13}{'+2 vos (uV)':>13}"
          f"{'dVX + 2 vos':>13}{'dVY + 2 vos':>13}")
    rows = []
    for r in res:
        if abs(r["vos"]) < 1e-12:
            continue
        dvx = (r["vx"] - zero["vx"]) * 1e6
        dvy = (r["vy"] - zero["vy"]) * 1e6
        v = r["vos"] * 1e6
        rows.append((v, dvx, dvy))
        print(f"{v:>10.1f}{dvx:>12.3f}{dvy:>12.3f}{-2*v:>13.1f}{2*v:>13.1f}"
              f"{dvx - (-2*v):>13.3f}{dvy - (-2*v):>13.3f}")
    print()

    # Slope through the two steps: (dV(+25) - dV(-25)) / (50 uV)
    plus = [r for r in rows if r[0] > 0][0]
    minus = [r for r in rows if r[0] < 0][0]
    slope_x = (plus[1] - minus[1]) / (plus[0] - minus[0])
    slope_y = (plus[2] - minus[2]) / (plus[0] - minus[0])
    print(f"Slope dV/dvos from the two steps: VX {slope_x:.5f}, VY {slope_y:.5f} (netlist -2, entry +2)")
    print()

    print("Magnitude check against the entry pass limit (2 uV): ||dV| - 2 |vos|| <= 2 uV")
    print(f"{'vos (uV)':>10}{'channel':>9}{'|dV| (uV)':>12}{'2|vos| (uV)':>13}{'diff (uV)':>12}"
          f"{'result':>9}")
    all_mag = True
    all_sign = True
    for v, dvx, dvy in rows:
        for ch, d in (("VX", dvx), ("VY", dvy)):
            diff = abs(d) - 2 * abs(v)
            ok = abs(diff) <= PASS_LIMIT_UV
            all_mag &= ok
            sign_ok = (d < 0) == (v > 0)           # netlist: negative shift for positive vos
            all_sign &= sign_ok
            print(f"{v:>10.1f}{ch:>9}{abs(d):>12.3f}{2*abs(v):>13.1f}{diff:>12.3f}"
                  f"{'pass' if ok else 'FAIL':>9}")
    print(f"Magnitude check, all rows: {'pass' if all_mag else 'FAIL'}")
    print(f"Sign against the netlist (-2 vos), all rows: {'pass' if all_sign else 'FAIL'}")
    print("Sign against the entry (+2 vos): FAIL for every row (the entry sign is reversed).")
    print()

    # Linearity: the mean of the two steps, relative to vos = 0
    mean_x = (plus[1] + minus[1]) / 2
    mean_y = (plus[2] + minus[2]) / 2
    print(f"Even part (dV(+25) + dV(-25)) / 2 (uV): VX {mean_x:.4f}, VY {mean_y:.4f}")
    print()

    # Model offset at vos = 0
    vx0 = zero["vx"]
    vy0 = zero["vy"]
    th_vx = ideal_vx(A)
    th_vy_model = model_vy(A)
    th_vy_ideal = MID - k_amp(A) * math.sin(math.radians(D_DEG))
    print("Model offset at vos = 0 (residual against theory)")
    print(f"{'channel':>9}{'measured (V)':>14}{'theory (V)':>14}{'theory basis':>44}"
          f"{'residual (mV)':>15}{'equiv. vos (uV)':>17}")
    res_x = (vx0 - th_vx) * 1e3
    res_y = (vy0 - th_vy_model) * 1e3
    res_y_ideal = (vy0 - th_vy_ideal) * 1e3
    print(f"{'VX':>9}{vx0:>14.7f}{th_vx:>14.7f}{'2.5 V - 2A/pi':>44}{res_x:>15.5f}{-res_x/2*1e3:>17.3f}")
    print(f"{'VY':>9}{vy0:>14.7f}{th_vy_model:>14.7f}{'P-08 model (0.18 deg, 126 ns, slew)':>44}"
          f"{res_y:>15.5f}{-res_y/2*1e3:>17.3f}")
    print(f"{'VY':>9}{vy0:>14.7f}{th_vy_ideal:>14.7f}{'ideal, 0.18 deg only':>44}"
          f"{res_y_ideal:>15.5f}{-res_y_ideal/2*1e3:>17.3f}")
    print()
    print("Cross-check against the P-08 fast run at 0.2 V (corrected means, docs/sim-results/P-08.md):")
    p08_vx, p08_vy = 2.3726752, 2.4996561
    print(f"  VX: P-13 vos = 0 {vx0:.7f} V, P-08 {p08_vx:.7f} V, difference {(vx0-p08_vx)*1e6:+.3f} uV")
    print(f"  VY: P-13 vos = 0 {vy0:.7f} V, P-08 {p08_vy:.7f} V, difference {(vy0-p08_vy)*1e6:+.3f} uV")
    print()

    # Plot
    fig, ax = plt.subplots(1, 1, figsize=(6, 4.5))
    xs = np.linspace(-30, 30, 13)
    ax.plot([r[0] for r in rows], [r[1] for r in rows], "o", label="VX shift, measured")
    ax.plot([r[0] for r in rows], [r[2] for r in rows], "s", label="VY shift, measured")
    ax.plot(xs, -2 * xs, "-", lw=0.8, label="netlist: -2 vos")
    ax.plot(xs, 2 * xs, "--", lw=0.8, label="entry: +2 vos")
    ax.axhline(0, color="grey", lw=0.5)
    ax.set_xlabel("vos (uV)")
    ax.set_ylabel("shift relative to vos = 0 (uV)")
    ax.set_title("P-13 op amp offset, Vampl = 0.2 V")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(PLOT, dpi=120)
    print(f"plot written: {PLOT}")


if __name__ == "__main__":
    main()
