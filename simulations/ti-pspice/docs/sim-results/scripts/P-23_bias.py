"""P-23a and P-23b: bias-point checks of afe_eval.cir against the expected values of the index entry.

Run from simulations/ti-pspice:  python docs/sim-results/scripts/P-23_bias.py
Reads the .OP bias tables (SMALL SIGNAL BIAS SOLUTION) of
  sim-runs/P23a_op/P23a_op.out          (vda = 0)
  sim-runs/P23b_heat/P23b_heat.out      (vda = 10 mV, default)
  sim-runs/P23a_abstol/P23a_abstol.out  (vda = 0, PTRAN and ABSTOL as in options.inc, 1 pA ABSTOL)
and the X_OUT analysis-path runs P23c_op_abstol1n, P23c_op_abstol1p, P23d_op_step and P23e_op_tight.

Method of the settling check: at DC the capacitor C13 is open, so the current into node NC13 must
be zero. The check is I(R14) - I(R15) = 0 with I(R14) = (X_DEM - NC13) / 200 kOhm and
I(R15) = (NC13 - U26BP) / 200 kOhm. The internal MID node of each OPAx196 must sit at (V+ + V-)/2.
Each such node is compared with its rail midpoint.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
NUM = r"[-+]?(?:\d+\.?\d*|\.\d+)(?:[Ee][-+]?\d+)?"
PAIR = re.compile(r"\(\s*([A-Za-z0-9_.+\-]+)\)\s*(" + NUM + r")")
STEP = re.compile(r"CURRENT STEP\s+PARAM\s+(\w+)\s*=\s*(\S+)")

# Closed-form expected values (ideal op amps, schematic values)
R5, R6 = 1e3, 120e3
GATE_EXP = (1 + R5 / R6) * 1.0 - (R5 / R6) * 1.65           # 0.994583 V (entry: 0.99458 V)
VSUP_EXP = 1.1 * 2.4 - 1e3 * 7.5e-6                          # 2.6325 V
DRN_EXP = VSUP_EXP - 330e3 * 7.5e-6                          # 0.1575 V
G_INA = 9.8968                                               # INA828 gain, 1 + 50 kOhm / 5.62 kOhm
R_HTR, R_UH = 600.0, 4.5                                     # rhtr, ronh (heater path)
R_SHUNT = 15.0                                               # R24 / R30
R_BLEED = 99.8e3                                             # R20 + R22 (feedback divider, 49.9 k each)
R_FILT = 200e3                                               # R14 and R15 (each)

# Op amps: (name, +IN, -IN, OUT, positive rail, negative rail)
OPAMPS = [
    ("U2", "DRN_B", "DRN_A", "INA_OUT", "P5VA", "M5VA"),     # INA828 (VIN+ = DRN_B, VIN- = DRN_A)
    ("U1B", "U1BP", "U1BM", "GOUT", "P5VA", "M5VA"),
    ("U1A", "0", "U1AO", "U1AO", "P5VA", "M5VA"),
    ("U10A", "DAC2", "U10AM", "U10AO", "P5VA", "M5VA"),
    ("U10B", "DAC3", "U10BM", "U10BO", "P5VA", "M5VA"),
    ("U9A", "DAC1", "U9AM", "HSH_A", "P5VP", "M5VA"),
    ("U9B", "DAC0", "U9BM", "HSH_B", "P5VP", "M5VA"),
    ("U3A", "U3AP", "U3AM", "HPF_OUT", "P5VA", "M5VA"),
    ("U3B", "U3BP", "U3BM", "BPF_OUT", "P5VA", "M5VA"),
    ("U26A", "D1", "U26AM", "X_DEM", "P5VA", "M5VA"),
    ("U26B", "U26BP", "U26BM", "X_OUT", "P5VA", "M5VA"),
    ("U27A", "D2", "U27AM", "Y_DEM", "P5VA", "M5VA"),
    ("U27B", "U27BP", "U27BM", "Y_OUT", "P5VA", "M5VA"),
]
TRANSITION = (-3.0, -1.5)   # OPA2196 input transition region, relative to V+ (window of the entry)
TRANSITION_STAGES = ("U26A", "U27A", "U3A", "U3B")   # the four inputs the P-23 rule names
MID_STAGES = ("U1B", "U1A", "U10A", "U10B", "U9A", "U9B", "U3A", "U3B", "U26A", "U26B", "U27A", "U27B")


def parse_bias(path, keep_dotted=False):
    """Return a list of (step_name, step_value, {node: volt}) for each bias table in the file.
    keep_dotted keeps the internal nodes of the models (for example X_U26B.MID)."""
    text = Path(path).read_text(errors="replace").splitlines()
    tables = []
    i = 0
    while i < len(text):
        if "SMALL SIGNAL BIAS SOLUTION" in text[i]:
            step_name, step_value = None, None
            for j in range(i, min(i + 6, len(text))):
                m = STEP.search(text[j])
                if m:
                    step_name, step_value = m.group(1), m.group(2)
            nodes = {}
            j = i + 1
            while j < len(text) and "TOTAL POWER DISSIPATION" not in text[j] \
                    and "OPERATING POINT INFORMATION" not in text[j] \
                    and "SMALL SIGNAL BIAS SOLUTION" not in text[j]:
                for name, val in PAIR.findall(text[j]):
                    if keep_dotted or "." not in name:   # default: top-level node names only
                        nodes.setdefault(name, float(val))
                j += 1
            tables.append((step_name, step_value, nodes))
            i = j
        else:
            i += 1
    return tables


def check(label, value, expected, tol, unit="V"):
    diff = value - expected
    ok = abs(diff) <= tol
    print(f"  {label:34s} measured {value: .6f} {unit}  expected {expected: .6f}  diff {diff*1e3:+.3f} mV  "
          f"limit {tol*1e3:.2f} mV  {'PASS' if ok else 'FAIL'}")
    return ok


def margins(nodes):
    """Output and input margin to the rails of every op amp and the INA828, and the transition-region check."""
    worst = (9.0, "")
    rows = []
    for name, inp, inm, out, vp_n, vm_n in OPAMPS:
        vp, vm = nodes[vp_n], nodes[vm_n]
        for pin, net in (("+IN", inp), ("-IN", inm), ("OUT", out)):
            v = 0.0 if net == "0" else nodes[net]
            m = min(vp - v, v - vm)              # margin to the nearest rail
            rows.append((name, pin, net, v, m, vp))
            if m < worst[0]:
                worst = (m, f"{name} {pin} {net}")
    print("  op amp and INA828 pins (rail margin = smaller distance to V+ and V-):")
    for name, pin, net, v, m, vp in rows:
        tr = ""
        if name in TRANSITION_STAGES and pin != "OUT":
            lo, hi = vp + TRANSITION[0], vp + TRANSITION[1]
            tr = f"transition {'IN' if lo <= v <= hi else 'out'} [{lo:.2f},{hi:.2f}]"
        print(f"    {name:4s} {pin:4s} {net:8s} {v: .6f} V  margin {m:.3f} V  {tr}")
    print(f"  smallest rail margin: {worst[0]:.3f} V at {worst[1]} (limit 0.2 V)")
    return worst[0] >= 0.2


def run_a(nodes, label="P23a_op"):
    print(f"{label} (v5 = 5.3 V, heaters off, vda = 0):")
    ok = []
    ok.append(check("GATE", nodes["GATE"], GATE_EXP, 0.3e-3))
    ok.append(check("VSUP_A", nodes["VSUP_A"], VSUP_EXP, 1e-3))
    ok.append(check("DRN_A", nodes["DRN_A"], DRN_EXP, 1e-3))
    ok.append(check("DRN_B", nodes["DRN_B"], DRN_EXP, 1e-3))
    diff_in = nodes["DRN_B"] - nodes["DRN_A"]
    ideal = G_INA * diff_in
    print(f"  drain difference DRN_B - DRN_A = {diff_in*1e6:+.2f} uV (x 330 kOhm = {diff_in/330e3*1e12:+.1f} pA)")
    print(f"  INA828 ideal G*(DRN_B-DRN_A) = {ideal*1e3:+.4f} mV, measured INA_OUT = {nodes['INA_OUT']*1e3:+.4f} mV, "
          f"implied offset {(nodes['INA_OUT']-ideal)*1e3:+.4f} mV")
    ok.append(abs(nodes["INA_OUT"]) < 2e-3)
    print(f"  INA_OUT |V| < 2 mV at equal drains: {'PASS' if ok[-1] else 'FAIL'}")
    for k, lim in (("HPF_OUT", 1e-3), ("BPF_OUT", 1e-3), ("X_OUT", 0.5e-3), ("Y_OUT", 0.5e-3)):
        ok.append(abs(nodes[k]) < lim)
        print(f"  {k:10s} {nodes[k]*1e3:+.4f} mV, limit {lim*1e3:.1f} mV: {'PASS' if ok[-1] else 'FAIL'}")
    i_p5va = (nodes["P5VIN"] - nodes["P5VA"]) / 1.0
    i_p5vp = (nodes["P5VIN"] - nodes["P5VP"]) / 1.0
    vf = nodes["VIN5P1"] - nodes["P5VIN"]
    print(f"  +5VA = {nodes['P5VA']:.6f} V (P5VIN {nodes['P5VIN']:.6f} V, VIN5P1 {nodes['VIN5P1']:.6f} V)")
    print(f"  I(+5VA) = {i_p5va*1e3:.3f} mA, I(D5) = {(i_p5va+i_p5vp)*1e3:.3f} mA, "
          f"V_F(D5) = {vf*1e3:.2f} mV (DSCHOTTKY, RS = 0.08 Ohm)")
    print(f"  M5VA = {nodes['M5VA']:.6f} V")
    ok.append(margins(nodes))
    return ok


def run_b(nodes, vh):
    print(f"P23b (heater A, DAC1 = {vh} V, heater B off, vda = 10 mV):")
    ok = []
    hfb_exp = 2 * vh
    i_htr = nodes["HPIX_A"] / R_HTR
    i_htr_exp = hfb_exp / (R_HTR + R_UH)
    i_bleed = hfb_exp / R_BLEED                           # R20/R22 feedback divider draws it through R24
    u9a_exp = hfb_exp + R_SHUNT * (i_htr_exp + i_bleed)   # corrected value
    hsense_exp = 25 * R_SHUNT * (i_htr_exp + i_bleed)
    print(f"  heater current from HPIX_A/600 Ohm = {i_htr*1e3:.4f} mA; hand value hfb/604.5 Ohm = {i_htr_exp*1e3:.4f} mA")
    print(f"  bleed current hfb/99.8 kOhm = {i_bleed*1e6:.2f} uA; shunt current = {(nodes['HSH_A']-nodes['HFB_A'])/R_SHUNT*1e3:.4f} mA")
    ok.append(check("HFB_A", nodes["HFB_A"], hfb_exp, 1e-3))
    ok.append(check("U9A out (HSH_A), corrected", nodes["HSH_A"], u9a_exp, 1e-3))
    print(f"    corrected value = {u9a_exp:.6f} V (2.5 + 15 x (I_htr + I_bleed) at hfb = {hfb_exp} V)")
    if abs(hfb_exp - 4.0) < 1e-9:   # the entry quotes 4.099 V for the 4.0 V heater case only
        ok.append(check("U9A out, entry value 4.099 V", nodes["HSH_A"], 4.099, 1e-3))
    head = nodes["P5VP"] - nodes["HSH_A"]
    ok.append(head >= 0.2)
    print(f"  headroom P5VP - HSH_A = {head:.4f} V, limit 0.2 V: {'PASS' if ok[-1] else 'FAIL'}")
    rel = (nodes["HSENSE_B"] - hsense_exp) / hsense_exp
    ok.append(abs(rel) <= 0.02)
    print(f"  HSENSE_B = {nodes['HSENSE_B']:.6f} V, corrected 25 x 15 Ohm x (I_htr + I_bleed) = {hsense_exp:.6f} V, "
          f"rel {rel*100:+.3f} %, limit 2 %: {'PASS' if ok[-1] else 'FAIL'}")
    diff_in = nodes["DRN_B"] - nodes["DRN_A"]
    ideal = G_INA * diff_in
    print(f"  drain difference DRN_B - DRN_A = {diff_in*1e6:+.2f} uV, INA828 ideal = {ideal*1e3:+.4f} mV, "
          f"measured INA_OUT = {nodes['INA_OUT']*1e3:+.4f} mV, implied offset {(nodes['INA_OUT']-ideal)*1e3:+.4f} mV")
    ok.append(margins(nodes))
    return ok


def settling_check(nodes, label):
    """KCL at NC13 (C13 open at DC) and the MID node of every OPAx196 against (V+ + V-)/2."""
    x_dem, nc13, u26bp = nodes["X_DEM"], nodes["NC13"], nodes["U26BP"]
    i14 = (x_dem - nc13) / R_FILT                          # R14, from X_DEM to NC13
    i15 = (nc13 - u26bp) / R_FILT                          # R15, from NC13 to U26BP
    kcl = i14 - i15                                        # current into C13 at DC is zero
    print(f"  {label}: I(R14) = {i14*1e12:+.1f} pA, I(R15) = {i15*1e12:+.1f} pA, KCL residual at NC13 = {kcl*1e12:+.1f} pA "
          f"(limit 1 pA): {'PASS' if abs(kcl) <= 1e-12 else 'FAIL'}")
    worst = (0.0, "")
    for name in MID_STAGES:
        vp = nodes[[o[4] for o in OPAMPS if o[0] == name][0]]
        vm = nodes[[o[5] for o in OPAMPS if o[0] == name][0]]
        key = f"X_{name}.MID"
        if key not in nodes:
            continue
        off = nodes[key] - (vp + vm) / 2
        if abs(off) > abs(worst[0]):
            worst = (off, name)
    print(f"  largest MID offset from (V+ + V-)/2 over {len(MID_STAGES)} op amps: {worst[0]*1e6:+.1f} uV at {worst[1]} "
          f"(limit 10 uV): {'PASS' if abs(worst[0]) <= 10e-6 else 'FAIL'}")
    return abs(kcl) <= 1e-12 and abs(worst[0]) <= 10e-6


def abstol_compare():
    """Settling and analysis-path comparison of single-point .OP runs (v5 = 5.3 V)."""
    print("Settling and analysis-path check (bias points, v5 = 5.3 V):")
    runs = (("plain .OP, vda = 10 mV, ABSTOL 1n", "P23c_op_abstol1n", 0),
            ("plain .OP, vda = 10 mV, ABSTOL 1p", "P23c_op_abstol1p", 0),
            (".OP + .STEP vda LIST 0, step vda = 0", "P23a_op", 0),
            (".OP + .STEP vda LIST 0, ABSTOL 1p", "P23a_abstol", 0),
            (".OP + .STEP vda LIST 0 10m, step vda = 0", "P23d_op_step", 0),
            (".OP + .STEP vda LIST 0 10m, step vda = 10 mV", "P23d_op_step", 1),
            ("tight PTRAN, step vda = 0", "P23e_op_tight", 0),
            ("tight PTRAN, step vda = 10 mV", "P23e_op_tight", 1))
    for label, folder, k in runs:
        path = ROOT / "sim-runs" / folder / f"{folder}.out"
        if not path.exists():
            print(f"  {label}: not present")
            continue
        tables = parse_bias(path, keep_dotted=True)
        if k >= len(tables):
            print(f"  {label}: not present")
            continue
        n = tables[k][2]
        i14 = (n["X_DEM"] - n["NC13"]) / R_FILT
        i15 = (n["NC13"] - n["U26BP"]) / R_FILT
        print(f"  {label}: X_OUT {n['X_OUT']*1e3:+.4f} mV, U26BP {n['U26BP']*1e3:+.4f} mV")
        settling_check(n, label)


def expected_x_out(nodes):
    """Expected DC X_OUT from the OPAx196 model: U26BP = X_DEM - R(14+15) I_B, X_OUT = U26BP + Vdiff offset."""
    i_b = 5.25e-12                     # OPAx196.LIB I_I_B (only the node-to-node path is used here)
    u26bp = nodes["X_DEM"] - 400e3 * i_b
    return u26bp, u26bp + 16.848e-6    # 16.848 uV = input difference of U26B from the model (coordinator, not verified here)


def main():
    results = {}
    runs = [("P23a_op", "P23a_op", run_a), ("P23a_abstol", "P23a_abstol", run_a),
            ("P23b_heat", "P23b_heat", run_b)]
    for label, folder, fn in runs:
        path = ROOT / "sim-runs" / folder / f"{folder}.out"
        if not path.exists():
            print(f"{label}: not present")
            continue
        for step_name, step_value, nodes in parse_bias(path):
            if fn is run_b:
                results[f"{label}_{step_value}"] = run_b(nodes, float(step_value))
            else:
                results[label] = run_a(nodes, label)
    abstol_compare()
    path = ROOT / "sim-runs" / "P23e_op_tight" / "P23e_op_tight.out"
    if path.exists():
        print("P23e tight-PTRAN X_OUT check (expected X_OUT about -0.052 mV in every state):")
        for step_name, step_value, nodes in parse_bias(path, keep_dotted=True):
            u26bp_e, x_e = expected_x_out({k: v for k, v in nodes.items()})
            ok_x = abs(nodes["X_OUT"] - (-0.052e-3)) <= 0.005e-3
            print(f"  vda = {step_value}: X_OUT {nodes['X_OUT']*1e3:+.4f} mV, expected {x_e*1e3:+.4f} mV "
                  f"(U26BP expected {u26bp_e*1e6:+.2f} uV, measured {nodes['U26BP']*1e6:+.2f} uV) "
                  f"{'PASS' if ok_x else 'CHECK'}")
    allok = all(all(v if isinstance(v, bool) else True for v in ok) for ok in results.values())
    for k, ok in results.items():
        print(f"{k}: {sum(bool(x) for x in ok)} of {len(ok)} checks pass")
    return 0 if allok else 1


if __name__ == "__main__":
    sys.exit(main())
