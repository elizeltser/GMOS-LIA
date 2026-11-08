"""P-26b: staircase excitation through the excitation chain (EXC_DAC and GATE, gate amplitude, THD, image, phases).

Run from simulations/ti-pspice:  python docs/sim-results/scripts/P-26_stair.py
Reads sim-runs/P26b_stair/P26b_stair.csd (circuits/afe_eval_stair.cir, .TRAN 0 0.1 0 2u, 2 us maximum step).

Window: the last 40 whole periods of 518 Hz, from 0.1 s - 40 T to 0.1 s (77.22 ms).
Method: resample to a uniform 0.5 us grid by linear interpolation, then least-squares fit of
DC and sin/cos at k f0 (k = 1 to 10), at the DAC image 127 f0 (65.786 kHz), and at the ZOH images
129 f0, 255 f0 and 257 f0. Exact whole-period windows make the fitted amplitudes exact.
Phases refer to t = 0 for the sine a sin(w t + phi), so an ideal sin(w t) has phi = 0.
Edge check: the 100 ns staircase edges at k ts and k ts + 100 ns must each have a solver time point
within 5 ns. ts = 1 / (128 f0) = 15.08 us.
Settling: amplitudes and phases of the fundamental from the first and the second half of the window
(20 periods each) are compared.
"""
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools"))
from csdf import read_csdf  # noqa: E402

F0 = 518.0
T = 1.0 / F0
TEND = 0.1
DT = 0.5e-6
WIN = 40 * T
TS = 1.0 / (128 * F0)
EDGE = 100e-9
IMAGES = [127, 129, 255, 257]  # ZOH images (k 128 +/- 1) of the staircase, in multiples of f0
HARM = list(range(1, 11))

# Analyst limits (not all are in the entry, see the summary)
LIM_AMP_PCT = 1.0        # gate amplitude, entry: within 1 %
LIM_THD_PCT = 0.3        # entry
LIM_IMG_DBC = -40.0      # entry, "at most"
LIM_IMG2_DBC = -80.0     # entry, "below"
LIM_PH_DEG = 0.05        # analyst
LIM_SETTLE_PCT = 0.1     # analyst, first vs second half of the window


def fit(t, y, freqs):
    cols = [np.ones_like(t)]
    for f in freqs:
        cols += [np.sin(2 * np.pi * f * t), np.cos(2 * np.pi * f * t)]
    A = np.column_stack(cols)
    c, *_ = np.linalg.lstsq(A, y, rcond=None)
    res = y - A @ c
    amps = {}
    for i, f in enumerate(freqs):
        s, co = c[1 + 2 * i], c[2 + 2 * i]
        amps[f] = (np.hypot(s, co), np.degrees(np.arctan2(co, s)))
    return c[0], amps, res.std()


def load(name):
    s = read_csdf(ROOT / "sim-runs" / name / f"{name}.csd")[0]
    t = np.real(np.asarray(s.x)).astype(float)
    return s, t


def edge_check(t):
    """Fraction of the staircase edges that have a solver time point within 5 ns."""
    w = (t >= TEND - WIN) & (t <= TEND)
    tw = t[w]
    dt = np.diff(tw)
    k0 = int(np.ceil((TEND - WIN) / TS))
    k1 = int(np.floor(TEND / TS))
    edges = np.concatenate([np.arange(k0, k1) * TS, np.arange(k0, k1) * TS + EDGE])
    d = np.array([np.min(np.abs(tw - e)) for e in edges[: 4000]])
    return np.median(dt), np.max(dt), np.mean(d <= 5e-9), len(edges[:4000])


def main():
    s, t = load("P26b_stair")
    tg = np.arange(TEND - WIN, TEND, DT)
    sig = {}
    for key in ("V(GATE)", "V(EXC_DAC)"):
        sig[key] = np.interp(tg, t, np.asarray(s[key], dtype=float))

    med, mx, frac, n = edge_check(t)
    print(f"edge check: median solver step {med*1e9:.1f} ns, max step {mx*1e9:.1f} ns, "
          f"{100*frac:.1f} % of the first {n} edges have a time point within 5 ns")

    mults = HARM + IMAGES                      # multiples of f0
    freqs = [m * F0 for m in mults]
    res = {}
    for key in sig:
        dc, amps, sd = fit(tg, sig[key], freqs)
        res[key] = (dc, amps, sd)
        a1 = amps[F0][0]
        print(f"{key}: DC {dc:.6f} V, fit residual {sd*1e6:.3f} uV rms, fundamental {a1*1e3:.5f} mV pk, "
              f"phase {amps[F0][1]:+.4f} deg")
    dc_e, ae, sde = res["V(EXC_DAC)"]
    dc_g, ag, sdg = res["V(GATE)"]
    a1e, a1g = ae[F0][0], ag[F0][0]

    print("EXC_DAC harmonics:")
    for k in (2, 3, 5, 7):
        print(f"  h{k}: {1e6*ae[k*F0][0]:.2f} uV pk")
    img_e = ae[127 * F0][0]
    print(f"EXC_DAC image at 127 f0 (65.786 kHz): {1e6*img_e:.2f} uV pk, {20*np.log10(img_e/a1e):.2f} dBc")

    thd = np.sqrt(sum(ag[k * F0][0] ** 2 for k in range(2, 11))) / a1g
    print(f"GATE THD (2nd to 10th) = {100*thd:.5f} % (limit {LIM_THD_PCT} %)")
    for k in (2, 3, 5, 7):
        print(f"  GATE h{k}: {1e6*ag[k*F0][0]:.4f} uV pk")
    img_g = ag[127 * F0][0]
    print(f"GATE image at 127 f0: {1e6*img_g:.4f} uV pk, {20*np.log10(img_g/a1g):.2f} dBc")

    print(f"gate amplitude: {2e3*a1g:.5f} mVpp; EXC_DAC fundamental x 2 / 119.9219 = "
          f"{2e3*a1e/119.9219:.5f} mVpp")
    print(f"gate DC {dc_g:.6f} V (expected 0.99458 V)")
    print(f"EXC_DAC fundamental phase vs ideal sine: {ae[F0][1]:+.4f} deg "
          f"(expected -1.406 deg for the half-sample hold, -1.4156 deg with the 50 ns edge lag)")
    print(f"GATE fundamental phase vs ideal sine: {ag[F0][1]:+.4f} deg")
    print(f"GATE minus EXC_DAC fundamental phase: {ag[F0][1]-ae[F0][1]:+.4f} deg (MFB, P26a)")

    half = len(tg) // 2
    for key in sig:
        _, a_1, _ = fit(tg[:half], sig[key][:half], [F0])
        _, a_2, _ = fit(tg[half:], sig[key][half:], [F0])
        A1, P1 = a_1[F0]
        A2, P2 = a_2[F0]
        print(f"settling {key}: fundamental first half {A1*1e3:.5f} mV, second half {A2*1e3:.5f} mV "
              f"({100*(A2/A1-1):+.4f} %), phase {P1:+.4f} vs {P2:+.4f} deg")


if __name__ == "__main__":
    main()
