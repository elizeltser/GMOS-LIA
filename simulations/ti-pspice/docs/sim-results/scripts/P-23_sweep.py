"""P-23c: DC sweep of the bench voltage v5 (+5 V input) in afe_eval.cir.

Run from simulations/ti-pspice:  python docs/sim-results/scripts/P-23_sweep.py
Reads sim-runs/P23c_sweep/P23c_sweep.csd (.DC LIN PARAM v5 4.6 5.6 0.05; v5n stays 5.3 V).
Reports the bench voltage that gives +5VA = 5.0 V and the zero-signal outputs over the sweep.
"""
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools"))
from csdf import read_csdf  # noqa: E402

sec = read_csdf(str(ROOT / "sim-runs" / "P23c_sweep" / "P23c_sweep.csd"))[0]
v5 = np.asarray(sec.x, dtype=float)
p5va = np.asarray(sec["V(P5VA)"], dtype=float)
p5vp = np.asarray(sec["V(P5VP)"], dtype=float)
xout = np.asarray(sec["V(X_OUT)"], dtype=float)
gate = np.asarray(sec["V(GATE)"], dtype=float)
vsup = np.asarray(sec["V(VSUP_A)"], dtype=float)

print(f"sweep points {len(v5)}, v5 from {v5[0]:.3f} V to {v5[-1]:.3f} V")
print("v5 (V)   +5VA (V)   +5VP (V)   X_OUT (mV)   GATE (V)     VSUP_A (V)")
for i in range(len(v5)):
    print(f"{v5[i]:6.3f}   {p5va[i]:9.6f}   {p5vp[i]:9.6f}   {xout[i]*1e3:+10.4f}   {gate[i]:.6f}   {vsup[i]:.6f}")

# bench voltage for +5VA = 5.0 V by linear interpolation between the two nearest points
target = 5.0
k = int(np.argmax(p5va >= target))
v5_t = v5[k - 1] + (target - p5va[k - 1]) * (v5[k] - v5[k - 1]) / (p5va[k] - p5va[k - 1])
slope = (p5va[k] - p5va[k - 1]) / (v5[k] - v5[k - 1])
print(f"\n+5VA = 5.000 V at v5 = {v5_t:.4f} V (slope d(+5VA)/d(v5) = {slope:.5f} V/V)")
print(f"+5VA at v5 = 5.0 V: {np.interp(5.0, v5, p5va):.6f} V (smoke run 4.820 V)")
print(f"+5VA at v5 = 5.3 V (default): {np.interp(5.3, v5, p5va):.6f} V")
print(f"v5 - (+5VA) at v5 = 5.3 V = {5.3 - np.interp(5.3, v5, p5va):.4f} V (diode D5 plus R18 and the 10 mOhm source)")

print(f"\nX_OUT over the sweep: max |X_OUT| = {np.max(np.abs(xout))*1e3:.4f} mV, limit 0.5 mV: "
      f"{'PASS' if np.max(np.abs(xout)) < 0.5e-3 else 'FAIL'}")
print(f"GATE spread over sweep: {(gate.max()-gate.min())*1e6:.3f} uV")
print(f"VSUP_A spread over sweep: {(vsup.max()-vsup.min())*1e6:.3f} uV, mean {vsup.mean():.6f} V")
print(f"DAC80508 reference check: +5VA >= 5.0 V at v5 >= {v5_t:.4f} V (VDD/2 = 2.5 V)")
print(f"smallest +5VA over sweep: {p5va.min():.6f} V at v5 = {v5[np.argmin(p5va)]:.3f} V")
