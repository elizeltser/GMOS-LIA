"""P-11 resistor mismatch with input offset (index entry P-11).

Reads the two P-11 runs (fast settings, circuits/lia_v3_fast_P11p.cir and _P11m.cir,
Vampl = 0.2 V, p = 0, cout = 1 uF, tau = 10 ms):

  P11p_mismatch  ost = +0.3 V, .STEP PARAM dr1 LIST -10m -1m 0 1m 10m
  P11m_mismatch  ost = -0.3 V, .STEP PARAM dr1 LIST -10m -1m 0 1m 10m

The LIST is sorted, because PSpice rejects an unsorted list (docs/simulation-quirks.md).
The step values are matched by step_value, not by section index.

Settled window: the last 20 whole periods of 517 Hz, 111.32 ms to 150.00 ms. The
window of the same length before it is the settling check. Means are time-weighted
trapezoid means of the PSpice points, with the window ends interpolated. The settling
bias is removed as in P-08_fast.py.

Deltas: each dr1 step minus the dr1 = 0 step of the same run.
Expected (entry): delta VX = -(delta/2) x ost - (delta/2) x 2A/pi, delta VY = 0, with
delta = dr1 (R1 = 10 kOhm x (1 + dr1)). Pass: |diff| <= max(0.005 mV, 1 % of expected).

Extra checks (not in the entry):
  - the ost dependence of VX at dr1 = 0, against the P-03 offset sweep (2 V amplitude);
  - whether the ost term changes with dr1 (interaction);
  - two diagnostic runs, if present in sim-runs/, with ost = -0.3, 0, +0.3 V and dr1 = 0:
      P11diag_ideal_opamp  op amp replaced by a VCVS of gain 1e6 (no CMRR, no Vos(Vcm), no Ib)
      P11diag_ron01        switch RON = 0.1 Ohm instead of 120 Ohm
      P11diag_noqinj       switch QINJ = 0, CS = CD = 1 fF, ILK = 0 (RON = 120 Ohm)

Run from the project root:
    python docs/sim-results/scripts/P-11_mismatch.py
"""

import csv
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

SIM = ROOT / "sim-runs"
PLOT = ROOT / "docs/sim-results/plots/P-11_mismatch.png"
P03_STEPS = SIM / "P03a_ost_p0/P03a_ost_p0_steps.csv"

F_OSC = 517.0
T = 1.0 / F_OSC
N_PER = 20
TW = N_PER * T
T_END = 0.15
TAU = 10e3 * 1e-6
MID = 2.5
A_IN = 0.2
K_DEM = 2 * A_IN / math.pi        # 127.324 mV
PASS_ABS = 0.005e-3
PASS_REL = 0.01
PASS_VY = 0.005e-3
VX_IDEAL_OST0 = MID - K_DEM       # p = 0, dr1 = 0, ost = 0

RUNS = {
    +0.3: "P11p_mismatch",
    -0.3: "P11m_mismatch",
}
DIAG = {
    "ideal op amp (VCVS 1e6)": "P11diag_ideal_opamp",
    "RON = 0.1 Ohm": "P11diag_ron01",
    "no QINJ, CS, CD, ILK": "P11diag_noqinj",
}


def window_mean(t, y, t0, t1):
    inside = (t > t0) & (t < t1)
    tt = np.concatenate(([t0], t[inside], [t1]))
    yy = np.concatenate(([np.interp(t0, t, y)], y[inside], [np.interp(t1, t, y)]))
    return float(np.trapezoid(yy, tt) / (t1 - t0))


def analyse(sec):
    t = sec.x
    t1 = T_END
    t0 = t1 - TW
    tp0 = t0 - TW
    r = {}
    vx_raw = window_mean(t, sec["V(VX)"], t0, t1)
    vy_raw = window_mean(t, sec["V(VY)"], t0, t1)
    vx_prior = window_mean(t, sec["V(VX)"], tp0, t0)
    vy_prior = window_mean(t, sec["V(VY)"], tp0, t0)
    e = math.exp(TW / TAU)
    r["dvx_prior"] = vx_raw - vx_prior
    r["dvy_prior"] = vy_raw - vy_prior
    r["bias_vx"] = r["dvx_prior"] / (1 - e)
    r["bias_vy"] = r["dvy_prior"] / (1 - e)
    f = (TAU / TW) * (1 - math.exp(-TW / TAU)) * math.exp(-t0 / TAU)
    r["F"] = f
    r["vx"] = (vx_raw - MID * f) / (1 - f)
    r["vy"] = (vy_raw - MID * f) / (1 - f)
    r["vx_raw"] = vx_raw
    r["vy_raw"] = vy_raw
    return r


def load(folder):
    path = SIM / folder / f"{folder}.csd"
    secs = read_csdf(str(path))
    return {round(s.step_value, 9): analyse(s) for s in secs}


def expected_dvx(dr1, ost):
    return -(dr1 / 2) * ost - (dr1 / 2) * K_DEM


def pct(meas, exp):
    return 100.0 * (meas - exp) / exp if abs(exp) > 1e-12 else float("nan")


def p03_slope():
    """Slope of VX against ost from the P-03 offset sweep at 2 V, |ost| <= 0.4 V."""
    if not P03_STEPS.exists():
        return None
    rows = list(csv.DictReader(open(P03_STEPS)))
    data = {round(float(r["ost"]), 6): float(r["vx_last"]) for r in rows}
    ref = data[0.0]
    xs, ys = [], []
    for ost, vx in data.items():
        if abs(ost) <= 0.4 + 1e-9:
            xs.append(ost)
            ys.append(vx - ref)
    xs, ys = np.array(xs), np.array(ys)
    slope, icpt = np.polyfit(xs, ys, 1)
    resid = ys - (slope * xs + icpt)
    return slope, float(np.max(np.abs(resid))), len(xs), data


def edge_check(slope_vx):
    """Period-mean error of V(VX_DEMOD) at ost = +0.3 V, from the transient run P11edge_ost03.

    Run: python tools/run_sim.py circuits/lia_v3_fast_P11p.cir --name P11edge_ost03
             --analysis ".TRAN 0 4m 0 5u SKIPBP" --extra ".OPTIONS NUMDGT=8"
             --extra ".IC V(VX)=2.5 V(VY)=2.5" --probe "V(VX_DEMOD)" "V(N00261)"
    The window is the second full period, T to 2T. The error is the time-weighted mean of
    V(VX_DEMOD) minus the entry ideal (50 % duty, -1 state in the first half). It is split
    into the reference duty part (reference-timed ideal, switching at the 50 % points of
    V(N00261)) and the switch delay part (demodulator against the reference-timed ideal).
    """
    path = SIM / "P11edge_ost03" / "P11edge_ost03.csd"
    if not path.exists():
        print("P11edge_ost03 not found, mechanism check skipped")
        return
    s = read_csdf(str(path))[0]
    t = s.x
    dem = s["V(VX_DEMOD)"]
    ctl = s["V(N00261)"]
    ost = 0.3
    t0, t1 = T, 2 * T
    win = 0.5e-6

    def crossing(y, t_center, rising):
        """50 % crossing of y near t_center (window +/- win), direction as given."""
        m = (t > t_center - win) & (t < t_center + win)
        x, yy = t[m], y[m] - 2.5
        a, b = yy[:-1], yy[1:]
        sel = (np.sign(a) != np.sign(b)) & ((b > a) if rising else (b < a))
        idx = np.where(sel)[0]
        if len(idx) != 1:
            raise RuntimeError(f"expected one crossing, found {len(idx)}")
        i = idx[0]
        return float(x[i] + (x[i + 1] - x[i]) * (-a[i]) / (b[i] - a[i]))

    # Edge at the start of the period: reference rises, demodulator falls (+1 to -1)
    ref_s = crossing(ctl, t0, True)
    dem_s = crossing(dem, t0, False)
    # Edge at T/2: reference falls, demodulator rises (-1 to +1)
    ref_h = crossing(ctl, t0 + T / 2 + 75e-9, False)
    dem_h = crossing(dem, t0 + T / 2 + 75e-9, True)
    d_r = dem_s - ref_s
    d_f = dem_h - ref_h
    print("Mechanism check: edges of V(VX_DEMOD) in the second period (transient at ost = +0.3 V)")
    print(f"  reference 50 % points: rising at {(ref_s-t0)*1e9:.1f} ns, falling at "
          f"{(ref_h-t0-T/2)*1e9:.1f} ns after T/2")
    print(f"  demodulator 50 % points: falling at {(dem_s-t0)*1e9:.1f} ns, rising at "
          f"{(dem_h-t0-T/2)*1e9:.1f} ns after T/2")
    print(f"  switch delay: after the rising reference edge {d_r*1e9:.1f} ns, after the falling "
          f"reference edge {d_f*1e9:.1f} ns, difference (falling minus rising) {(d_f-d_r)*1e9:.1f} ns")
    print(f"  reference high time (V(N00261) above 2.5 V): {(ref_h-ref_s)*1e6:.3f} us "
          f"(T/2 = {T/2*1e6:.3f} us, excess {(ref_h-ref_s-T/2)*1e9:.1f} ns)")

    g = np.linspace(t0, t1, 2000001)
    dg = np.interp(g, t, dem)
    ph = (g / T) % 1.0
    vin = MID + ost + A_IN * np.sin(2 * math.pi * F_OSC * g)
    ideal_entry = np.where(ph < 0.5, 2 * MID - vin, vin)
    cg = np.interp(g, t, ctl)
    ideal_ref = np.where(cg > 2.5, 2 * MID - vin, vin)

    def pmean(y):
        return float(np.trapezoid(y, g) / (t1 - t0))

    e_entry = pmean(dg - ideal_entry)
    e_ref = pmean(dg - ideal_ref)
    print(f"  period-mean error of V(VX_DEMOD) vs entry ideal: {e_entry*1e3:.5f} mV "
          f"(= {e_entry/ost*1e3:.5f} mV/V)")
    print(f"    duty part (entry ideal minus reference-timed ideal): {(e_entry-e_ref)*1e3:.5f} mV "
          f"(= {(e_entry-e_ref)/ost*1e3:.5f} mV/V)")
    print(f"    switch delay part (reference-timed ideal): {e_ref*1e3:.5f} mV "
          f"(= {e_ref/ost*1e3:.5f} mV/V)")
    print(f"  VX slope from P11p and P11m times 0.3 V: {slope_vx*ost*1e3:.5f} mV "
          f"(= {slope_vx*1e3:.5f} mV/V)")
    print(f"  switch delay part predicted from the edges, -2 (delta_fall - delta_rise) / T: "
          f"{-2*(d_f-d_r)/T*1e3:.5f} mV/V")
    print(f"  duty part predicted from the reference high time, -2 x excess / T: "
          f"{-2*(ref_h-ref_s-T/2)/T*1e3:.5f} mV/V")
    print()


def main():
    runs = {ost: load(name) for ost, name in RUNS.items()}
    p = runs[+0.3]
    m = runs[-0.3]

    print(f"T = {T*1e3:.6f} ms, window {(T_END-TW)*1e3:.4f} to {T_END*1e3:.4f} ms "
          f"({N_PER} periods), 2A/pi = {K_DEM*1e3:.4f} mV")
    print()

    print("Settling check: last window minus the window of the same length before it (mV)")
    print(f"{'run':<16}{'dr1':>8}{'dVX (mV)':>11}{'dVY (mV)':>11}{'bias VX (uV)':>14}{'bias VY (uV)':>14}")
    for name, runs_ in (("P11p (+0.3 V)", p), ("P11m (-0.3 V)", m)):
        for d, r in runs_.items():
            print(f"{name:<16}{d:>8.4g}{r['dvx_prior']*1e3:>11.4f}{r['dvy_prior']*1e3:>11.4f}"
                  f"{r['bias_vx']*1e6:>14.3f}{r['bias_vy']*1e6:>14.3f}")
    print()

    print("Absolute window means (V), settled, bias removed")
    print(f"{'run':<16}{'dr1':>8}{'VX (V)':>14}{'VY (V)':>14}{'VX - ideal0 (mV)':>18}")
    for name, runs_ in (("P11p (+0.3 V)", p), ("P11m (-0.3 V)", m)):
        for d, r in runs_.items():
            print(f"{name:<16}{d:>8.4g}{r['vx']:>14.7f}{r['vy']:>14.7f}"
                  f"{(r['vx']-VX_IDEAL_OST0)*1e3:>18.5f}")
    print()

    # Deltas and comparison
    checks = []
    print("Deltas against dr1 = 0 of the same run (mV) and comparison with the entry")
    print(f"{'run':<16}{'dr1':>8}{'dVX (mV)':>11}{'expected':>11}{'diff (mV)':>11}{'pct err':>9}"
          f"{'tol (mV)':>10}{'result':>8}{'dVY (mV)':>11}{'VY ok':>7}")
    for name, ost, runs_ in (("P11p (+0.3 V)", +0.3, p), ("P11m (-0.3 V)", -0.3, m)):
        base = runs_[0.0]
        for d in sorted(runs_):
            if d == 0.0:
                continue
            r = runs_[d]
            dvx = r["vx"] - base["vx"]
            dvy = r["vy"] - base["vy"]
            exp = expected_dvx(d, ost)
            tol = max(PASS_ABS, PASS_REL * abs(exp))
            ok = abs(dvx - exp) <= tol
            vy_ok = abs(dvy) < PASS_VY
            checks.append((name, d, dvx, exp, ok, dvy, vy_ok))
            print(f"{name:<16}{d:>8.4g}{dvx*1e3:>11.4f}{exp*1e3:>11.4f}{(dvx-exp)*1e3:>11.5f}"
                  f"{pct(dvx, exp):>9.3f}{tol*1e3:>10.4f}{'pass' if ok else 'FAIL':>8}"
                  f"{dvy*1e3:>11.5f}{'pass' if vy_ok else 'FAIL':>7}")
    print()

    # Expected table of the entry, for the record
    print("Expected table of the entry (mV), from the formula above")
    for d in (0.001, -0.001, 0.01, -0.01):
        print(f"  dr1 = {d:+.3f}: ost +0.3 V -> {expected_dvx(d, 0.3)*1e3:+.4f} mV, "
              f"ost -0.3 V -> {expected_dvx(d, -0.3)*1e3:+.4f} mV")
    print()

    # Ost term at dr1 = 0, and whether it changes with dr1
    vx_p0 = p[0.0]["vx"]
    vx_m0 = m[0.0]["vx"]
    slope_run = (vx_p0 - vx_m0) / 0.6
    print("Ost term of VX at dr1 = 0 (this run pair)")
    print(f"  VX(+0.3 V) = {vx_p0:.7f} V, VX(-0.3 V) = {vx_m0:.7f} V")
    print(f"  slope d VX / d ost = {slope_run*1e3:.5f} mV/V (central difference over +/-0.3 V)")
    print(f"  mean of the two = {(vx_p0+vx_m0)/2:.7f} V, ideal ost = 0 value {VX_IDEAL_OST0:.7f} V, "
          f"difference {((vx_p0+vx_m0)/2-VX_IDEAL_OST0)*1e3:.5f} mV")
    slope_run_y = (p[0.0]["vy"] - m[0.0]["vy"]) / 0.6
    print(f"  VY(+0.3 V) = {p[0.0]['vy']:.7f} V, VY(-0.3 V) = {m[0.0]['vy']:.7f} V")
    print(f"  slope d VY / d ost = {slope_run_y*1e3:.5f} mV/V (ideal: 0 mV/V)")
    print(f"  ideal (no ost term) slope at dr1 = 0: 0 mV/V")
    print()

    print("Interaction: does the ost term change with dr1?")
    print(f"{'dr1':>8}{'Delta_p - Delta_m (mV)':>24}{'expected -0.3 dr1 (mV)':>24}{'residual (mV)':>15}")
    for d in sorted(p):
        if d == 0.0:
            continue
        dp = p[d]["vx"] - p[0.0]["vx"]
        dm = m[d]["vx"] - m[0.0]["vx"]
        exp = -0.3 * d
        print(f"{d:>8.4g}{(dp-dm)*1e3:>24.5f}{exp*1e3:>24.5f}{(dp-dm-exp)*1e3:>15.5f}")
    print()

    # P-03 comparison
    res = p03_slope()
    if res is None:
        print("P-03 step table not found, comparison skipped")
    else:
        slope03, maxres, npts, data = res
        print("P-03 offset sweep (2 V amplitude, p = 0, dr1 = 0), VX step values")
        print(f"  linear fit of VX - VX(ost = 0) against ost, |ost| <= 0.4 V ({npts} steps): "
              f"slope = {slope03*1e3:.5f} mV/V, max residual {maxres*1e6:.2f} uV")
        print(f"  P-11 slope at 0.2 V amplitude: {slope_run*1e3:.5f} mV/V. "
              f"Ratio P-11 / P-03 = {slope_run/slope03:.4f}")
        print(f"  P-03 point at ost = -0.4 V: VX - VX(0) = {(data[-0.4]-data[0.0])*1e3:.4f} mV")
    print()

    # Diagnostic runs
    diag = {}
    for label, folder in DIAG.items():
        path = SIM / folder / f"{folder}.csd"
        if not path.exists():
            continue
        secs = read_csdf(str(path))
        vals = {}
        for s in secs:
            vals[round(s.step_value, 6)] = (window_mean(s.x, s["V(VX)"], T_END - TW, T_END),
                                            window_mean(s.x, s["V(VY)"], T_END - TW, T_END))
        diag[label] = vals
    if diag:
        print("Diagnostic runs, dr1 = 0, VX window means (no settling correction, bias < 1 uV)")
        print(f"{'variant':<26}{'VX(-0.3) (V)':>15}{'VX(0) (V)':>14}{'VX(+0.3) (V)':>15}"
              f"{'slope (mV/V)':>14}{'VY slope (mV/V)':>17}")
        for label, vals in diag.items():
            keys = sorted(vals)
            if len(keys) != 3:
                print(f"{label:<26}{len(keys)} steps found, expected 3")
                continue
            vm, v0, vp = (vals[k][0] for k in keys)
            ym, _, yp = (vals[k][1] for k in keys)
            sl = (vp - vm) / 0.6
            syl = (yp - ym) / 0.6
            print(f"{label:<26}{vm:>15.7f}{v0:>14.7f}{vp:>15.7f}{sl*1e3:>14.5f}{syl*1e3:>17.5f}")
        print()
    else:
        print("No diagnostic runs found in sim-runs/ (P11diag_*), so the cause is not tested here.")
        print()

    edge_check(slope_run)

    # Plot
    fig, ax = plt.subplots(1, 2, figsize=(11, 4.5))
    dd = sorted(d for d in p if d != 0.0)
    for name, ost, runs_, style in (("ost = +0.3 V", 0.3, p, "o-"), ("ost = -0.3 V", -0.3, m, "s-")):
        meas = [(runs_[d]["vx"] - runs_[0.0]["vx"]) * 1e3 for d in dd]
        ax[0].plot([d * 100 for d in dd], meas, style, label=f"{name}, measured")
        ax[0].plot([d * 100 for d in dd], [expected_dvx(d, ost) * 1e3 for d in dd], "k--", lw=0.8,
                   label=f"{name}, expected" if ost > 0 else None)
    ax[0].set_xlabel("dr1 (% change of R1)")
    ax[0].set_ylabel("delta VX vs dr1 = 0 (mV)")
    ax[0].set_title("P-11 delta VX against the entry formula")
    ax[0].legend(fontsize=8)
    ost_axis = [-0.3, 0.3]
    ax[1].plot(ost_axis, [m[0.0]["vx"], p[0.0]["vx"]], "o-", label="P-11 at 0.2 V amplitude")
    ax[1].axhline(VX_IDEAL_OST0, color="k", ls="--", lw=0.8, label="ideal (no ost term)")
    if res is not None:
        xs = np.linspace(-0.4, 0.4, 9)
        ax[1].plot(xs, VX_IDEAL_OST0 + slope03 * xs, ":", lw=0.8,
                   label="P-03 slope (2 V), same origin")
    ax[1].set_xlabel("ost (V)")
    ax[1].set_ylabel("VX at dr1 = 0 (V)")
    ax[1].set_title("VX against ost, dr1 = 0")
    ax[1].legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(PLOT, dpi=120)
    print(f"plot written: {PLOT}")


if __name__ == "__main__":
    main()
