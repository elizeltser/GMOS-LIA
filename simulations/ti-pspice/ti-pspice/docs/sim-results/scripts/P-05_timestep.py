"""P-05 time-step check: maximum step 20 us, 5 us and 2 us (VX gain deficit).

Runs used (all with 1 s, .IC at 2.5 V, NUMDGT = 8, p = 0, ost = 0):
    20 us: P05_harm (n = 2, 3, 4, 5, 7) and P04_ampl (Vampl = 2 V, from its cache)
     5 us: P05_step5u (n = 2, 3, 7) and P04_step5u (Vampl = 2 V)
     2 us: P05_step2u (n = 2, 3, 7) and P04_step2u (Vampl = 2 V)

The first run parses each .csd once and caches the settled numbers to
sim-runs/<run>/<run>_timestep.csv. Later runs read the caches. The script prints
the fundamental gain deficit, the odd-harmonic deficits (against the n = 2 step of
the same run, as the judge asked), the convergence ratios and the model
(n w h)^2 / 12. It writes no plots.

Run from the project root:
    python docs/sim-results/scripts/P-05_timestep.py
    python docs/sim-results/scripts/P-05_timestep.py --rebuild
"""

import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools"))
from csdf import read_csdf  # noqa: E402

F_OSC = 517.0
T = 1.0 / F_OSC
T_END = 1.0
N_PER = 50
DT_GRID = 1e-6
MID = 2.5
A = 2.0
AH = 0.2
K = 2.0 * A / math.pi
SETTLE_K = 7.6e-5
EPS = 100e-9 * F_OSC
S_Y = 0.480e-3
THETA_Y = math.asin((S_Y - (-0.002995)) / K)   # baseline-derived Y phase, rad (P-05.md)
OMEGA_S_X = math.radians(0.023)

RUNS = {
    20: {"harm": "P05_harm", "fund": "P04_ampl"},
    5: {"harm": "P05_step5u", "fund": "P04_step5u"},
    2: {"harm": "P05_step2u", "fund": "P04_step2u"},
}
COLS = ["step", "vx", "vy", "set_vx_mV", "set_vy_mV", "pp_vx_mV", "pp_vy_mV", "n_points"]


def trap_mean(t, y):
    return float(np.sum(0.5 * (y[1:] + y[:-1]) * np.diff(t)) / (t[-1] - t[0]))


def window(t_raw, y_raw, t_start, t_stop):
    n = round((t_stop - t_start) / DT_GRID) + 1
    grid = np.linspace(t_start, t_stop, n)
    yg = np.interp(grid, t_raw, y_raw)
    return grid, yg, trap_mean(grid, yg)


def stats_from_section(s):
    t = s.x
    vx, vy = s["V(VX)"], s["V(VY)"]
    t1 = T_END - N_PER * T
    t0 = T_END - 2 * N_PER * T
    _, vx1, mvx1 = window(t, vx, t1, T_END)
    _, vy1, mvy1 = window(t, vy, t1, T_END)
    _, _, mvx0 = window(t, vx, t0, t1)
    _, _, mvy0 = window(t, vy, t0, t1)
    return [mvx1, mvy1, (mvx1 - mvx0) * 1e3, (mvy1 - mvy0) * 1e3,
            (vx1.max() - vx1.min()) * 1e3, (vy1.max() - vy1.min()) * 1e3, len(t)]


def build_cache(run, is_fund):
    cache = ROOT / f"sim-runs/{run}/{run}_timestep.csv"
    rows = []
    if is_fund:
        if run == "P04_ampl":
            # Use the cached 20 us P-04 run (validated in P-04). Take the Vampl = 2 V row.
            d = np.genfromtxt(ROOT / "sim-runs/P04_ampl/P04_steps.csv", delimiter=",", names=True)
            i = int(np.argmin(np.abs(d["ampl"] - 2.0)))
            r = d[i]
            rows.append([0, r["vx_last"], r["vy_last"], (r["vx_last"] - r["vx_prev"]) * 1e3,
                         (r["vy_last"] - r["vy_prev"]) * 1e3, r["vx_pp_mV"], r["vy_pp_mV"], 0])
        else:
            s = read_csdf(str(ROOT / f"sim-runs/{run}/{run}.csd"))[0]
            rows.append([0] + stats_from_section(s))
    else:
        for s in read_csdf(str(ROOT / f"sim-runs/{run}/{run}.csd")):
            rows.append([round(s.step_value)] + stats_from_section(s))
    arr = np.array(rows)
    cache.parent.mkdir(parents=True, exist_ok=True)
    np.savetxt(cache, arr, delimiter=",", header=",".join(COLS), comments="", fmt="%.10g")
    return arr


def load(run, is_fund, rebuild):
    cache = ROOT / f"sim-runs/{run}/{run}_timestep.csv"
    if rebuild or not cache.exists():
        arr = build_cache(run, is_fund)
    else:
        arr = np.genfromtxt(cache, delimiter=",", skip_header=1)
    out = {}
    for r in np.atleast_2d(arr):
        step = int(round(r[0]))
        vx_raw, vy_raw = r[1], r[2]
        out[step] = {
            "vx": vx_raw + SETTLE_K * (vx_raw - MID),
            "vy": vy_raw + SETTLE_K * (vy_raw - MID),
            "set_vx": r[3], "set_vy": r[4], "pp_vx": r[5], "pp_vy": r[6],
        }
    return out


def theory_vx(n):
    if n % 2 == 0:
        return -2.0 * AH * EPS * math.sin(n * OMEGA_S_X)
    return -(2.0 * AH / (n * math.pi)) * math.cos(n * OMEGA_S_X)


def theory_vy(n):
    if n % 2 == 0:
        return 2.0 * AH * EPS * (-1) ** (n // 2) * math.sin(n * THETA_Y)
    sgn = (-1) ** ((n - 1) // 2)
    timing = -(2.0 * AH / (n * math.pi)) * sgn * math.sin(n * THETA_Y)
    slew = 2.0 * (S_Y / A) * AH * math.sin(n * math.pi / 2)
    return timing + slew


def model_deficit(n, h):
    return (n * 2 * math.pi * F_OSC * h) ** 2 / 12.0


def main():
    rebuild = "--rebuild" in sys.argv
    data = {}
    for h, runs in RUNS.items():
        fund = load(runs["fund"], True, rebuild)
        harm = load(runs["harm"], False, rebuild)
        data[h] = (fund, harm)

    ideal_vx = MID - K
    print(f"Ideal VX at 2 V = {ideal_vx:.7f} V, K = {K:.6f} V, THETA_Y = {math.degrees(THETA_Y):.5f} deg")
    print()

    print("Fundamental (2 V, no harmonic). Deficit = 1 - (VX - 2.5)/(-K), in %.")
    print(f"{'h (us)':>6} {'VX (V)':>12} {'VX - ideal (mV)':>16} {'deficit (%)':>12} "
          f"{'VY (V)':>12} {'VY - 2.5 (mV)':>14}")
    fund_def = {}
    for h in (20, 5, 2):
        f = data[h][0][0]
        d = 1.0 - (f["vx"] - MID) / (-K)
        fund_def[h] = d
        print(f"{h:6d} {f['vx']:12.7f} {(f['vx'] - ideal_vx) * 1e3:16.4f} {d * 100:12.4f} "
              f"{f['vy']:12.7f} {(f['vy'] - MID) * 1e3:14.4f}")
    print()

    print("Harmonic steps, deltas against the n = 2 step of the same run (mV). Theory from P-05.md.")
    print(f"{'h (us)':>6} {'n':>2} {'dVX meas':>10} {'dVX theory':>11} {'VX deficit %':>13} "
          f"{'dVY meas':>10} {'dVY theory':>11} {'VY resid':>9}")
    deficits = {}
    for h in (20, 5, 2):
        harm = data[h][1]
        base = harm[2]
        for n in sorted(harm):
            dvx = (harm[n]["vx"] - base["vx"]) * 1e3
            dvy = (harm[n]["vy"] - base["vy"]) * 1e3
            if n % 2 == 1:
                th_x = theory_vx(n) * 1e3
                th_y = theory_vy(n) * 1e3
                defi = (1.0 - dvx / th_x) * 100
                deficits[(h, n)] = defi
                print(f"{h:6d} {n:2d} {dvx:10.4f} {th_x:11.4f} {defi:13.4f} "
                      f"{dvy:10.4f} {th_y:11.4f} {dvy - th_y:9.4f}")
            else:
                print(f"{h:6d} {n:2d} {dvx:10.4f} {theory_vx(n) * 1e3:11.4f} {'':>13} "
                      f"{dvy:10.4f} {theory_vy(n) * 1e3:11.4f} {dvy - theory_vy(n) * 1e3:9.4f}")
    print()

    print("Even harmonic n = 2 against its own step, without the n = 2 baseline correction:")
    for h in (20, 5, 2):
        harm = data[h][1]
        print(f"  h = {h:2d} us: VX(n=2) - VX fundamental = "
              f"{(harm[2]['vx'] - data[h][0][0]['vx']) * 1e3:+.4f} mV, "
              f"VY(n=2) - VY fundamental = {(harm[2]['vy'] - data[h][0][0]['vy']) * 1e3:+.4f} mV")
    print()

    print("Convergence. Fundamental deficit ratio and model (n w h)^2/12 for n = 1, 3, 7 (in %).")
    print(f"{'quantity':>12} {'20 us':>10} {'5 us':>10} {'2 us':>10} {'20/5':>8} {'20/2':>8}")
    f20, f5, f2 = fund_def[20], fund_def[5], fund_def[2]
    print(f"{'fund meas':>12} {f20 * 100:10.4f} {f5 * 100:10.4f} {f2 * 100:10.4f} "
          f"{f20 / f5:8.2f} {f20 / f2:8.2f}")
    for n in (1, 3, 7):
        m = [model_deficit(n, h) * 100 for h in (20e-6, 5e-6, 2e-6)]
        print(f"{'model n=' + str(n):>12} {m[0]:10.4f} {m[1]:10.4f} {m[2]:10.4f} "
              f"{m[0] / m[1]:8.2f} {m[0] / m[2]:8.2f}")
    print()
    for n in (3, 7):
        m = [model_deficit(n, h) * 100 for h in (20e-6, 5e-6, 2e-6)]
        meas = [deficits[(h, n)] for h in (20, 5, 2)]
        print(f"n = {n}: deficit meas (%) {meas[0]:.4f}, {meas[1]:.4f}, {meas[2]:.4f}; "
              f"model (%) {m[0]:.4f}, {m[1]:.4f}, {m[2]:.4f}; "
              f"meas ratio 20/5 = {meas[0] / meas[1]:.2f}, 20/2 = {meas[0] / meas[2]:.2f}")
    print()

    print("Settling check (raw, mV) and ripple (mV p-p) per run, n = 3 step:")
    for h in (20, 5, 2):
        harm = data[h][1]
        st = data[h][0][0]
        print(f"  h = {h:2d} us: fund set VX {st['set_vx']:+.4f}, set VY {st['set_vy']:+.4f}; "
              f"n = 3 set VX {harm[3]['set_vx']:+.4f}, set VY {harm[3]['set_vy']:+.4f}; "
              f"n = 3 ripple VX {harm[3]['pp_vx']:.3f}, VY {harm[3]['pp_vy']:.3f}")


if __name__ == "__main__":
    main()
