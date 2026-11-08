"""P-26a: AC response of the excitation chain (V_EXC to GATE and GOUT) at 518 Hz and at the DAC image, for cgate = 50 pF and 1 nF.

Run from simulations/ti-pspice:  python docs/sim-results/scripts/P-26_ac.py
Reads sim-runs/P26a_ac3/P26a_ac3.csd (circuits/afe_eval_P26a.cir, acexc = 1, .AC DEC 100 10 1MEG).

The log grid has 100 points per decade, so 518 Hz and 65.786 kHz are not grid points. Values at these
frequencies are interpolated: log|H| and the unwrapped phase are linear in log f between the two neighbours.
The interpolation error is estimated from a quadratic through three neighbours.

Closed form: mfb() of afe_eval_expected.py (ideal op amp). A nodal model with a single-pole open loop
gain (GBW) and a series output resistance (Ro) is included for the deviation check. GBW and Ro are not
verified values, so the model is shown as a deviation test only.
"""
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools"))
from csdf import read_csdf  # noqa: E402

EXP = ROOT / "docs/sim-results/scripts/afe_eval_expected.py"
_ns = {}
exec(compile(EXP.read_text(encoding="utf-8").split('section("Front end')[0], str(EXP), "exec"), _ns)
mfb = _ns["mfb"]

F0 = 518.0
FI = 65786.0
RUN = "P26a_ac3"
R1, R2, R3, C1, C2 = 120e3, 1e3, 1e3, 47e-9, 22e-9


def interp(f, H, f0):
    """Log-frequency interpolation of |H| and unwrapped phase between the two neighbours."""
    k = int(np.searchsorted(f, f0)) - 1
    t = (np.log10(f0) - np.log10(f[k])) / (np.log10(f[k + 1]) - np.log10(f[k]))
    lm = (1 - t) * np.log(abs(H[k])) + t * np.log(abs(H[k + 1]))
    ph = np.unwrap(np.angle(H[k:k + 2]))
    p = (1 - t) * ph[0] + t * ph[1]
    return np.exp(lm + 1j * p), k


def interp_quadratic_phase(f, H, f0):
    """Phase at f0 from a quadratic through three neighbours in log f (error estimate)."""
    k = int(np.searchsorted(f, f0)) - 1
    x = np.log10(f[k - 1:k + 2])
    y = np.unwrap(np.angle(H[k - 1:k + 2]))
    c = np.polyfit(x, y, 2)
    return np.polyval(c, np.log10(f0))


def nodal(f, GBW=1.1e6, Ro=1e-6):
    """MFB with single-pole op amp (GBW, output resistance Ro), vp = 0, input 1 V. Returns V(GATE) for an ideal gate."""
    s = 2j * np.pi * f
    A = 2 * np.pi * GBW / s
    G1, G2, G3, Go = 1 / R1, 1 / R2, 1 / R3, 1 / Ro
    M = np.zeros((4, 4), complex)
    b = np.zeros(4, complex)
    M[0] = [-(G1 + s * C1 + G2 + G3), G3, G2, 0]
    b[0] = -G1
    M[1] = [G3, -(G3 + s * C2), s * C2, 0]
    M[2] = [G2, s * C2, -(Go + G2 + s * C2), Go]
    M[3] = [0, A, 0, 1]
    return np.linalg.solve(M, b)[2]


def main():
    secs = read_csdf(ROOT / "sim-runs" / RUN / f"{RUN}.csd")
    assert len(secs) == 2, f"expected 2 sections (cgate 50 pF, 1 nF), got {len(secs)}"
    H0 = mfb(F0)
    HI = mfb(FI)
    print(f"closed form MFB: |H(518 Hz)| = {abs(H0):.7e} V/V, 1/|H| = {1/abs(H0):.5f}, "
          f"phase {np.degrees(np.angle(H0)):+.4f} deg")
    print(f"closed form image 65.786 kHz rel 518 Hz: {20*np.log10(abs(HI)/abs(H0)):+.3f} dB")

    rows = []
    for s, label in zip(secs, ("50 pF", "1 nF")):
        f = np.real(np.asarray(s.x)).astype(float)
        g = np.asarray(s["V(GATE)"], dtype=complex)
        o = np.asarray(s["V(GOUT)"], dtype=complex)
        Hg, k = interp(f, g, F0)
        Ho, _ = interp(f, o, F0)
        Hi, _ = interp(f, g, FI)
        ph_quad = interp_quadratic_phase(f, g, F0)
        ph_lin = np.degrees(np.angle(Hg))
        rows.append((label, Hg, Hi))
        print(f"cgate {label}: grid points {f[k]:.3f} Hz and {f[k+1]:.3f} Hz")
        print(f"  V(GATE) at 518 Hz: |H| = {abs(Hg):.7e} V/V, 1/|H| = {1/abs(Hg):.5f}, phase {ph_lin:+.4f} deg")
        print(f"  phase interpolation error (linear minus quadratic): {ph_lin - np.degrees(ph_quad):+.5f} deg")
        print(f"  V(GOUT) at 518 Hz: phase {np.degrees(np.angle(Ho)):+.4f} deg")
        print(f"  V(GATE) at 65.786 kHz: |H| = {abs(Hi):.7e} V/V, {20*np.log10(abs(Hi)/abs(H0)):+.3f} dB rel 518 Hz")
        m = f > 100e3
        mono = np.all(np.diff(np.abs(g[m])) <= 0)
        i102 = int(np.argmin(np.abs(f - 102e3)))
        print(f"  monotonic decrease above 100 kHz: {bool(mono)}; |V(GATE)| at {f[i102]/1e3:.2f} kHz = {abs(g[i102]):.3e} V/V")

    d_phase = np.degrees(np.angle(rows[1][1]) - np.angle(rows[0][1]))
    d_gain = 100 * (abs(rows[1][1]) / abs(rows[0][1]) - 1)
    print(f"50 pF to 1 nF at 518 Hz: phase {d_phase:+.4f} deg, gain {d_gain:+.5f} %")
    print(f"closed form R59 x (1 nF - 50 pF) x omega: {np.degrees(100*(1e-9-50e-12)*2*np.pi*F0):+.4f} deg")
    print(f"closed form 1 nF alone, R59 x 1 nF x omega: {np.degrees(100*1e-9*2*np.pi*F0):+.4f} deg")

    print("image attenuation at 65.786 kHz, simulated against the closed form and the nodal model:")
    for label, Hg, Hi in rows:
        print(f"  {label}: simulated {20*np.log10(abs(Hi)/abs(Hg)):+.3f} dB")
    print(f"  closed form (ideal op amp): {20*np.log10(abs(HI)/abs(H0)):+.3f} dB")
    h0m = nodal(F0, GBW=1e12, Ro=1e-6)  # ideal op amp
    for GBW, Ro in [(1.1e6, 1e-6), (2.5e6, 1e-6), (1.1e6, 200), (1.1e6, 300), (1.1e6, 500)]:
        h0 = nodal(F0, GBW, Ro)
        hi = nodal(FI, GBW, Ro)
        print(f"  nodal GBW {GBW/1e6:.1f} MHz, Ro {Ro:g} Ohm: image {20*np.log10(abs(hi)/abs(h0)):+.3f} dB, "
              f"phase 518 Hz {np.degrees(np.angle(h0)):+.4f} deg "
              f"({np.degrees(np.angle(h0)-np.angle(h0m)):+.4f} deg against the ideal op amp)")
    print("single-pole and output-resistance values are not verified against the OPAx196 model.")

    print("the -40.9 dB image attenuation printed above is the value for each cgate value (50 pF, 1 nF).")


if __name__ == "__main__":
    main()
