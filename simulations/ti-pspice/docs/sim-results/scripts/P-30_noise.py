"""P-30 analysis: drain-referred noise of circuits/afe_eval_P30.cir (compensated pixel shot-noise resistors).

Run from simulations/ti-pspice:  python docs/sim-results/scripts/P-30_noise.py

Reads two runs:
  sim-runs/P30a2_noise518   .AC LIN 1 518 518 with .NOISE V([BPF_OUT]) V_EXC 1 (full tables in the .out)
  sim-runs/P30b2_noise_dec  .AC DEC 50 10 100k with the same .NOISE (201 tables, fold-down factor)

Drain-referred noise = S_out / |V(BPF_OUT)/(V(DRN_B)-V(DRN_A))|^2 at 518 Hz, with the AC gain of the same run.
The .out lists every contributor (DIODE, RESISTOR and VOLTAGE CONTROLLED SWITCH tables, from the line
'NOISE ANALYSIS' to 'Top Contributors'). The sum of the items is checked against the total.
"""
import collections
import os
import re
import sys

import numpy as np

sys.path.insert(0, "tools")
from csdf import read_csdf

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..")
RUN_518 = os.path.join(ROOT, "sim-runs", "P30a2_noise518")
RUN_DEC = os.path.join(ROOT, "sim-runs", "P30b2_noise_dec")
F0 = 518.0
SENSOR = ("R_SHA", "R_SHB", "R_R25", "R_R31")


def parse_full_table(out_path):
    """Every contributor of the .NOISE table at one frequency: list of (device, output V^2/Hz)."""
    txt = open(out_path, errors="replace").read()
    body = txt.split("NOISE ANALYSIS")[1].split("Top Contributors")[0]
    items, names, sect = [], [], None
    for line in body.splitlines():
        s = line.strip()
        if s.startswith("****"):
            sect, names = s, []
            continue
        if not s or s.startswith("FREQUENCY"):
            continue
        tok = s.split()
        if tok[0] in ("RS", "ID", "FN", "RD", "IB", "IC", "RB", "RC", "RE", "RG", "TOTAL", "IG", "FLICKER") and len(tok) > 1 \
                and all(re.match(r"^-?[\d.]+E[+-]\d+$", t) for t in tok[1:]):
            if tok[0] == "TOTAL":
                vals = [float(t) for t in tok[1:]]
                assert len(vals) == len(names), (names, vals)
                items += [(sect, n, v) for n, v in zip(names, vals)]
                names = []
            continue
        if all(re.match(r"^[A-Za-z_][\w.$:]*$", t) for t in tok):
            names += tok
    total = float(re.search(r"TOTAL OUTPUT NOISE VOLTAGE\s*=\s*([\d.E+-]+)", txt).group(1))
    return items, total


def dec_tables(out_path):
    """Frequencies and total output densities (V^2/Hz) of every noise table in a .NOISE run."""
    txt = open(out_path, errors="replace").read()
    freqs = [float(x) for x in re.findall(r"FREQUENCY =\s+([\d.E+-]+) HZ", txt)]
    tots = [float(x) for x in re.findall(r"TOTAL OUTPUT NOISE VOLTAGE\s*=\s*([\d.E+-]+) SQ V/HZ", txt)]
    assert len(freqs) == len(tots), (len(freqs), len(tots))
    return np.array(freqs), np.array(tots)


def fold_analysis(run_dec):
    """Fold-down factor at VX from the DEC run: white-input form (|H| only) and noise-weighted form."""
    name = os.path.basename(run_dec)
    csd = read_csdf(os.path.join(run_dec, name + ".csd"))
    sec = csd[0]
    x = np.asarray(sec.x)
    H = sec["V(BPF_OUT)"] / (sec["V(DRN_B)"] - sec["V(DRN_A)"])
    fT, S = dec_tables(os.path.join(run_dec, name + ".out"))
    assert np.allclose(fT, x, rtol=1e-3), "noise and AC grids differ"
    lx = np.log10(x)

    def interp(arr, f):
        return np.exp(np.interp(np.log10(f), lx, np.log(arr)))

    H0 = interp(np.abs(H), F0)
    S0 = interp(S, F0)
    w_sum = 0.0
    ws_sum = 0.0
    nmax = 0
    for n in range(1, 400, 2):
        f = n * F0
        if f > x[-1]:
            break
        nmax = n
        w = (4 / (n * np.pi)) ** 2 / 2
        w_sum += w * interp(np.abs(H), f) ** 2
        ws_sum += w * interp(S, f)
    fold_white = np.sqrt(w_sum) / H0
    fold_noise = np.sqrt(ws_sum / S0)
    print(f"fold-down, white input, sum (4/(n pi))^2/2 |H(n f0)|^2 over |H(f0)|^2, n up to {nmax}: {fold_white:.4f}")
    print(f"fold-down, noise-weighted, sum w S(n f0) over S(f0): {fold_noise:.4f}")
    print(f"|H(f0)| from the DEC grid by interpolation: {H0:.4f} V/V (exact 518 Hz run: 39.5775 V/V)")
    return fold_white, fold_noise


def group_of(name):
    if name in ("R_SHA", "R_SHB"):
        return "pixel shot (R_SHA, R_SHB)"
    if name in ("R_R25", "R_R31"):
        return "R_D (R25, R31)"
    if name.startswith("X_U2"):
        if ".XI_" in name:
            return "INA828 input current (XI)"
        if ".XE_" in name:
            return "INA828 input voltage (XE)"
        return "INA828 other"
    if name.startswith("X_U1B"):
        return "U1B (MFB, gate path)"
    if name in ("R_R5", "R_R7"):
        return "R5, R7 (MFB network)"
    if name == "R_R10":
        return "RG (R10)"
    if name == "R_R59":
        return "R59 (gate series)"
    if name.startswith("X_U10A"):
        return "U10A (drain bias)"
    if name.startswith("X_U10B"):
        return "U10B (drain bias)"
    return "other"


if __name__ == "__main__":
    items, total = parse_full_table(os.path.join(RUN_518, "P30a2_noise518.out"))
    csd = read_csdf(os.path.join(RUN_518, "P30a2_noise518.csd"))
    sec = csd[0]
    G = sec["V(BPF_OUT)"][0] / (sec["V(DRN_B)"][0] - sec["V(DRN_A)"][0])
    g2 = abs(G) ** 2
    summed = sum(v for _, _, v in items)
    print(f"gain V(BPF_OUT)/(V(DRN_B)-V(DRN_A)) at {F0:.0f} Hz = {abs(G):.4f} V/V, phase {np.degrees(np.angle(G)):+.3f} deg")
    print(f"items in the full table: {len(items)}")
    print(f"sum of items = {summed:.5e} V^2/Hz, TOTAL OUTPUT NOISE VOLTAGE = {total:.5e} V^2/Hz, ratio {summed/total:.5f}")
    print(f"total output density at BPF_OUT: {np.sqrt(total)*1e9:.1f} nV/rtHz")
    print(f"drain-referred total, differential = {np.sqrt(total/g2)*1e9:.2f} nV/rtHz")

    grp = collections.defaultdict(float)
    for _, n, v in items:
        grp[group_of(n)] += v
    print("\nGrouped table (share of output power, drain-referred differential noise):")
    print(f"{'group':34s} {'share %':>9s} {'nV/rtHz':>9s}")
    for k, v in sorted(grp.items(), key=lambda kv: -kv[1]):
        print(f"{k:34s} {100*v/total:9.3f} {np.sqrt(v/g2)*1e9:9.2f}")
    print(f"{'sum of groups':34s} {100*sum(grp.values())/total:9.3f}")

    print("\nIndividual devices of the groups with more than 0.05 % share:")
    per = collections.defaultdict(float)
    for _, n, v in items:
        per[n] += v
    for n, v in sorted(per.items(), key=lambda kv: -kv[1])[:12]:
        print(f"  {n:24s} {100*v/total:7.3f} %  {np.sqrt(v/g2)*1e9:8.2f} nV/rtHz")

    sens_pow = sum(grp[k] for k in ("pixel shot (R_SHA, R_SHB)", "R_D (R25, R31)"))
    amp_pow = total - sens_pow
    sens = np.sqrt(sens_pow / g2) * 1e9
    amp = np.sqrt(amp_pow / g2) * 1e9
    print(f"\nsensor items (R_SHA, R_SHB, R_R25, R_R31): {sens:.2f} nV/rtHz")
    print(f"amplifier and other items (quadrature): {amp:.2f} nV/rtHz, {100*amp_pow/total:.3f} % of the power")
    print(f"sqrt(729.0^2 + amp^2) = {np.sqrt(729.0**2 + amp**2):.2f} nV/rtHz, measured total {np.sqrt(total/g2)*1e9:.2f} nV/rtHz")

    print("\nX_OUT noise (white input, fold-down 0.9011, ENBW 0.4167 Hz, gain at 518 Hz):")
    fold = 0.9011
    enbw = 0.4167
    gain = abs(G)
    for lab, v in (("sensor only", 729.00e-9), ("all sources", np.sqrt(total / g2))):
        print(f"  {lab:12s}: {v*gain*fold*np.sqrt(enbw)*1e6:.2f} uV rms")

    print("\nFold-down factor from the DEC run:")
    fold_analysis(RUN_DEC)
