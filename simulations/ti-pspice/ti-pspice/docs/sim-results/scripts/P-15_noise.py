"""P-15 noise floor of the front end (circuits/chain_ss_P15.cir).

Reads the noise tables in the .out files of two runs (the .csd has no noise
section, see docs/simulation-quirks.md):

    sim-runs/P15a_noise517c/P15a_noise517c.out   .AC LIN 1 517 517, .NOISE V([VSAMPLE]) V_SIN 1
    sim-runs/P15b_noise_dec/P15b_noise_dec.out   .AC DEC 50 10 100k, same .NOISE

and the AC response of P15b from sim-runs/P15b_noise_dec/P15b_noise_dec.csd.

Results printed:
  1. Output noise density at f_osc (P15a) and its input-referred value.
  2. R_R16 (5 kOhm gain resistor) share, transfer and input-referred value,
     against the 4kTR value of a 5 kOhm resistor at 300 K.
  3. Log-log interpolated output density and gain at 3, 5, 7 f_osc (P15b),
     checked against the CSDF gain.
  4. Exact fold-down factor from P15b: sqrt(sum over odd n of
     (4/(n pi))^2 / 2 x S(n f) / S(f)), with n f up to 100 kHz.
  5. Minimum sensor amplitude for SNR = 1 (1 sigma) with ENBW = 1/(4 tau):
     tau = 0.1 s (2.5 Hz, design RC) and tau = 10 ms (25 Hz, fast RC of cout = 1 uF).
  6. Demodulator noise estimate from datasheet recall values. This is NOT
     simulated, because the switches change state in the noise analysis.

Run from the project root:
    python docs/sim-results/scripts/P-15_noise.py
"""

import math
import re
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools"))
from csdf import read_csdf  # noqa: E402

OUT_A = ROOT / "sim-runs/P15a_noise517c/P15a_noise517c.out"
OUT_B = ROOT / "sim-runs/P15b_noise_dec/P15b_noise_dec.out"
CSD_B = ROOT / "sim-runs/P15b_noise_dec/P15b_noise_dec.csd"
PLOT = ROOT / "docs/sim-results/plots/P-15_noise.png"

F_OSC = 517.0
F_MAX_SUM = 100e3          # harmonics summed up to this frequency
KB = 1.380649e-23          # J/K
T_K = 300.15               # 27 degC, PSpice default TEMP
R16 = 5e3                  # INA828 gain resistor, design value in docs/design-context.md
R_DEM = 10e3               # demodulator resistors R1 to R4 (circuit value)
TAU_DESIGN = 0.1           # s, 10 kOhm x 10 uF (design RC)
TAU_FAST = 10e-3           # s, 10 kOhm x 1 uF (cout = 1 uF in chain_ss_P15.cir)
E_N_OPA192 = 4.5e-9        # V/sqrt(Hz), NOT VERIFIED (recalled, not in project files)
E_N_INA828 = 7e-9          # V/sqrt(Hz), NOT VERIFIED (not in project files)

NUM = r"([0-9.]+E[+-][0-9]+)"


def fourkt_r(r):
    """Thermal noise voltage density sqrt(4kTR) in V/sqrt(Hz)."""
    return math.sqrt(4 * KB * T_K * r)


def parse_a(path):
    """Parse the single 517 Hz noise block of P15a."""
    text = path.read_text(encoding="latin-1")
    res = {}
    res["freq"] = float(re.search(r"FREQUENCY =\s+" + NUM, text).group(1))
    res["S_out"] = float(re.search(r"TOTAL OUTPUT NOISE VOLTAGE\s+=\s+" + NUM, text).group(1))
    res["H"] = float(re.search(r"V\(VSAMPLE\)/V_SIN\s+=\s+" + NUM, text).group(1))
    res["e_in"] = float(re.search(r"EQUIVALENT INPUT NOISE AT V_SIN =\s+" + NUM, text).group(1))
    # Top contributors block: "name =  value (pp %)" lines
    block = text.split("Top Contributors To Output Noise")[1].split("TOTAL OUTPUT NOISE")[0]
    contrib = {}
    for m in re.finditer(r"(\S+) =\s+" + NUM + r"\s+\(\s*([0-9.]+) %\)", block):
        contrib[m.group(1)] = (float(m.group(2)), float(m.group(3)))
    res["contrib"] = contrib
    return res


def parse_b(path):
    """Parse all noise blocks of P15b. Returns arrays f, S_out, H, e_in."""
    re_f = re.compile(r"FREQUENCY =\s+" + NUM + r" HZ")
    re_s = re.compile(r"TOTAL OUTPUT NOISE VOLTAGE\s+=\s+" + NUM)
    re_h = re.compile(r"V\(VSAMPLE\)/V_SIN\s+=\s+" + NUM)
    re_i = re.compile(r"EQUIVALENT INPUT NOISE AT V_SIN =\s+" + NUM)
    f, s, h, e = [], [], [], []
    with open(path, encoding="latin-1") as fh:
        for line in fh:
            m = re_f.search(line)
            if m:
                f.append(float(m.group(1)))
                continue
            m = re_s.search(line)
            if m:
                s.append(float(m.group(1)))
                continue
            m = re_h.search(line)
            if m:
                h.append(float(m.group(1)))
                continue
            m = re_i.search(line)
            if m:
                e.append(float(m.group(1)))
    f, s, h, e = map(np.array, (f, s, h, e))
    assert len(f) == len(s) == len(h) == len(e) == 201, (len(f), len(s), len(h), len(e))
    return f, s, h, e


def loglog(fg, yg, x):
    """Log-log linear interpolation of yg(fg) at x (scalar or array)."""
    return 10 ** np.interp(np.log10(x), np.log10(fg), np.log10(yg))


def main():
    a = parse_a(OUT_A)
    fB, SB, HB, eB = parse_b(OUT_B)

    print("=== 1. Output noise at f_osc (P15a, .out) ===")
    G = a["H"]
    S0 = a["S_out"]
    e_out = math.sqrt(S0)
    e_in = e_out / G
    print(f"f = {a['freq']:.1f} Hz")
    print(f"total output density  S_out = {S0:.4e} V^2/Hz = {e_out*1e9:.2f} nV/sqrt(Hz)")
    print(f"gain |V(VSAMPLE)/V_SIN| = {G:.4f} V/V")
    print(f"input-referred density (out / gain) = {e_in*1e9:.3f} nV/sqrt(Hz)")
    print(f"PSpice reported equivalent input noise = {a['e_in']*1e9:.3f} nV/sqrt(Hz)")
    print()

    print("=== 2. Top contributors (P15a) and input-referred values ===")
    print(f"{'device':<14}{'out V^2/Hz':>14}{'% of out':>10}{'in-ref nV/rtHz':>16}")
    for name, (val, pct) in sorted(a["contrib"].items(), key=lambda kv: -kv[1][1]):
        in_ref = math.sqrt(val) / G
        print(f"{name:<14}{val:>14.4e}{pct:>10.2f}{in_ref*1e9:>16.3f}")
    print()

    r16_out_v2, r16_pct = a["contrib"]["R_R16"]
    H16 = math.sqrt(r16_out_v2 / fourkt_r(R16) ** 2)
    e16_in = math.sqrt(r16_out_v2) / G
    print("R_R16 (5 kOhm, between the RG pins):")
    print(f"  4kTR, 5 kOhm at {T_K:.2f} K             = {fourkt_r(R16)*1e9:.3f} nV/sqrt(Hz)")
    print(f"  transfer R_R16 -> output (|H16|)        = {H16:.3f} V/V (signal gain {G:.3f} V/V)")
    print(f"  transfer ratio H16 / G                  = {H16/G:.4f}")
    print(f"  input-referred R_R16 (sqrt(S)/G)        = {e16_in*1e9:.3f} nV/sqrt(Hz)")
    print(f"  input-referred / 4kTR                   = {e16_in/fourkt_r(R16):.4f}")
    print(f"  share of output power (PSpice)          = {r16_pct:.2f} %")
    print(f"  share check (e16_in / e_in)^2           = {100*(e16_in/e_in)**2:.2f} %")
    print()

    ina_names = [k for k in a["contrib"] if k.startswith("X_U1.")]
    ina_out = sum(a["contrib"][k][0] for k in ina_names)
    ina_pct = sum(a["contrib"][k][1] for k in ina_names)
    ina_in = math.sqrt(ina_out) / G
    print(f"INA828 internal contributors listed ({len(ina_names)} devices): "
          f"{ina_pct:.2f} % of output power, input-referred {ina_in*1e9:.2f} nV/sqrt(Hz) "
          f"(quadrature sum of the listed items)")
    rest_pct = 100 - r16_pct - ina_pct - a["contrib"]["R_R18"][1]
    print(f"Contributors not listed (each below 3 %): {rest_pct:.2f} % of output power")
    print()

    print("=== 3. P15b interpolation and CSDF check ===")
    secs = read_csdf(str(CSD_B))
    sec = secs[0]
    Hc = np.abs(sec["V(VSAMPLE)"])
    print(f"CSDF |V(VSAMPLE)| vs .out transfer, max relative difference over 201 points: "
          f"{np.max(np.abs(Hc/HB - 1)):.2e}")
    G517_b = float(loglog(fB, HB, F_OSC))
    S517_b = float(loglog(fB, SB, F_OSC))
    print(f"P15b at 517 Hz (interpolated): gain {G517_b:.4f} V/V (P15a {G:.4f}), "
          f"S_out {S517_b:.4e} V^2/Hz (P15a {S0:.4e}), difference "
          f"{100*(S517_b/S0 - 1):+.3f} %")
    print()
    # Check: local quadratic in log-log through the three grid points around f_osc
    i0 = int(np.searchsorted(fB, F_OSC)) - 1
    xs = np.log10(fB[i0:i0 + 3])
    for name, arr, exact in (('S_out', SB, S0), ('gain', HB, G)):
        cq = np.polyfit(xs, np.log10(arr[i0:i0 + 3]), 2)
        q = 10 ** np.polyval(cq, np.log10(F_OSC))
        print(f"quadratic check {name} at 517 Hz (grid {fB[i0]:.1f}, {fB[i0+1]:.1f}, {fB[i0+2]:.1f} Hz): "
              f"{q:.6g} vs P15a {exact:.6g}, difference {100*(q/exact-1):+.3f} %")
    print()

    S0_b = float(loglog(fB, SB, F_OSC))
    print(f"{'n':>3}{'f (Hz)':>10}{'S_out (V^2/Hz)':>16}{'e (nV/rtHz)':>13}{'|H| (V/V)':>12}"
          f"{'S(nf)/S(f)':>12}{'w_n':>11}{'w_n S ratio':>13}")
    for n in (1, 3, 5, 7):
        fn = n * F_OSC
        Sn = float(loglog(fB, SB, fn))
        Hn = float(loglog(fB, HB, fn))
        wn = (4 / (n * math.pi)) ** 2 / 2
        print(f"{n:>3}{fn:>10.1f}{Sn:>16.4e}{math.sqrt(Sn)*1e9:>13.3f}{Hn:>12.4f}{Sn/S0_b:>12.4e}"
              f"{wn:>11.6f}{wn*Sn/S0_b:>13.4e}")
    print()

    print("=== 4. Exact fold-down factor from P15b ===")
    n_all = np.arange(1, 10 ** 4, 2)
    n_all = n_all[n_all * F_OSC <= F_MAX_SUM]
    w = (4 / (n_all * math.pi)) ** 2 / 2
    # Numerator and denominator both from P15b, so the grid interpolation error cancels
    S0_b = float(loglog(fB, SB, F_OSC))
    Sn_all = loglog(fB, SB, n_all * F_OSC)
    terms = w * Sn_all / S0_b
    fold2 = float(np.sum(terms))
    fold = math.sqrt(fold2)
    tail_w = 1.0 - float(np.sum(w))   # weight of harmonics above 100 kHz (all with S <= S(100 kHz))
    print(f"odd harmonics summed: n = 1 to {n_all[-1]} (n f up to {n_all[-1]*F_OSC/1e3:.1f} kHz)")
    print(f"sum of weights (n <= {n_all[-1]}) = {np.sum(w):.6f}, weight above 100 kHz = {tail_w:.6f}")
    print(f"n = 1 term alone: weight {w[0]:.6f}, ratio 1.0 -> term {w[0]:.6f}")
    print(f"n = 3 term: weight {w[1]:.6f}, S ratio {Sn_all[1]/S0_b:.4e} -> term {terms[1]:.4e}")
    print(f"sum of terms (power ratio) = {fold2:.6f}")
    print(f"exact fold-down factor = sqrt(sum) = {fold:.6f}")
    print(f"upper bound if S above 100 kHz equals S(100 kHz): factor "
          f"{math.sqrt(fold2 + tail_w*loglog(fB, SB, F_MAX_SUM)/S0_b):.6f}")
    e_dc = fold * e_out   # e_out is the exact P15a value at 517 Hz
    print(f"DC-band density at VX = fold x e_out = {e_dc*1e9:.2f} nV/sqrt(Hz)")
    print()

    print("=== 5. Minimum detectable sensor amplitude (SNR = 1) ===")
    print("A_min = (pi/2) x fold x e_out x sqrt(ENBW) / G, with ENBW = 1/(4 tau).")
    print("The factor pi/2 is 1 / (2/pi), the DC gain of a +/-1 demodulator for a sine.")
    res = {}
    for label, tau in (("design RC, tau = 0.1 s", TAU_DESIGN), ("fast RC, tau = 10 ms", TAU_FAST)):
        enbw = 1 / (4 * tau)
        A_min = (math.pi / 2) * e_dc * math.sqrt(enbw) / G
        A_min_index = (math.pi / 2) * 0.90 * e_out * math.sqrt(enbw) / 11.08
        res[label] = (enbw, A_min)
        print(f"{label}: ENBW = {enbw:.2f} Hz, A_min = {A_min*1e9:.2f} nV "
              f"(index approximation 0.90 and 11.08 V/V: {A_min_index*1e9:.2f} nV)")
    print()

    print("=== 6. Demodulator noise estimate (NOT simulated) ===")
    e_R = fourkt_r(R_DEM)
    e_op = E_N_OPA192 * (1 + 1.0)          # noise gain 1 + R1/R2 = 2
    e_R1_out = e_R                          # R1 thermal noise at the op amp output, gain 1
    e_R3 = e_R                              # R3 in series with the RC, transfer 1 at DC
    e_dem_out = math.sqrt(e_op ** 2 + e_R1_out ** 2 + e_R3 ** 2)
    e_dem_out_noR3 = math.sqrt(e_op ** 2 + e_R1_out ** 2)
    e_R2_sample = e_R                       # R2 in the signal path, folded with the sample
    print(f"4kTR, 10 kOhm at {T_K:.2f} K = {e_R*1e9:.2f} nV/sqrt(Hz)")
    print(f"OPAx192 e_n x 2 (noise gain)  = {e_op*1e9:.2f} nV/sqrt(Hz)")
    print(f"demodulator DC-band noise at VX, op amp + R1 + R3 = {e_dem_out*1e9:.2f} nV/sqrt(Hz) "
          f"(without R3: {e_dem_out_noR3*1e9:.2f})")
    print(f"ratio to chain DC-band density (fold x e_out) = {e_dem_out/e_dc:.4f} "
          f"(power share {100*(e_dem_out/e_dc)**2:.2f} %)")
    print(f"chain + demodulator DC-band density = "
          f"{math.sqrt(e_dc**2 + e_dem_out**2)*1e9:.2f} nV/sqrt(Hz) "
          f"(chain alone {e_dc*1e9:.2f})")
    e_dem_in = e_dem_out / ((2 / math.pi) * G)
    print(f"demodulator noise referred to the sensor input = {e_dem_in*1e9:.2f} nV/sqrt(Hz)")
    e_chain_sensor = e_dc / ((2 / math.pi) * G)
    print(f"chain noise referred to the sensor input (fold x pi/2 x e_in) = {e_chain_sensor*1e9:.2f} nV/sqrt(Hz)")
    e_tot_sensor = math.sqrt(e_chain_sensor ** 2 + e_dem_in ** 2)
    print(f"total, chain + demodulator = {e_tot_sensor*1e9:.2f} nV/sqrt(Hz)")
    for label, (enbw, _) in res.items():
        A_tot = e_tot_sensor * math.sqrt(enbw)
        print(f"  A_min with demodulator, {label}: {A_tot*1e9:.2f} nV")
    print(f"R2 (signal path) adds {e_R2_sample*1e9:.2f} nV/sqrt(Hz) at VSAMPLE per channel, "
          f"{100*((math.sqrt(e_out**2 + e_R2_sample**2)/e_out) - 1):.2f} % in density")
    print()

    print("=== 7. Lower gain resistor (estimate, not simulated) ===")
    print("Assumptions: R_G term = 4kT R_G x (H16/G), the measured transfer ratio;")
    print("INA828 internal term = its listed input-referred value, gain independent;")
    print("rest (R18, the unlisted INA828 items, op amps, filters) = output-referred power / G_new.")
    S_later = (100 - r16_pct - ina_pct) / 100 * S0   # R18 plus all unlisted items
    S_ina = ina_out
    print(f"{'R_G (ohm)':>10}{'G (V/V)':>9}{'R_G term':>11}{'INA internal':>14}{'rest':>14}{'total':>10}")
    for rg in (5e3, 2e3, 1e3, 500.0):
        Gn = 1 + 50e3 / rg
        t_rg = fourkt_r(rg) * (H16 / G)
        t_ina = math.sqrt(S_ina) / G
        t_later = math.sqrt(S_later) / Gn
        tot = math.sqrt(t_rg ** 2 + t_ina ** 2 + t_later ** 2)
        print(f"{rg:>10.0f}{Gn:>9.1f}{t_rg*1e9:>10.2f}n{t_ina*1e9:>13.2f}n{t_later*1e9:>13.2f}n{tot*1e9:>9.2f}n")
    print("(all values nV/sqrt(Hz), input-referred; the 5 kOhm row is the simulated split, the others are estimates)")
    print()

    # Plot: output density against frequency with the harmonics marked
    fig, ax = plt.subplots(figsize=(7, 4.2))
    ax.loglog(fB, np.sqrt(SB) * 1e9, label="total output noise (P15b)")
    for n in (1, 3, 5, 7):
        ax.axvline(n * F_OSC, color="grey", ls=":", lw=0.8)
    ax.plot([F_OSC], [e_out * 1e9], "o", color="C3", label=f"P15a, 517 Hz: {e_out*1e9:.1f} nV/rtHz")
    ax.set_xlabel("frequency (Hz)")
    ax.set_ylabel("output noise density (nV/sqrt(Hz))")
    ax.set_title("P-15: output noise of the front end, V(VSAMPLE)")
    ax.legend(fontsize=8)
    ax.grid(True, which="both", lw=0.3)
    fig.tight_layout()
    PLOT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(PLOT, dpi=130)
    print(f"plot written: {PLOT}")


if __name__ == "__main__":
    main()
