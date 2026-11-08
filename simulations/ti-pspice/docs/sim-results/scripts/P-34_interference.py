"""P-34 interference and harmonic rejection at X_OUT (Sallen-Key post-filter, SIM-15).

Reads the .csd files of the run P34_ref (ai = 0) and of the runs P34_f<fi> (interferer at BPF_OUT),
subtracts the reference from each run and fits the products over the last 0.5 s.

Demodulator products (square reference, odd harmonics n, interferer sin(2 pi fi t) with phase 0):
  difference |n f0 - fi| with weight +2 ai / (n pi),  sum n f0 + fi with weight -2 ai / (n pi).
  n runs over odd values up to NMAX. Products at equal frequency add as real weights.

Post-filter models:
  ideal:        X_OUT = X_DEM(f) H_post(f),  H_post = 1 / (1 - (w tau)^2 + 2 j w tau), tau = R C = 0.3 s.
  feedthrough:  X_OUT = X_DEM(f) (H_post(f) + j w L / R14). The current X_DEM / R14 through C13
                meets the closed-loop output impedance of U26B, which is inductive with L. L is
                taken from the quadrature part of the reference 2f0 ripple (1036 Hz).

Fit model of the difference X_OUT(t) - X_OUT_ref(t) on t in [0.5, 1] s:
  DC + sum over product frequencies f <= 4 kHz of [a cos(2 pi f t) + b sin(2 pi f t)]
  + (d + e t) exp(-t / tau), the free response of the critically damped post-filter pair.

Rejection in dB = 20 log10( amplitude at X_OUT / ((2/pi) x 0.4 V) ), the X_OUT of an f0 signal
with the same drain amplitude as the interferer.

Floors:
  control-bin floor: the amplitude spectrum (2 Hz bins, 100 Hz to 4 kHz) of the fit residual with the
  product bins and the 2f0 harmonic bins (+-2 Hz) removed. The floor is the mean plus 3 sigma of the
  remaining bins.

Run from simulations/ti-pspice:  python docs/sim-results/scripts/P-34_interference.py
"""
import sys
import numpy as np

sys.path.insert(0, "tools")
from csdf import read_csdf

F0 = 518.0
F2 = 2 * F0                   # 2f0 = 1036 Hz
AIN = 0.4
R14 = 200e3
C_POST = 1.5e-6
TAU = R14 * C_POST            # 0.3 s
T0, T1 = 0.5, 1.0             # fit window
DT = 5e-6                     # uniform grid of the fit
NMAX = 39                     # odd harmonics of the reference used in the products
FMAX = 4000.0                 # products above this frequency are not fitted
REF = (2 / np.pi) * AIN       # X_OUT of an f0 signal with the same drain amplitude as the interferer
RUNS = {50: "P34_f50", 500: "P34_f500", 550: "P34_f550", 1036: "P34_f1036", 1554: "P34_f1554"}
# Interferer amplitudes in the circuit files, ai = 0.4 V |H(fi)| / |H(f0)| (ideal front end)
AI_FILE = {50: 0.003761, 500: 0.397999, 550: 0.394342, 1036: 0.123091, 1554: 0.049319}


def load(name):
    sec = read_csdf(f"sim-runs/{name}/{name}.csd")[0]
    return sec.x, sec["V(X_OUT)"], sec["V(Y_OUT)"]


def h_post(f):
    w = 2 * np.pi * f
    return 1.0 / (1 - (w * TAU) ** 2 + 2j * w * TAU)


def h_front_ideal(f):
    """Ideal front end, K = 2 band-pass and INA828 gain (afe_eval_expected.py)."""
    G = 1 + 50e3 / 5.62e3
    R9 = R11 = R12 = R13 = 9.31e3
    C9 = C10 = C11 = C12 = 33e-9
    s = 2j * np.pi * f
    k = 2.0
    hp = k * s**2 / (s**2 + s * (1 / (R13 * C10) + 1 / (R13 * C11) + (1 - k) / (R9 * C10))
                     + 1 / (R9 * R13 * C10 * C11))
    w = 1 / (R11 * R12 * C9 * C12)
    lp = k * w / (s**2 + s * (1 / (R11 * C9) + 1 / (R12 * C9) + (1 - k) / (R12 * C12)) + w)
    return G * hp * lp


def db(a):
    return 20 * np.log10(max(a, 1e-300) / REF)


def weights(fi, ai):
    """Real weight of each product frequency (<= FMAX) of the demodulated interferer."""
    P = {}
    for n in range(1, NMAX + 1, 2):
        A = 2 * ai / (n * np.pi)
        fd = round(abs(n * F0 - fi), 6)
        fs = round(n * F0 + fi, 6)
        P[fd] = P.get(fd, 0.0) + A
        P[fs] = P.get(fs, 0.0) - A
    return {f: w for f, w in P.items() if f <= FMAX}


def h_ft(f, L):
    w = 2 * np.pi * f
    return h_post(f) + 1j * w * L / R14


def fit(t, y, freqs, transient=True):
    """Least squares. Returns dc, amplitude per frequency, (a, b) per frequency, residual."""
    cols = [np.ones_like(t)]
    nz = [f for f in freqs if f != 0]
    for f in nz:
        cols += [np.cos(2 * np.pi * f * t), np.sin(2 * np.pi * f * t)]
    if transient:
        cols += [np.exp(-t / TAU), t * np.exp(-t / TAU)]
    A = np.column_stack(cols)
    coef, *_ = np.linalg.lstsq(A, y, rcond=None)
    resid = y - A @ coef
    amp, ab = {0.0: abs(coef[0])}, {}
    k = 1
    for f in nz:
        ab[f] = (coef[k], coef[k + 1])
        amp[f] = np.hypot(coef[k], coef[k + 1])
        k += 2
    return coef[0], amp, ab, resid


def control_floor(resid, freqs):
    """Mean + 3 sigma of the residual amplitude spectrum over control bins (100 Hz to 4 kHz)."""
    N = len(resid)
    spec = 2 * np.abs(np.fft.rfft(resid)) / N
    f = np.fft.rfftfreq(N, DT)
    excl = [f0 for f0 in freqs if f0 > 0] + [k * F2 for k in range(1, int(FMAX // F2) + 1)]
    mask = (f >= 100) & (f <= FMAX)
    for e in excl:
        mask &= np.abs(f - e) > 2.0
    vals = spec[mask]
    return vals.mean(), vals.mean() + 3 * vals.std(), mask.sum()


def main():
    tg = np.arange(T0, T1, DT)
    tref, xref_raw, yref_raw = load("P34_ref")
    xr = np.interp(tg, tref, xref_raw)
    yr = np.interp(tg, tref, yref_raw)

    print("== Reference run P34_ref (ai = 0)")
    print(f"X_OUT at t = 0: {xref_raw[0]:.7f} V (the state nodes start at the .IC values)")
    print(f"X_OUT mean over [{T0}, {T1}] s: {1e6*(xr.mean()-REF):+.2f} uV against (2/pi) x 0.4 V")
    print("Settled offsets, fit of DC + (d + e t) exp(-t/tau) from several start times:")
    tall = np.arange(0.05, 1.0, DT)
    xa = np.interp(tall, tref, xref_raw)
    ya = np.interp(tall, tref, yref_raw)
    print("| Window start (s) | X_OUT settled offset (uV) | Y_OUT settled (uV) |")
    print("|---|---|---|")
    for s0 in (0.05, 0.2, 0.5):
        m = tall >= s0
        dcx = fit(tall[m], xa[m], [])[0]
        dcy = fit(tall[m], ya[m], [])[0]
        print(f"| {s0} | {1e6*(dcx-REF):+.2f} | {1e6*dcy:+.2f} |")
    print()

    # Reference 2f0 and 4f0 ripple of X_OUT and the feedthrough inductance
    dcr, ampr, abr, _ = fit(tg, xr, [F2, 2 * F2])
    a, b = abr[F2]
    M = a - 1j * b                                         # phasor of cos a + sin b
    V2 = -(4 / (3 * np.pi)) * AIN                          # 2f0 component of |sin| at X_DEM
    V4 = -(4 / (15 * np.pi)) * AIN                         # 4f0 component
    Phi = V2 * h_post(F2)
    u = Phi / abs(Phi)
    comp = M * np.conj(u)
    q = comp.imag
    L = abs(q) * R14 / (abs(V2) * 2 * np.pi * F2)
    print("== Feedthrough of the Sallen-Key stage from the reference 2f0 ripple")
    print(f"reference 2f0 ripple at X_OUT: {1e9*abs(M):.1f} nV, in phase with the ideal "
          f"{1e9*comp.real:.1f} nV (ideal {1e9*abs(Phi):.1f} nV), quadrature {1e9*q:+.1f} nV")
    print(f"L = {L*1e6:.2f} uH, closed-loop output impedance at 1036 Hz = {2*np.pi*F2*L:.4f} Ohm")
    print("| Line (Hz) | Ideal model (nV) | Feedthrough model (nV) | Measured (nV) | Measured minus model (dB) |")
    print("|---|---|---|---|---|")
    ripple_rows = []
    for f, V, meas in ((F2, V2, ampr[F2]), (2 * F2, V4, ampr[2 * F2])):
        ideal = abs(V * h_post(f))
        ft = abs(V * h_ft(f, L))
        print(f"| {f:.0f} | {1e9*ideal:.2f} | {1e9*ft:.2f} | {1e9*meas:.2f} | {20*np.log10(meas/ft):+.2f} |")
        ripple_rows.append((f, meas))
    print()

    # Products of each run
    summary = []
    for fi, name in RUNS.items():
        t, x_raw, _ = load(name)
        xi = np.interp(tg, t, x_raw)
        d = xi - xr
        ai = AI_FILE[fi]
        P = weights(fi, ai)
        freqs = sorted(P.keys())
        dc, amp, ab, resid = fit(tg, d, freqs)
        dc2, amp2, _, _ = fit(tg[tg >= 0.6], d[tg >= 0.6], freqs)
        mean_f, floor_f, nbins = control_floor(resid, freqs)
        print(f"== Run {name}: fi = {fi} Hz, ai = {ai} V, {len(freqs)} product frequencies <= 4 kHz, "
              f"control bins {nbins}, floor mean {1e9*mean_f:.2f} nV, mean + 3 sigma {1e9*floor_f:.2f} nV "
              f"({db(floor_f):.1f} dB)")
        print("| Frequency (Hz) | Weight | Ideal (dB) | Feedthrough (dB) | Measured (dB) | Measured minus feedthrough (dB) | Window 0.6-1 s (dB) | Floor (dB) |")
        print("|---|---|---|---|---|---|---|---|")
        for f in freqs:
            w = P[f]
            if f == 0:
                ideal = abs(w)
                ft = abs(w)
                meas = abs(dc)
                meas2 = abs(dc2)
            else:
                ideal = abs(w * h_post(f))
                ft = abs(w * h_ft(f, L))
                meas = amp[f]
                meas2 = amp2[f]
            summary.append((name, fi, f, ideal, ft, meas))
            print(f"| {f:.2f} | {w:+.4e} | {db(ideal):.2f} | {db(ft):.2f} | {db(meas):.2f} | "
                  f"{db(meas)-db(ft):+.2f} | {db(meas2):.2f} | {db(floor_f):.1f} |")
        if fi == 1554:
            print(f"DC shift fit: {1e3*dc:.4f} mV, predicted {1e3*P[0.0]:.4f} mV "
                  f"(2/(3 pi)) ai, phase of the 3f0 interferer 0 so cos = 1")
        print()

    # Verdict for the main terms
    print("== Verdict for the main terms")
    print("| Run | Term | Ideal (dB) | Feedthrough (dB) | Measured (dB) | Ideal rule (2 dB) | Feedthrough rule (2 dB) | SIM-15 limit (dB) | Limit |")
    print("|---|---|---|---|---|---|---|---|---|")
    main_terms = [("P34_f50", 468.0, 60), ("P34_f500", 18.0, 30), ("P34_f550", 32.0, 30),
                  ("P34_f1036", 518.0, 40), ("P34_f1554", 0.0, 25)]
    for name, f, lim in main_terms:
        row = [r for r in summary if r[0] == name and abs(r[2] - f) < 1e-6][0]
        _, _, _, ideal, ft, meas = row
        ri = "PASS" if abs(db(meas) - db(ideal)) <= 2 else "FAIL"
        rf = "PASS" if abs(db(meas) - db(ft)) <= 2 else "FAIL"
        sim = "PASS" if db(meas) <= -lim else "FAIL"
        print(f"| {name} | {f:.2f} Hz | {db(ideal):.2f} | {db(ft):.2f} | {db(meas):.2f} | {ri} | {rf} | "
              f"{-lim} | {sim} |")
    f2_ref = ripple_rows[0][1]
    print(f"| P34_ref | 2f0 ripple (1036 Hz) | - | - | {db(f2_ref):.2f} ({1e9*f2_ref:.1f} nV) | - | - | "
          f"0.1 uV | {'PASS' if f2_ref <= 1e-7 else 'FAIL'} |")


if __name__ == "__main__":
    main()
