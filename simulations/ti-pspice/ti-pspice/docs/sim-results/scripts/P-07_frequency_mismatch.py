"""P-07 frequency mismatch for the LIA circuit (input 518 Hz, references 517 Hz).

The script reads sim-runs/P07_mismatch/P07_mismatch.csd and does four things:

1. Builds the exact expected VX(t) and VY(t) from the ideal square-wave demodulator
   (odd reference harmonics n = 1 to 15, sum and difference products), with the RC
   output filter (tau = 0.1 s) applied to every product, and with the start transient
   from V(0) = 0 V. Two variants are computed: the ideal model of the index
   (Y reference delay 482.6 us), and a calibrated model that adds the constant
   reference delays and the gain deficit found in P-01, P-02 and P-04.
2. Fits VX and VY on 1 s to 3 s with c + A cos(2 pi f_b t + phi), f_b free (the brief).
3. Fits the same window with DC, the 1 Hz beat, the expected ripple frequencies, and the
   IC transient (linear least squares, all frequencies integer, so the fit is exact).
   This gives the 2f ripple and checks the beat amplitude.
4. Compares the full 0 s to 3 s record with the expected waveform, and writes plots.

Run from the project root:
    python docs/sim-results/scripts/P-07_frequency_mismatch.py
"""

import math
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from scipy.optimize import curve_fit  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools"))
from csdf import read_csdf  # noqa: E402

RUN = "P07_mismatch"
CSD = ROOT / f"sim-runs/{RUN}/{RUN}.csd"
PLOT_DIR = ROOT / "docs/sim-results/plots"

F_IN = 518.0                     # Hz, V4 frequency (fin)
F_REF = 517.0                    # Hz, f_osc, references V2 and V6
A_IN = 2.0                       # V, input amplitude (V4)
MID = 2.5                        # V, input midpoint and output rest level
TAU = 0.1                        # s, RC = 10 kOhm x 10 uF
TAU_D = 482.6e-6                 # s, delay of the Y reference (V6)
NMAX = 15                        # highest odd reference harmonic used
T_END = 3.0                      # s
DT = 5e-6                        # s, uniform grid for the fits and plots
G = np.arange(0.0, T_END + 1e-12, DT)
FIT_LO, FIT_HI = 1.0, 3.0        # s, fit window (after the transient)
GAIN_P02 = 1.0 - 0.00039         # P-02 common gain deficit (-0.039 %)
DX_P02 = 127e-9                  # s, P-02 constant X delay (100 ns plus 27 ns switch)
DY_P02 = 136e-9                  # s, P-02 constant Y delay (fit constant, slew excluded)
D_IDEAL = 90.0 - 360.0 * F_REF * TAU_D * 1.0   # deg, Y timing error d = T/4 - 482.6 us (index)
DEG = 180.0 / math.pi


def h_of(f):
    """RC low-pass transfer function for a signed frequency f (Hz)."""
    return 1.0 / (1.0 + 1j * 2.0 * math.pi * f * TAU)


def terms_model(f_in=F_IN, f_ref=F_REF, gain=1.0, dx=0.0, dy=0.0):
    """Return the DC and the complex phasors Z(f) of the expected outputs.

    The input is A sin(w_i t). Each reference is -sgn(sin(w_r (t - delay))), written as the
    odd harmonic series -(4/pi) sum sin(n w_r (t - delay)) / n. The product with the input
    gives, for each n, a difference and a sum term with amplitude 2 A / (n pi). The filter
    multiplies each term by H(f). A term c cos(2 pi f t + ph) becomes Re[c H(f) e^{j ph} e^{j2 pi f t}].
    """
    out = {}
    for name, delay in (("X", dx), ("Y", dy)):
        dc = MID
        phasors = {}
        # the Y delay of the circuit is 482.6 us, and the index uses it for all Y runs
        extra = 0.0
        if name == "Y":
            extra = TAU_D
        delta_rad = 2.0 * math.pi * f_ref * (extra + delay)
        for n in range(1, NMAX + 1, 2):
            c = gain * 2.0 * A_IN / (n * math.pi)
            # difference product: phase +n delta, sum product: phase -n delta
            for f_t, amp, ph in (
                (f_in - n * f_ref, -c, n * delta_rad),
                (f_in + n * f_ref, +c, -n * delta_rad),
            ):
                z = amp * h_of(f_t) * complex(math.cos(ph), math.sin(ph))
                if f_t == 0:
                    dc += z.real
                    continue
                if f_t < 0:
                    f_abs, z = -f_t, z.conjugate()
                else:
                    f_abs = f_t
                phasors[f_abs] = phasors.get(f_abs, 0j) + z
        out[name] = (dc, phasors)
    return out


def expected_wave(t, model):
    """Steady-state plus the start transient for VX and VY (V(0) = 0 V)."""
    res = {}
    for name in ("X", "Y"):
        dc, phasors = model[name]
        w = np.zeros_like(t)
        for f_abs, z in phasors.items():
            w += (z.real * np.cos(2 * math.pi * f_abs * t)
                  - z.imag * np.sin(2 * math.pi * f_abs * t))
        ss = dc + w
        ss0 = dc + sum(z.real for z in phasors.values())   # steady state at t = 0
        res[name] = ss - ss0 * np.exp(-t / TAU)
    return res


def fit_sine(t, y):
    """Fit c + a cos(2 pi f t) + b sin(2 pi f t) with f free. Return c, A, f, phi."""
    def model(tt, c, a, b, f):
        return c + a * np.cos(2 * math.pi * f * tt) + b * np.sin(2 * math.pi * f * tt)
    # start from a linear fit at f = 1 Hz
    m0 = np.column_stack([np.ones_like(t), np.cos(2 * math.pi * t), np.sin(2 * math.pi * t)])
    c0, a0, b0 = np.linalg.lstsq(m0, y, rcond=None)[0]
    p, _ = curve_fit(model, t, y, p0=[c0, a0, b0, 1.0])
    c, a, b, f = p
    amp = math.hypot(a, b)
    phi = math.atan2(-b, a)              # A cos(w t + phi) = a cos - b sin
    return c, amp, f, phi


def fit_components(t, y, freqs):
    """Linear least squares with DC, sine/cosine pairs at fixed freqs, and the IC transient."""
    cols = [np.ones_like(t)]
    for f in freqs:
        cols.append(np.cos(2 * math.pi * f * t))
        cols.append(np.sin(2 * math.pi * f * t))
    cols.append(np.exp(-t / TAU))
    m = np.column_stack(cols)
    sol, *_ = np.linalg.lstsq(m, y, rcond=None)
    return sol, m @ sol


def main():
    secs = list(read_csdf(str(CSD)))
    assert len(secs) == 1, f"expected one section, found {len(secs)}"
    s = secs[0]
    print(f"CSDF points {len(s.x)}, t from {s.x[0]:.6g} s to {s.x[-1]:.6g} s")
    assert abs(s.x[-1] - T_END) < 1e-12, f"section ends at {s.x[-1]}"
    vx = np.interp(G, s.x, s["V(VX)"])
    vy = np.interp(G, s.x, s["V(VY)"])

    # Expected waveforms: ideal model (index) and calibrated model (P-02 constants)
    ideal = expected_wave(G, terms_model())
    calib = expected_wave(G, terms_model(gain=GAIN_P02, dx=DX_P02, dy=DY_P02))
    # Matched-frequency check of the model against the index formulas at DC
    m_dc = terms_model(f_in=F_REF, f_ref=F_REF)
    k_val = 2 * A_IN / math.pi
    print(f"Check matched DC: VX - 2.5 = {m_dc['X'][0] - MID:+.6f} V (expect {-k_val:+.6f}),"
          f" VY - 2.5 = {m_dc['Y'][0] - MID:+.6f} V (expect {-k_val * math.sin(math.radians(D_IDEAL)):+.6f}"
          f" from d = {D_IDEAL} deg)")

    # Ideal beat amplitude and phase
    h1 = abs(h_of(1.0))
    k_h = k_val * h1
    phi_lag = math.atan(2 * math.pi * 1.0 * TAU)
    print(f"Ideal: K = {k_val:.6f} V, |H(1 Hz)| = {h1:.6f}, K|H| = {k_h:.6f} V,"
          f" lag = {math.degrees(phi_lag):.4f} deg")

    # Fit window
    w = (G >= FIT_LO - 1e-12) & (G <= FIT_HI + 1e-12)
    tw = G[w]
    results = {}
    for name, y in (("VX", vx), ("VY", vy)):
        yw = y[w]
        c, amp, f_b, phi = fit_sine(tw, yw)
        resid_a = yw - (c + amp * np.cos(2 * math.pi * f_b * tw + phi))
        # all expected products (integer Hz, so orthogonal over the 2 s window) and the transient
        ripple_freqs = sorted({abs(F_IN - n * F_REF) for n in range(1, NMAX + 1, 2)}
                              | {F_IN + n * F_REF for n in range(1, NMAX + 1, 2)})
        coef, fit_full = fit_components(tw, yw, ripple_freqs)
        resid_b = yw - fit_full
        results[name] = dict(c=c, amp=amp, f_b=f_b, phi=phi, resid_a=resid_a,
                             coef=coef, freqs=ripple_freqs, resid_b=resid_b)

    print("\nFit A (brief): c + A cos(2 pi f_b t + phi), window 1 s to 3 s")
    for name in ("VX", "VY"):
        r = results[name]
        print(f"  {name}: c = {r['c']:.6f} V, A = {r['amp']:.6f} V, f_b = {r['f_b']:.7f} Hz,"
              f" phi = {math.degrees(r['phi']):.3f} deg,"
              f" residual RMS = {np.sqrt(np.mean(r['resid_a'] ** 2)) * 1e3:.4f} mV")

    # Expected components at the 1 Hz beat and the ripple frequencies
    ideal_x = ideal["X"]
    print("\nExpected phasors of the ideal model (Z at each frequency, V):")
    print("  f (Hz)     |Z| ideal (mV)    phase X (deg)    |Z| calib (mV)")
    for f_abs in sorted(terms_model()["X"][1].keys())[:8]:
        zx = terms_model()["X"][1][f_abs]
        zc = terms_model(gain=GAIN_P02, dx=DX_P02, dy=DY_P02)["X"][1][f_abs]
        print(f"  {f_abs:9.1f}  {abs(zx) * 1e3:12.5f}   {math.degrees(np.angle(zx)):10.3f}"
              f"   {abs(zc) * 1e3:12.5f}")

    print("\nFit B: linear least squares, DC, all expected products, IC transient (window 1 s to 3 s)")
    expected_ideal = terms_model()
    expected_cal = terms_model(gain=GAIN_P02, dx=DX_P02, dy=DY_P02)
    rows = []
    for name, idx in (("VX", "X"), ("VY", "Y")):
        coef = results[name]["coef"]
        freqs = results[name]["freqs"]
        for k, f in enumerate(freqs):
            a, b = coef[1 + 2 * k], coef[2 + 2 * k]
            fit_amp = math.hypot(a, b)
            fit_ph = math.atan2(-b, a)
            z = expected_ideal[idx][1].get(f, 0j)
            zc = expected_cal[idx][1].get(f, 0j)
            e_amp = abs(z)
            rows.append((name, f, e_amp, fit_amp, fit_amp / e_amp if e_amp > 0 else float("nan"),
                         math.degrees(np.angle(z)), math.degrees(fit_ph), abs(zc)))
    print("  chan  f (Hz)   expected (mV)  fit (mV)   ratio   phase exp (deg)  phase fit (deg)  calib (mV)")
    for name, f, e_amp, f_amp, ratio, pe, pf, ac in rows:
        print(f"  {name}  {f:8.1f}  {e_amp * 1e3:12.5f}  {f_amp * 1e3:9.5f}  {ratio:7.4f}"
              f"  {pe:14.3f}  {pf:14.3f}  {ac * 1e3:10.5f}")
    for name, idx in (("VX", "X"), ("VY", "Y")):
        coef = results[name]["coef"]
        dc_fit = coef[0]
        tr = coef[-1]
        ss0 = expected_ideal[idx][0] + sum(z.real for z in expected_ideal[idx][1].values())
        print(f"  {name}: fit DC = {dc_fit:.6f} V, fit transient amplitude = {tr:.6f} V,"
              f" expected transient amplitude = {-ss0:.6f} V")

    # Start transient check: remove the expected steady state, then fit C exp(-t/tau) on 0 s to 0.3 s
    print("\nStart transient check (0 s to 0.3 s, expected steady state removed):")
    wt = G <= 0.3
    for name, idx, y in (("VX", "X", vx), ("VY", "Y", vy)):
        dc, ph = expected_ideal[idx]
        ss = dc + sum(z.real * np.cos(2 * math.pi * f * G) - z.imag * np.sin(2 * math.pi * f * G)
                      for f, z in ph.items())
        ss0 = dc + sum(z.real for z in ph.values())
        r = (y - ss)[wt]
        e = np.exp(-G[wt] / TAU)
        c_fit = float(np.sum(r * e) / np.sum(e * e))
        print(f"  {name}: fitted transient amplitude = {c_fit:.5f} V,"
              f" expected = {-ss0:.5f} V, difference = {(c_fit + ss0) * 1e3:+.3f} mV")

    # Residuals after fit B and comparison with the full expected waveform
    print("\nResidual RMS of window 1 s to 3 s after fit B (all products and transient fitted):")
    for name in ("VX", "VY"):
        r = results[name]["resid_b"]
        print(f"  {name}: {np.sqrt(np.mean(r ** 2)) * 1e3:.4f} mV rms, max {np.max(np.abs(r)) * 1e3:.4f} mV")

    print("\nFull record 0 s to 3 s, data minus expected (mV):")
    summary = {}
    e_ideal_x, e_ideal_y = ideal["X"], ideal["Y"]
    e_cal_x, e_cal_y = calib["X"], calib["Y"]
    for name, y, ei, ec in (("VX", vx, e_ideal_x, e_cal_x), ("VY", vy, e_ideal_y, e_cal_y)):
        d_i = y - ei
        d_c = y - ec
        for label, lo, hi in (("0 to 3 s", 0.0, 3.0), ("0 to 0.5 s (transient)", 0.0, 0.5),
                              ("1 to 3 s", 1.0, 3.0)):
            m = (G >= lo) & (G <= hi)
            print(f"  {name} {label:24s} ideal: RMS {np.sqrt(np.mean(d_i[m] ** 2)) * 1e3:8.4f}"
                  f"  max {np.max(np.abs(d_i[m])) * 1e3:8.4f}   calib: RMS {np.sqrt(np.mean(d_c[m] ** 2)) * 1e3:8.4f}"
                  f"  max {np.max(np.abs(d_c[m])) * 1e3:8.4f}")
        summary[name] = dict(ideal=d_i, calib=d_c)

    # Amplitude error of the beat
    print("\nBeat amplitude error (fit A, window 1 s to 3 s):")
    for name in ("VX", "VY"):
        amp = results[name]["amp"]
        print(f"  {name}: A = {amp:.6f} V, ideal K|H| = {k_h:.6f} V,"
              f" error = {(amp - k_h) / k_h * 100:+.4f} %, error {(amp - k_h) * 1e3:+.4f} mV,"
              f" versus P-02 calibrated {GAIN_P02 * k_h:.6f} V ({(amp - GAIN_P02 * k_h) * 1e3:+.4f} mV)")

    # X-Y phase difference from fit A
    px, py = results["VX"]["phi"], results["VY"]["phi"]
    dphi = math.degrees((px - py + math.pi) % (2 * math.pi) - math.pi)
    print(f"\nPhase X minus Y from fit A: {dphi:+.3f} deg (expected -(90 - d) = -89.82 deg)")
    print(f"Phase lag of the beat: phi_X = {math.degrees(px):.3f} deg (expected 147.86 deg),"
          f" phi_Y = {math.degrees(py):.3f} deg (expected -122.32 deg)")

    # Plots
    PLOT_DIR.mkdir(parents=True, exist_ok=True)
    step = 200
    tt = G[::step]
    fig, axes = plt.subplots(2, 1, figsize=(9, 7), sharex=True)
    for ax, name, y, ei, ec in ((axes[0], "VX", vx, ideal["X"], calib["X"]),
                                (axes[1], "VY", vy, ideal["Y"], calib["Y"])):
        ax.plot(tt, y[::step], lw=0.6, color="0.55", label="simulation")
        ax.plot(tt, ei[::step], lw=1.2, color="C0", label="expected (index model)")
        ax.plot(tt, ec[::step], lw=0.8, ls="--", color="C3", label="expected (calibrated)")
        ax.set_ylabel(f"{name} (V)")
        ax.grid(alpha=0.3)
        ax.legend(loc="upper right", fontsize=8)
    axes[1].set_xlabel("time (s)")
    fig.suptitle("P-07: VX and VY, input 518 Hz, references 517 Hz")
    fig.tight_layout()
    fig.savefig(PLOT_DIR / "P-07_vx_vy_vs_t.png", dpi=110)
    plt.close(fig)

    fig, axes = plt.subplots(2, 1, figsize=(9, 6), sharex=True)
    for ax, name in ((axes[0], "VX"), (axes[1], "VY")):
        key = "X" if name == "VX" else "Y"
        r_ideal = summary[name]["ideal"]
        r_fitb = results[name]["resid_b"]
        ax.plot(tt, r_ideal[::step] * 1e3, lw=0.6, color="C0", label="data minus expected (index model)")
        wn = np.nonzero(w)[0]
        ax.plot(G[wn][::step] , r_fitb[::step] * 1e3, lw=0.6, color="C2",
                label="residual after fit B, 1 s to 3 s")
        ax.set_ylabel(f"{name} residual (mV)")
        ax.grid(alpha=0.3)
        ax.legend(loc="upper right", fontsize=8)
    axes[1].set_xlabel("time (s)")
    fig.suptitle("P-07: residuals")
    fig.tight_layout()
    fig.savefig(PLOT_DIR / "P-07_residual.png", dpi=110)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(6, 6))
    wf = (G >= 1.0) & (G <= 3.0)
    ax.plot(vx[wf][::step] - MID, vy[wf][::step] - MID, lw=0.6, color="0.4", label="simulation")
    ax.plot(ideal["X"][wf][::step] - MID, ideal["Y"][wf][::step] - MID, lw=1.0, color="C0",
            label="expected (index model)")
    ax.plot([0], [0], "k+")
    ax.set_xlabel("VX - 2.5 V (V)")
    ax.set_ylabel("VY - 2.5 V (V)")
    ax.set_aspect("equal")
    ax.grid(alpha=0.3)
    ax.legend(loc="upper right", fontsize=8)
    ax.set_title("P-07: VX against VY, 1 s to 3 s")
    fig.tight_layout()
    fig.savefig(PLOT_DIR / "P-07_xy.png", dpi=110)
    plt.close(fig)
    print(f"\nPlots written to {PLOT_DIR}")


if __name__ == "__main__":
    main()
