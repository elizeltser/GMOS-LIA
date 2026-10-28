"""P-04 dynamic range versus input amplitude for the LIA circuit (lia_v2.cir, Vampl step).

The first run parses the .csd file once and caches the per-step numbers to
sim-runs/P04_ampl/P04_steps.csv. Later runs read only that CSV. The script then
computes the settled means of VX and VY (with the P-01 settling-bias correction),
the settling check, the comparison with the ideal theory, the polynomial fits
a + b A + c A^2, the linear-region limit, and the steady extremes of V(VX_DEMOD)
(0.1 and 99.9 percentiles over the last 50 periods). It writes the plots.

Run from the project root:
    python docs/sim-results/scripts/P-04_amplitude.py
    python docs/sim-results/scripts/P-04_amplitude.py --rebuild   (re-parse the .csd)
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

RUN = "P04_ampl"
CSD = ROOT / f"sim-runs/{RUN}/{RUN}.csd"
CACHE = ROOT / f"sim-runs/{RUN}/P04_steps.csv"
PLOT_DIR = ROOT / "docs/sim-results/plots"

F_OSC = 517.0
T = 1.0 / F_OSC
T_END = 1.0
N_PER = 50
DT_GRID = 1e-6
MID = 2.5
K_PER_V = 2.0 / math.pi                  # V per V of amplitude
D_DEG = 0.1785                            # deg, brief value of the Y timing error d
SETTLE_K = 0.097e-3 / 1.27                # V/V, P-01 settling bias per V of |V - 2.5|
D_EFF_DEG = 0.134                         # deg, effective Y timing at p = 0 (P-02: d - 0.044)

COLS = ["ampl", "vx_last", "vy_last", "vx_prev", "vy_prev", "vx_t0", "vy_t0",
        "vx_pp_mV", "vy_pp_mV", "dem_p001", "dem_p9999", "dem_min", "dem_max",
        "dem_mean", "n_points"]


def trap_mean(t, y):
    return float(np.sum(0.5 * (y[1:] + y[:-1]) * np.diff(t)) / (t[-1] - t[0]))


def window(t_raw, y_raw, t_start, t_stop):
    n = round((t_stop - t_start) / DT_GRID) + 1
    grid = np.linspace(t_start, t_stop, n)
    yg = np.interp(grid, t_raw, y_raw)
    return grid, yg, trap_mean(grid, yg)


def build_cache():
    rows = []
    for s in read_csdf(str(CSD)):
        t = s.x
        assert abs(t[-1] - T_END) < 1e-12, f"step ends at {t[-1]}"
        vx, vy, dm = s["V(VX)"], s["V(VY)"], s["V(VX_DEMOD)"]
        t1 = T_END - N_PER * T
        t0 = T_END - 2 * N_PER * T
        _, vx1, mvx1 = window(t, vx, t1, T_END)
        _, vy1, mvy1 = window(t, vy, t1, T_END)
        _, dm1, mdm1 = window(t, dm, t1, T_END)
        _, _, mvx0 = window(t, vx, t0, t1)
        _, _, mvy0 = window(t, vy, t0, t1)
        rows.append([
            s.step_value, mvx1, mvy1, mvx0, mvy0, float(vx[0]), float(vy[0]),
            (vx1.max() - vx1.min()) * 1e3, (vy1.max() - vy1.min()) * 1e3,
            np.percentile(dm1, 0.1), np.percentile(dm1, 99.9),
            dm1.min(), dm1.max(), mdm1, len(t),
        ])
    arr = np.array(rows)
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    np.savetxt(CACHE, arr, delimiter=",", header=",".join(COLS), comments="", fmt="%.10g")
    print(f"parsed {len(rows)} sections, wrote {CACHE}")


def load_cache():
    d = np.genfromtxt(CACHE, delimiter=",", names=True)
    return d[np.argsort(d["ampl"])]


def fit_quad(a, y):
    X = np.column_stack([np.ones_like(a), a, a ** 2])
    coef, *_ = np.linalg.lstsq(X, y, rcond=None)
    return coef, y - X @ coef


def fit_lin(a, y):
    X = np.column_stack([np.ones_like(a), a])
    coef, *_ = np.linalg.lstsq(X, y, rcond=None)
    return coef, y - X @ coef


def cusp_check(d):
    """Estimate the 99.9 percentile drop of VX_DEMOD from the cusp geometry, and compare it with the data.

    At p = 0 the steady upper edge of V(VX_DEMOD) is a V-shaped cusp. Its slope is about
    A x 2 pi x f_osc per second. If N cusps per window each remove a width 2 delta / s, and the
    top 0.1 % of the window is removed, then delta = 0.001 x T_window x s / (2 N).
    The script counts the cusps and the slope on the 1 us grid, and compares the predicted drop
    with 2.5 V - p99.9 from the cache.
    """
    sections = {round(s.step_value, 6): s for s in read_csdf(str(CSD))}
    print("Cusp check of the VX_DEMOD upper edge (1 us grid, last 50 periods)")
    print(f"{'A(V)':>6} {'cusps/period':>12} {'slope (mV/us)':>14} {'pred. drop (mV)':>16} "
          f"{'meas. drop (mV)':>16} {'pred/V':>8} {'meas/V':>8} {'0.1us drop (mV)':>16} {'0.1us/V':>9}")
    t_win = N_PER * T
    t1 = T_END - t_win
    rows_fine = []
    for i in range(len(d)):
        A_i = d["ampl"][i]
        s = sections[round(A_i, 6)]
        t = s.x
        _, yg, _ = window(t, s["V(VX_DEMOD)"], t1, T_END)
        peaks = np.where((yg[1:-1] > yg[:-2]) & (yg[1:-1] >= yg[2:]) & (yg[1:-1] > MID - 0.1))[0] + 1
        n_per = len(peaks) / N_PER
        band = (yg[:-1] > MID - 0.1) & (yg[:-1] < MID - 0.005)
        slope = float(np.median(np.abs(np.diff(yg))[band])) * 1e3 if band.any() else float("nan")  # mV per us
        s_v = slope * 1e-3 / 1e-6                                # V/s
        drop_pred = 0.001 * t_win * s_v / (2.0 * len(peaks)) * 1e3 if len(peaks) else float("nan")  # mV
        drop_meas = (MID - d["dem_p9999"][i]) * 1e3
        # Same percentile on a 0.1 us grid, to test the effect of the 1 us sampling
        g_fine = np.linspace(t1, T_END, round(t_win / 0.1e-6) + 1)
        yf = np.interp(g_fine, t, s["V(VX_DEMOD)"])
        drop_fine = (MID - np.percentile(yf, 99.9)) * 1e3
        rows_fine.append((A_i, drop_fine))
        print(f"{A_i:6.3f} {n_per:12.2f} {slope:14.3f} {drop_pred:16.4f} {drop_meas:16.4f} "
              f"{drop_pred / A_i:8.3f} {drop_meas / A_i:8.3f} {drop_fine:14.4f} {drop_fine / A_i:9.3f}")
    print()
    print("Samples in the excluded band per cusp at 2 V: 2 delta / (s x 1 us) with delta = 3.5 mV and s = 6.5 mV/us")
    print(f"  = {2 * 3.5 / 6.5:.2f} samples (1 us grid)")
    print()


def main():
    if "--rebuild" in sys.argv or not CACHE.exists():
        build_cache()
    d = load_cache()
    if "--cusp" in sys.argv:
        cusp_check(d)
        return
    A = d["ampl"]
    n = len(A)

    # Settling-bias correction (P-01), applied as in P-02
    vx = d["vx_last"] + SETTLE_K * (d["vx_last"] - MID)
    vy = d["vy_last"] + SETTLE_K * (d["vy_last"] - MID)
    bias_vx = (vx - d["vx_last"]) * 1e3
    bias_vy = (vy - d["vy_last"]) * 1e3
    set_vx = (d["vx_last"] - d["vx_prev"]) * 1e3
    set_vy = (d["vy_last"] - d["vy_prev"]) * 1e3

    # Ideal theory (brief): VX - 2.5 = -K A, VY - 2.5 = K A sin(-d)
    th_vx = -K_PER_V * A
    th_vy = K_PER_V * A * np.sin(np.radians(-D_DEG))
    th_vy_eff = K_PER_V * A * np.sin(np.radians(-D_EFF_DEG))
    err_vx = (vx - MID - th_vx) * 1e3
    err_vy = (vy - MID - th_vy) * 1e3
    pct_vx = (vx - MID) / th_vx * 100 - 100
    pct_vy = np.where(np.abs(th_vy) > 0, (vy - MID) / np.where(th_vy == 0, 1, th_vy) * 100 - 100, 0)

    print("step settled values, corrected")
    print(f"{'A(V)':>6} {'VX':>12} {'VY':>12} {'dVX(mV)':>10} {'dVY(mV)':>10} "
          f"{'setVX(mV)':>10} {'setVY(mV)':>10} {'ppVX(mV)':>9} {'ppVY(mV)':>9}")
    for i in range(n):
        print(f"{A[i]:6.3f} {vx[i]:12.6f} {vy[i]:12.6f} {(vx[i]-MID)*1e3:10.4f} "
              f"{(vy[i]-MID)*1e3:10.4f} {set_vx[i]:10.4f} {set_vy[i]:10.4f} "
              f"{d['vx_pp_mV'][i]:9.4f} {d['vy_pp_mV'][i]:9.4f}")
    print()
    print("comparison with brief theory (mV)")
    print(f"{'A(V)':>6} {'thVX':>10} {'errVX':>9} {'%VX':>9} {'thVY':>10} {'errVY':>9} {'thVY_eff':>10} {'errVY_eff':>10}")
    for i in range(n):
        print(f"{A[i]:6.3f} {th_vx[i]*1e3:10.4f} {err_vx[i]:9.4f} {pct_vx[i]:9.4f} "
              f"{th_vy[i]*1e3:10.4f} {err_vy[i]:9.4f} {th_vy_eff[i]*1e3:10.4f} "
              f"{((vy[i]-MID)-th_vy_eff[i])*1e3:10.4f}")
    print()

    # Steady demodulator extremes
    print("VX_DEMOD steady extremes (0.1 / 99.9 percentile, mean)")
    for i in range(n):
        print(f"{A[i]:6.3f} p0.1={d['dem_p001'][i]:.5f} p99.9={d['dem_p9999'][i]:.5f} "
              f"mean={d['dem_mean'][i]:.5f} abs_min={d['dem_min'][i]:.5f} abs_max={d['dem_max'][i]:.5f}")
    print()

    # Linear region: fit on all amplitudes up to 2 V (first 7 steps: 0.01 ... 2 V)
    lin = A <= 2.0 + 1e-9
    al = A[lin]
    cx, rx = fit_quad(al, (vx - MID)[lin])
    cy, ry = fit_quad(al, (vy - MID)[lin])
    lx, lrx = fit_lin(al, (vx - MID)[lin])
    ly, lry = fit_lin(al, (vy - MID)[lin])
    print("Quadratic fit a + b A + c A^2 (A <= 2 V, 7 points)")
    print(f"VX: a = {cx[0]*1e3:+.5f} mV, b = {cx[1]:+.7f} V/V (ideal {-K_PER_V:+.7f}), c = {cx[2]*1e3:+.5f} mV/V^2, rms {np.sqrt(np.mean(rx**2))*1e3:.4f} mV")
    print(f"VY: a = {cy[0]*1e3:+.5f} mV, b = {cy[1]:+.7f} V/V (ideal {K_PER_V*np.sin(np.radians(-D_DEG)):+.7f}), c = {cy[2]*1e3:+.5f} mV/V^2, rms {np.sqrt(np.mean(ry**2))*1e3:.4f} mV")
    print("Linear fit a + b A (A <= 2 V)")
    print(f"VX: a = {lx[0]*1e3:+.5f} mV, b = {lx[1]:+.7f} V/V, rms {np.sqrt(np.mean(lrx**2))*1e3:.4f} mV")
    print(f"VY: a = {ly[0]*1e3:+.5f} mV, b = {ly[1]:+.7f} V/V, rms {np.sqrt(np.mean(lry**2))*1e3:.4f} mV")
    print(f"Gain ratio VX b / (-2/pi) - 1 = {(cx[1]/(-K_PER_V)-1)*100:+.4f} %")
    print()

    # Y timing decomposition at A = 2 V (VY - 2.5 = K sin(-phi), K = 2/pi per V of A)
    A2 = 2.0
    phi_eff_deg = math.degrees(math.asin(abs(cy[1]) / K_PER_V))
    dphi_lin = D_DEG - phi_eff_deg                                 # deg, constant lag reduction
    dphi_sq = math.degrees(cy[2] * A2 ** 2 / (K_PER_V * A2))        # deg, square-law term at 2 V
    t_per = 1.0 / F_OSC * 1e9                                       # ns per period
    print("Y timing decomposition at 2 V")
    print(f"ideal lag d = {D_DEG:.4f} deg, effective lag from linear gain = {phi_eff_deg:.4f} deg")
    print(f"constant lag reduction = {dphi_lin:.4f} deg = {dphi_lin / 360 * t_per:.1f} ns")
    print(f"square-law part at 2 V = {dphi_sq:.4f} deg = {dphi_sq / 360 * t_per:.1f} ns")
    print(f"sum = {(dphi_lin + dphi_sq) / 360 * t_per:.1f} ns (P-01 total 235 ns)")
    print(f"linear part of the 2 V error = {(cy[1]*A2 + K_PER_V * A2 * math.sin(math.radians(D_DEG)))*1e3:+.4f} mV (measured minus ideal),"
          f" square-law part = {cy[2]*A2**2*1e3:+.4f} mV")
    print()

    # Full-range check of the linear model against all 11 steps
    print("Largest A with |VX - linear fit| <= 1 mV and <= 0.1 % (fit a + b A + c A^2 on A <= 2 V)")
    pred = cx[0] + cx[1] * A + cx[2] * A ** 2
    dev = (vx - MID) - pred
    rel = dev / np.where(np.abs(pred) > 0, pred, np.nan) * 100
    predy = cy[0] + cy[1] * A + cy[2] * A ** 2
    devy = (vy - MID) - predy
    print(f"{'A(V)':>6} {'VX dev(mV)':>11} {'VX rel(%)':>10} {'VY dev(mV)':>11} {'VY dev vs (2/pi)A sin(-d) (mV)':>32}")
    for i in range(n):
        print(f"{A[i]:6.3f} {dev[i]*1e3:11.4f} {rel[i]:10.4f} {devy[i]*1e3:11.4f} {((vy[i]-MID)-th_vy[i])*1e3:32.4f}")
    print()

    # Plots
    PLOT_DIR.mkdir(parents=True, exist_ok=True)
    a_fine = np.linspace(0.005, 3.0, 300)
    fig, ax = plt.subplots(1, 2, figsize=(11, 4.5))
    ax[0].loglog(A, np.abs(vx - MID), "o", label="VX - 2.5 V (measured)")
    ax[0].loglog(A, np.abs(vy - MID), "s", label="VY - 2.5 V (measured)")
    ax[0].loglog(a_fine, K_PER_V * a_fine, "k--", label="(2/pi) A")
    ax[0].set_xlabel("Vampl (V)")
    ax[0].set_ylabel("|output - 2.5 V| (V)")
    ax[0].legend()
    ax[0].grid(True, which="both", alpha=0.3)
    ax[1].plot(A, vx - MID, "o", label="VX - 2.5 V (measured)")
    ax[1].plot(A, vy - MID, "s", label="VY - 2.5 V (measured)")
    ax[1].plot(a_fine, -K_PER_V * a_fine, "k--", label="-(2/pi) A")
    ax[1].set_xlabel("Vampl (V)")
    ax[1].set_ylabel("output - 2.5 V (V)")
    ax[1].legend()
    ax[1].grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(PLOT_DIR / "P-04_output_vs_ampl.png", dpi=130)
    plt.close(fig)

    fig, ax = plt.subplots(1, 2, figsize=(11, 4.5))
    ax[0].plot(A, err_vx, "o-", label="VX error vs -(2/pi) A")
    ax[0].plot(A, (vy - MID - th_vy) * 1e3, "s-", label="VY error vs (2/pi) A sin(-d)")
    ax[0].axhline(1, color="gray", ls=":")
    ax[0].axhline(-1, color="gray", ls=":")
    ax[0].set_xlabel("Vampl (V)")
    ax[0].set_ylabel("error (mV)")
    ax[0].legend()
    ax[0].grid(True, alpha=0.3)
    ax[1].plot(A, dev * 1e3, "o-", label="VX minus fit (a + bA + cA^2)")
    ax[1].axhline(1, color="gray", ls=":")
    ax[1].axhline(-1, color="gray", ls=":")
    ax[1].set_xlabel("Vampl (V)")
    ax[1].set_ylabel("residual (mV)")
    ax[1].legend()
    ax[1].grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(PLOT_DIR / "P-04_error_vs_ampl.png", dpi=130)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(6.5, 4.5))
    ax.plot(A, d["dem_p9999"], "o-", label="99.9 percentile")
    ax.plot(A, d["dem_p001"], "s-", label="0.1 percentile")
    ax.plot(A, MID - A, "k--", label="2.5 V - Vampl")
    ax.plot(A, MID + A, "k:", label="2.5 V + Vampl")
    ax.axhline(0.0, color="gray", ls=":")
    ax.axhline(5.0, color="gray", ls=":")
    ax.set_xlabel("Vampl (V)")
    ax.set_ylabel("V(VX_DEMOD) (V)")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(PLOT_DIR / "P-04_demod_extremes_vs_ampl.png", dpi=130)
    plt.close(fig)
    print("plots written to", PLOT_DIR)


if __name__ == "__main__":
    main()
