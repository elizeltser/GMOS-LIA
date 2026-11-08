"""P-24a and P-24b: AC response of the LIA-AFE-Eval front end (INA828 and K = 2 band-pass).

Run from simulations/ti-pspice:  python docs/sim-results/scripts/P-24_ac.py
Reads sim-runs/P24a_vendor/P24a_vendor.csd (vendor INA828 and OPAx196 models, circuits/afe_eval.cir)
and sim-runs/P24b_ideal/P24b_ideal.csd (ideal E-source blocks, circuits/afe_eval_P24b.cir).

Ideal values are the closed forms of afe_eval_expected.py. They are evaluated at the same grid
frequencies as the run, so the 1.16 % grid step does not enter the comparison. Band edges and the
peak are found on the grid by the same routine for the run and for the ideal curve.
Optional plot: docs/sim-results/plots/P-24_front_end.png (matplotlib, skipped if missing).
"""
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools"))
from csdf import read_csdf  # noqa: E402

# Closed forms: exec the definitions of afe_eval_expected.py (everything before its first printing call)
EXP = ROOT / "docs/sim-results/scripts/afe_eval_expected.py"
_src = EXP.read_text(encoding="utf-8")
_ns = {}
exec(compile(_src.split('section("Front end')[0], str(EXP), "exec"), _ns)
front, hpf, lpf, G_INA = _ns["front"], _ns["hpf"], _ns["lpf"], _ns["G_INA"]

F0 = 518.0
LIM_GAIN = 0.01    # percent
LIM_PHASE = 0.01   # deg
LIM_FREQ = 0.01    # percent
LIM_SLOPE = 0.01   # percent


def load(name):
    secs = read_csdf(ROOT / "sim-runs" / name / f"{name}.csd")
    assert len(secs) == 1, f"{name}: expected one section (acexc = 1), got {len(secs)}"
    s = secs[0]
    f = np.real(np.asarray(s.x)).astype(float)
    diff = s["V(DRN_B)"] - s["V(DRN_A)"]
    d = dict(
        f=f,
        ina=s["V(INA_OUT)"] / diff,                 # INA828 stage, full
        hp=s["V(HPF_OUT)"] / s["V(INA_OUT)"],        # K = 2 high-pass (U3A), stage
        bp=s["V(BPF_OUT)"] / s["V(HPF_OUT)"],        # K = 2 low-pass (U3B), stage
        tot=s["V(BPF_OUT)"] / diff,                  # whole front end
        diff=diff,
    )
    return d


def ideal(f):
    return dict(ina=np.full_like(f, G_INA, dtype=complex), hp=hpf(f), bp=lpf(f), tot=front(f))


def nearest(f, target):
    return int(np.argmin(np.abs(f - target)))


def cross_log(f0, f1, m0, m1, lev):
    t = (lev - m0) / (m1 - m0)
    return 10 ** (np.log10(f0) + t * (np.log10(f1) - np.log10(f0)))


def band_edges(f, mag):
    """Peak frequency and value on the grid, -3 dB edges by log-frequency interpolation."""
    k = int(np.argmax(mag))
    lev = mag[k] / np.sqrt(2)
    i = k
    while i > 0 and mag[i - 1] >= lev:
        i -= 1
    j = k
    while j < len(f) - 1 and mag[j + 1] >= lev:
        j += 1
    fl = cross_log(f[i - 1], f[i], mag[i - 1], mag[i], lev)
    fr = cross_log(f[j], f[j + 1], mag[j], mag[j + 1], lev)
    return f[k], mag[k], fl, fr


def slope_deg_per_hz(f, H, k):
    ph = np.angle(H[k + 1] / H[k - 1], deg=True)
    return ph / (f[k + 1] - f[k - 1])


def pct(a, b):
    return (abs(a) / abs(b) - 1.0) * 100.0


def dphase(a, b):
    return np.angle(a / b, deg=True)


def main():
    A = load("P24a_vendor")
    B = load("P24b_ideal")
    f = A["f"]
    assert np.allclose(f, B["f"]), "vendor and ideal runs must share the frequency grid"
    I = ideal(f)
    ideal_exact_f0 = {"tot": front(F0), "ina": G_INA, "hp": hpf(F0), "bp": lpf(F0)}

    print(f"grid: {len(f)} points, {f[0]:.2f} Hz to {f[-1]:.1f} Hz, step ratio {f[1]/f[0]:.5f}")
    print(f"exact ideal at {F0:.0f} Hz: |H| = {abs(ideal_exact_f0['tot']):.5f} V/V, "
          f"phase {np.degrees(np.angle(ideal_exact_f0['tot'])):+.4f} deg")

    # ---- P24b wiring check at the entry frequencies (same grid points for run and ideal)
    print("\n== P24b (ideal blocks) against the ideal closed form, same grid point")
    checks = [("518 Hz", F0), ("50 Hz", 50.0), ("1036 Hz", 2 * F0), ("1554 Hz", 3 * F0), ("5 kHz", 5000.0)]
    rows_b = []
    fail = []
    for label, t in checks:
        k = nearest(f, t)
        mb = abs(B["tot"][k]); mi = abs(I["tot"][k])
        pb = np.degrees(np.angle(B["tot"][k])); pi = np.degrees(np.angle(I["tot"][k]))
        ge = pct(mb, mi); pe = pb - pi
        ok = abs(ge) <= LIM_GAIN and abs(pe) <= LIM_PHASE
        fail += [] if ok else [label]
        rows_b.append((label, f[k], mb, mi, ge, pb, pi, pe, ok))
        print(f"  {label:8s} f = {f[k]:9.3f} Hz: run |H| {mb:.6f}, ideal {mi:.6f} V/V, diff {ge:+.5f} %, "
              f"run phase {pb:+.4f} deg, ideal {pi:+.4f} deg, diff {pe:+.5f} deg, {'PASS' if ok else 'FAIL'}")

    # peak and band edges, same algorithm on run and on ideal
    fpk_b, mpk_b, fl_b, fr_b = band_edges(f, abs(B["tot"]))
    fpk_i, mpk_i, fl_i, fr_i = band_edges(f, abs(I["tot"]))
    print("\n== Peak and -3 dB band (grid algorithm, same for run and ideal)")
    band_rows = []
    for lab, a, b in [("peak frequency (Hz)", fpk_b, fpk_i), ("peak |H| (V/V)", mpk_b, mpk_i),
                      ("lower -3 dB edge (Hz)", fl_b, fl_i), ("upper -3 dB edge (Hz)", fr_b, fr_i)]:
        d = pct(a, b)
        ok = abs(d) <= LIM_FREQ if "Hz" in lab else abs(d) <= LIM_GAIN
        band_rows.append((lab, a, b, d, ok))
        print(f"  {lab:24s} run {a:.6f}, ideal {b:.6f}, diff {d:+.5f} %, {'PASS' if ok else 'FAIL'}")
    # analytic reference from the entry, not a pass criterion (grid-limited)
    print(f"  analytic: peak {abs(front(518.03)):.4f} V/V, band edges 377.5 Hz and 710.9 Hz (entry)")

    # phase slope at 518 Hz by finite differences on the grid
    k0 = nearest(f, F0)
    sb = slope_deg_per_hz(f, B["tot"], k0)
    si = slope_deg_per_hz(f, I["tot"], k0)
    d_s = pct(sb, si)
    print(f"\n== Phase slope near 518 Hz (grid points {f[k0-1]:.2f}..{f[k0+1]:.2f} Hz)")
    print(f"  run {sb:.5f} deg/Hz, ideal grid {si:.5f} deg/Hz, diff {d_s:+.4f} %, "
          f"{'PASS' if abs(d_s) <= LIM_SLOPE else 'FAIL'}; analytic -0.4424 deg/Hz")

    # ---- vendor models: per stage at 518 Hz (no limit in the entry, reported)
    print("\n== Vendor models per stage at the grid point nearest 518 Hz")
    stage_rows = []
    for key, lab in [("ina", "INA828 (V(INA_OUT)/dV)"), ("hp", "K=2 HPF (HPF/INA)"),
                     ("bp", "K=2 LPF (BPF/HPF)"), ("tot", "Front end (BPF/dV)")]:
        mv = abs(A[key][k0]); mi = abs(I[key][k0])
        ph = dphase(A[key][k0], I[key][k0])
        stage_rows.append((lab, f[k0], mv, mi, pct(mv, mi), ph))
        print(f"  {lab:24s} f = {f[k0]:.3f} Hz: |H| {mv:.6f} vs ideal {mi:.6f} ({pct(mv, mi):+.4f} %), "
              f"phase deficit {ph:+.4f} deg")

    # ---- GBW estimate: op-amp phase and gain deficit scaled by 1/GBW (estimate)
    print("\n== GBW estimate (ESTIMATE: deficit scaled by nominal/GBW, OPAx196 stages only)")
    gbw = {}
    for key in ("hp", "bp"):
        gbw[key] = (pct(abs(A[key][k0]), abs(I[key][k0])), dphase(A[key][k0], I[key][k0]))
    for lab, s in [("GBW -30 %", 1 / 0.7), ("GBW +30 %", 1 / 1.3)]:
        tot_phase = sum(gbw[k][1] for k in gbw) * s
        print(f"  {lab}: phase of HPF {gbw['hp'][1]*s:+.4f} deg, LPF {gbw['bp'][1]*s:+.4f} deg, "
              f"sum {tot_phase:+.4f} deg (nominal sum {sum(gbw[k][1] for k in gbw):+.4f} deg), "
              f"change {tot_phase - sum(gbw[k][1] for k in gbw):+.4f} deg")

    # ---- vendor minus ideal, total front end, at selected grid points
    print("\n== Vendor minus ideal, whole front end, at selected grid points")
    for t in [50.0, F0, 706.27, 2 * F0, 3 * F0, 5000.0, f[-1]]:
        k = nearest(f, t)
        gerr = pct(abs(A["tot"][k]), abs(I["tot"][k]))
        perr = dphase(A["tot"][k], I["tot"][k])
        print(f"  f = {f[k]:10.3f} Hz: gain {gerr:+.3f} %, phase {perr:+.3f} deg")

    # ---- plot
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        out = ROOT / "docs/sim-results/plots/P-24_front_end.png"
        out.parent.mkdir(parents=True, exist_ok=True)
        fig, ax = plt.subplots(2, 1, sharex=True, figsize=(7, 6))
        ax[0].semilogx(f, 100 * (abs(A["tot"]) / abs(I["tot"]) - 1), label="vendor models")
        ax[0].semilogx(f, 100 * (abs(B["tot"]) / abs(I["tot"]) - 1), label="ideal blocks (P24b)")
        ax[0].set_ylabel("gain error vs ideal (%)")
        ax[1].semilogx(f, np.angle(A["tot"] / I["tot"], deg=True), label="vendor models")
        ax[1].semilogx(f, np.angle(B["tot"] / I["tot"], deg=True), label="ideal blocks (P24b)")
        ax[1].set_ylabel("phase error vs ideal (deg)")
        ax[1].set_xlabel("frequency (Hz)")
        ax[0].legend()
        ax[0].grid(True, which="both", alpha=0.3)
        ax[1].grid(True, which="both", alpha=0.3)
        fig.tight_layout()
        fig.savefig(out, dpi=120)
        print(f"\nplot written: {out}")
    except ImportError:
        print("\nmatplotlib not available, plot skipped")

    print("\nFAILED P24b checks:", fail if fail else "none")


if __name__ == "__main__":
    main()
