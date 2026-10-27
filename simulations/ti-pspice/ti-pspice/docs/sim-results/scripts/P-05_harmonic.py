"""P-05 harmonic response of the LIA using V7 (run P05_harm, circuits/lia_v2_harm.cir).

The first run parses the .csd file once and caches the per-step numbers to
sim-runs/P05_harm/P05_steps.csv. Later runs read only that CSV. The script computes
the settled means of VX and VY (last 50 periods, with the P-01 settling-bias
correction), the settling check, the ripple, the changes against the no-harmonic
baseline (P-04, Vampl = 2 V), the theory for odd and even n, the residuals, the
rejection table and two plots.

Run from the project root:
    python docs/sim-results/scripts/P-05_harmonic.py
    python docs/sim-results/scripts/P-05_harmonic.py --rebuild   (re-parse the .csd)
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

RUN = "P05_harm"
CSD = ROOT / f"sim-runs/{RUN}/{RUN}.csd"
CACHE = ROOT / f"sim-runs/{RUN}/P05_steps.csv"
PLOT_DIR = ROOT / "docs/sim-results/plots"

F_OSC = 517.0
T = 1.0 / F_OSC
T_END = 1.0
N_PER = 50
DT_GRID = 1e-6
MID = 2.5
A = 2.0                       # V, fundamental amplitude (Vampl)
AH = 0.2                      # V, harmonic amplitude (Vharm_ampl)
K = 2.0 * A / math.pi         # V, ideal fundamental gain
SETTLE_K = 7.6e-5             # V/V, P-01 settling bias per volt of |V - 2.5 V|
T_SLOPE = 100e-9              # s, reference edge time
EPS = T_SLOPE * F_OSC         # duty-cycle excess, D = 0.5 + EPS
PHX_DEG = -0.023              # deg, P-02 extended fit, X constant phase (X delay about 127 ns)
S_Y = 0.480e-3                # V, P-02 slew term of VY at A = 2 V and p = 0
BASE_VX = 1.227224            # V, P-04 baseline at Vampl = 2 V (settling corrected)
BASE_VY = 2.497005            # V, P-04 baseline at Vampl = 2 V (settling corrected)

# Y effective timing error, derived from the baseline: VY - 2.5 = -K sin(theta) + S_Y
THETA_Y = math.asin((S_Y - (BASE_VY - MID)) / K)     # rad
OMEGA_S_X = math.radians(-PHX_DEG)                   # rad, X constant delay phase

COLS = ["n_harm", "vx_last", "vy_last", "vx_prev", "vy_prev", "vx_pp_mV", "vy_pp_mV", "n_points"]


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
        vx, vy = s["V(VX)"], s["V(VY)"]
        t1 = T_END - N_PER * T
        t0 = T_END - 2 * N_PER * T
        _, vx1, mvx1 = window(t, vx, t1, T_END)
        _, vy1, mvy1 = window(t, vy, t1, T_END)
        _, _, mvx0 = window(t, vx, t0, t1)
        _, _, mvy0 = window(t, vy, t0, t1)
        rows.append([
            round(s.step_value), mvx1, mvy1, mvx0, mvy0,
            (vx1.max() - vx1.min()) * 1e3, (vy1.max() - vy1.min()) * 1e3, len(t),
        ])
    arr = np.array(rows)
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    np.savetxt(CACHE, arr, delimiter=",", header=",".join(COLS), comments="", fmt="%.10g")
    print(f"parsed {len(rows)} sections, wrote {CACHE}")


def load_cache():
    d = np.genfromtxt(CACHE, delimiter=",", names=True)
    return d[np.argsort(d["n_harm"])]


def theory_vx(n):
    """VX change (V) from the harmonic n, amplitude AH, p = 0."""
    if n % 2 == 0:
        return -2.0 * AH * EPS * math.sin(n * OMEGA_S_X)
    return -(2.0 * AH / (n * math.pi)) * math.cos(n * OMEGA_S_X)


def theory_vy(n):
    """VY change (V) from the harmonic n. Returns (timing part, slew part)."""
    if n % 2 == 0:
        return 2.0 * AH * EPS * (-1) ** (n // 2) * math.sin(n * THETA_Y), 0.0
    sgn = (-1) ** ((n - 1) // 2)
    timing = -(2.0 * AH / (n * math.pi)) * sgn * math.sin(n * THETA_Y)
    slew = 2.0 * (S_Y / A) * AH * math.sin(n * math.pi / 2)   # slew term scales with A^2
    return timing, slew


def db(x):
    return 20.0 * math.log10(abs(x))


def main():
    if "--rebuild" in sys.argv or not CACHE.exists():
        build_cache()
    d = load_cache()

    print(f"THETA_Y = {math.degrees(THETA_Y):.5f} deg (from baseline), "
          f"omega*s_X = {math.degrees(OMEGA_S_X):.5f} deg, EPS = {EPS:.4e}")
    print()
    print("Per step (settled, corrected). Deltas are in mV against the 2 V baseline.")
    print(f"{'n':>2} {'VX (V)':>12} {'VY (V)':>12} {'setVX mV':>9} {'setVY mV':>9} "
          f"{'corr VX mV':>10} {'corr VY mV':>10} {'ppVX mV':>8} {'ppVY mV':>8} "
          f"{'dVX mV':>10} {'dVY mV':>10}")

    rows = []
    for r in d:
        n = int(r["n_harm"])
        vx_raw, vy_raw = r["vx_last"], r["vy_last"]
        set_vx = (r["vx_last"] - r["vx_prev"]) * 1e3
        set_vy = (r["vy_last"] - r["vy_prev"]) * 1e3
        vx = vx_raw + SETTLE_K * (vx_raw - MID)
        vy = vy_raw + SETTLE_K * (vy_raw - MID)
        dvx = (vx - BASE_VX) * 1e3
        dvy = (vy - BASE_VY) * 1e3
        rows.append((n, vx, vy, dvx, dvy))
        print(f"{n:2d} {vx:12.6f} {vy:12.6f} {set_vx:9.4f} {set_vy:9.4f} "
              f"{(vx - vx_raw) * 1e3:10.4f} {(vy - vy_raw) * 1e3:10.4f} "
              f"{r['vx_pp_mV']:8.3f} {r['vy_pp_mV']:8.3f} {dvx:10.4f} {dvy:10.4f}")
    print()

    print("Theory (mV). VY timing part and slew part are shown separately.")
    print(f"{'n':>2} {'thVX':>10} {'thVY_tim':>10} {'thVY_slew':>10} {'thVY_tot':>10} "
          f"{'dVX-thVX':>10} {'dVY-thVY':>10} {'dVY-tim':>10}")
    res = []
    for n, vx, vy, dvx, dvy in rows:
        tvx = theory_vx(n) * 1e3
        tvy_t, tvy_s = theory_vy(n)
        tvy_t *= 1e3
        tvy_s *= 1e3
        tvy = tvy_t + tvy_s
        res.append((n, dvx, dvy, tvx, tvy, tvy_t))
        print(f"{n:2d} {tvx:10.4f} {tvy_t:10.4f} {tvy_s:10.4f} {tvy:10.4f} "
              f"{dvx - tvx:10.4f} {dvy - tvy:10.4f} {dvy - tvy_t:10.4f}")
    print()

    print("Rejection, odd n. X relative to the ideal fundamental gain 2/pi. Y relative to its own fundamental and to 2/pi.")
    fund_vx_per_v = K / A                                 # V/V, ideal
    print(f"{'n':>2} {'X meas V/V':>11} {'X dB meas':>10} {'X dB theory':>12} "
          f"{'Y meas V/V':>11} {'Y dB own fund':>14} {'Y dB vs 2/pi':>13}")
    for n, dvx, dvy, tvx, tvy, tvy_t in res:
        if n % 2 == 0:
            continue
        x_per_v = (dvx * 1e-3) / AH
        y_per_v = (dvy * 1e-3) / AH
        y_fund = (BASE_VY - MID) / A                        # measured own fundamental, V/V
        y_fund_th = -K * math.sin(THETA_Y) / A
        x_th_per_v = theory_vx(n) / AH
        print(f"{n:2d} {x_per_v:11.5f} {db(x_per_v / (2.0 / math.pi)):10.3f} "
              f"{db(x_th_per_v / (2.0 / math.pi)):12.3f} {y_per_v:11.6f} "
              f"{db(y_per_v / y_fund):14.3f} {db(y_per_v / (2.0 / math.pi)):13.3f}")
    print(f"  theory X: 1/n gives {[round(20*math.log10(1/n),3) for n in (3,5,7)]} dB for n = 3, 5, 7")
    print("  theory Y own fundamental: 0 dB for every odd n (ratio sin(n theta)/(n sin theta) = 1 at small theta)")
    print()

    PLOT_DIR.mkdir(parents=True, exist_ok=True)
    nn = np.array([r[0] for r in res], dtype=float)
    dvx = np.array([r[1] for r in res])
    dvy = np.array([r[2] for r in res])
    tvx = np.array([r[3] for r in res])
    tvy = np.array([r[4] for r in res])
    tvy_t = np.array([r[5] for r in res])

    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.plot(nn, dvx, "o", label="VX measured")
    ax.plot(nn, tvx, "s--", label="VX theory")
    ax.plot(nn, dvy, "^", label="VY measured")
    ax.plot(nn, tvy, "d-", label="VY theory (timing + slew)")
    ax.plot(nn, tvy_t, "x:", label="VY theory (timing only)")
    ax.axhline(0, color="grey", lw=0.6)
    ax.set_xlabel("harmonic n (input at n x 517 Hz)")
    ax.set_ylabel("change against 2 V baseline (mV)")
    ax.set_xticks([2, 3, 4, 5, 7])
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(PLOT_DIR / "P-05_deltas_vs_n.png", dpi=130)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(7, 4.0))
    ax.plot(nn, dvx - tvx, "o-", label="VX measured minus theory")
    ax.plot(nn, dvy - tvy, "^-", label="VY measured minus theory (timing + slew)")
    ax.axhline(0, color="grey", lw=0.6)
    ax.set_xlabel("harmonic n")
    ax.set_ylabel("residual (mV)")
    ax.set_xticks([2, 3, 4, 5, 7])
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(PLOT_DIR / "P-05_residual_vs_n.png", dpi=130)
    plt.close(fig)
    print(f"wrote plots to {PLOT_DIR}")


if __name__ == "__main__":
    main()
