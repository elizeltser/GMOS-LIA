"""P-27 full chain: X/Y scale factor and phase over a full excitation turn (LIA-AFE-Eval).

Run from simulations/ti-pspice:  python docs/sim-results/scripts/P-27_phase.py
Reads sim-runs/P27_phase/P27_phase.csd (circuit circuits/afe_eval_fast.cir, pexc = 0 to 315 deg in 45 deg steps).

Conventions
- A node signal inside a window is fitted as c + a sin(w t) + b cos(w t) at f0 = 518 Hz. Its phasor is
  C = a + j b = A exp(j phi), so phi = atan2(b, a) is the phase of A sin(w t + phi).
- EXC_DAC = 1.65 + 0.3 sin(w t + pexc), so its phase is pexc.
- Main window: 20 whole periods (38.61 ms) from 60 ms. Samples are resampled to a uniform 1 us grid.
- Settling trend: two whole-period windows of 10 periods each, from 60 ms and from 60 ms + 10 T.
- X_OUT and Y_OUT are time means over the same windows. X = R cos(phi), Y = -R sin(phi).

Drain model (ideal current source on side A, pixel polarity: the pixel sinks current, so the drain falls with
the gate). Two coupled nodes with admittance matrix [[Y, -jw Cd], [-jw Cd, Y]], Y = 1/R_D + jw C_self.
Normalised transfer T = R_D V / I (1 at DC). C_self = cnode + cmux + C_CMN(INA828) + C_DIFF, Cd = C_DIFF.
Two cases: 60 pF (cnode + cmux, no INA828 input capacitance) and 71 pF (with 10 pF and 1 pF of INA828.LIB).
"""
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools"))
from csdf import read_csdf  # noqa: E402

CSD = ROOT / "sim-runs" / "P27_phase" / "P27_phase.csd"
F0 = 518.0
T0 = 1.0 / F0
TW = 0.060
DT = 1e-6
NODES = ["GATE", "DRN_A", "DRN_B", "INA_OUT", "HPF_OUT", "BPF_OUT"]
K = 2.0 / np.pi
RD = 330e3
VEXC_A = 0.3
VGA = VEXC_A / 120           # 2.5 mV, pixel normalisation of the gate amplitude
VDA = 10e-3

# ---- closed forms (ideal op amps, schematic values), as in afe_eval_expected.py ----
RG = 5.62e3
G_INA = 1 + 50e3 / RG
R9 = R11 = R12 = R13 = 9.31e3
C9 = C10 = C11 = C12 = 33e-9
KSK = 2.0


def hpf(f):
    s = 2j * np.pi * f
    R1, R2, C1, C2, k = R9, R13, C10, C11, KSK
    num = k * s**2
    den = s**2 + s * (1 / (R2 * C1) + 1 / (R2 * C2) + (1 - k) / (R1 * C1)) + 1 / (R1 * R2 * C1 * C2)
    return num / den


def lpf(f):
    s = 2j * np.pi * f
    R1, R2, C1, C2, k = R11, R12, C9, C12, KSK
    w = 1 / (R1 * R2 * C1 * C2)
    den = s**2 + s * (1 / (R1 * C1) + 1 / (R2 * C1) + (1 - k) / (R2 * C2)) + w
    return k * w / den


def mfb(f, R1=120e3, R2=1e3, R3=1e3, C1=47e-9, C2=22e-9):
    s = 2j * np.pi * f
    return -(1 / (R1 * R3 * C1 * C2)) / (s**2 + s / C1 * (1 / R1 + 1 / R2 + 1 / R3) + 1 / (R2 * R3 * C1 * C2))


# ---- P-24 and P-26 vendor values ----
VEND_INA_DEG, VEND_HPF_DEG, VEND_LPF_DEG, VEND_FRONT_DEG = -0.059, -0.055, -0.062, -0.177
VEND_FRONT_MAG = 39.577492
VEND_MFB_PHASE_DEG = 171.6972
VEND_MFB_MAG = 1 / 119.9219
ENTRY_PHASE_CONST = 167.87


def two_node(f, c_self, c_mut):
    """Normalised transfer T_A = R_D V_A / I_A and T_B = R_D V_B / I_A for a unit current into node A."""
    w = 2 * np.pi * f
    Y = 1 / RD + 1j * w * c_self
    Ym = -1j * w * c_mut
    M = np.array([[Y, Ym], [Ym, Y]])
    V = np.linalg.solve(M, np.array([1.0 + 0j, 0.0 + 0j]))
    return V[0] / RD, V[1] / RD


def fit(t, v):
    w = 2 * np.pi * F0
    M = np.column_stack([np.ones_like(t), np.sin(w * t), np.cos(w * t)])
    coef, *_ = np.linalg.lstsq(M, v, rcond=None)
    _, a, b = coef
    C = a + 1j * b
    return C, abs(C), np.degrees(np.angle(C))


def uniform(sec, name, t0, t1):
    x = np.asarray(sec.x, dtype=float)
    y = np.asarray(sec[name], dtype=float)
    t = np.arange(t0, t1, DT)
    return t, np.interp(t, x, y)


def wrap(d):
    return (np.asarray(d) + 180.0) % 360.0 - 180.0


def main():
    secs = read_csdf(str(CSD))
    secs = sorted(secs, key=lambda s: s.step_value)
    win1 = (TW, TW + 20 * T0)
    win_a = (TW, TW + 10 * T0)
    win_b = (TW + 10 * T0, TW + 20 * T0)

    # ---- data checks ----
    max_step = 0.0
    for s in secs:
        x = np.asarray(s.x, dtype=float)
        m = (x >= TW - 1e-9) & (x <= win1[1] + 1e-9)
        d = np.diff(x[m])
        max_step = max(max_step, d.max())
    print(f"Sample check: maximum solver step in the window {max_step*1e6:.3f} us (TRAN maximum 5 us); "
          f"points per period {T0/5e-6:.1f} at the maximum step, data {T0/max_step:.1f} at the largest step")
    print()

    rows = []
    for s in secs:
        pexc = s.step_value
        rec = {"pexc": pexc}
        t, _ = uniform(s, "V(X_OUT)", *win1)
        for n in ("X_OUT", "Y_OUT"):
            _, v = uniform(s, f"V({n})", *win1)
            rec[n] = float(np.mean(v))
        for n in NODES:
            _, v = uniform(s, f"V({n})", *win1)
            C, amp, ph = fit(t, v)
            rec[n] = C
            rec[n + "_amp"] = amp
            rec[n + "_ph"] = ph
        # two whole-period windows, 10 periods each
        for tag, w_ in (("A", win_a), ("B", win_b)):
            for n in ("X_OUT", "Y_OUT"):
                _, v = uniform(s, f"V({n})", *w_)
                rec[f"{n}_{tag}"] = float(np.mean(v))
        rows.append(rec)

    # ---- table 1: per step ----
    print("pexc  X_OUT(mV)   Y_OUT(mV)   R(mV)      phi_BPF    phi_XY     phi_BPF-pexc  |DRN_A|(mV)  R/|DRN_A|  R/|diff|")
    ratio_A, ratio_D, ratio_demod = [], [], []
    for r in rows:
        X, Y = r["X_OUT"], r["Y_OUT"]
        R = np.hypot(X, Y)
        phi_xy = np.degrees(np.arctan2(-Y, X))
        dif = r["DRN_B"] - r["DRN_A"]
        ratio_A.append(R / r["DRN_A_amp"])
        ratio_D.append(R / abs(dif))
        ratio_demod.append(R / (K * r["BPF_OUT_amp"]))
        print(f"{r['pexc']:4.0f} {X*1e3:10.4f} {Y*1e3:10.4f} {R*1e3:10.4f} {r['BPF_OUT_ph']:10.4f} {phi_xy:10.4f} "
              f"{wrap(r['BPF_OUT_ph']-r['pexc']):12.4f} {r['DRN_A_amp']*1e3:12.5f} {R/r['DRN_A_amp']:10.4f} {R/abs(dif):10.4f}")
    Rs = np.array([np.hypot(r["X_OUT"], r["Y_OUT"]) for r in rows])
    pc = np.array([wrap(r["BPF_OUT_ph"] - r["pexc"]) for r in rows])
    print(f"R mean {Rs.mean()*1e3:.4f} mV, spread {(Rs.max()-Rs.min())/Rs.mean()*100:.4f} %")
    print(f"phi_BPF - pexc mean {pc.mean():.4f} deg, spread {pc.max()-pc.min():.4f} deg")
    print(f"scale factor R/|DRN_A|: mean {np.mean(ratio_A):.4f} V/V, spread {(max(ratio_A)-min(ratio_A))/np.mean(ratio_A)*100:.4f} %")
    print(f"scale factor R/|DRN_B-DRN_A|: mean {np.mean(ratio_D):.4f} V/V")
    print(f"demodulator check R/((2/pi)|BPF_OUT|): mean {np.mean(ratio_demod):.6f}")
    print()

    # ---- table 2: means of the node phasors over the turn ----
    def stage(num_fn, den_fn):
        q = [num_fn(r) / den_fn(r) for r in rows]
        am = np.array([abs(z) for z in q])
        ph = wrap([np.degrees(np.angle(z)) for z in q])
        return am.mean(), ph.mean(), ph.max() - ph.min(), am.max() - am.min()

    DIFF = lambda r: r["DRN_B"] - r["DRN_A"]
    EXC = lambda r: VEXC_A * np.exp(1j * np.radians(r["pexc"]))
    stages = [
        ("GATE / EXC (MFB)", lambda r: r["GATE"], EXC),
        ("DRN_A / GATE", lambda r: r["DRN_A"], lambda r: r["GATE"]),
        ("(DRN_B - DRN_A) / GATE", DIFF, lambda r: r["GATE"]),
        ("INA_OUT / (DRN_B - DRN_A)", lambda r: r["INA_OUT"], DIFF),
        ("HPF_OUT / INA_OUT (U3A)", lambda r: r["HPF_OUT"], lambda r: r["INA_OUT"]),
        ("BPF_OUT / HPF_OUT (U3B)", lambda r: r["BPF_OUT"], lambda r: r["HPF_OUT"]),
        ("BPF_OUT / (DRN_B - DRN_A)", lambda r: r["BPF_OUT"], DIFF),
        ("BPF_OUT / EXC (chain)", lambda r: r["BPF_OUT"], EXC),
    ]
    print("Stage                          |H| mean         phase mean (deg)   spread (deg)   |H| range")
    stage_out = {}
    for name, nf, df in stages:
        am, ph, sp, ar = stage(nf, df)
        stage_out[name] = (am, ph)
        print(f"{name:<30} {am:12.6f} {ph:+16.4f} {sp:14.4f} {ar:12.2e}")
    print()

    gate_amp = np.mean([r["GATE_amp"] for r in rows])
    gate_ph = np.mean([wrap(r["GATE_ph"] - r["pexc"]) for r in rows])
    dA_amp = np.mean([r["DRN_A_amp"] for r in rows])
    diff_amp = np.mean([abs(DIFF(r)) for r in rows])
    diff_over_gate = np.mean([abs(DIFF(r)) / abs(r['GATE']) for r in rows])
    bpf_amp = np.mean([r["BPF_OUT_amp"] for r in rows])
    Xamp = np.mean([np.hypot(r["X_OUT"], r["Y_OUT"]) for r in rows])

    # ---- settling trend (two 10-period windows) ----
    dX = np.array([r["X_OUT_A"] - r["X_OUT_B"] for r in rows])
    dY = np.array([r["Y_OUT_A"] - r["Y_OUT_B"] for r in rows])
    print("Settling trend, mean over 10 periods from 60 ms minus mean over the next 10 periods (mV):")
    print(f"  X_OUT max |diff| {np.max(np.abs(dX))*1e3:.5f} mV, Y_OUT max |diff| {np.max(np.abs(dY))*1e3:.5f} mV")
    print(f"  analytic bias of the critically damped post filter (tau 3 ms) at 60 ms: (1 + t/tau) exp(-t/tau) = "
          f"{21*np.exp(-20):.2e} of the initial error")
    print()

    # ---- drain node model ----
    print("Drain node model (normalised transfer, pixel polarity inverts the drain, per unit gate ratio):")
    cases = {}
    for label, cs, cm in (("60 pF", 60e-12, 0.0), ("71 pF", 71e-12, 1e-12)):
        TA, TB = two_node(F0, cs, cm)
        ratio = TB / TA
        diff_norm = TA * (ratio - 1.0)            # (B - A) per unit side-A drive, sign referenced to A
        g_A = -TA                                  # DRN_A / GATE (inverted pixel)
        g_D = -diff_norm                           # (DRN_B - DRN_A) / GATE
        cases[label] = (TA, ratio, g_A, g_D)
        print(f"  {label}: |T_A| {abs(TA):.6f}, DRN_A lag {-np.degrees(np.angle(TA)):+.4f} deg (phase DRN_A/GATE "
              f"{np.degrees(np.angle(g_A)):+.4f}); DRN_B/DRN_A {abs(ratio)*100:.5f} % at {np.degrees(np.angle(ratio)):+.4f} deg; "
              f"(DRN_B-DRN_A)/GATE |H| {abs(g_D):.6f}, phase {np.degrees(np.angle(g_D)):+.4f} deg")
    TA71, ratio71, gA71, gD71 = cases["71 pF"]
    fb =np.degrees(np.angle(ratio71 - 1.0)) - 180.0
    print(f"  feedthrough part of the difference phase (71 pF): {fb:+.4f} deg")
    print()

    # ---- expected values and checks ----
    H_mfb_c = mfb(F0)
    amp_mfb_c = abs(H_mfb_c)
    ph_mfb_c = np.degrees(np.angle(H_mfb_c))
    H_front_c = G_INA * hpf(F0) * lpf(F0)
    print("Gate amplitude (pk, mV):")
    print(f"  closed form 0.3 V / {1/amp_mfb_c:.4f} = {VEXC_A*amp_mfb_c*1e3:.5f} mV, "
          f"P-26 vendor 0.3 V / 119.9219 = {VEXC_A*VEND_MFB_MAG*1e3:.5f} mV, measured {gate_amp*1e3:.5f} mV "
          f"({(gate_amp/(VEXC_A*VEND_MFB_MAG)-1)*100:+.4f} % vs vendor)")
    print()

    # drain amplitude expectation
    gate_pk_closed = VEXC_A * amp_mfb_c
    drain_closed_60 = VDA * (gate_pk_closed / VGA) * abs(cases["60 pF"][0])
    drain_closed_71 = VDA * (gate_pk_closed / VGA) * abs(TA71)
    drain_meas_diff = diff_over_gate * gate_amp
    print("Drain amplitude (mV pk):")
    print(f"  measured |DRN_A| {dA_amp*1e3:.5f}; expected 60 pF {drain_closed_60*1e3:.5f} "
          f"({(dA_amp/drain_closed_60-1)*100:+.4f} %); expected 71 pF {drain_closed_71*1e3:.5f} "
          f"({(dA_amp/drain_closed_71-1)*100:+.4f} %)")
    print(f"  measured differential: |DRN_B-DRN_A|/|GATE| = {diff_over_gate:.6f}, times gate amplitude {gate_amp*1e3:.5f} mV = {drain_meas_diff*1e3:.5f} mV")
    print()

    # R checks
    R_vend_meas = K * VEND_FRONT_MAG * (drain_meas_diff)
    R_vend_71 = K * VEND_FRONT_MAG * drain_closed_71
    R_vend_60 = K * VEND_FRONT_MAG * drain_closed_60
    print("R against the P-24 vendor gain (R in mV):")
    print(f"  measured differential drain: 2/pi x 39.5775 x {drain_meas_diff*1e3:.5f} = {R_vend_meas*1e3:.4f} "
          f"(measured mean {Rs.mean()*1e3:.4f}, {(Rs.mean()/R_vend_meas-1)*100:+.4f} %)")
    print(f"  closed-form MFB, 71 pF: {R_vend_71*1e3:.4f} ({(Rs.mean()/R_vend_71-1)*100:+.4f} %)")
    print(f"  closed-form MFB, 60 pF: {R_vend_60*1e3:.4f} ({(Rs.mean()/R_vend_60-1)*100:+.4f} %)")
    print()

    # phase chain
    ph_chain71 = VEND_MFB_PHASE_DEG + np.degrees(np.angle(gD71)) + np.degrees(np.angle(H_front_c)) + VEND_FRONT_DEG
    ph_chain60 = VEND_MFB_PHASE_DEG + np.degrees(np.angle(cases["60 pF"][3])) + np.degrees(np.angle(H_front_c)) + VEND_FRONT_DEG
    print("Phase of BPF_OUT relative to EXC (deg):")
    print(f"  chain with 71 pF: {VEND_MFB_PHASE_DEG:.4f} {np.degrees(np.angle(gD71)):+.4f} {np.degrees(np.angle(H_front_c)):+.4f} "
          f"{VEND_FRONT_DEG:+.4f} = pexc + {ph_chain71:.4f}")
    print(f"  chain with 60 pF: pexc + {ph_chain60:.4f} (entry: pexc + {ENTRY_PHASE_CONST})")
    print(f"  measured mean: pexc + {pc.mean():.4f}; difference to 71 pF chain {pc.mean()-ph_chain71:+.4f} deg")
    print()

    # scale factor against ideal and E-9
    H_front_abs = abs(H_front_c)
    ideal_scale = K * abs(G_INA * hpf(F0) * lpf(F0))
    E9_25 = K * 40.0 * 1.0  # 2/pi x 4 x 10 = 25.465 at G = 10 (front end 40 V/V)
    E9_scaled = E9_25 * G_INA / 10.0
    print("Scale factor split (R/|DRN_A| mean):")
    print(f"  ideal (2/pi)|H_front| = {ideal_scale:.4f} V/V; E-9 rounded 25.5 gives 2/pi x 40 = {E9_25:.4f} at G = 10, "
          f"scaled to G = {G_INA:.4f} gives {E9_scaled:.4f} V/V")
    print(f"  measured R/|DRN_A| = {np.mean(ratio_A):.4f} V/V, against ideal {(np.mean(ratio_A)/ideal_scale-1)*100:+.4f} %")
    print(f"  front-end vendor deficit: |BPF/(B-A)| {abs(stage_out['BPF_OUT / (DRN_B - DRN_A)'][0]):.4f} vs ideal "
          f"{abs(H_front_c):.4f}: {(abs(stage_out['BPF_OUT / (DRN_B - DRN_A)'][0])/abs(H_front_c)-1)*100:+.4f} %")
    print(f"  feedthrough |(DRN_B-DRN_A)|/|DRN_A|: {(diff_amp/dA_amp-1)*100:+.4f} %")
    print(f"  demodulator R/((2/pi)|BPF_OUT|): {(np.mean(ratio_demod)-1)*100:+.4f} %")
    print()

    # front end vs ideal
    print(f"Front end at 518 Hz: vendor |BPF/(B-A)| {abs(stage_out['BPF_OUT / (DRN_B - DRN_A)'][0]):.6f} V/V, "
          f"phase {stage_out['BPF_OUT / (DRN_B - DRN_A)'][1]:+.4f} deg; ideal |H| {abs(H_front_c):.6f}, "
          f"phase {np.degrees(np.angle(H_front_c)):+.4f} deg")
    return rows


if __name__ == "__main__":
    main()
