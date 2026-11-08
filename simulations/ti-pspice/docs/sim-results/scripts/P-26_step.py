"""P-26c: step response of U1B with the MFB, GATE and GOUT, for cgate = 50 pF and 1 nF.

Run from simulations/ti-pspice:  python docs/sim-results/scripts/P-26_step.py
Reads sim-runs/P26c_step/P26c_step.csd (circuits/afe_eval_P26c.cir: V_EXC steps by +0.3 V at 1 ms,
.TRAN 0 4m 0 50n). Section 0 is cgate = 50 pF, section 1 is cgate = 1 nF.

Measures:
- Step: mean in 0.9 to 1.0 ms against the mean in 3.5 to 4.0 ms. Closed form: -0.3 V / 120 = -2.5000 mV
  (DC gain -R2/R1 of the MFB, the entry used the same DC gain).
- Overshoot: sample minimum after the step, (V_final - V_min) / |dV| x 100 %.
- Ringing: damped cosine with an offset, fitted to 1.0 to 3.9 ms. The fit gives the damped frequency,
  the decay rate, zeta = a / w0, f0 = sqrt(fd^2 + (a / 2 pi)^2), and Q = 1 / (2 zeta).
  Ringing overshoot of the fit: exp(-pi zeta / sqrt(1 - zeta^2)).
- Settling: means of the first and the second half of the final window (0.25 ms each).
- Closed form of the MFB from afe_eval_expected.py: f0 = 1 / (2 pi sqrt(R2 R3 C1 C2)), Q as in
  section "Excitation MFB". Overshoot from the closed-form Q.
"""
import sys
from pathlib import Path

import numpy as np
from scipy.optimize import curve_fit

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools"))
from csdf import read_csdf  # noqa: E402

T_STEP = 1e-3
PRE = (0.9e-3, 1.0e-3)
FINAL = (3.5e-3, 4.0e-3)
FIT = (1.0e-3, 3.9e-3)
R1, R2, R3, C1, C2 = 120e3, 1e3, 1e3, 47e-9, 22e-9
DC_GAIN = -R2 / R1
STEP_IN = 0.3


def closed_form():
    f0 = 1 / (2 * np.pi * np.sqrt(R2 * R3 * C1 * C2))
    Q = np.sqrt(C1 / C2) * np.sqrt(R2 * R3) / (R2 + R3 + R2 * R3 / R1)
    z = 1 / (2 * Q)
    over = np.exp(-np.pi * z / np.sqrt(1 - z * z)) * 100
    fd = f0 * np.sqrt(1 - z * z)
    return f0, Q, over, fd


def damped(x, A, a, f, ph, c):
    return A * np.exp(-a * x) * np.cos(2 * np.pi * f * x + ph) + c


def analyse(t, v, label):
    v0 = v[(t >= PRE[0]) & (t <= PRE[1])].mean()
    vf = v[(t >= FINAL[0]) & (t <= FINAL[1])].mean()
    dv = vf - v0
    post = t >= T_STEP
    tp, vp = t[post], v[post]
    imin = int(np.argmin(vp))
    vmin = vp[imin]
    over = (vf - vmin) / abs(dv) * 100.0

    m = (t > FIT[0]) & (t < FIT[1])
    tt, rr = t[m] - T_STEP, v[m] - vf
    p, _ = curve_fit(damped, tt, rr, p0=[-2.5e-3, 21000, 3600, 0, 0], maxfev=20000)
    A, a, fd, ph, c = p
    w0 = np.hypot(2 * np.pi * fd, a)
    zeta = a / w0
    f0 = w0 / (2 * np.pi)
    Q = 1 / (2 * zeta)
    over_fit = np.exp(-np.pi * zeta / np.sqrt(1 - zeta * zeta)) * 100
    res = rr - damped(tt, *p)

    fw = final_halves(t, v)
    print(f"{label}:")
    print(f"  V before {v0*1e3:.4f} mV, V final {vf*1e3:.4f} mV, dV {dv*1e3:+.5f} mV "
          f"(closed form {STEP_IN*DC_GAIN*1e3:+.5f} mV)")
    print(f"  overshoot (sample minimum at {tp[imin]*1e3:.4f} ms) {over:.3f} %; "
          f"overshoot of the fit {over_fit:.3f} %")
    print(f"  fit: damped frequency {fd:.1f} Hz, zeta {zeta:.4f}, f0 {f0:.1f} Hz, Q {Q:.4f}, "
          f"fit residual {res.std()*1e6:.2f} uV rms against an amplitude of {abs(A)*1e3:.4f} mV")
    print(f"  settling of the final level: first half {fw[0]*1e3:.5f} mV, second half {fw[1]*1e3:.5f} mV, "
          f"difference {100*(fw[1]-fw[0])/abs(dv):+.5f} % of the step")
    return dict(dv=dv, over=over, over_fit=over_fit, fd=fd, zeta=zeta, f0=f0, Q=Q, res=res.std())


def final_halves(t, v):
    a = v[(t >= FINAL[0]) & (t < (FINAL[0] + FINAL[1]) / 2)].mean()
    b = v[(t >= (FINAL[0] + FINAL[1]) / 2) & (t <= FINAL[1])].mean()
    return a, b


def main():
    f0, Q, over_cf, fd_cf = closed_form()
    print(f"closed form MFB: f0 {f0:.1f} Hz, Q {Q:.4f}, overshoot {over_cf:.3f} %, damped frequency {fd_cf:.1f} Hz")
    print(f"closed form step: {STEP_IN} V x ({DC_GAIN:.6f}) = {STEP_IN*DC_GAIN*1e3:+.5f} mV")
    secs = read_csdf(ROOT / "sim-runs" / "P26c_step" / "P26c_step.csd")
    assert len(secs) == 2, f"expected 2 sections, got {len(secs)}"
    for s, label in zip(secs, ("cgate 50 pF", "cgate 1 nF")):
        t = np.real(np.asarray(s.x)).astype(float)
        for key in ("V(GOUT)", "V(GATE)"):
            v = np.asarray(s[key], dtype=float)
            analyse(t, v, f"{label} {key}")


if __name__ == "__main__":
    main()
