"""P-32a and P-32b: overload of the front end and DC step at the drains (LIA-AFE-Eval).

Run from simulations/ti-pspice:  python docs/sim-results/scripts/P-32_overload.py
Reads sim-runs/P32a_overload/P32a_overload.csd (vda = 10, 50, 100 mV) and
sim-runs/P32b_dstep/P32b_dstep.csd (dstep = 0, 20, 100 mV, vda = 10 mV).
Circuits: circuits/afe_eval_P32a.cir and circuits/afe_eval_P32b.cir (cpf = 15 nF). No new simulation is run.

Measures:
  P-32a: amplitude of each node by a least-squares fit at f0 over 20 whole periods from 60 ms, peak of each node
         from 60 ms, clipping flag (samples within 1 mV of the peak), X/Y scaling against the 10 mV run.
  P-32b: difference of each run from the dstep = 0 run on a 1 us grid, period-averaged (boxcar of one period,
         removes f0 and 2f0 ripple), peak disturbance, recovery time to 0.1 mV (last time above 0.1 mV),
         DC shift of INA_OUT over the last 20 periods.
  Cross-check: P32b dstep = 0 against P32a vda = 10 mV (same circuit).
"""
import re
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools"))
from csdf import read_csdf  # noqa: E402

F0 = 518.0
T0 = 1.0 / F0
N_PER = 20
TW = 0.060                  # start of the settled window
WIN = N_PER * T0            # 38.610 ms
TEND = 0.3                  # end of the run
DT = 1e-6                   # uniform grid for the difference analysis
RAIL = 5.12                 # +5VA, +5.3 V default input (P-23)
REC_TOL = 0.1e-3            # recovery tolerance, V
T_STEP = 0.050              # R60/C74 step time (PULSE TD)
TAU_R60 = 10e-3             # R60 x C74 = 1 kOhm x 10 uF
GAIN_INA = 9.8968           # INA828 gain with RG 5.62 kOhm (P-27)
K_STEP = 1.1                # VSUP_A per dstep (entry value, U10A buffer and R21/R23 divider)

NODES_A = ["INA_OUT", "HPF_OUT", "BPF_OUT", "X_DEM", "X_OUT", "Y_OUT", "DRN_A"]
NODES_B = NODES_A + ["VSUP_A"]


def step_key(v):
    try:
        return round(float(v), 9)
    except (TypeError, ValueError):
        return round(float(re.findall(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?", str(v))[0]), 9)


def load(name, nodes):
    out = {}
    for s in read_csdf(ROOT / "sim-runs" / name / f"{name}.csd"):
        t = np.real(np.asarray(s.x)).astype(float)
        d = {n: np.asarray(s[f"V({n})"], float) for n in nodes}
        out[step_key(s.step_value)] = (t, d)
    return out


def tmean(t, y, t0, t1):
    m = (t > t0) & (t < t1)
    tt = np.concatenate(([t0], t[m], [t1]))
    yy = np.concatenate(([np.interp(t0, t, y)], y[m], [np.interp(t1, t, y)]))
    return np.trapezoid(yy, tt) / (t1 - t0)


def fit_f0(t, y, t0, t1):
    """Least-squares c + a sin + b cos at f0 over [t0, t1] on a uniform 1 us grid.
    Returns (mean, amplitude pk). The uniform grid avoids the bias of the adaptive samples."""
    tu = np.arange(t0, t1 - DT / 2, DT)
    yu = np.interp(tu, t, y)
    w = 2 * np.pi * F0
    A = np.column_stack([np.ones(tu.size), np.sin(w * tu), np.cos(w * tu)])
    c, a, b = np.linalg.lstsq(A, yu, rcond=None)[0]
    return c, float(np.hypot(a, b))


TAIL0 = TEND - WIN          # last 20 whole periods, settled check (0.2614 s to 0.3 s)


def uniform(t, y):
    tu = np.arange(0.0, TEND + DT / 2, DT)
    return tu, np.interp(tu, t, y)


def period_mean(tu, yu):
    """Trailing mean over one period: M(t) = (I(t) - I(t - T0)) / T0."""
    cum = np.concatenate(([0.0], np.cumsum((yu[1:] + yu[:-1]) / 2 * DT)))
    lag = np.interp(tu - T0, tu, cum, left=0.0)
    return (cum - lag) / T0


def plateau_fraction(t, y, t0, t1, tol=1e-3):
    m = (t >= t0) & (t <= t1)
    pk = np.max(np.abs(y[m]))
    return float(np.mean(np.abs(y[m]) >= pk - tol))


def part_a():
    runs = load("P32a_overload", NODES_A)
    print("=== P-32a: drain amplitude sweep (vda) ===")
    print(f"{'vda mV':>7} {'INA pk':>9} {'HPF pk':>9} {'BPF pk':>9} {'X_DEM pk':>9} "
          f"{'X mean':>10} {'Y mean':>10} {'R mV':>9} {'BPF fit':>9} {'R/BPFfit':>9} "
          f"{'DRN pk':>9} {'BPF/vda':>8}")
    res = {}
    for key in sorted(runs):
        t, d = runs[key]
        X = tmean(t, d["X_OUT"], TW, TW + WIN) * 1e3
        Y = tmean(t, d["Y_OUT"], TW, TW + WIN) * 1e3
        R = np.hypot(X, Y)
        _, bpf_fit = fit_f0(t, d["BPF_OUT"], TW, TW + WIN)
        bpf_fit *= 1.0
        pk = {n: float(np.max(np.abs(d[n][(t >= TW)]))) for n in NODES_A}
        res[key] = dict(X=X, Y=Y, R=R, bpf=bpf_fit, pk=pk, t=t, d=d)
        print(f"{key*1e3:7.1f} {pk['INA_OUT']:9.4f} {pk['HPF_OUT']:9.4f} {pk['BPF_OUT']:9.4f} "
              f"{pk['X_DEM']:9.4f} {X:10.3f} {Y:10.3f} {R:9.3f} {bpf_fit:9.4f} "
              f"{R / 1e3 / (2 / np.pi * bpf_fit):9.5f} {pk['DRN_A']*1e3:9.3f} {bpf_fit / key:8.3f}")
    print("\nPeak |V| (V) from 60 ms to 0.3 s and rail margin (rail = +/-5.12 V):")
    print(f"{'vda mV':>7} " + " ".join(f"{n:>10}" for n in NODES_A) + f" {'min margin':>11} {'clip node':>12}")
    for key in sorted(res):
        pk = res[key]["pk"]
        margins = {n: RAIL - pk[n] for n in NODES_A}
        worst = min(margins, key=margins.get)
        print(f"{key*1e3:7.1f} " + " ".join(f"{pk[n]:10.4f}" for n in NODES_A)
              + f" {margins[worst]:11.4f} {worst:>12}")
    print("\nPlateau test (fraction of samples within 1 mV of the peak, sine ~ 0.02 to 0.03):")
    print(f"{'vda mV':>7} " + " ".join(f"{n:>10}" for n in NODES_A))
    for key in sorted(res):
        t, d = res[key]["t"], res[key]["d"]
        print(f"{key*1e3:7.1f} " + " ".join(f"{plateau_fraction(t, d[n], TW, TEND):10.4f}" for n in NODES_A))

    print("\nScaling against the 10 mV run (linear = vda / 10 mV):")
    base = res[min(res)]
    print(f"{'vda mV':>7} {'X lin mV':>10} {'X meas mV':>10} {'X err %':>9} {'Y lin mV':>10} "
          f"{'Y meas mV':>10} {'Y err %':>9} {'BPF ideal V':>12} {'BPF err %':>10}")
    for key in sorted(res):
        g = key / min(res)
        Xl = base["X"] * g
        Yl = base["Y"] * g
        bpf_ideal = base["bpf"] * g
        print(f"{key*1e3:7.1f} {Xl:10.3f} {res[key]['X']:10.3f} {100*(res[key]['X']-Xl)/Xl:9.4f} "
              f"{Yl:10.3f} {res[key]['Y']:10.3f} {100*(res[key]['Y']-Yl)/Yl:9.4f} "
              f"{bpf_ideal:12.5f} {100*(res[key]['bpf']-bpf_ideal)/bpf_ideal:10.4f}")
    print(f"\nFront-end gain (BPF_OUT pk / 10 mV drain pk): {base['bpf'] / min(res) / 1:.4f} V/V "
          f"(entry 39.578 V/V)")

    print("\nSettled check: the last 20 whole periods (0.2614 s to 0.3 s) against the window from 60 ms:")
    print(f"{'vda mV':>7} {'X 60ms':>10} {'X tail':>10} {'Y 60ms':>10} {'Y tail':>10} "
          f"{'BPF fit 60ms':>13} {'BPF fit tail':>13} {'tail/60 %':>10}")
    tail = {}
    for key in sorted(res):
        t, d = res[key]["t"], res[key]["d"]
        Xt = tmean(t, d["X_OUT"], TAIL0, TEND) * 1e3
        Yt = tmean(t, d["Y_OUT"], TAIL0, TEND) * 1e3
        _, bt = fit_f0(t, d["BPF_OUT"], TAIL0, TEND)
        tail[key] = dict(X=Xt, Y=Yt, bpf=bt)
        print(f"{key*1e3:7.1f} {res[key]['X']:10.3f} {Xt:10.3f} {res[key]['Y']:10.3f} {Yt:10.3f} "
              f"{res[key]['bpf']*1e3:13.3f} {bt*1e3:13.3f} {100*(bt-res[key]['bpf'])/res[key]['bpf']:10.4f}")

    print("\nScaling against the 10 mV run, settled tail window (linear = vda / 10 mV):")
    tb = tail[min(tail)]
    print(f"{'vda mV':>7} {'X lin mV':>10} {'X meas mV':>10} {'X err %':>9} {'Y lin mV':>10} "
          f"{'Y meas mV':>10} {'Y err %':>9} {'BPF err %':>10} {'R/(2/pi BPF) ':>14}")
    for key in sorted(tail):
        g = key / min(tail)
        Xl, Yl = tb["X"] * g, tb["Y"] * g
        Rm = np.hypot(tail[key]["X"], tail[key]["Y"])
        print(f"{key*1e3:7.1f} {Xl:10.3f} {tail[key]['X']:10.3f} {100*(tail[key]['X']-Xl)/Xl:9.4f} "
              f"{Yl:10.3f} {tail[key]['Y']:10.3f} {100*(tail[key]['Y']-Yl)/Yl:9.4f} "
              f"{100*(tail[key]['bpf']-tb['bpf']*g)/(tb['bpf']*g):10.4f} "
              f"{Rm/1e3/(2/np.pi*tail[key]['bpf']):14.5f}")
    return res


def part_b():
    runs = load("P32b_dstep", NODES_B)
    keys = sorted(runs)
    print("\n=== P-32b: DC step at the drains (vda = 10 mV) ===")
    tu = np.arange(0.0, TEND + DT / 2, DT)
    grid = {}
    for k in keys:
        t, d = runs[k]
        grid[k] = {n: np.interp(tu, t, d[n]) for n in NODES_B}
    base = grid[0.0]

    print("Cross-check: P32b dstep = 0 against P32a vda = 10 mV, maximum difference over 60 ms to 0.3 s (mV):")
    a = load("P32a_overload", NODES_A)
    ta, da = a[min(a)]
    for n in ["X_OUT", "Y_OUT", "BPF_OUT", "INA_OUT"]:
        ref = np.interp(tu, ta, da[n])
        m = tu >= TW
        print(f"  {n:8s} max |diff| = {np.max(np.abs(ref[m]-base[n][m]))*1e3:.6f} mV")

    results = {}
    for k in keys:
        if k == 0.0:
            continue
        dd = {n: grid[k][n] - base[n] for n in NODES_B}
        mm = {n: period_mean(tu, dd[n]) for n in ["X_OUT", "Y_OUT"]}
        win = (tu >= T_STEP) & (tu <= TEND)
        pkraw = {n: float(np.max(np.abs(dd[n][win]))) for n in NODES_B}
        pkavg = {n: float(np.max(np.abs(mm[n][win]))) for n in mm}
        rec = {}
        for n in mm:
            over = np.where((np.abs(mm[n]) >= REC_TOL) & win)[0]
            if over.size == 0:
                rec[n] = 0.0
            elif over[-1] >= len(tu) - 1:
                rec[n] = float("nan")
            else:
                rec[n] = tu[over[-1]] - T_STEP
        # INA_OUT shift at the end of the run (last 20 whole periods)
        tl = TEND - WIN
        dina_end = np.mean(dd["INA_OUT"][tu >= tl])
        dina_pk = float(np.max(np.abs(dd["INA_OUT"][win])))
        dv = dict(
            expected_ina=-GAIN_INA * K_STEP * k,
            ina_end=dina_end,
            ina_pk=dina_pk,
            dvsup_end=np.mean(dd["VSUP_A"][tu >= tl]),
            dhpf_pk=pkraw["HPF_OUT"],
            dbpf_pk=pkraw["BPF_OUT"],
            dx_raw=pkraw["X_OUT"], dy_raw=pkraw["Y_OUT"],
            dx_avg=pkavg["X_OUT"], dy_avg=pkavg["Y_OUT"],
            rec_x=rec["X_OUT"], rec_y=rec["Y_OUT"],
            dxend=np.mean(mm["X_OUT"][tu >= tl]), dyend=np.mean(mm["Y_OUT"][tu >= tl]),
            dx_tail=np.max(np.abs(mm["X_OUT"][tu >= 0.2])), dy_tail=np.max(np.abs(mm["Y_OUT"][tu >= 0.2])),
        )
        results[k] = dict(dv=dv, grid=grid[k])
        print(f"\n-- dstep = {k*1e3:.0f} mV --")
        print(f"  VSUP_A end shift (last 20 periods): {dv['dvsup_end']*1e3:.4f} mV "
              f"(expected {K_STEP * k * 1e3:.2f} mV)")
        print(f"  INA_OUT shift at end (mean, last 20 periods): {dina_end*1e3:.4f} mV, "
              f"expected {dv['expected_ina']*1e3:.4f} mV, error {100*(dina_end-dv['expected_ina'])/abs(dv['expected_ina']):.4f} %")
        print(f"  INA_OUT peak disturbance from 50 ms: {dina_pk*1e3:.4f} mV")
        print(f"  HPF_OUT raw difference peak: {pkraw['HPF_OUT']*1e3:.4f} mV; BPF_OUT raw difference peak: "
              f"{pkraw['BPF_OUT']*1e3:.4f} mV")
        print(f"  X_OUT raw difference peak {dv['dx_raw']*1e6:.3f} uV, period-averaged peak {dv['dx_avg']*1e6:.3f} uV, "
              f"recovery to 0.1 mV at {dv['rec_x']*1e3:.2f} ms after 50 ms")
        print(f"  Y_OUT raw difference peak {dv['dy_raw']*1e6:.3f} uV, period-averaged peak {dv['dy_avg']*1e6:.3f} uV, "
              f"recovery to 0.1 mV at {dv['rec_y']*1e3:.2f} ms after 50 ms")
        print(f"  X_OUT / Y_OUT period-averaged difference over the last 20 periods: {dv['dxend']*1e6:.3f} uV, "
              f"{dv['dyend']*1e6:.3f} uV")
        print(f"  X_OUT / Y_OUT maximum period-averaged difference from 200 ms: {dv['dx_tail']*1e6:.3f} uV, "
              f"{dv['dy_tail']*1e6:.3f} uV")
        for n in ["INA_OUT", "HPF_OUT", "BPF_OUT", "X_DEM", "X_OUT", "Y_OUT"]:
            mx = float(np.max(np.abs(grid[k][n][tu >= TW])))
            print(f"  clipping check {n:8s} max |V| = {mx:.4f} V, margin to +/-{RAIL} V = {RAIL - mx:.4f} V")
    return results


SR_RISE = 7.07 / 790e-9     # OPAx196.LIB: AOL_2 IPOS = 7.07 into C_C5 = 790 nF, 8.95 V/us
SR_FALL = 5.24 / 790e-9     # AOL_2 INEG = -5.24 into C_C5, 6.63 V/us


def part_c():
    """Judge checks (8 November 2026): phase of (X, Y), slew model of the demodulator edges,
    cause of the cross-check difference, and the impulse-area model of the P-32b recovery."""
    print("\n=== Checks: phase, edge slew, cross-check, recovery model ===")
    runs = load("P32a_overload", NODES_A)
    keys = sorted(runs)
    rows = []
    for k in keys:
        t, d = runs[k]
        X = tmean(t, d["X_OUT"], TAIL0, TEND)
        Y = tmean(t, d["Y_OUT"], TAIL0, TEND)
        tu = np.arange(TAIL0, TEND - DT / 2, DT)
        w = 2 * np.pi * F0
        M = np.column_stack([np.ones(tu.size), np.sin(w * tu), np.cos(w * tu)])
        _, a, b = np.linalg.lstsq(M, np.interp(tu, t, d["BPF_OUT"]), rcond=None)[0]
        rows.append((k, X, Y, np.hypot(a, b), np.degrees(np.arctan2(Y, X)), np.degrees(np.arctan2(b, a))))
    k0, X0, Y0, A0, p0, pb0 = rows[0]
    print("Tail window, scaling by the fitted BPF_OUT amplitude (not the nominal vda):")
    print(f"{'vda mV':>7} {'phase(X,Y) deg':>15} {'dphase deg':>11} {'dphase BPF deg':>15} "
          f"{'X err %':>8} {'Y err %':>8} {'|Y| short mV':>13} {'slew model mV':>14}")
    phi = np.radians(p0)
    s_y = np.abs(np.cos(phi))           # BPF_OUT at the Y edges, per unit amplitude
    s_x = np.abs(np.sin(phi))           # BPF_OUT at the X edges
    for k, X, Y, A, p, pb in rows:
        g = A / A0
        dy = abs(Y0) * g - abs(Y)
        # slew area per edge (2 s)^2 / (2 SR), two edges per period, minus its linear part from 10 mV
        model = 4 * F0 * s_y**2 / SR_FALL * A * (A - A0)
        print(f"{k*1e3:7.1f} {p:15.4f} {p-p0:11.4f} {pb-pb0:15.4f} {100*(X/(X0*g)-1):8.4f} "
              f"{100*(Y/(Y0*g)-1):8.4f} {dy*1e3:13.3f} {model*1e3:14.3f}")
    print(f"Edge values per unit amplitude: X edges {s_x:.4f}, Y edges {s_y:.4f}. "
          f"Model slew rates: rising {SR_RISE/1e6:.2f} V/us, falling {SR_FALL/1e6:.2f} V/us.")
    t, d = runs[keys[-1]]
    n0 = int(np.ceil(TAIL0 / (T0 / 2)))
    for n in (n0, n0 + 1):
        te = n * T0 / 2
        print(f"  X edge {n % 2}: BPF_OUT {np.interp(te, t, d['BPF_OUT']):+.4f} V, X_DEM "
              f"{np.interp(te - 1e-6, t, d['X_DEM']):+.4f} V -> {np.interp(te + 3e-6, t, d['X_DEM']):+.4f} V; "
              f"Y edge {n % 2} (REF_Y {'rising' if n % 2 == 0 else 'falling'}): BPF_OUT "
              f"{np.interp(te + T0 / 4, t, d['BPF_OUT']):+.4f} V, Y_DEM steps by "
              f"{(2 if n % 2 == 0 else -2) * np.interp(te + T0 / 4, t, d['BPF_OUT']):+.4f} V "
              f"(Y_DEM = 2 D2 - BPF_OUT)")

    print("\nCross-check cause (P32b dstep = 0 against P32a vda = 10 mV):")
    b = load("P32b_dstep", NODES_B)
    ta, da = runs[keys[0]]
    tb, db = b[0.0]
    n = min(ta.size, tb.size)
    div = np.nonzero(np.abs(ta[:n] - tb[:n]) > 1e-15)[0]
    print(f"  samples {ta.size} and {tb.size}, time grids diverge at t = {ta[div[0]]*1e9:.1f} ns")
    tu = np.arange(0.0, TEND + DT / 2, DT)
    m = tu >= TW
    for nm in ["BPF_OUT", "X_DEM", "Y_OUT"]:
        dd = np.abs(np.interp(tu, ta, da[nm]) - np.interp(tu, tb, db[nm]))
        j = np.argmax(np.where(m, dd, 0))
        print(f"  {nm:8s} max {dd[m].max()*1e3:.3f} mV at {(tu[j] % T0)/T0*360:.1f} deg of the period, "
              f"99.9th percentile {np.percentile(dd[m], 99.9)*1e3:.4f} mV, median {np.median(dd[m])*1e6:.3f} uV")
    _, fa = fit_f0(ta, da["BPF_OUT"], TAIL0, TEND)
    _, fb = fit_f0(tb, db["BPF_OUT"], TAIL0, TEND)
    print(f"  BPF_OUT fitted amplitude, tail: {fa*1e3:.4f} mV and {fb*1e3:.4f} mV ({(fb-fa)*1e6:+.2f} uV)")

    print("\nRecovery model: X/Y difference treated as an impulse of area S into the post-filter "
          "(two poles, 200 kOhm x cpf, Q = 0.5):")
    for k in sorted(b):
        if k == 0.0:
            continue
        for nm in ["X_OUT", "Y_OUT"]:
            dd = np.interp(tu, b[k][0], b[k][1][nm]) - np.interp(tu, tb, db[nm])
            w = tu >= T_STEP
            S = np.trapezoid(dd[w], tu[w])
            for tau in (3e-3, 0.3):
                # h(t) = S t / tau^2 exp(-t / tau): peak S / (e tau), last time at 0.1 mV
                tt = np.linspace(tau, 40 * tau, 200001)
                h = abs(S) * tt / tau**2 * np.exp(-tt / tau)
                above = tt[h >= REC_TOL]
                trec = f"{above[-1]*1e3:.1f} ms" if above.size else "never above 0.1 mV"
                print(f"  dstep {k*1e3:.0f} mV {nm}: S = {S*1e6:.3f} uV s, tau {tau*1e3:.0f} ms: "
                      f"peak {abs(S)/(np.e*tau)*1e3:.4f} mV, recovery {trec}")


def main():
    part_a()
    part_b()
    part_c()


if __name__ == "__main__":
    main()
