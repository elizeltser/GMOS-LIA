"""P-14 filter tolerance Monte Carlo of the front end (circuits/frontend_mc.cir).

Two parts:

1. PSpice run P14_mc2 (sim-runs/P14_mc2/P14_mc2.csd and .out). Section 0 is
   the Monte Carlo NOMINAL, sections 1 to 499 are Pass 2 to Pass 500. Each
   section has one AC point at 517 Hz. The two CSDF columns both hold the
   complex V(VSAMPLE), so VP and VM are derived here from the complex value:
   |H| = abs(V), phase = angle(V) in degrees. The script checks that the
   column pair is identical and that the phase deviations match the
   "SORTED DEVIATIONS OF VP(VSAMPLE)" table of the .out file.

2. numpy reference Monte Carlo of the ideal transfer function from
   ti-pspice-PSpiceFiles/differential-amplifier/README.md section 3:
       H(s) = G(RG) x H_HP(s) x H_LP(s)
       G(RG) = 1 + 50 kOhm / RG                       (section 3.1)
       H_HP(s) = s^2 R17 R18 C1 C2 / (s^2 R17 R18 C1 C2 + s R17 (C1 + C2) + 1)
                                                      (section 3.2)
       H_LP(s) = 1 / (s^2 R22 R21 C4 C3 + s C3 (R22 + R21) + 1)
                                                      (section 3.3)
   Every R (RG = R16, R17, R18, R21, R22) is uniform within +/-1 %. Every C
   (C1, C2, C3, C4) is uniform within +/-5 %. The sample count is 200 000.

Definitions (phi = phase of H in degrees, H_nom = nominal complex H):
    phase shift     d_phi = phi_k - phi_nom                       [deg]
    gain error R   e_R   = |H_k| / |H_nom| - 1                     [%]
    gain error X   e_X   = Re(H_k) / |H_nom| - 1                   [%]
    extra X error  e_xR  = Re(H_k) / |H_k| - 1 = cos(phi_k) - 1    [%]

Settling and window: the AC analysis is a single frequency (517 Hz). No
settling window applies. The PSpice run uses .AC LIN 1 517 517 with the
.MC 500 AC VP(VSAMPLE) YMAX OUTPUT ALL SEED=17 directive, as in circuits/frontend_mc.cir.

Run from the project root:
    python docs/sim-results/scripts/P-14_mc.py
Requires numpy and matplotlib.
"""

import re
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools"))
from csdf import read_csdf  # noqa: E402

CSD = ROOT / "sim-runs" / "P14_mc2" / "P14_mc2.csd"
OUT = ROOT / "sim-runs" / "P14_mc2" / "P14_mc2.out"
PLOT = ROOT / "docs" / "sim-results" / "plots" / "P-14_mc_phase.png"
F_OSC = 517.0
N_NUMPY = 200_000
SEED = 2026
TOL_R = 0.01     # uniform +/-1 % for resistors
TOL_C = 0.05     # uniform +/-5 % for capacitors

# Nominal values from frontend_mc.cir
R_NOM = {"RG": 5e3, "R17": 4.64e3, "R18": 18.7e3, "R21": 4.64e3, "R22": 4.64e3}
C_NOM = {"C1": 33e-9, "C2": 33e-9, "C3": 33e-9, "C4": 130e-9}


def ideal_H(f, R, C):
    """Ideal chain transfer function, README section 3 (arrays broadcast)."""
    s = 2j * np.pi * f
    G = 1.0 + 50e3 / R["RG"]
    R17, R18, R21, R22 = R["R17"], R["R18"], R["R21"], R["R22"]
    C1, C2, C3, C4 = C["C1"], C["C2"], C["C3"], C["C4"]
    hp = (s**2 * R17 * R18 * C1 * C2) / (
        s**2 * R17 * R18 * C1 * C2 + s * R17 * (C1 + C2) + 1.0)
    lp = 1.0 / (s**2 * R22 * R21 * C4 * C3 + s * C3 * (R22 + R21) + 1.0)
    return G * hp * lp


def calibrated_metrics(H, H0):
    """Entry definition (phase calibrated at the nominal circuit).

    r = H / H0, ph = angle(r), g = abs(r), X = g cos(ph), R = g.
    Returns the R error, the X error and the extra X error (X - R), in percent.
    The per-sample phase deviation from nominal stays in the reading.
    """
    r = H / H0
    ph = np.angle(r)
    g = np.abs(r)
    X = g * np.cos(ph)
    eR = 100.0 * (g - 1.0)
    eX = 100.0 * (X - 1.0)
    extra = 100.0 * (X - g)
    return np.degrees(ph), eR, eX, extra


def se_band(x, n_boot=2000, seed=7):
    """Sampling standard errors of mean, std and the 2.5 %, 97.5 % points (bootstrap)."""
    x = np.asarray(x)
    n = len(x)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, n, size=(n_boot, n))
    xb = x[idx]
    stats = np.stack([xb.mean(axis=1), xb.std(axis=1, ddof=1),
                      np.percentile(xb, 2.5, axis=1), np.percentile(xb, 97.5, axis=1)])
    return stats.std(axis=1, ddof=1)


def stats_row(x):
    x = np.asarray(x)
    lo, hi = np.percentile(x, [2.5, 97.5])
    return x.mean(), x.std(ddof=1), lo, hi


def fmt_row(name, unit, st):
    return f"| {name} | {st[0]:+.4f} {unit} | {st[1]:.4f} {unit} | {st[2]:+.4f} {unit} | {st[3]:+.4f} {unit} |"


def metrics(H, H_nom):
    """Phase shift, gain errors R and X, extra X error from complex H arrays."""
    phi = np.degrees(np.angle(H))
    phi_nom = np.degrees(np.angle(H_nom))
    d_phi = phi - phi_nom
    eR = 100.0 * (np.abs(H) / np.abs(H_nom) - 1.0)
    eX = 100.0 * (H.real / np.abs(H_nom) - 1.0)
    exR = 100.0 * (H.real / np.abs(H) - 1.0)
    return d_phi, eR, eX, exR


def pspice_part():
    secs = read_csdf(str(CSD))
    print(f"PSpice file: {CSD.relative_to(ROOT)}, sections = {len(secs)}")
    print(f"Section 0 label: {secs[0].header.get('SUBTITLE', '').strip()}")
    print(f"Section 1 label: {secs[1].header.get('SUBTITLE', '').strip()}, "
          f"last label: {secs[-1].header.get('SUBTITLE', '').strip()}")
    print(f"Section names: {secs[0].groups}")
    V = np.array([s["V(VSAMPLE)"][0] for s in secs])  # column 0 of each section
    V2 = np.array([s.data[0, 1] for s in secs])        # column 1 of each section
    print(f"Column 0 equals column 1 in all sections: {np.array_equal(V, V2)}")
    print(f"Frequency of all sections: {set(float(s.x[0]) for s in secs)}")

    V_nom = V[0]
    V_mc = V[1:]
    print(f"Nominal |H| = {abs(V_nom):.6f} V/V, phase = {np.degrees(np.angle(V_nom)):+.4f} deg")
    print(f"Samples = {len(V_mc)} (Pass 2 to Pass 500)")

    # Cross-check against the sorted deviations of the .out file
    text = OUT.read_text(errors="replace")
    block = text[text.index("SORTED DEVIATIONS"):]
    rows = re.findall(r"Pass\s+(\d+)\s+([-+]?[\d.]+(?:E[-+]?\d+)?)\s+\(\s*([-\d.]+) sigma\)\s+(lower|higher)", block)
    dev_out = {int(p): (float(v), d) for p, v, _, d in rows}
    phi_all = np.degrees(np.angle(V))
    max_diff = 0.0
    n_match = 0
    for k in range(1, len(secs)):
        pass_no = k + 1
        if pass_no not in dev_out:
            continue
        v, direction = dev_out[pass_no]
        d_csd = phi_all[k] - phi_all[0]
        sign_ok = (d_csd < 0) == (direction == "lower")
        max_diff = max(max_diff, abs(abs(d_csd) - v))
        n_match += int(sign_ok)
    print(f".out sorted-deviation rows: {len(rows)}; passes with matching sign: {n_match}; "
          f"max |csd deviation| - |.out deviation| = {max_diff:.2e} deg")
    sigma_out = re.search(r"Sigma\s*=\s*([\d.]+)", text)
    mean_out = re.search(r"Mean Deviation =\s*([-\d.]+)", text)
    print(f".out Mean Deviation = {mean_out.group(1)} deg, Sigma = {sigma_out.group(1)} deg")

    d_phi, eR, eX, exR = metrics(V_mc, V_nom)
    return {
        "nom_abs": abs(V_nom), "nom_phase": np.degrees(np.angle(V_nom)),
        "d_phi": d_phi, "eR": eR, "eX": eX, "exR": exR,
        "V_mc": V_mc, "V_nom": V_nom,
    }


def numpy_part():
    rng = np.random.default_rng(SEED)
    R_keys = ["RG", "R17", "R18", "R21", "R22"]
    C_keys = ["C1", "C2", "C3", "C4"]
    R = {k: R_NOM[k] * (1.0 + rng.uniform(-TOL_R, TOL_R, N_NUMPY)) for k in R_keys}
    C = {k: C_NOM[k] * (1.0 + rng.uniform(-TOL_C, TOL_C, N_NUMPY)) for k in C_keys}
    H = ideal_H(F_OSC, R, C)
    H_nom = ideal_H(F_OSC, R_NOM, C_NOM)
    d_phi, eR, eX, exR = metrics(H, H_nom)
    return {"nom_abs": abs(H_nom), "nom_phase": np.degrees(np.angle(H_nom)),
            "d_phi": d_phi, "eR": eR, "eX": eX, "exR": exR, "H": H, "H_nom": H_nom}


def check_formulas():
    """The README formulas against a direct nodal solution at a few frequencies."""
    f = np.array([100.0, 517.0, 724.0, 3000.0])
    s = 2j * np.pi * f
    R17, R18, R21, R22 = (R_NOM[k] for k in ["R17", "R18", "R21", "R22"])
    C1, C2, C3, C4 = (C_NOM[k] for k in ["C1", "C2", "C3", "C4"])
    # Nodal solution of the high-pass: Vb = Vo, node A and node B
    Ya1, Ya2 = s * C1, s * C2
    G17, G18 = 1 / R17, 1 / R18
    # Node A: (Vi - Va) Ya1 = (Va - Vb) Ya2 + (Va - Vb) G17
    # Node B: (Va - Vb) Ya2 = Vb G18
    # With Vi = 1 solve for Vb
    Vb = np.empty_like(s)
    for i in range(len(s)):
        M = np.array([[Ya1[i] + Ya2[i] + G17, -(Ya2[i] + G17)],
                      [-Ya2[i], Ya2[i] + G18]], dtype=complex)
        rhs = np.array([Ya1[i], 0.0], dtype=complex)
        Va_, Vb_ = np.linalg.solve(M, rhs)
        Vb[i] = Vb_
    hp_readme = (s**2 * R17 * R18 * C1 * C2) / (s**2 * R17 * R18 * C1 * C2 + s * R17 * (C1 + C2) + 1)
    err = np.max(np.abs(Vb - hp_readme) / np.abs(hp_readme))
    print(f"Check HP formula against nodal solution: max relative difference = {err:.2e}")
    return err


def main():
    print("== Part 1: PSpice run P14_mc2 ==")
    ps = pspice_part()
    print("\n== Part 2: numpy reference (200 000 samples) ==")
    check_formulas()
    npy = numpy_part()
    print(f"Ideal nominal |H| = {npy['nom_abs']:.5f} V/V, phase = {npy['nom_phase']:+.4f} deg")
    print(f"PSpice nominal |H| = {ps['nom_abs']:.5f} V/V, phase = {ps['nom_phase']:+.4f} deg")
    print(f"Difference PSpice - ideal: |H| {ps['nom_abs'] - npy['nom_abs']:+.5f} V/V "
          f"({100 * (ps['nom_abs'] / npy['nom_abs'] - 1):+.4f} %), "
          f"phase {ps['nom_phase'] - npy['nom_phase']:+.4f} deg")

    print("\n== Statistics (columns: mean, std, 2.5 %, 97.5 %) ==")
    rows = []
    for label, d in [("PSpice (499 samples)", ps), ("numpy (200 000 samples)", npy)]:
        rows.append((label, {
            "phase": stats_row(d["d_phi"]),
            "R": stats_row(d["eR"]),
            "X": stats_row(d["eX"]),
            "extra": stats_row(d["exR"]),
        }))
    for label, st in rows:
        print(label)
        print(fmt_row("Phase shift", "deg", st["phase"]))
        print(fmt_row("Gain error R", "%", st["R"]))
        print(fmt_row("Gain error X", "%", st["X"]))
        print(fmt_row("Extra X error", "%", st["extra"]))

    # Common gain spread: correlation of R and X gain errors
    for label, d in [("PSpice", ps), ("numpy", npy)]:
        corr = np.corrcoef(d["eR"], d["eX"])[0, 1]
        print(f"{label}: correlation of gain error R and X = {corr:.6f}")
        diff = d["eX"] - d["eR"]
        print(f"{label}: (e_X - e_R) mean {diff.mean():+.4f} %, max abs {np.abs(diff).max():.4f} % "
              f"(e_X - e_R should equal cos(phi) - 1)")

    # Entry definition: phase calibrated at the nominal circuit, r = H / H0
    print("\n== Entry definition (r = H / H0, X = g cos(ph), extra = X - g) ==")
    cal = {}
    cal["PSpice"] = calibrated_metrics(ps["V_mc"], ps["V_nom"])
    cal["numpy"] = calibrated_metrics(npy["H"], npy["H_nom"])
    names = ["Phase deviation (deg)", "Gain error R (%)", "Gain error X (%)", "Extra X - R (%)"]
    for label, (ph, eR, eX, ex) in cal.items():
        n = len(ph)
        print(f"{label} (n = {n}): columns mean, std, 2.5 %, 97.5 %, SE(mean), SE(std)")
        for name, x in zip(names, (ph, eR, eX, ex)):
            m, s, lo, hi = stats_row(x)
            se_m, se_s, se_lo, se_hi = se_band(x)
            print(f"  {name:24s} {m:+.4f}  {s:.4f}  {lo:+.4f}  {hi:+.4f}  "
                  f"SE_mean {se_m:.4f}  SE_std {se_s:.4f}  SE_2.5 {se_lo:.4f}  SE_97.5 {se_hi:.4f}")
    # Uncalibrated (total phase) definition kept as a secondary reading
    print("Uncalibrated total-phase reading (secondary):")
    for label, d in [("PSpice", ps), ("numpy", npy)]:
        m, s, lo, hi = stats_row(d["exR"])
        print(f"  {label}: extra X error mean {m:+.4f} %, std {s:.4f} %, 2.5 % {lo:+.4f} %")
    sig_py = npy["d_phi"].std(ddof=1)
    print(f"Check: -sigma^2/2 with calibrated numpy phase std = {-100 * np.radians(cal['numpy'][0].std(ddof=1))**2 / 2:+.4f} %")

    # Sample-size convergence of the PSpice phase shift (no settling applies to AC)
    d = ps["d_phi"]
    print("\nPSpice convergence of phase shift (n, mean deg, std deg, ddof 1):")
    for n in (100, 200, 300, len(d)):
        print(f"  {n:4d}  {d[:n].mean():+.3f}  {d[:n].std(ddof=1):.3f}")
    print(f"PSpice std with ddof 0 = {d.std(ddof=0):.4f} deg "
          f"(matches the .out Sigma 3.43916894 deg, so PSpice uses ddof 0)")

    # Extra X error: the entry value -0.17 % equals -sigma^2/2 with a zero mean phase.
    # The total phase includes the nominal +1.63 deg (ideal) and gives the value below.
    sig_rad = np.radians(npy["d_phi"].std(ddof=1))
    print(f"Zero-mean term -sigma^2/2 with numpy sigma = {-100 * sig_rad**2 / 2:+.4f} %")
    ex_rel_nom = 100.0 * (np.cos(np.radians(ps["d_phi"] + ps["nom_phase"]))
                          / np.cos(np.radians(ps["nom_phase"])) - 1.0)
    print(f"PSpice extra X error relative to the nominal X: mean {ex_rel_nom.mean():+.4f} %, "
          f"std {ex_rel_nom.std(ddof=1):.4f} %")
    print(f"Nominal X error from cos of nominal phase = {100 * (np.cos(np.radians(ps['nom_phase'])) - 1):+.4f} %")

    # Save a plot
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        PLOT.parent.mkdir(parents=True, exist_ok=True)
        fig, ax = plt.subplots(1, 2, figsize=(10, 4))
        bins = np.linspace(-12, 12, 61)
        ax[0].hist(ps["d_phi"], bins=bins, density=True, alpha=0.6, label="PSpice (499)")
        ax[0].hist(npy["d_phi"], bins=bins, density=True, histtype="step", lw=1.5,
                   label="numpy (200 000)")
        ax[0].set_xlabel("Phase shift from nominal (deg)")
        ax[0].set_ylabel("Probability density (1/deg)")
        ax[0].legend()
        ax[1].hist(ps["eR"], bins=np.linspace(-15, 15, 61), density=True, alpha=0.6,
                   label="PSpice gain R")
        ax[1].hist(ps["eX"], bins=np.linspace(-15, 15, 61), density=True, alpha=0.4,
                   label="PSpice gain X")
        ax[1].set_xlabel("Gain error (%)")
        ax[1].legend()
        fig.suptitle("P-14 front-end Monte Carlo at 517 Hz")
        fig.tight_layout()
        fig.savefig(PLOT, dpi=120)
        print(f"Plot written: {PLOT.relative_to(ROOT)}")
    except ImportError:
        print("matplotlib not available, plot skipped")


if __name__ == "__main__":
    main()
