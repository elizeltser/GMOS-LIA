"""P-31 power-up with the +/-15 V input first (LIA-AFE-Eval, SIM-18).

Run from simulations/ti-pspice:  python docs/sim-results/scripts/P-31_powerup.py
Reads sim-runs/P31_powerup/P31_powerup.csd (circuit circuits/afe_eval_P31.cir, tramp = 1, 5, 20 ms).
The ESD stand-in current is the voltage across its 1 Ohm series resistor, so no diode current is probed.

Conventions
- Resampled to a uniform 1 us grid (linear interpolation of the adaptive solver points).
- Window means use the cumulative trapezoid integral, so a window of n whole periods is exact.
- Final value: mean over the last 20 whole periods (38.61 ms at 518 Hz) of the run, which ends at 0.3 s.
- Settling: the one-period boxcar mean of X_OUT and Y_OUT (removes the 2f0 ripple). The settling time is the
  last time at which the boxcar mean differs from the final value by more than 1 mV.
- ESD stand-in current: maximum of |I| over the whole run for each stand-in, from the raw solver points.
- Rail check: distance of each op-amp node to the rails P5VA and M5VA after the J5 ramp.
- Drain-bias time constant: exponential fit of the boxcar mean of VSUP_A after the J5 ramp.
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
T15 = 10e-3
N_WIN = 20
DT = 1e-6
SETTLE_LIMIT = 1e-3       # V
ESD_LIMIT = 1e-9          # A
P27_X = -244.9893e-3      # V, P-27 pexc = 0 (P-27.md)
P27_Y = -55.9785e-3       # V
RAIL_MARGIN = 0.5         # V, distance from a rail that counts as stuck

# Stand-in current = voltage across its 1 Ohm series resistor: (K node - other node) / 1 Ohm.
ESD = {"EBP": ("V(KEBP)", "V(P15V)"), "EBN": ("V(KEBN)", "V(BPF_OUT)"),
       "ED1": ("V(KED1)", "V(P15V)"), "EN1": ("V(KEN1)", "V(D1)"),
       "ED2": ("V(KED2)", "V(P15V)"), "EN2": ("V(KEN2)", "V(D2)"),
       "EX": ("V(KEX)", "V(P15V)"), "ENX": ("V(KENX)", "V(REF_X)"),
       "EY": ("V(KEY)", "V(P15V)"), "ENY": ("V(KENY)", "V(REF_Y)")}
ESD_NAMES = list(ESD)
NODES = ["V(P15V)", "V(M15V)", "V(P5VA)", "V(M5VA)", "V(BPF_OUT)", "V(X_OUT)", "V(Y_OUT)", "V(GATE)", "V(VSUP_A)",
         "V(D1)", "V(D2)", "V(REF_X)", "V(REF_Y)"]


def get(section, name):
    """Return a signal by name, accepting the bracket form and the plain form."""
    for cand in (name, name.replace("V(", "V([").replace(")", "])") if name.startswith("V(") else name):
        try:
            return np.asarray(section[cand], dtype=float)
        except Exception:
            pass
    raise KeyError(name)


def cum_trapz(t, y):
    c = np.zeros_like(y)
    c[1:] = np.cumsum(0.5 * (y[1:] + y[:-1]) * np.diff(t))
    return c


def at(t, c, tq):
    return np.interp(tq, t, c)


def analyse(section, tramp):
    t_raw = np.asarray(section.x, dtype=float)
    grid = np.arange(0.0, T_END + DT / 2, DT)
    sig = {n: np.interp(grid, t_raw, get(section, n)) for n in NODES}
    for k, (a, b) in ESD.items():
        sig["I_" + k] = (np.interp(grid, t_raw, get(section, a)) - np.interp(grid, t_raw, get(section, b))) / 1.0
    t = grid
    t_ramp_end = T5 + tramp
    out = {"tramp": tramp, "t_ramp_end": t_ramp_end}

    # (1) ESD stand-ins over the whole run
    # peaks from the raw solver points: the 1 us grid misses the 10 ns reference edges (judge correction)
    esd_peak = {}
    for k in ESD_NAMES:
        a, b = ESD[k]
        ir = get(section, a) - get(section, b)
        i = np.argmax(np.abs(ir))
        esd_peak[k] = (abs(ir[i]), t_raw[i])
    worst = max(esd_peak.items(), key=lambda kv: kv[1][0])
    out["esd_peak"] = esd_peak
    out["esd_worst"] = worst

    # (2) final values and settling of X_OUT and Y_OUT
    res = {}
    for n in ("V(X_OUT)", "V(Y_OUT)"):
        cum = cum_trapz(t, sig[n])
        T_WIN = N_WIN * T0
        final = (at(t, cum, T_END) - at(t, cum, T_END - T_WIN)) / T_WIN
        Tb = T0
        box = (at(t, cum, t) - at(t, cum, np.maximum(t - Tb, 0.0))) / Tb
        mask = (t >= t_ramp_end) & (t <= T_END)
        dev = np.abs(box - final)
        over = np.where(mask & (dev > SETTLE_LIMIT))[0]
        t_last = t[over[-1]] if over.size else t_ramp_end
        res[n] = {"final": final, "t_settle": t_last, "after_ramp": t_last - t_ramp_end,
                  "max_dev_after_ramp": dev[mask].max() if mask.any() else np.nan,
                  "pp_ripple_last": np.ptp(sig[n][(t >= T_END - 5 * T0) & (t <= T_END)])}
    out["xy"] = res

    # (3) rails: op-amp nodes after the ramp and at the end of the run
    rail_p = sig["V(P5VA)"]
    rail_m = sig["V(M5VA)"]
    rails = {}
    for n in ("V(BPF_OUT)", "V(X_OUT)", "V(Y_OUT)", "V(GATE)", "V(VSUP_A)"):
        m = (t >= t_ramp_end) & (t <= T_END)
        v = sig[n]
        d_pos = np.min(rail_p[m] - v[m])
        d_neg = np.min(v[m] - rail_m[m])
        rails[n] = {"min_dist_pos": d_pos, "min_dist_neg": d_neg,
                    "stuck": (d_pos < RAIL_MARGIN) or (d_neg < RAIL_MARGIN),
                    "end_value": v[-1], "range_after_ramp": (v[m].min(), v[m].max())}
    out["rails"] = rails
    out["rail_end"] = (rail_p[-1], rail_m[-1])

    # (4) time constant of VSUP_A after the ramp (fit of the boxcar mean)
    cum = cum_trapz(t, sig["V(VSUP_A)"])
    box = (at(t, cum, t) - at(t, cum, np.maximum(t - T0, 0.0))) / T0
    vf = (at(t, cum, T_END) - at(t, cum, T_END - N_WIN * T0)) / (N_WIN * T0)
    m = (t >= t_ramp_end + 2e-3) & (t <= t_ramp_end + 0.15)
    dev = box[m] - vf
    tt = t[m] - t_ramp_end
    sel = np.abs(dev) > 1e-4 * np.abs(dev).max()
    sel &= np.sign(dev) == np.sign(dev[np.argmax(np.abs(dev))])
    slope, icpt = np.polyfit(tt[sel], np.log(np.abs(dev[sel])), 1)
    out["tau_vsup"] = -1.0 / slope
    out["vsup_final"] = vf
    return out


def main():
    sections = read_csdf(str(CSD))
    print(f"sections: {len(sections)}")
    for s in sections:
        tramp = s.step_value
        r = analyse(s, tramp)
        print(f"\n=== tramp = {tramp * 1e3:.1f} ms, J5 ramp end = {r['t_ramp_end'] * 1e3:.1f} ms ===")
        wname, (w, tw) = r["esd_worst"]
        print(f"ESD peak |I| = {w * 1e9:.4f} nA ({wname}) at {tw * 1e3:.3f} ms; pass < 1 nA: {w < ESD_LIMIT}")
        for n, v in r["esd_peak"].items():
            print(f"   {n:6s} {v[0] * 1e9:10.5f} nA at {v[1] * 1e3:9.3f} ms")
        for n in ("V(X_OUT)", "V(Y_OUT)"):
            x = r["xy"][n]
            print(f"{n}: final {x['final'] * 1e3:.4f} mV, settled within 1 mV from {x['t_settle'] * 1e3:.3f} ms, "
                  f"{x['after_ramp'] * 1e3:.2f} ms after the ramp end, ripple pp (5 periods) {x['pp_ripple_last'] * 1e3:.3f} mV")
        print(f"   vs P-27 (pexc = 0): X diff {(r['xy']['V(X_OUT)']['final'] - P27_X) * 1e3:+.5f} mV, "
              f"Y diff {(r['xy']['V(Y_OUT)']['final'] - P27_Y) * 1e3:+.5f} mV")
        for n, v in r["rails"].items():
            print(f"{n:12s} stuck={v['stuck']!s:5s} min dist +rail {v['min_dist_pos']:.3f} V, "
                  f"-rail {v['min_dist_neg']:.3f} V, end {v['end_value']:.4f} V, range {v['range_after_ramp'][0]:.4f} to {v['range_after_ramp'][1]:.4f} V")
        print(f"rails at end: P5VA {r['rail_end'][0]:.4f} V, M5VA {r['rail_end'][1]:.4f} V")
        print(f"VSUP_A final {r['vsup_final']:.5f} V, fitted tau after the ramp {r['tau_vsup'] * 1e3:.3f} ms")


if __name__ == "__main__":
    main()
