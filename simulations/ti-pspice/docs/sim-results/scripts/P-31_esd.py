"""P-31 ESD stand-in currents, split into start-up conduction, edge (displacement) spikes and DC leakage.

Run from simulations/ti-pspice:  python docs/sim-results/scripts/P-31_esd.py
Reads sim-runs/P31_powerup/P31_powerup.csd (circuit circuits/afe_eval_P31.cir).
Stand-in current = voltage across its 1 Ohm series resistor (K node minus its other node).
- t_up: first time P15V reaches 5 V (the rail is up).
- Peak before t_up: start-up conduction while the reference is high and the rail is low.
- Peak after t_up: includes the displacement current of the 100 pF CJO at each reference edge.
- DC: mean over the last 20 whole periods (end of run, rails settled), which is the leakage / static current.
- Settling time constants: exponential fit of the boxcar mean after the J5 ramp (2 % to 2 mV band).
- Peaks, the charge and the forward-bias check use the raw solver points (judge correction, 8 November 2026):
  the 1 us grid misses the 10 ns reference edges and underestimates the start-up peak (2.26 A instead of 2.45 A).
- Forward bias: diode voltage V(anode) - V(cathode node K). After the rails are up every stand-in is reverse biased,
  so the edge peaks are displacement current of CJO and the DC is -IS (model artifacts, not conduction).
- Model artifacts before J5: the ideal DAC80508 sources (V_DAC2, V_DAC3 = 2.4 V) back-power +5VA through the
  U10A/U10B input clamps (P5VA about 1.64 V), so BPF_OUT is 0.2 V to 0.4 V before 50 ms and P15V starts at 0.298 V.
"""
import sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools"))
from csdf import read_csdf  # noqa: E402

CSD = ROOT / "sim-runs" / "P31_powerup" / "P31_powerup.csd"
F0 = 518.0
T0 = 1.0 / F0
T_END = 0.3
T5 = 50e-3
DT = 1e-6
ESD = {"EBP": ("V(KEBP)", "V(P15V)"), "ED1": ("V(KED1)", "V(P15V)"), "ED2": ("V(KED2)", "V(P15V)"),
       "EX": ("V(KEX)", "V(P15V)"), "EY": ("V(KEY)", "V(P15V)"), "EBN": ("V(KEBN)", "V(BPF_OUT)"),
       "EN1": ("V(KEN1)", "V(D1)"), "EN2": ("V(KEN2)", "V(D2)"), "ENX": ("V(KENX)", "V(REF_X)"),
       "ENY": ("V(KENY)", "V(REF_Y)")}
REF = {"EBP": "BPF_OUT", "ED1": "D1", "ED2": "D2", "EX": "REF_X", "EY": "REF_Y"}
# diode (anode, cathode node) of each stand-in
DIODE = {"EBP": ("V(BPF_OUT)", "V(KEBP)"), "ED1": ("V(D1)", "V(KED1)"), "ED2": ("V(D2)", "V(KED2)"),
         "EX": ("V(REF_X)", "V(KEX)"), "EY": ("V(REF_Y)", "V(KEY)"), "EBN": ("V(M15V)", "V(KEBN)"),
         "EN1": ("V(M15V)", "V(KEN1)"), "EN2": ("V(M15V)", "V(KEN2)"), "ENX": ("V(M15V)", "V(KENX)"),
         "ENY": ("V(M15V)", "V(KENY)")}


def get(s, n):
    for c in (n, n.replace("V(", "V([").replace(")", "])")):
        try:
            return np.asarray(s[c], dtype=float)
        except Exception:
            pass
    raise KeyError(n)


def main():
    secs = read_csdf(str(CSD))
    for s in secs:
        tramp = s.step_value
        tr = np.asarray(s.x, dtype=float)
        t = np.arange(0.0, T_END + DT / 2, DT)
        ev = lambda n: np.interp(t, tr, get(s, n))
        P15 = ev("V(P15V)")
        t_up = t[np.argmax(P15 >= 5.0)]
        t_ramp = T5 + tramp
        last = t >= T_END - 20 * T0
        print(f"\n=== tramp {tramp * 1e3:.0f} ms: P15V reaches 5 V at {t_up * 1e3:.3f} ms, J5 ramp end {t_ramp * 1e3:.1f} ms")
        print(f"{'stand-in':8s} {'peak before t_up (uA)':>22s} {'peak after t_up (uA)':>21s} {'DC, last 20 periods (nA)':>26s}")
        raw = lambda n: get(s, n)
        P15r = raw("V(P15V)")
        t_up_r = tr[np.argmax(P15r >= 5.0)]
        for k, (a, b) in ESD.items():
            i = raw(a) - raw(b)
            pre = np.max(np.abs(i[tr < t_up_r]))
            post = np.max(np.abs(i[tr >= t_up_r]))
            dc = np.mean(ev(a)[last] - ev(b)[last])
            print(f"{k:8s} {pre * 1e6:22.3f} {post * 1e6:21.3f} {dc * 1e9:26.4f}")
        print("forward-bias check (raw points): largest diode voltage before and after t_up")
        for k, (a, c) in DIODE.items():
            vd = raw(a) - raw(c)
            print(f"  {k:4s} before {np.max(vd[tr < t_up_r]):+8.4f} V, after {np.max(vd[tr >= t_up_r]):+8.4f} V")
        b_pre = raw("V(BPF_OUT)")[tr < T5]
        print(f"BPF_OUT before 50 ms: {b_pre.min():+.4f} V to {b_pre.max():+.4f} V, "
              f"P5VA max before 50 ms {np.max(raw('V(P5VA)')[tr < T5]):.4f} V, P15V(0) {P15r[0]:.4f} V")
        # start-up conduction: forward current into the rail while it is below 5 V
        pre = t < t_up
        print("start-up conduction (t < t_up): forward current above 1 mA, duration and charge into the rail")
        for k in ("EBP", "ED1", "ED2", "EX", "EY"):
            a, b = ESD[k]
            i = ev(a) - ev(b)
            hi = pre & (i > 1e-3)
            dur = np.sum(hi) * DT
            ir = raw(a) - raw(b)
            pr = tr < t_up_r
            q = np.trapezoid(ir[pr], tr[pr])
            q10 = np.trapezoid(ir[tr < 10e-3], tr[tr < 10e-3])
            kp = np.argmax(np.where(pr, ir, -np.inf))
            print(f"  {k:4s} duration above 1 mA {dur * 1e3:8.3f} ms, charge before t_up {q * 1e6:10.3f} uC, "
                  f"before 10 ms {q10 * 1e6:10.3f} uC, peak {ir[kp]:8.4f} A at {tr[kp] * 1e9:8.1f} ns")
        p10 = np.interp(10e-3, tr, P15r)
        print(f"P15V(10 ms) {p10:.4f} V, 11.1 uF x (P15V(10 ms) - P15V(0)) = {11.1e-6 * (p10 - P15r[0]) * 1e6:.3f} uC")
        # reference drive while the rail is still low
        ref_high = max(np.max(ev("V(REF_X)")[t < t_up]), np.max(ev("V(REF_Y)")[t < t_up]))
        print(f"reference high level before t_up: {ref_high:.3f} V; P15V at 0 V over [0, {t_up * 1e3:.3f}] ms")
        # time (from the start) during which a positive stand-in conducts more than 1 nA
        cond = np.zeros_like(t, dtype=bool)
        for k in ("EBP", "ED1", "ED2", "EX", "EY"):
            a, b = ESD[k]
            cond |= (ev(a) - ev(b)) > 1e-9
        if cond.any():
            idx = np.where(cond)[0]
            print(f"positive stand-ins above 1 nA: first {t[idx[0]] * 1e6:.3f} us, last {t[idx[-1]] * 1e3:.3f} ms, "
                  f"total {np.sum(cond) * DT * 1e3:.3f} ms")
        # settling of X_OUT, Y_OUT, GATE, VSUP_A (boxcar mean after the ramp)
        for n in ("V(X_OUT)", "V(Y_OUT)", "V(GATE)", "V(VSUP_A)"):
            v = ev(n)
            c = np.zeros_like(v)
            c[1:] = np.cumsum(0.5 * (v[1:] + v[:-1]) * DT)
            box = (np.interp(t, t, c) - np.interp(np.maximum(t - T0, 0.0), t, c)) / T0
            fin = (c[-1] - np.interp(T_END - 20 * T0, t, c)) / (20 * T0)
            dev = box - fin
            m = (t >= t_ramp + 1e-3) & (t <= t_ramp + 0.15)
            d0 = dev[m][0]
            sel = m & (np.sign(dev) == np.sign(d0)) & (np.abs(dev) > 0.02 * abs(d0)) & (np.abs(dev) > 2e-3)
            if sel.sum() > 50:
                sl, _ = np.polyfit(t[sel] - t_ramp, np.log(np.abs(dev[sel])), 1)
                print(f"tau {n:11s} = {-1 / sl * 1e3:8.3f} ms (fit, initial deviation {d0:+.4f} V, final {fin:+.5f} V)")
            else:
                print(f"tau {n:11s} : too few points for a fit")


if __name__ == "__main__":
    main()
