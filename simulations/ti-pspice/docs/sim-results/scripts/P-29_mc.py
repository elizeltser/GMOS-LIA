"""P-29 system CMRR Monte Carlo analysis.

Run from simulations/ti-pspice:
    python docs/sim-results/scripts/P-29_mc.py sim-runs/P29_mc/P29_mc.csd sim-runs/P29_nom/P29_nom.csd

Section 0 of the MC CSDF is the nominal (no tolerance). Sections 1 to n are the passes.
Probes: V(DRN_A), V(DRN_B) (complex drain voltages) and V(BPF_OUT) (complex front-end output), 518 Hz.

CMRR (drain probes) = |(V_A + V_B) / 2| / |V_B - V_A|, per pass.
Cross-check: |(BPF - BPF_nom) / 39.578| against |V_B - V_A|. The nominal BPF_OUT is the vendor INA828
common-mode leakage (no differential at the drains). Gain 39.578 V/V is the P-27 vendor value.

Phase split: the wanted differential drain signal per unit pixel current on side A has phase
phi_ref = +175.58 deg (nodal model with 70 pF and 1 pF coupling, equal to P-27 -4.427 deg plus 180 deg,
because a pixel sinks current). The common-mode drain has the same sign convention, so the leakage
of the R_D mismatch lies on the wanted axis (X) and the C mismatch in quadrature (Y).
X and Y are given per cent of the common-mode drain amplitude.
"""
import importlib.util
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "tools"))
from csdf import read_csdf  # noqa: E402

spec = importlib.util.spec_from_file_location("p29exp", os.path.join(HERE, "P-29_expected.py"))
p29 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p29)

G_BPF = 39.578
PHI_W = -4.427  # deg, wanted differential phase per unit in-phase sink current on side A (P-27)


def load(path):
    secs = read_csdf(path)
    nom = secs[0]
    passes = secs[1:]
    a = np.array([complex(s["V(DRN_A)"][0]) for s in passes])
    b = np.array([complex(s["V(DRN_B)"][0]) for s in passes])
    h = np.array([complex(s["V(BPF_OUT)"][0]) for s in passes])
    h0 = complex(nom["V(BPF_OUT)"][0])
    an = complex(nom["V(DRN_A)"][0])
    bn = complex(nom["V(DRN_B)"][0])
    return a, b, h, h0, an, bn, len(passes)


def stats(x):
    return float(np.median(x)), float(np.percentile(x, 5)), float(np.percentile(x, 95)), float(np.std(x, ddof=1))


def numpy_xy(rng, n=200_000):
    """numpy expectation for the X and Y split, corrected board model (model 2 of P-29_expected.py)."""
    RA = p29.R0 * (1 + rng.uniform(-0.001, 0.001, n))
    RB = p29.R0 * (1 + rng.uniform(-0.001, 0.001, n))
    CA = 50e-12 * (1 + rng.uniform(-0.10, 0.10, n)) + 20e-12
    CB = 50e-12 * (1 + rng.uniform(-0.10, 0.10, n)) + 20e-12
    Cd = np.full(n, 1e-12)
    sink = np.full(n, -p29.I_CM, dtype=complex)  # sink convention as in the PSpice circuit
    VA, VB = p29.solve(RA, RB, CA, CB, Cd, sink, sink)
    cm = (VA + VB) / 2
    eps = (VB - VA) * np.exp(-1j * np.radians(PHI_W)) / np.abs(cm)
    X = 100 * eps.real
    Y = 100 * eps.imag
    cmrr = 20 * np.log10(np.abs(cm) / np.abs(VB - VA))
    return X, Y, cmrr


def main(mc_path, nom_path):
    a, b, h, h0, an, bn, npass = load(mc_path)
    _, _, _, _, _, _, _ = load(nom_path)
    cm = (a + b) / 2
    diff = b - a
    cmrr = 20 * np.log10(np.abs(cm) / np.abs(diff))
    med, p5, p95, sd = stats(cmrr)
    print(f"passes {npass}")
    print(f"nominal drains: |A| {abs(an):.6f} V, |B| {abs(bn):.6f} V, |B - A| {abs(bn - an):.3e} V")
    print(f"nominal BPF_OUT {abs(h0):.4e} V at {np.degrees(np.angle(h0)):+.2f} deg (INA828 common-mode leak)")
    rng_b = np.random.default_rng(1)
    boot = np.median(cmrr[rng_b.integers(0, len(cmrr), size=(5000, len(cmrr)))], axis=1)
    print(f"CMRR (drain probes): median {med:.2f} dB (bootstrap SE {np.std(boot, ddof=1):.2f} dB), 5 % {p5:.2f} dB, 95 % {p95:.2f} dB, std {sd:.2f} dB")
    print(f"|cm| mean {np.mean(np.abs(cm)):.5f} V, min {np.min(np.abs(cm)):.5f} V, max {np.max(np.abs(cm)):.5f} V")

    # Cross-check through BPF_OUT
    dbpf = (h - h0) / G_BPF
    ratio = dbpf / diff
    print(f"BPF/39.578 against |B - A|: ratio magnitude median {np.median(np.abs(ratio)):.6f}, "
          f"spread {np.std(np.abs(ratio)) / np.mean(np.abs(ratio)) * 100:.4f} %")
    print(f"BPF/39.578 phase against B - A: median {np.degrees(np.median(np.angle(ratio))):+.3f} deg")
    cmrr_bpf = 20 * np.log10(np.abs(cm) / np.abs(dbpf))
    m2, q5, q95, s2 = stats(cmrr_bpf)
    print(f"CMRR via BPF_OUT (nominal leak removed): median {m2:.2f} dB, 5 % {q5:.2f} dB, 95 % {q95:.2f} dB")
    print(f"CMRR of INA828 common-mode leak (nominal BPF): {20*np.log10(np.abs(cm).mean() / (np.abs(h0)/G_BPF)):.2f} dB")

    # Phase split
    eps = diff * np.exp(-1j * np.radians(PHI_W)) / np.abs(cm)
    X = 100 * eps.real
    Y = 100 * eps.imag
    print(f"X (in phase with wanted), % of |cm|: median {np.median(X):+.4f}, std {np.std(X, ddof=1):.4f}")
    print(f"Y (quadrature), % of |cm|: median {np.median(Y):+.4f}, std {np.std(Y, ddof=1):.4f}")
    print(f"Power share of Y in leakage: {np.mean(Y**2) / np.mean(X**2 + Y**2) * 100:.1f} %")

    rng = np.random.default_rng(2026)
    Xn, Yn, cn = numpy_xy(rng)
    print(f"numpy X std {np.std(Xn):.4f} %, Y std {np.std(Yn):.4f} %, CMRR median {np.median(cn):.2f} dB")
    print(f"numpy Y power share {np.mean(Yn**2) / np.mean(Xn**2 + Yn**2) * 100:.1f} %")
    print(f"| Quantity | numpy (corrected) | PSpice |")
    print("|---|---|---|")
    print(f"| CMRR median (dB) | {np.median(cn):.2f} | {med:.2f} |")
    print(f"| CMRR 5 % (dB) | {np.percentile(cn, 5):.2f} | {p5:.2f} |")
    print(f"| CMRR 95 % (dB) | {np.percentile(cn, 95):.2f} | {p95:.2f} |")
    print(f"| X std (%) | {np.std(Xn):.4f} | {np.std(X, ddof=1):.4f} |")
    print(f"| Y std (%) | {np.std(Yn):.4f} | {np.std(Y, ddof=1):.4f} |")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit("usage: P-29_mc.py <csd MC> <csd nominal>")
    main(sys.argv[1], sys.argv[2])
