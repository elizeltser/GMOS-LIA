"""P-06 non-harmonic interference (V7 at 50 Hz and 600 Hz) for the LIA circuit.

The first run parses the .csd files once and caches the waveforms of the last 0.5 s on a
uniform 1 us grid, for the two P06 steps and for the 2 V baseline of P04. Later runs read
only that cache (add --rebuild to parse again). The script then computes:

1. The settled means over the last 50 periods, with the P-01 settling-bias correction,
   the settling check and the delta from the baseline.
2. The window-mean residual of the beat products, and a least-squares fit (DC, the
   decaying IC transient with tau = 0.1 s, and sine/cosine pairs at the expected products).
3. The ripple table: expected (square-wave weights, |H| and the Y-reference phase) against
   the fitted amplitudes, for VX and VY, and the Y minus X phase.
4. Plots: the last 200 ms, and an amplitude spectrum of the last 0.5 s.

Run from the project root:
    python docs/sim-results/scripts/P-06_interference.py
    python docs/sim-results/scripts/P-06_interference.py --rebuild   (re-parse the .csd files)
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

RUN = "P06_interf"
CSD = ROOT / f"sim-runs/{RUN}/{RUN}.csd"
BASE_CSD = ROOT / "sim-runs/P04_ampl/P04_ampl.csd"
CACHE = ROOT / f"sim-runs/{RUN}/P06_wave_cache.npz"
PLOT_DIR = ROOT / "docs/sim-results/plots"

F = 517.0                        # f_osc, Hz
T = 1.0 / F                      # s
N_PER = 50
T_END = 1.0                      # s
T_WIN = N_PER * T                # 96.71 ms
T1 = T_END - T_WIN               # start of the last 50 periods
T0 = T1 - T_WIN                  # start of the 50 periods before
TAU = 0.1                        # RC = 10 kOhm x 10 uF, s
A_IN = 2.0                       # V, fundamental amplitude (V4)
A_H = 0.2                        # V, interferer amplitude (V7)
TAU_D = 482.6e-6                 # s, delay of the Y reference (V6)
THETA = 2 * math.pi * F * TAU_D  # rad, phase of the fundamental of the Y reference
MID = 2.5
SETTLE_K = 0.097e-3 / 1.27       # P-01 settling-bias correction, per V of |V - 2.5 V|
NS = [1, 3]                      # odd reference harmonics used for the products
N_HARM_50 = 0.096711799          # .STEP LIST values of n_harm (circuits/lia_v2_harm.cir)
N_HARM_600 = 1.160541586
G0 = 0.5                         # s, cache starts here
DT = 1e-6                        # s, uniform grid
G = np.linspace(G0, T_END, round((T_END - G0) / DT) + 1)
FIT_LONG = (0.5, 1.0)            # least-squares window, 500 ms
FIT_SHORT = (0.8, 1.0)           # cross-check window, 200 ms
TRAP = getattr(np, "trapezoid", None) or np.trapz


def H(f):
    """RC low-pass of the output filter, complex."""
    return 1.0 / (1.0 + 1j * 2 * math.pi * f * TAU)


def build_cache():
    cache = {}
    secs = list(read_csdf(str(CSD)))
    print(f"P06 file: {len(secs)} sections")
    for s in secs:
        assert abs(s.x[-1] - T_END) < 1e-12, f"section ends at {s.x[-1]}"
        key = "s50" if s.step_value < 0.5 else "s600"
        f_i = F * (N_HARM_50 if key == "s50" else N_HARM_600)   # CSDF rounds the step value
        print(f"  CSDF step value {s.step_value!r} -> {key}, f_i = {f_i:.6f} Hz")
        cache[key + "_vx"] = np.interp(G, s.x, s["V(VX)"])
        cache[key + "_vy"] = np.interp(G, s.x, s["V(VY)"])
        cache[key + "_fi"] = np.array(f_i)
    del secs
    base = [s for s in read_csdf(str(BASE_CSD)) if abs(s.step_value - 2.0) < 1e-9]
    assert len(base) == 1, "P04 2 V section not found"
    b = base[0]
    assert abs(b.x[-1] - T_END) < 1e-12
    cache["base_vx"] = np.interp(G, b.x, b["V(VX)"])
    cache["base_vy"] = np.interp(G, b.x, b["V(VY)"])
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    np.savez(CACHE, **cache)
    print(f"wrote {CACHE}")


def load_cache():
    d = np.load(CACHE)
    return {k: d[k] for k in d.files}


def wmean(y, t0, t1):
    m = (G >= t0 - 1e-9) & (G <= t1 + 1e-9)
    g, yy = G[m], y[m]
    return float(TRAP(yy, g) / (g[-1] - g[0]))


def design(t, freqs):
    cols = [np.ones_like(t), np.exp(-t / TAU)]
    for f in freqs:
        cols.append(np.cos(2 * math.pi * f * t))
        cols.append(np.sin(2 * math.pi * f * t))
    return np.column_stack(cols)


def fit(y, win, freqs):
    """Least squares on a window. Returns DC, exp coefficient, {f: z} with y = Re[z exp(j 2 pi f t)], rms."""
    m = (G >= win[0] - 1e-9) & (G <= win[1] + 1e-9)
    t = G[m]
    X = design(t, freqs)
    coef, *_ = np.linalg.lstsq(X, y[m], rcond=None)
    res = y[m] - X @ coef
    z = {}
    for k, f in enumerate(freqs):
        c, s = coef[2 + 2 * k], coef[3 + 2 * k]
        z[f] = c - 1j * s
    return coef[0], coef[1], z, float(np.sqrt(np.mean(res ** 2)))


def terms(fa, amp, theta_ch, ns=None):
    """Output terms (n, name, |f|, complex z) of a sine at fa and amp times the square-wave reference.

    Output = -(mean of input x reference), filtered by H. Harmonic n of the reference
    carries the phase -n theta_ch (theta_ch = 0 for X, THETA for Y).
    """
    ns = NS if ns is None else ns
    out = []
    for n in ns:
        coef = 2 * amp / (n * math.pi)
        for name, fterm, c, psi in (
            ("diff", fa - n * F, -coef, n * theta_ch),
            ("sum", fa + n * F, +coef, -n * theta_ch),
        ):
            fabs = abs(fterm)
            psi_eff = psi if fterm >= 0 else -psi
            z = c * H(fabs) * np.exp(1j * psi_eff)
            out.append((n, name, fabs, z))
    return out


def predicted_z(fa, amp, theta_ch, ns=None):
    acc = {}
    for n, name, fabs, z in terms(fa, amp, theta_ch, ns):
        key = round(fabs, 3)
        acc[key] = acc.get(key, 0) + z
    return acc


def deg(z):
    return math.degrees(np.angle(z))


def wrap(a):
    return (a + 180.0) % 360.0 - 180.0


def window_residual(z, f, t0, t1):
    """Mean over [t0, t1] of Re[z exp(j 2 pi f t)]."""
    if f == 0:
        return z.real
    w = t1 - t0
    k = 2j * math.pi * f
    return float(np.real(z * (np.exp(k * t1) - np.exp(k * t0)) / (k * w)))


def main():
    if "--rebuild" in sys.argv or not CACHE.exists():
        build_cache()
    c = load_cache()
    fi_50, fi_600 = float(c["s50_fi"]), float(c["s600_fi"])
    print()
    print("Frequencies and timing")
    print(f"  f_i(50 Hz step) = {fi_50:.6f} Hz, f_i(600 Hz step) = {fi_600:.6f} Hz, f_osc = {F:.1f} Hz")
    print(f"  THETA = {math.degrees(THETA):.4f} deg (Y reference delay of the fundamental)")
    print(f"  T = {T * 1e3:.6f} ms, window = {T_WIN * 1e3:.4f} ms, T1 = {T1:.7f} s, T0 = {T0:.7f} s")
    print()

    steps = {
        "base": {"f": 0.0, "vx": c["base_vx"], "vy": c["base_vy"]},
        "s50": {"f": fi_50, "vx": c["s50_vx"], "vy": c["s50_vy"]},
        "s600": {"f": fi_600, "vx": c["s600_vx"], "vy": c["s600_vy"]},
    }

    # 1. Settled means and settling check
    print("1. Settled means (50 periods, raw and P-01 corrected) and settling check")
    print(f"{'step':>6} {'VX raw':>12} {'VY raw':>12} {'VX corr':>12} {'VY corr':>12} "
          f"{'VX set mV':>10} {'VY set mV':>10} {'dVX mV':>9} {'dVY mV':>9}")
    means = {}
    for k, st in steps.items():
        mx = wmean(st["vx"], T1, T_END)
        my = wmean(st["vy"], T1, T_END)
        px = wmean(st["vx"], T0, T1)
        py = wmean(st["vy"], T0, T1)
        means[k] = {"raw_x": mx, "raw_y": my,
                    "cor_x": mx + SETTLE_K * (mx - MID), "cor_y": my + SETTLE_K * (my - MID),
                    "set_x": (mx - px) * 1e3, "set_y": (my - py) * 1e3}
    for k in steps:
        m = means[k]
        m["dx"] = (m["cor_x"] - means["base"]["cor_x"]) * 1e3
        m["dy"] = (m["cor_y"] - means["base"]["cor_y"]) * 1e3
        print(f"{k:>6} {m['raw_x']:12.8f} {m['raw_y']:12.8f} {m['cor_x']:12.8f} {m['cor_y']:12.8f} "
              f"{m['set_x']:10.4f} {m['set_y']:10.4f} {m['dx']:9.4f} {m['dy']:9.4f}")
    print()

    # Frequencies for the fit
    prod_freqs = {}
    for k in ("s50", "s600"):
        fi = steps[k]["f"]
        fl = [2 * F, 4 * F]
        for n in NS:
            fl += [abs(fi - n * F), fi + n * F]
        prod_freqs[k] = sorted(set(round(f, 6) for f in fl))
    prod_freqs["base"] = [2 * F, 4 * F]

    fits = {}
    for k in steps:
        for ch in ("x", "y"):
            y = steps[k]["v" + ch]
            fits[(k, ch, "long")] = fit(y, FIT_LONG, prod_freqs[k])
            fits[(k, ch, "short")] = fit(y, FIT_SHORT, prod_freqs[k])

    print("   Least-squares settled DC (exp transient with tau = 0.1 s and product sines included)")
    print(f"{'step':>6} {'VX DC 0.5s':>13} {'VX DC 0.2s':>13} {'VY DC 0.5s':>13} {'VY DC 0.2s':>13} "
          f"{'VX exp coef':>12} {'VY exp coef':>12} {'rms VX mV':>10} {'rms VY mV':>10}")
    dc = {}
    for k in steps:
        fxl, fyl = fits[(k, "x", "long")], fits[(k, "y", "long")]
        fxs, fys = fits[(k, "x", "short")], fits[(k, "y", "short")]
        dc[k] = {"x": fxl[0], "y": fyl[0], "x_s": fxs[0], "y_s": fys[0]}
        print(f"{k:>6} {fxl[0]:13.8f} {fxs[0]:13.8f} {fyl[0]:13.8f} {fys[0]:13.8f} "
              f"{fxl[1]:12.6f} {fyl[1]:12.6f} {fxl[3] * 1e3:10.5f} {fyl[3] * 1e3:10.5f}")
    print()
    print("   Settled delta from baseline (mV): fit 0.5 s, fit 0.2 s, corrected 50-period mean")
    print(f"{'step':>6} {'dVX fit':>10} {'dVX 0.2s':>10} {'dVY fit':>10} {'dVY 0.2s':>10} "
          f"{'dVX mean':>10} {'dVY mean':>10}")
    for k in ("s50", "s600"):
        print(f"{k:>6} {(dc[k]['x'] - dc['base']['x']) * 1e3:10.5f} "
              f"{(dc[k]['x_s'] - dc['base']['x_s']) * 1e3:10.5f} "
              f"{(dc[k]['y'] - dc['base']['y']) * 1e3:10.5f} "
              f"{(dc[k]['y_s'] - dc['base']['y_s']) * 1e3:10.5f} "
              f"{means[k]['dx']:10.5f} {means[k]['dy']:10.5f}")
    print()

    # 2. Window-mean residual of the products
    print("2. Window-mean residual: 50-period mean minus fitted DC, and the part from each product")
    for k in ("base", "s50", "s600"):
        for ch in ("x", "y"):
            resid_meas = (means[k]["raw_" + ch] - dc[k][ch]) * 1e3
            fit_long = fits[(k, ch, "long")]
            prod = 0.0
            details = []
            for f, z in fit_long[2].items():
                r = window_residual(z, f, T1, T_END) * 1e3
                prod += r
                details.append(f"{f:.1f} Hz {r:+.5f}")
            exp_bias = fit_long[1] * TAU * (math.exp(-T1 / TAU) - math.exp(-T_END / TAU)) / (T_END - T1) * 1e3
            print(f"  {k:>5} {ch.upper()}: mean - fit DC = {resid_meas:+.5f} mV, exp part = {exp_bias:+.5f} mV, "
                  f"product part = {prod:+.5f} mV [{'; '.join(details)}]")
    print()

    # 3. Ripple: expected against fitted
    print("3. Ripple: expected against fitted amplitude (mV) and Y minus X phase (deg), 0.5 s window")
    for k in ("base", "s50", "s600"):
        fi = steps[k]["f"]
        fa, amp = (F, A_IN) if k == "base" else (fi, A_H)
        ex_x = predicted_z(fa, amp, 0.0)
        ex_y = predicted_z(fa, amp, THETA)
        labels = {}
        # the 2f and 4f terms belong to the fundamental, present in every step (n = 1 to 5)
        fund_x = predicted_z(F, A_IN, 0.0, ns=[1, 3, 5])
        fund_y = predicted_z(F, A_IN, THETA, ns=[1, 3, 5])
        labels = {round(2 * F, 3): "2f (fundamental)", round(4 * F, 3): "4f (fundamental)"}
        if k == "base":
            ex_x, ex_y = fund_x, fund_y
        else:
            for n, name, fabs, _ in terms(fa, amp, 0.0):
                labels.setdefault(round(fabs, 3), f"n={n} {name}")
            for key in (round(2 * F, 3), round(4 * F, 3)):
                ex_x[key] = fund_x[key]
                ex_y[key] = fund_y[key]
        title = "baseline, 2 V, no interferer" if k == "base" else f"interferer {fi:.4f} Hz"
        print(f"  --- {title}")
        print(f"  {'f (Hz)':>8} {'term':>22} {'|H|':>8} {'VX exp':>9} {'VX fit':>9} {'VX rat':>7} "
              f"{'VY exp':>9} {'VY fit':>9} {'VY rat':>7} {'VX 0.2s':>8} {'VY 0.2s':>8} "
              f"{'Y-X exp':>8} {'Y-X fit':>8}")
        for f in sorted(fits[(k, "x", "long")][2].keys()):
            key = round(f, 3)
            zxe, zye = ex_x.get(key, 0), ex_y.get(key, 0)
            zxm, zym = fits[(k, "x", "long")][2][f], fits[(k, "y", "long")][2][f]
            zxs, zys = fits[(k, "x", "short")][2][f], fits[(k, "y", "short")][2][f]
            print(f"  {f:8.2f} {labels.get(key, ''):>22} {abs(H(f)):8.5f} "
                  f"{abs(zxe) * 1e3:9.5f} {abs(zxm) * 1e3:9.5f} {abs(zxm) / abs(zxe):7.4f} "
                  f"{abs(zye) * 1e3:9.5f} {abs(zym) * 1e3:9.5f} {abs(zym) / abs(zye):7.4f} "
                  f"{abs(zxs) / abs(zxe):8.4f} {abs(zys) / abs(zye):8.4f} "
                  f"{wrap(deg(zye / zxe)):8.2f} {wrap(deg(zym / zxm)):8.2f}")
        print()

    # 4. Plots
    PLOT_DIR.mkdir(parents=True, exist_ok=True)
    import matplotlib as _mpl  # noqa: F401  (backend already set)
    m200 = (G >= FIT_SHORT[0] - 1e-9) & (G <= FIT_SHORT[1] + 1e-9)
    tg = G[m200]
    fig, ax = plt.subplots(2, 2, figsize=(11, 7), sharex=True)
    for row, ch in enumerate(("x", "y")):
        for col, k in enumerate(("s50", "s600")):
            a = ax[row, col]
            base_dc = dc["base"][ch]
            a.plot((tg - FIT_SHORT[0]) * 1e3, (steps["base"]["v" + ch][m200] - base_dc) * 1e3,
                   color="0.5", lw=1.0, label="baseline (2 V)")
            a.plot((tg - FIT_SHORT[0]) * 1e3, (steps[k]["v" + ch][m200] - base_dc) * 1e3,
                   color="C0" if k == "s50" else "C3", lw=1.0, label=f"interferer {steps[k]['f']:.0f} Hz")
            a.set_title(f"V{ch.upper()}, {steps[k]['f']:.0f} Hz interferer, last 200 ms", fontsize=10)
            a.set_ylabel(f"V{ch.upper()} minus baseline DC (mV)")
            a.grid(True, alpha=0.3)
            a.legend(fontsize=8, loc="upper right")
    ax[1, 0].set_xlabel("time within the last 200 ms (ms)")
    ax[1, 1].set_xlabel("time within the last 200 ms (ms)")
    fig.tight_layout()
    fig.savefig(PLOT_DIR / "P-06_last200ms.png", dpi=130)
    plt.close(fig)

    m05 = (G >= FIT_LONG[0] - 1e-9) & (G <= FIT_LONG[1] + 1e-9)
    tt = G[m05]
    w = np.hanning(len(tt))
    norm = np.sum(w)
    freq_ax = np.fft.rfftfreq(len(tt), DT)
    fig, ax = plt.subplots(2, 2, figsize=(11, 7), sharex=True)
    for row, ch in enumerate(("x", "y")):
        for col, k in enumerate(("s50", "s600")):
            a = ax[row, col]
            for kk, color, lab in (("base", "0.5", "baseline (2 V)"),
                                   (k, "C0" if k == "s50" else "C3", f"{steps[k]['f']:.0f} Hz interferer")):
                y = steps[kk]["v" + ch][m05]
                ex = fits[(kk, ch, "long")][1] * np.exp(-tt / TAU)
                yr = y - dc[kk][ch] - ex
                spec = 2 * np.abs(np.fft.rfft(yr * w)) / norm * 1e3
                a.semilogy(freq_ax, np.maximum(spec, 1e-4), color=color, lw=0.9, label=lab)
            fi = steps[k]["f"]
            for mkf in [2 * F] + [abs(fi - n * F) for n in NS] + [fi + n * F for n in NS]:
                a.axvline(mkf, color="k", ls=":", lw=0.7)
            a.set_xlim(0, 2500)
            a.set_ylim(1e-3, 20)
            a.set_title(f"V{ch.upper()} amplitude spectrum, {steps[k]['f']:.0f} Hz interferer", fontsize=10)
            a.set_ylabel("amplitude (mV)")
            a.grid(True, alpha=0.3)
            a.legend(fontsize=8, loc="upper right")
    ax[1, 0].set_xlabel("frequency (Hz); dotted lines at 2 f_osc and |f_i +/- n f_osc|")
    ax[1, 1].set_xlabel("frequency (Hz); dotted lines at 2 f_osc and |f_i +/- n f_osc|")
    fig.tight_layout()
    fig.savefig(PLOT_DIR / "P-06_spectrum.png", dpi=130)
    plt.close(fig)
    print("plots written to", PLOT_DIR)


if __name__ == "__main__":
    main()
