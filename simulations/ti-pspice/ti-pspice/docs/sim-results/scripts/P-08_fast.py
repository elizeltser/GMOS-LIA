"""P-08 validation of the fast settings for lia_v3_fast.cir.

Reads sim-runs/P08_fast/P08_fast.csd (.STEP Vampl = 0.2 and 2 V, 0.15 s,
output capacitors 1 uF, tau = 10 ms) and the reference run
sim-runs/P04_step5u/P04_step5u.csd (lia_v2.cir, 2 V, 1 s, 5 us, 10 uF, tau = 0.1 s).

Settled value: time-weighted trapezoid mean over the last whole periods of
517 Hz (fast run: 20 periods, 38.68 ms, from 111.3 ms to 150 ms; reference:
50 periods, 96.71 ms, from 903.3 ms to 1000 ms). The mean is taken on the raw
PSpice points with the window ends interpolated, because point means are
biased (docs/simulation-quirks.md). A uniform 0.5 us grid gives the same mean
to 0.01 uV, and this is printed as a check.

Settling bias: the window mean of a first-order decay from 2.5 V is
m = V_ss + (2.5 - V_ss) F, with F = (tau / Tw) (1 - exp(-Tw / tau)) exp(-t0 / tau).
The bias is estimated from the data as B = (m_last - m_prior) / (1 - exp(Tw / tau)),
where m_prior is the mean of the window of the same length before. The
corrected value is V_ss = (m - 2.5 F) / (1 - F). The same correction gives the
quoted reference values, so the reference in the entry is a corrected mean.

Ripple: least-squares fit of the 1f and 2f sinusoids on a 0.5 us grid over
the last window. The fit is used for the ripple only, not for the mean.

Model for VY (P-04 terms): VY - 2.5 V = -K sin(d - delta) + c A^2, with
K = 2A/pi, d = 0.1785 deg (entry), delta = 126 ns (P-04 constant lag, 0.0234 deg)
and c A^2 with c A^2 = 0.457 mV at A = 2 V (P-04 slew term, 111 ns at 2 V).

Run from the project root:
    python docs/sim-results/scripts/P-08_fast.py
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

FAST_CSD = ROOT / "sim-runs/P08_fast/P08_fast.csd"
REF_CSD = ROOT / "sim-runs/P04_step5u/P04_step5u.csd"
PLOT = ROOT / "docs/sim-results/plots/P-08_fast.png"

F_OSC = 517.0
T = 1.0 / F_OSC
MID = 2.5
DT_RIPPLE = 0.5e-6
T_DELAY_Y = 482.6e-6
TAU_FAST = 10e3 * 1e-6      # R3 x C1 = 10 kOhm x 1 uF
TAU_REF = 10e3 * 10e-6      # R x C = 10 kOhm x 10 uF

# Entry and P-04 values
D_DEG = 360.0 * (T / 4 - T_DELAY_Y) / T            # Y timing error, 0.1785 deg
DELTA_DEG = 360.0 * 126e-9 / T                      # P-04 constant lag, 0.02345 deg
C_SLEW = 0.457e-3 / 2.0 ** 2                        # V per V^2, from 0.457 mV at 2 V

# Quoted reference in the entry (corrected 50-period means of P04_step5u)
REF_VX = 1.2268012
REF_VY = 2.4969886


def k_amp(a):
    return 2.0 * a / math.pi


def ideal_vx(a):
    return MID - k_amp(a)                           # p = 0


def ideal_vy(a):
    return MID - k_amp(a) * math.sin(math.radians(D_DEG))


def model_vy(a):
    lag = math.radians(D_DEG - DELTA_DEG)
    return MID - k_amp(a) * math.sin(lag) + C_SLEW * a * a


def window_mean(t, y, t0, t1):
    """Time-weighted trapezoid mean on the raw points, ends interpolated."""
    inside = (t > t0) & (t < t1)
    tt = np.concatenate(([t0], t[inside], [t1]))
    yy = np.concatenate(([np.interp(t0, t, y)], y[inside], [np.interp(t1, t, y)]))
    return float(np.trapezoid(yy, tt) / (t1 - t0))


def grid_mean(t, y, t0, t1, h=0.5e-6):
    """Same mean on a uniform grid, used as a cross-check of the raw-point mean."""
    g = np.linspace(t0, t1, round((t1 - t0) / h) + 1)
    return float(np.trapezoid(np.interp(g, t, y), g) / (t1 - t0))


def ripple_fit(t, y, t0, t1):
    """Peak amplitudes of the 1f and 2f components (least squares, uniform grid)."""
    grid = np.arange(t0, t1, DT_RIPPLE)
    yg = np.interp(grid, t, y)
    w = 2 * math.pi * F_OSC
    cols = [np.ones_like(grid)]
    for k in (1, 2):
        cols += [np.cos(k * w * grid), np.sin(k * w * grid)]
    a = np.column_stack(cols)
    c, *_ = np.linalg.lstsq(a, yg, rcond=None)
    return math.hypot(c[1], c[2]), math.hypot(c[3], c[4])


def settle_factor(t0, tw, tau):
    """Window mean of exp(-t/tau) from t0 to t0 + tw, relative to the start value of 1."""
    return (tau / tw) * (1 - math.exp(-tw / tau)) * math.exp(-t0 / tau)


def analyse_section(sec, a, n, t_end, tau):
    t = sec.x
    vx = sec["V(VX)"]
    vy = sec["V(VY)"]
    tw = n * T
    t1 = t_end
    t0 = t1 - tw
    tp0 = t0 - tw
    res = {"a": a, "t_end": t_end, "t0": t0, "n": n, "points": len(t), "tau": tau}
    res["vx_raw"] = window_mean(t, vx, t0, t1)
    res["vy_raw"] = window_mean(t, vy, t0, t1)
    res["vx_grid"] = grid_mean(t, vx, t0, t1)
    res["vy_grid"] = grid_mean(t, vy, t0, t1)
    res["vx_prior"] = window_mean(t, vx, tp0, t0)
    res["vy_prior"] = window_mean(t, vy, tp0, t0)
    res["dvx_prior"] = res["vx_raw"] - res["vx_prior"]
    res["dvy_prior"] = res["vy_raw"] - res["vy_prior"]
    e = math.exp(tw / tau)
    res["bias_vx_data"] = res["dvx_prior"] / (1 - e)
    res["bias_vy_data"] = res["dvy_prior"] / (1 - e)
    f = settle_factor(t0, tw, tau)
    res["F"] = f
    res["vx"] = (res["vx_raw"] - MID * f) / (1 - f)
    res["vy"] = (res["vy_raw"] - MID * f) / (1 - f)
    # Bias B = raw mean minus settled value, same sign as the data estimate
    res["bias_model_vx"] = f * (MID - res["vx_raw"])
    res["bias_model_vy"] = f * (MID - res["vy_raw"])
    res["amp1_vx"], res["amp2_vx"] = ripple_fit(t, vx, t0, t1)
    res["amp1_vy"], res["amp2_vy"] = ripple_fit(t, vy, t0, t1)
    return res


def pct_err(meas, exp):
    return 100.0 * (meas - exp) / exp if abs(exp) > 1e-12 else float("nan")


def main():
    fast = read_csdf(str(FAST_CSD))
    ref = read_csdf(str(REF_CSD))

    runs = {}
    for sec in fast:
        a = round(sec.step_value, 6)
        runs[a] = analyse_section(sec, a, 20, float(sec.x[-1]), TAU_FAST)
    r02, r2 = runs[0.2], runs[2.0]
    ref_res = analyse_section(ref[0], 2.0, 50, float(ref[0].x[-1]), TAU_REF)

    print(f"T = {T*1e3:.6f} ms, d = {D_DEG:.5f} deg, constant lag = {DELTA_DEG:.5f} deg, "
          f"slew c = {C_SLEW*1e6:.3f} uV/V^2")
    print(f"Fast run: end {r2['t_end']:.6f} s, window {r2['t0']*1e3:.4f} to {r2['t_end']*1e3:.4f} ms, "
          f"20 periods, points {r2['points']}")
    print(f"Reference run: end {ref_res['t_end']:.6f} s, window {ref_res['t0']*1e3:.4f} to "
          f"{ref_res['t_end']*1e3:.4f} ms, 50 periods, points {ref_res['points']}")
    print()

    print("Means over the settled window (V). raw = trapezoid on the PSpice points.")
    print("grid = trapezoid on a 0.5 us grid. corrected = raw with the settling bias removed.")
    print(f"{'run':<22}{'VX raw':>13}{'VX grid':>13}{'VX corr':>13}{'VY raw':>13}{'VY grid':>13}{'VY corr':>13}")
    for name, r in (("fast 0.2 V", r02), ("fast 2 V", r2), ("ref 2 V, 50 T", ref_res)):
        print(f"{name:<22}{r['vx_raw']:>13.7f}{r['vx_grid']:>13.7f}{r['vx']:>13.7f}"
              f"{r['vy_raw']:>13.7f}{r['vy_grid']:>13.7f}{r['vy']:>13.7f}")
    print(f"{'quoted reference':<22}{'':>13}{'':>13}{REF_VX:>13.7f}{'':>13}{'':>13}{REF_VY:>13.7f}")
    print()

    print("Settling check: last window against the window of the same length before it")
    print(f"{'run':<14}{'tau (ms)':>9}{'F':>12}{'dVX (mV)':>11}{'dVY (mV)':>11}"
          f"{'B VX data (uV)':>16}{'B VX model (uV)':>17}{'B VY data (uV)':>16}")
    for name, r in (("fast 0.2 V", r02), ("fast 2 V", r2), ("ref 2 V, 50 T", ref_res)):
        print(f"{name:<14}{r['tau']*1e3:>9.1f}{r['F']:>12.4e}{r['dvx_prior']*1e3:>11.4f}"
              f"{r['dvy_prior']*1e3:>11.4f}{r['bias_vx_data']*1e6:>16.3f}"
              f"{r['bias_model_vx']*1e6:>17.3f}{r['bias_vy_data']*1e6:>16.3f}")
    print()

    print("Ripple in the last window, peak amplitude of the fitted sinusoid")
    print(f"{'run':<14}{'1f VX (mV)':>12}{'2f VX (mV)':>12}{'1f VY (mV)':>12}{'2f VY (mV)':>12}")
    for name, r in (("fast 0.2 V", r02), ("fast 2 V", r2)):
        print(f"{name:<14}{r['amp1_vx']*1e3:>12.4f}{r['amp2_vx']*1e3:>12.4f}"
              f"{r['amp1_vy']*1e3:>12.4f}{r['amp2_vy']*1e3:>12.4f}")
    print()

    # (name, measured, expected) with the quantities in mV
    rows = [
        ("VX - 2.5 V, 0.2 V, ideal", (r02["vx"] - MID) * 1e3, (ideal_vx(0.2) - MID) * 1e3),
        ("VY - 2.5 V, 0.2 V, ideal", (r02["vy"] - MID) * 1e3, (ideal_vy(0.2) - MID) * 1e3),
        ("VY - 2.5 V, 0.2 V, P-04 model", (r02["vy"] - MID) * 1e3, (model_vy(0.2) - MID) * 1e3),
        ("VX - 2.5 V, 2 V, ideal", (r2["vx"] - MID) * 1e3, (ideal_vx(2.0) - MID) * 1e3),
        ("VY - 2.5 V, 2 V, ideal", (r2["vy"] - MID) * 1e3, (ideal_vy(2.0) - MID) * 1e3),
        ("VY - 2.5 V, 2 V, P-04 model", (r2["vy"] - MID) * 1e3, (model_vy(2.0) - MID) * 1e3),
        ("VX, 2 V, vs quoted reference", r2["vx"] * 1e3, REF_VX * 1e3),
        ("VY, 2 V, vs quoted reference", r2["vy"] * 1e3, REF_VY * 1e3),
        ("VX, 2 V, vs ref recomputed", r2["vx"] * 1e3, ref_res["vx"] * 1e3),
        ("VY, 2 V, vs ref recomputed", r2["vy"] * 1e3, ref_res["vy"] * 1e3),
    ]
    print("Comparison. Rows with a ' - 2.5 V' label are in mV. The other rows are absolute values in mV.")
    print(f"{'quantity':<32}{'measured (mV)':>15}{'expected (mV)':>15}{'diff (mV)':>12}{'pct err (%)':>13}")
    for name, meas, exp in rows:
        print(f"{name:<32}{meas:>15.5f}{exp:>15.5f}{meas-exp:>12.5f}{pct_err(meas, exp):>13.4f}")
    print()
    print(f"Ideal VX at 0.2 V and 2 V (V): {ideal_vx(0.2):.7f}, {ideal_vx(2.0):.7f}")
    print(f"Ideal VY at 0.2 V and 2 V (V): {ideal_vy(0.2):.7f}, {ideal_vy(2.0):.7f}")
    print(f"P-04 model VY at 0.2 V and 2 V (V): {model_vy(0.2):.7f}, {model_vy(2.0):.7f}")
    print(f"Lag term K sin(delta) at 0.2 V and 2 V (mV): "
          f"{k_amp(0.2)*math.sin(math.radians(DELTA_DEG))*1e3:.5f}, "
          f"{k_amp(2.0)*math.sin(math.radians(DELTA_DEG))*1e3:.5f}")
    print(f"Slew term c A^2 at 0.2 V and 2 V (mV): {C_SLEW*0.04*1e3:.5f}, {C_SLEW*4.0*1e3:.5f}")
    print()

    # Plot: full run at 2 V, and the last 5 periods at 2 V
    s2 = [s for s in fast if abs(s.step_value - 2.0) < 1e-9][0]
    t = s2.x
    vx = s2["V(VX)"]
    vy = s2["V(VY)"]
    fig, ax = plt.subplots(2, 1, figsize=(8, 7))
    ax[0].plot(t * 1e3, (vx - MID) * 1e3, lw=0.6, label="VX - 2.5 V")
    ax[0].plot(t * 1e3, (vy - MID) * 1e3, lw=0.6, label="VY - 2.5 V")
    ax[0].axvspan(r2["t0"] * 1e3, r2["t_end"] * 1e3, color="grey", alpha=0.2, label="settled window (20 T)")
    ax[0].set_xlabel("time (ms)")
    ax[0].set_ylabel("output relative to 2.5 V (mV)")
    ax[0].set_title("P-08 fast run, Vampl = 2 V, cout = 1 uF")
    ax[0].legend(fontsize=8)
    m = t > r2["t_end"] - 5 * T
    ax[1].plot(t[m] * 1e3, (vx[m] - r2["vx"]) * 1e3, lw=0.6, label="VX - settled mean")
    ax[1].plot(t[m] * 1e3, (vy[m] - r2["vy"]) * 1e3, lw=0.6, label="VY - settled mean")
    ax[1].set_xlabel("time (ms)")
    ax[1].set_ylabel("relative to settled mean (mV)")
    ax[1].set_title("Last 5 periods of the 2 V run, relative to the settled mean (ripple at 2f)")
    ax[1].legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(PLOT, dpi=120)
    print(f"plot written: {PLOT}")


if __name__ == "__main__":
    main()
