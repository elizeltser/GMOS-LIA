"""P-25 band-pass tolerance Monte Carlo: gain and phase spread at 518 Hz.

Run from simulations/ti-pspice:
    python docs/sim-results/scripts/P-25_mc.py sim-runs/P25a_mc5/P25a_mc5.csd sim-runs/P25b_mc1/P25b_mc1.csd

Each CSDF holds one AC section per pass (section 0 = Monte Carlo NOMINAL).
The probe V(BPF_OUT) is the complex front-end output at 518 Hz.
Relative gain and phase are taken against the nominal section of the same run.

The numpy block is the ideal reference of the entry: ideal op amps, uniform
tolerances (PSpice default DISTRIBUTION=UNIFORM), default_rng(seed=1),
200 000 samples per tolerance, R 0.1 % on R9 R10 R11 R12 R13 R70 R71 R72 R73,
C 5 % or 1 % on C9 C10 C11 C12. Gain and phase are relative to the ideal
nominal front(518 Hz).
"""
import sys
import os
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "tools"))
from csdf import read_csdf  # noqa: E402

F0 = 518.0
# Table of the entry (numpy, ideal amplifiers, uniform tolerances, 200 000 samples)
TABLE = {
    "5 %": {"gain_std": 7.13, "phase_std": 3.31},
    "1 %": {"gain_std": 1.43, "phase_std": 0.67},
}
SIM14 = {"gain_lim": 1.0, "phase_lim": 2.0}

# Nominal values of afe_eval.cir front end (same as afe_eval_expected.py)
RG = 5.62e3
R9 = R11 = R12 = R13 = 9.31e3
C9 = C10 = C11 = C12 = 33e-9
K = 2.0
G_INA = 1 + 50e3 / RG


def hpf(f, R1=R9, R2=R13, C1=C10, C2=C11, k=K):
    s = 2j * np.pi * f
    num = k * s**2
    den = s**2 + s * (1 / (R2 * C1) + 1 / (R2 * C2) + (1 - k) / (R1 * C1)) + 1 / (R1 * R2 * C1 * C2)
    return num / den


def lpf(f, R1=R11, R2=R12, C1=C9, C2=C12, k=K):
    s = 2j * np.pi * f
    w = 1 / (R1 * R2 * C1 * C2)
    den = s**2 + s * (1 / (R1 * C1) + 1 / (R2 * C1) + (1 - k) / (R2 * C2)) + w
    return k * w / den


def front(f):
    return G_INA * hpf(f) * lpf(f)


def load(path):
    secs = read_csdf(path)
    nom = secs[0]
    passes = secs[1:]
    h0 = complex(nom["V(BPF_OUT)"][0])
    h = np.array([complex(s["V(BPF_OUT)"][0]) for s in passes])
    return h0, h, len(secs), len(passes)


def stats(x):
    return {
        "mean": float(np.mean(x)),
        "std": float(np.std(x, ddof=1)),
        "p025": float(np.percentile(x, 2.5)),
        "p975": float(np.percentile(x, 97.5)),
    }


def boot_se_std(x, n_boot=2000, seed=1):
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(x), size=(n_boot, len(x)))
    s = np.std(x[idx], axis=1, ddof=1)
    return float(np.std(s, ddof=1))


def yields(gain_err, phase):
    yg = float(np.mean(np.abs(gain_err) <= SIM14["gain_lim"]) * 100.0)
    yp = float(np.mean(np.abs(phase) <= SIM14["phase_lim"]) * 100.0)
    yb = float(np.mean((np.abs(gain_err) <= SIM14["gain_lim"]) & (np.abs(phase) <= SIM14["phase_lim"])) * 100.0)
    return yg, yp, yb


def analyse(path, label):
    h0, h, nsec, npass = load(path)
    r = h / h0
    gain_err = (np.abs(r) - 1.0) * 100.0            # %, relative to nominal
    phase = np.degrees(np.angle(r))                  # deg, relative to nominal
    g = stats(gain_err)
    p = stats(phase)
    yg, yp, yb = yields(gain_err, phase)
    # Open point 3: absolute phase = nominal phase + deviation, limit 0 +- 2 deg
    abs_phase = np.degrees(np.angle(h))
    yp_abs = float(np.mean(np.abs(abs_phase) <= SIM14["phase_lim"]) * 100.0)
    yb_abs = float(np.mean((np.abs(gain_err) <= SIM14["gain_lim"]) & (np.abs(abs_phase) <= SIM14["phase_lim"])) * 100.0)
    print(f"== {label} ({path})")
    print(f"sections {nsec}, passes {npass} (nominal is section 0)")
    print(f"nominal H(518 Hz) = {h0.real:.6f}{h0.imag:+.6f}j, |H| = {abs(h0):.5f} V/V, "
          f"phase {np.degrees(np.angle(h0)):+.4f} deg")
    print(f"gain error %: mean {g['mean']:+.3f}, std {g['std']:.3f} (SE {boot_se_std(gain_err):.3f}), "
          f"2.5..97.5 % {g['p025']:+.2f}..{g['p975']:+.2f}")
    print(f"phase dev deg: mean {p['mean']:+.3f}, std {p['std']:.3f} (SE {boot_se_std(phase):.3f}), "
          f"2.5..97.5 % {p['p025']:+.2f}..{p['p975']:+.2f}")
    print(f"yield relative to nominal: gain within +-1 %: {yg:.1f} %; phase within +-2 deg: {yp:.1f} %; both: {yb:.1f} %")
    print(f"yield with absolute phase (nominal included): phase within +-2 deg: {yp_abs:.1f} %; both: {yb_abs:.1f} %")
    return {"gain_err": gain_err, "phase": phase, "g": g, "p": p,
            "yields": (yg, yp, yb), "h0": h0, "npass": npass}


def numpy_reference(ctol_pct, seed=1, n=200000):
    """Ideal-amplifier Monte Carlo with uniform tolerances (entry reference)."""
    rng = np.random.default_rng(seed)
    ct = ctol_pct / 100.0

    def u(t):
        return 1 + rng.uniform(-t, t, n)

    kk = 1 + (10e3 * u(1e-3)) / (10e3 * u(1e-3))
    k2 = 1 + (10e3 * u(1e-3)) / (10e3 * u(1e-3))
    Hh = hpf(F0, R9 * u(1e-3), R13 * u(1e-3), C10 * u(ct), C11 * u(ct), kk)
    Hl = lpf(F0, R11 * u(1e-3), R12 * u(1e-3), C9 * u(ct), C12 * u(ct), k2)
    H = (1 + 50e3 / (RG * u(1e-3))) * Hh * Hl
    gain_err = (abs(H) / abs(front(F0)) - 1) * 100
    phase = np.degrees(np.angle(H) - np.angle(front(F0)))
    yg, yp, yb = yields(gain_err, phase)
    return {"gain_std": float(gain_err.std()), "phase_std": float(phase.std()),
            "yields": (yg, yp, yb), "n": n, "seed": seed}


def table_check(res, key):
    t = TABLE[key]
    rows = []
    for name, val, ref in (("gain std", res["g"]["std"], t["gain_std"]),
                           ("phase std", res["p"]["std"], t["phase_std"])):
        rel = (val / ref - 1.0) * 100.0
        ok = abs(rel) <= 10.0
        rows.append((name, ref, val, rel, "Pass" if ok else "Fail"))
    print(f"\n| Quantity ({key} C) | numpy | PSpice | Difference | Verdict |")
    print("|---|---|---|---|---|")
    for name, ref, val, rel, v in rows:
        print(f"| {name} | {ref:.2f} | {val:.3f} | {rel:+.1f} % | {v} |")


def yield_table(r5, r1, np5, np1):
    print("\n| Criterion | C 5 % PSpice | C 5 % numpy | C 1 % PSpice | C 1 % numpy |")
    print("|---|---|---|---|---|")
    names = ("Gain within +-1 %", "Phase within +-2 deg", "Gain and phase within the limits")
    for i, nm in enumerate(names):
        print(f"| {nm} | {r5['yields'][i]:.1f} % | {np5['yields'][i]:.1f} % | "
              f"{r1['yields'][i]:.1f} % | {np1['yields'][i]:.1f} % |")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit("usage: P-25_mc.py <csd C5 %> <csd C1 %>")
    r5 = analyse(sys.argv[1], "C 5 % (P25a_mc5)")
    table_check(r5, "5 %")
    r1 = analyse(sys.argv[2], "C 1 % (P25b_mc1)")
    table_check(r1, "1 %")
    np5 = numpy_reference(5.0)
    np1 = numpy_reference(1.0)
    print(f"\nnumpy reference: default_rng(seed={np5['seed']}), {np5['n']} samples per tolerance, ideal amplifiers")
    print(f"numpy C 5 %: gain std {np5['gain_std']:.3f} %, phase std {np5['phase_std']:.3f} deg")
    print(f"numpy C 1 %: gain std {np1['gain_std']:.3f} %, phase std {np1['phase_std']:.3f} deg")
    yield_table(r5, r1, np5, np1)
