"""P-33c: drain bias amplifier output and VSUP_A against vdrc_a (LIA-AFE-Eval).

Run from simulations/ti-pspice:  python docs/sim-results/scripts/P-33_drain.py
Reads sim-runs/P33c_vdrc/P33c_vdrc.csd (circuits/afe_eval.cir, .DC LIN PARAM vdrc_a 0.4 3.3 0.05).

Conventions
- Expected: VSUP_A = 1.1 x vdrc_a - 7.5 mV (7.5 uA through R60, 1 kOhm).
- Linearity window: vdrc_a from 0.46 V to 3.19 V (the window of the entry). The deviation is taken from
  the least-squares line through the window, and from the expected formula.
- Compliance: the pixel stand-in is an ideal current sink, so DRN_A = VSUP_A - 7.5 uA x 330 kOhm. DRN_A is
  positive only for VSUP_A above 2.475 V. The linear result is valid while DRN_A stays above about 0 V.
- Transition: the largest kinks (second differences) of VSUP_A and U10AO against vdrc_a.
"""
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools"))
from csdf import read_csdf  # noqa: E402

sec = read_csdf(ROOT / "sim-runs" / "P33c_vdrc" / "P33c_vdrc.csd")[0]
x = sec.x
vsup = sec["V(VSUP_A)"]
u10 = sec["V(U10AO)"]
drn = sec["V(DRN_A)"]

exp = 1.1 * x - 7.5e-3
win = (x >= 0.46 - 1e-9) & (x <= 3.19 + 1e-9)
a, b = np.polyfit(x[win], vsup[win], 1)
dev_fit = vsup[win] - (a * x[win] + b)
dev_exp = vsup[win] - exp[win]
print("P-33c: drain bias amplifier")
print(f"window vdrc_a 0.46 to 3.19 V, {win.sum()} points")
print(f"least-squares VSUP_A = {a:.6f} x vdrc_a + {b*1e3:.4f} mV")
print(f"max |deviation from the line| = {np.abs(dev_fit).max()*1e3:.4f} mV "
      f"at vdrc_a = {x[win][np.argmax(np.abs(dev_fit))]:.2f} V")
print(f"max |VSUP_A - (1.1 vdrc_a - 7.5 mV)| = {np.abs(dev_exp).max()*1e3:.4f} mV")
d2 = np.diff(vsup, 2)
for i in np.argsort(np.abs(d2))[::-1][:3]:
    print(f"  VSUP_A kink at vdrc_a = {x[i+1]:.2f} V, second difference {d2[i]*1e6:.3f} uV per step^2")
d2u = np.diff(u10, 2)
iu = int(np.argmax(np.abs(d2u)))
print(f"largest U10AO kink at vdrc_a = {x[iu+1]:.2f} V, second difference {d2u[iu]*1e6:.3f} uV per step^2")
print(f"U10AO - VSUP_A at vdrc_a = 2.4 V: {(np.interp(2.4, x, u10) - np.interp(2.4, x, vsup))*1e3:.3f} mV "
      "(R60 drop, 7.5 mV expected)")
pos = np.where(drn > 0)[0]
v0 = x[pos[0]] if pos.size else float("nan")
j = pos[0] if pos.size else 0
vz = float(np.interp(0.0, [drn[j - 1], drn[j]], [x[j - 1], x[j]])) if j > 0 else float("nan")
print(f"DRN_A > 0 from grid point vdrc_a = {v0:.3f} V, interpolated zero crossing at vdrc_a = {vz:.3f} V; DRN_A at 0.46 V = {np.interp(0.46, x, drn):.4f} V; "
      f"at 3.19 V = {np.interp(3.19, x, drn):.4f} V")
