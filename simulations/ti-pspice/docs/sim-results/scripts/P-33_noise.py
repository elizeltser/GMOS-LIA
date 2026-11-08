"""P-33d: noise of the drain bias node VSUP_A and DRN_A (LIA-AFE-Eval).

Run from simulations/ti-pspice:  python docs/sim-results/scripts/P-33_noise.py
Reads sim-runs/P33d_noise (AC and .NOISE at VSUP_A, AC 1 on V_DAC2) and sim-runs/P33d_noise_drn
(.NOISE at DRN_A, same circuit).

Method
- The transfer from V_DAC2 to a node is the complex AC value at 518 Hz (AC 1 on V_DAC2).
- The DAC noise is 100 nV/sqrt(Hz) at V_DAC2 (an assumed source, not in the netlist). Its contribution at
  the node is 100 nV/sqrt(Hz) x |H|.
- Device noise = TOTAL OUTPUT NOISE VOLTAGE of the .NOISE table (resistors and OPAx196 models).
- Total = root sum of squares of device and DAC contributions.
- Pass: at most 50 nV/sqrt(Hz) at VSUP_A.
"""
import re
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools"))
from csdf import read_csdf  # noqa: E402

DAC_NOISE = 100e-9  # V/sqrt(Hz)
RUNS = {"VSUP_A": "P33d_noise", "DRN_A": "P33d_noise_drn"}


def transfer(name, node):
    sec = read_csdf(ROOT / "sim-runs" / name / f"{name}.csd")[0]
    return float(np.abs(sec[f"V({node})"][0]))


def out_noise(name):
    text = (ROOT / "sim-runs" / name / f"{name}.out").read_text(errors="replace")
    m = re.search(r"TOTAL OUTPUT NOISE VOLTAGE\s*=\s*([0-9.E+-]+)\s*SQ V/HZ", text)
    contrib = re.findall(r"^\s*(\S+)\s*=\s*([0-9.E+-]+)\s*\(", text, re.M)
    return float(m.group(1)), contrib


for node, name in RUNS.items():
    H = transfer(name, node)
    dev_sq, contrib = out_noise(name)
    dev = np.sqrt(dev_sq)
    dac = DAC_NOISE * H
    tot = np.sqrt(dev**2 + dac**2)
    print(f"{node} at 518 Hz: |V({node})/V_DAC2| = {H:.6f} V/V")
    print(f"  device output noise (.NOISE table) = {dev*1e9:.4f} nV/sqrt(Hz)")
    print(f"  DAC noise at the node = {dac*1e9:.4f} nV/sqrt(Hz)")
    print(f"  total = {tot*1e9:.4f} nV/sqrt(Hz)")
    if node == "VSUP_A":
        print(f"  pass (at most 50 nV/sqrt(Hz)): {'yes' if tot*1e9 <= 50 else 'no'}")
    top = sorted(((float(v), k) for k, v in contrib if k.startswith(("R_", "X_"))), reverse=True)[:6]
    for v, k in top:
        print(f"    top device contributor {k:18s} {np.sqrt(v)*1e9:8.4f} nV/sqrt(Hz) at the output")
