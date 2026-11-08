"""P-29 expected CMRR of the drain stage, numpy, two models.

Run from simulations/ti-pspice:
    python docs/sim-results/scripts/P-29_expected.py

Nodal model of the two drains at f = 518 Hz. Each drain is R_D to an ideal supply (AC ground)
in parallel with its node capacitance. Common-mode drive: 1/330 kOhm A into each drain (in phase).
Differential leakage = V_B - V_A. CMRR = |(V_A + V_B) / 2| / |V_B - V_A|.

Model 1 (entry, as written in simulation-index.md P-29): node C = 50 pF x (1 + u), u uniform in +-10 %,
  R_D = 330 kOhm x (1 + v), v uniform in +-0.1 %, no fixed capacitance, no coupling.
Model 2 (corrected, board model): node C = 50 pF x (1 + u) + 20 pF (10 pF TMUX1109 cmux and 10 pF INA828
  input capacitance, both fixed and matched), coupling C_DIFF = 1 pF between the drains (INA828 internal).
Model 3 (matched C, entry): C = 50 pF on both nodes, R tolerance only (entry value 64.6 dB).
Model 4 (matched C, corrected): C = 70 pF on both nodes, coupling 1 pF, R tolerance only.

Nodal equations (V_A, V_B are phasors, I = 1/330k A):
  (G_A + jw(C_A + Cd)) V_A - jw Cd V_B = I
  -jw Cd V_A + (G_B + jw(C_B + Cd)) V_B = I
The wanted differential phase is taken from a unit pixel current into side A (side B blind), see wanted_phase().
"""
import numpy as np

F = 518.0
W = 2 * np.pi * F
R0 = 330e3
I_CM = 1.0 / R0
N = 200_000
SEED = 2026


def solve(RA, RB, CA, CB, Cd, IA, IB):
    """Solve the two-node system for a current IA into node A and IB into node B (arrays)."""
    yA = 1 / RA + 1j * W * (CA + Cd)
    yB = 1 / RB + 1j * W * (CB + Cd)
    c = -1j * W * Cd
    det = yA * yB - c * c
    VA = (IA * yB - c * IB) / det
    VB = (yA * IB - c * IA) / det
    return VA, VB


def cmrr_db(RA, RB, CA, CB, Cd):
    one = np.full_like(RA, I_CM, dtype=complex)
    zero = np.zeros_like(RA, dtype=complex)
    VA, VB = solve(RA, RB, CA, CB, Cd, one, one)
    vcm = np.abs((VA + VB) / 2)
    vdiff = np.abs(VB - VA)
    return 20 * np.log10(vcm / vdiff)


def draw(rng, cfix, cdiff, rtol, ctol, matched=False):
    RA = R0 * (1 + rng.uniform(-rtol, rtol, N))
    RB = R0 * (1 + rng.uniform(-rtol, rtol, N))
    if matched:
        CA = np.full(N, 50e-12) + cfix
        CB = CA.copy()
    else:
        CA = 50e-12 * (1 + rng.uniform(-ctol, ctol, N)) + cfix
        CB = 50e-12 * (1 + rng.uniform(-ctol, ctol, N)) + cfix
    return RA, RB, CA, CB, np.full(N, cdiff)


def pct(x):
    return np.percentile(x, [5, 50, 95])


def wanted_phase(CA, CB, Cd):
    """Phase of V_B - V_A per unit pixel current into side A, nominal capacitance (deg, median)."""
    one = np.full(1, -1.0 / 330e3, dtype=complex)  # unit in-phase sink current into side A (PSpice convention)
    zero = np.zeros(1, dtype=complex)
    VA, VB = solve(np.full(1, R0), np.full(1, R0), np.full(1, CA), np.full(1, CB), np.full(1, Cd), one, zero)
    return np.degrees(np.angle(VB - VA))[0]


def main():
    rng = np.random.default_rng(SEED)
    rows = []
    cases = [
        ("1 entry (50 pF toleranced, R 0.1 %)", 0.0, 0.0, 0.1, 10.0, False),
        ("2 corrected (50 pF toleranced + 20 pF matched, Cd 1 pF)", 20e-12, 1e-12, 0.1, 10.0, False),
        ("3 matched C, entry (50 pF, R 0.1 %)", 0.0, 0.0, 0.1, 0.0, True),
        ("4 matched C, corrected (70 pF, Cd 1 pF)", 20e-12, 1e-12, 0.1, 0.0, True),
    ]
    print("| Model | 5 % point (dB) | median (dB) | 95 % point (dB) |")
    print("|---|---|---|---|")
    out = {}
    for name, cfix, cdiff, rtol_pct, ctol_pct, matched in cases:
        RA, RB, CA, CB, Cd = draw(rng, cfix, cdiff, rtol_pct / 100, ctol_pct / 100, matched)
        d = cmrr_db(RA, RB, CA, CB, Cd)
        p5, p50, p95 = pct(d)
        out[name[0]] = p50
        print(f"| {name} | {p5:.1f} | {p50:.1f} | {p95:.1f} |")
    print()
    # Wanted differential phase (nominal corrected node, pixel on side A)
    phi_w = wanted_phase(70e-12, 70e-12, 1e-12)
    print(f"Wanted differential phase per in-phase sink current on A, nodal (70 pF, Cd 1 pF): {phi_w:+.3f} deg")
    print(f"Reference: P-27 (DRN_B - DRN_A)/GATE = -4.427 deg (71 pF node, used in P-29_mc.py)")
    print()
    print(f"Entry median (model 1) {out['1']:.1f} dB, corrected median (model 2) {out['2']:.1f} dB, "
          f"difference {out['2'] - out['1']:+.1f} dB")
    print(f"Matched C: entry (model 3) {out['3']:.1f} dB, corrected (model 4) {out['4']:.1f} dB")


if __name__ == "__main__":
    main()
