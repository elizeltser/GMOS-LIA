"""P-10 coherent pickup on the reference and the rail (index entry P-10).

Reads the six P-10 runs (fast settings, circuits/lia_v3_fast copies, Vampl = 0.2 V,
ost = 0, p = 0, cout = 1 uF, tau = 10 ms):

  P10a0_refripple      .STEP PARAM aref LIST 0 1m          pref = 0,  kref = 0
  P10a90_refripple     .STEP PARAM aref LIST 0 1m          pref = 90, kref = 0
  P10b_railripple      .STEP PARAM arail LIST 0 1m         prail = 0, kref = 0
  P10c_railripple_kref .STEP PARAM arail LIST 0 1m         prail = 0, kref = 1
  P10d_iexc            .STEP PARAM iexc LIST 0 10m         rrail = 1 Ohm, kref = 0
  P10e_iexc_kref       .STEP PARAM iexc LIST 0 10m         rrail = 1 Ohm, kref = 1

Settled window: the last 20 whole periods of f_osc = 517 Hz. The run ends at 0.15 s,
so the window is 111.32 ms to 150.00 ms (38.68 ms). The window of the same length
before it (72.63 ms to 111.32 ms) is the settling check.

Means: time-weighted trapezoid means of the PSpice points, with the window ends
interpolated. Point means are biased by the adaptive step (docs/simulation-quirks.md).
The settling bias of VX and VY is removed as in P-08_fast.py. Its size is printed.

Readout (entry definition): VX and VY minus the mean of V(REF) in the same window.
Deltas: each step minus step 0 of the same run. Absolute deltas are printed too.

Ripple: least-squares fit of the 1f and 2f sinusoids on a 0.5 us grid, used for the
rail ripple and the reference ripple only.

Run from the project root:
    python docs/sim-results/scripts/P-10_pickup.py
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

SIM = ROOT / "sim-runs"
PLOT = ROOT / "docs/sim-results/plots/P-10_pickup.png"

F_OSC = 517.0
T = 1.0 / F_OSC
N_PER = 20
TW = N_PER * T
T_END = 0.15
TAU = 10e3 * 1e-6          # R3 x C1 = 10 kOhm x 1 uF
MID = 2.5
A_IN = 0.2                 # Vampl
K_DEM = 2 * A_IN / math.pi  # 2A/pi = 127.324 mV
RRAIL_TEST = 1.0           # Ohm, P10d and P10e
PASS_ABS = 0.01e-3         # V, entry pass criterion
PASS_REL = 0.03
BELOW_ZERO = 0.005e-3      # V, "below 0.005 mV" statements in the entry
DT_FIT = 0.5e-6

RUNS = {
    "P10a0": "P10a0_refripple",
    "P10a90": "P10a90_refripple",
    "P10b": "P10b_railripple",
    "P10c": "P10c_railripple_kref",
    "P10d": "P10d_iexc",
    "P10e": "P10e_iexc_kref",
}


def window_mean(t, y, t0, t1):
    """Time-weighted trapezoid mean on the raw points, ends interpolated."""
    inside = (t > t0) & (t < t1)
    tt = np.concatenate(([t0], t[inside], [t1]))
    yy = np.concatenate(([np.interp(t0, t, y)], y[inside], [np.interp(t1, t, y)]))
    return float(np.trapezoid(yy, tt) / (t1 - t0))


def ripple_fit(t, y, t0, t1):
    """Peak amplitudes of the 1f and 2f components in [t0, t1] (least squares)."""
    grid = np.arange(t0, t1, DT_FIT)
    yg = np.interp(grid, t, y)
    w = 2 * math.pi * F_OSC
    cols = [np.ones_like(grid)]
    for k in (1, 2):
        cols += [np.cos(k * w * grid), np.sin(k * w * grid)]
    c, *_ = np.linalg.lstsq(np.column_stack(cols), yg, rcond=None)
    return math.hypot(c[1], c[2]), math.hypot(c[3], c[4])


def half_period_means(t, y, t0, t1):
    """Means of y over the first and second half of each period (phase from t = 0)."""
    grid = np.arange(t0, t1, DT_FIT)
    yg = np.interp(grid, t, y)
    phase = (grid / T) % 1.0
    first = yg[phase < 0.5]
    second = yg[phase >= 0.5]
    return float(first.mean()), float(second.mean())


def analyse(sec):
    t = sec.x
    t1 = T_END
    t0 = t1 - TW
    tp0 = t0 - TW
    r = {"a": round(sec.step_value, 9), "t0": t0}
    r["vx_raw"] = window_mean(t, sec["V(VX)"], t0, t1)
    r["vy_raw"] = window_mean(t, sec["V(VY)"], t0, t1)
    r["ref"] = window_mean(t, sec["V(REF)"], t0, t1)
    r["vdc"] = window_mean(t, sec["V(VDC)"], t0, t1)
    r["vx_prior"] = window_mean(t, sec["V(VX)"], tp0, t0)
    r["vy_prior"] = window_mean(t, sec["V(VY)"], tp0, t0)
    # Settling: the last window minus the window of the same length before it.
    e = math.exp(TW / TAU)
    r["dvx_prior"] = r["vx_raw"] - r["vx_prior"]
    r["dvy_prior"] = r["vy_raw"] - r["vy_prior"]
    r["bias_vx"] = r["dvx_prior"] / (1 - e)
    r["bias_vy"] = r["dvy_prior"] / (1 - e)
    f = (TAU / TW) * (1 - math.exp(-TW / TAU)) * math.exp(-t0 / TAU)
    r["F"] = f
    r["vx"] = (r["vx_raw"] - MID * f) / (1 - f)
    r["vy"] = (r["vy_raw"] - MID * f) / (1 - f)
    # Readout relative to the mean of V(REF)
    r["vxr"] = r["vx"] - r["ref"]
    r["vyr"] = r["vy"] - r["ref"]
    r["vdc_1f"], r["vdc_2f"] = ripple_fit(t, sec["V(VDC)"], t0, t1)
    r["ref_1f"], r["ref_2f"] = ripple_fit(t, sec["V(REF)"], t0, t1)
    r["vdc_h1"], r["vdc_h2"] = half_period_means(t, sec["V(VDC)"], t0, t1)
    r["points"] = len(t)
    return r


def load(folder):
    path = SIM / folder / f"{folder}.csd"
    secs = sorted(read_csdf(str(path)), key=lambda s: s.step_value)
    return {round(s.step_value, 9): analyse(s) for s in secs}


def expected(run, a, base):
    """Expected deltas (V) relative to step 0 of the same run, from the entry table.

    Returns (exp_dVXr, exp_dVYr, exp_dVX_abs, exp_dVY_abs, exp_dREF_mean).
    """
    D = RRAIL_TEST * 10e-3          # rail drop of iexc = 10 mA through 1 Ohm
    if run == "P10a0":
        return 2 * a / math.pi, 0.0, None, None, None
    if run == "P10a90":
        return 0.0, -2 * a / math.pi, None, None, None
    if run in ("P10b", "P10d"):
        return 0.0, 0.0, None, None, None
    if run == "P10c":
        # kref = 1: REF carries half the rail ripple
        return (a / 2) * 2 / math.pi, 0.0, None, None, None
    if run == "P10e":
        # REF drops by D/2 in the first half, so mean REF drops by D/4
        return -D / 4, 0.0, -D / 2, -D / 4, -D / 4
    raise KeyError(run)


def pct(meas, exp):
    return 100.0 * (meas - exp) / exp if abs(exp) > 1e-12 else float("nan")


def main():
    data = {k: load(v) for k, v in RUNS.items()}

    print(f"T = {T*1e3:.6f} ms, window = {TW*1e3:.4f} ms ({N_PER} periods), "
          f"from {(T_END-TW)*1e3:.4f} ms to {T_END*1e3:.4f} ms, tau = {TAU*1e3:.1f} ms")
    print(f"2A/pi = {K_DEM*1e3:.4f} mV, rail test resistance = {RRAIL_TEST} Ohm, "
          f"rail drop at 10 mA = {RRAIL_TEST*10:.3f} mV")
    print()

    print("Baseline (step 0 of each run), absolute window means (V)")
    print(f"{'run':<6}{'VDC':>13}{'REF':>13}{'VX':>13}{'VY':>13}{'VX - REF':>13}{'VY - REF':>13}")
    for run in RUNS:
        b = data[run][0.0]
        print(f"{run:<6}{b['vdc']:>13.7f}{b['ref']:>13.7f}{b['vx']:>13.7f}{b['vy']:>13.7f}"
              f"{b['vxr']:>13.7f}{b['vyr']:>13.7f}")
    print()

    print("Settling check: last window minus the window of the same length before it (mV)")
    print(f"{'run':<6}{'step':>8}{'F':>12}{'dVX (mV)':>11}{'dVY (mV)':>11}"
          f"{'bias VX (uV)':>14}{'bias VY (uV)':>14}")
    for run in RUNS:
        for a, r in data[run].items():
            print(f"{run:<6}{a:>8.4g}{r['F']:>12.3e}{r['dvx_prior']*1e3:>11.4f}"
                  f"{r['dvy_prior']*1e3:>11.4f}{r['bias_vx']*1e6:>14.3f}{r['bias_vy']*1e6:>14.3f}")
    print()

    print("Ripple and rail at the last window (peak amplitudes of the fitted sinusoids, mV)")
    print(f"{'run':<6}{'step':>8}{'VDC 1f':>10}{'VDC 2f':>10}{'REF 1f':>10}{'REF 2f':>10}"
          f"{'VDC H1-H2 (mV)':>16}")
    for run in RUNS:
        for a, r in data[run].items():
            print(f"{run:<6}{a:>8.4g}{r['vdc_1f']*1e3:>10.4f}{r['vdc_2f']*1e3:>10.4f}"
                  f"{r['ref_1f']*1e3:>10.4f}{r['ref_2f']*1e3:>10.4f}"
                  f"{(r['vdc_h1']-r['vdc_h2'])*1e3:>16.4f}")
    print()

    # Deltas against step 0 of the same run
    rows = []
    print("Deltas against step 0 of the same run (mV). Readout relative to mean V(REF).")
    print(f"{'run':<6}{'step':>8}{'dREF mean':>12}{'dVDC mean':>12}{'dVX abs':>10}{'dVY abs':>10}"
          f"{'dVXr':>10}{'dVYr':>10}")
    for run in RUNS:
        base = data[run][0.0]
        for a, r in data[run].items():
            if a == 0.0:
                continue
            dref = r["ref"] - base["ref"]
            dvdc = r["vdc"] - base["vdc"]
            dvx = r["vx"] - base["vx"]
            dvy = r["vy"] - base["vy"]
            dvxr = r["vxr"] - base["vxr"]
            dvyr = r["vyr"] - base["vyr"]
            print(f"{run:<6}{a:>8.4g}{dref*1e3:>12.4f}{dvdc*1e3:>12.4f}{dvx*1e3:>10.4f}"
                  f"{dvy*1e3:>10.4f}{dvxr*1e3:>10.4f}{dvyr*1e3:>10.4f}")
            rows.append((run, a, dvxr, dvyr, dvx, dvy, dref, dvdc))
    print()

    # Comparison with the entry. Measured quantities are the readout deltas (VX and VY
    # relative to mean V(REF)). Absolute deltas are compared for P10e.
    print("Comparison with the entry (mV). Pass: |diff| <= max(0.01 mV, 3 % of expected).")
    print(f"{'quantity':<34}{'measured':>11}{'expected':>11}{'diff':>10}{'pct err':>9}"
          f"{'tol':>9}{'result':>8}")
    checks = []
    for run in RUNS:
        base = data[run][0.0]
        for a, r in data[run].items():
            if a == 0.0:
                continue
            exp_dvxr, exp_dvyr, exp_dvx, exp_dvy, exp_dref = expected(run, a, base)
            dvxr = r["vxr"] - base["vxr"]
            dvyr = r["vyr"] - base["vyr"]
            checks.append((f"{run} step {a:g} dVXr", dvxr, exp_dvxr))
            checks.append((f"{run} step {a:g} dVYr", dvyr, exp_dvyr))
            if exp_dvx is not None:
                checks.append((f"{run} step {a:g} dVX abs", r["vx"] - base["vx"], exp_dvx))
                checks.append((f"{run} step {a:g} dVY abs", r["vy"] - base["vy"], exp_dvy))
            if exp_dref is not None:
                checks.append((f"{run} step {a:g} dREF mean", r["ref"] - base["ref"], exp_dref))
    results = []
    for name, meas, exp in checks:
        tol = max(PASS_ABS, PASS_REL * abs(exp))
        ok = abs(meas - exp) <= tol
        results.append((name, meas, exp, ok))
        print(f"{name:<34}{meas*1e3:>11.4f}{exp*1e3:>11.4f}{(meas-exp)*1e3:>10.4f}"
              f"{pct(meas, exp):>9.2f}{tol*1e3:>9.4f}{'pass' if ok else 'FAIL':>8}")
    print()

    print("Statements of 'below 0.005 mV' for P10b and P10d (entry), applied to the readout deltas")
    for run in ("P10b", "P10d"):
        base = data[run][0.0]
        for a, r in data[run].items():
            if a == 0.0:
                continue
            dvxr = (r["vxr"] - base["vxr"]) * 1e3
            dvyr = (r["vyr"] - base["vyr"]) * 1e3
            print(f"{run} step {a:g}: |dVXr| = {abs(dvxr):.5f} mV, |dVYr| = {abs(dvyr):.5f} mV, "
                  f"below 0.005 mV: {abs(dvxr) < 0.005 and abs(dvyr) < 0.005}")
    print()

    # Y reference timing. The Y reference is high from t_s = 482.6 us (V_V6), not from T/4.
    t_s = 482.6e-6
    print("Y reference timing (explains the small VY residuals)")
    D = RRAIL_TEST * 10e-3
    for label, t_end_iexc in (("iexc window ends at T/2", T / 2),
                              ("iexc window ends at T/2 + 100 ns", T / 2 + 100e-9)):
        ov = (t_end_iexc - t_s) / T
        print(f"  P10e VY absolute, {label}: {-D*ov*1e3:.4f} mV (overlap {ov*100:.3f} % of T)")
    e = data["P10e"][0.01]
    b = data["P10e"][0.0]
    print(f"  P10e VY absolute measured: {(e['vy']-b['vy'])*1e3:.4f} mV")
    print(f"  P10e VY relative with the T/2 window end: {(-D*(T/2-t_s)/T + D/4)*1e3:.4f} mV "
          f"(entry expects 0)")
    a = 1e-3
    pred_a0 = (2 * a / math.pi) * math.cos(2 * math.pi * F_OSC * t_s)
    print(f"  P10a0 VY relative predicted (2a/pi) cos(2 pi f t_s) = {pred_a0*1e3:.5f} mV, "
          f"measured {(data['P10a0'][a]['vyr']-data['P10a0'][0.0]['vyr'])*1e3:.5f} mV")
    print()

    # Rail coupling sizes
    print("Rail coupling sizes")
    b = data["P10b"][0.0]
    r = data["P10b"][1e-3]
    dvx = (r["vxr"] - b["vxr"])
    dvy = (r["vyr"] - b["vyr"])
    print(f"P10b: VDC ripple (1f fit) = {r['vdc_1f']*1e3:.4f} mV, dVXr = {dvx*1e3:.5f} mV, "
          f"dVYr = {dvy*1e3:.5f} mV")
    if r["vdc_1f"] > 0:
        for name, d in (("VX", dvx), ("VY", dvy)):
            ratio = abs(d) / r["vdc_1f"]
            db = 20 * math.log10(ratio) if ratio > 0 else float("-inf")
            print(f"    {name}: ratio = {ratio:.4e} V/V, {db:.1f} dB (rail ripple to output)")
    for run in ("P10d", "P10e"):
        base = data[run][0.0]
        r = data[run][10e-3]
        drop = (r["vdc_h1"] - r["vdc_h2"]) - (base["vdc_h1"] - base["vdc_h2"])
        dvx = r["vxr"] - base["vxr"]
        dvy = r["vyr"] - base["vyr"]
        print(f"{run}: VDC first half minus second half = {drop*1e3:.4f} mV (step 10 mA minus "
              f"step 0), dVXr = {dvx*1e3:.5f} mV, dVYr = {dvy*1e3:.5f} mV")
        if abs(drop) > 0:
            print(f"    VX: {abs(dvx)/abs(drop):.4e} V/V of the rail step, "
                  f"VY: {abs(dvy)/abs(drop):.4e} V/V of the rail step")
    print()

    # Plot: readout deltas against expected (mV), and the rail and reference of P10e
    fig, ax = plt.subplots(1, 2, figsize=(11, 4.5))
    sel = [(n, m, e) for n, m, e, _ in results if " dVXr" in n or " dVYr" in n]
    labels = []
    for n, _, _ in sel:
        run, step, quantity = n.split(" ")[0], n.split(" step ")[1].split(" ")[0], n.split(" ")[-1]
        labels.append(run + chr(10) + step + " " + quantity)
    meas = np.array([m for _, m, _ in sel]) * 1e3
    exp = np.array([e for _, _, e in sel]) * 1e3
    x = np.arange(len(sel))
    ax[0].bar(x, meas, width=0.6, label="measured")
    ax[0].hlines(exp, x - 0.35, x + 0.35, colors="k", lw=2, label="expected")
    ax[0].set_xticks(x)
    ax[0].set_xticklabels(labels, fontsize=6, rotation=90)
    ax[0].set_ylabel("readout delta (mV)")
    ax[0].set_title("P-10 readout deltas relative to mean V(REF)")
    ax[0].legend(fontsize=8)

    run_path = SIM / RUNS["P10e"] / f"{RUNS['P10e']}.csd"
    s_ = [s for s in read_csdf(str(run_path)) if abs(s.step_value - 0.01) < 1e-9][0]
    t = s_.x
    m_ = t > T_END - 2 * T
    ax[1].plot(t[m_] * 1e3, (s_["V(VDC)"][m_] - 5.0) * 1e3, lw=0.7, label="V(VDC) - 5 V")
    ax[1].plot(t[m_] * 1e3, (s_["V(REF)"][m_] - MID) * 1e3, lw=0.7, label="V(REF) - 2.5 V")
    ax[1].set_xlabel("time (ms)")
    ax[1].set_ylabel("deviation (mV)")
    ax[1].set_title("P10e, 10 mA, last 2 periods")
    ax[1].legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(PLOT, dpi=120)
    print(f"plot written: {PLOT}")


if __name__ == "__main__":
    main()
