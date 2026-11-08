"""P-33a and P-33b: heater driver headroom, HSENSE clipping and step response (LIA-AFE-Eval).

Run from simulations/ti-pspice:  python docs/sim-results/scripts/P-33_heater.py
Reads sim-runs/P33a_r300, P33a_r600, P33a_r1200 (.DC PARAM vh_a 0 to 2.3 V, 0.05 V steps)
and sim-runs/P33b_step (.TRAN 0 2m 0 50n, DAC1 step 1.5 V to 1.6 V at 0.5 ms, chtr = 100 p, 1 n, 10 n).

Conventions
- Heater current I = V(HPIX_A) / rhtr, the current in the heater after the TMUX1109 on-path.
- Ideal feedback gain 2 (49.9 k / 49.9 k): the ideal HFB_A is 2 x vh_a.
- HSENSE_B is the INA190 stand-in: 25 x (V(HSH_A) - V(HFB_A)) = 25 x 15 Ohm x I, clipped to 0 to 3.3 V.
- Pass tolerance for P-33a: |HFB_A - 2 vh_a| <= 1 mV. The limit is the last point before the first violation.
- P-33b: step height from the mean of 0.2 ms to 0.5 ms (before the step) to the mean of the last 0.2 ms.
  Overshoot = (peak - final) / step x 100 %. Ringing frequency from the mean period of the residual peaks.
"""
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools"))
from csdf import read_csdf  # noqa: E402

RUNS = {300: "P33a_r300", 600: "P33a_r600", 1200: "P33a_r1200"}
TOL = 1e-3
SENSE_CLIP = 3.3


def p33a():
    print("P-33a: DC sweep of vh_a")
    print("rhtr_Ohm  vh_lim_V  HFB_lim_V  I_lim_mA  margin_lim_V  HFB_end_V  I_end_mA  margin_end_V  HSENSE_end_V  vh_clip_V  I_clip_mA  tol_violated")
    for rhtr, name in RUNS.items():
        sec = read_csdf(ROOT / "sim-runs" / name / f"{name}.csd")[0]
        vh = sec.x
        hsh, hfb = sec["V(HSH_A)"], sec["V(HFB_A)"]
        hsense, p5 = sec["V(HSENSE_B)"], sec["V(P5VP)"]
        hpix = sec["V(HPIX_A)"]
        err = np.abs(hfb - 2 * vh)
        bad = np.where(err > TOL)[0]
        k = (bad[0] - 1) if bad.size else len(vh) - 1
        cur = hpix / rhtr
        margin = p5 - hsh
        clip = np.where(hsense >= SENSE_CLIP - 1e-3)[0]
        vh_clip = vh[clip[0]] if clip.size else float("nan")
        i_clip = cur[clip[0]] * 1e3 if clip.size else float("nan")
        viol = f"yes, first at vh_a = {vh[bad[0]]:.3f} V" if bad.size else "no"
        print(f"{rhtr:8d}  {vh[k]:8.3f}  {hfb[k]:9.4f}  {cur[k]*1e3:8.3f}  {margin[k]:12.4f}  {hfb[-1]:9.4f}  "
              f"{cur[-1]*1e3:8.3f}  {margin[-1]:12.4f}  {hsense[-1]:12.4f}  {vh_clip:9.3f}  {i_clip:9.3f}  {viol}")
        print(f"   P5VP = {p5[-1]:.4f} V; min margin P5VP - HSH_A over the sweep = {margin.min():.4f} V; "
              f"max HSENSE_B = {hsense.max():.4f} V")


def p33b():
    print("P-33b: step response of HFB_A, DAC1 1.5 V to 1.6 V at 0.5 ms")
    for s in read_csdf(ROOT / "sim-runs" / "P33b_step" / "P33b_step.csd"):
        t = s.x
        hfb = s["V(HFB_A)"]
        pre = hfb[(t > 0.2e-3) & (t < 0.5e-3)].mean()
        post = hfb[t > 1.8e-3].mean()
        step = post - pre
        after = t > 0.5e-3
        peak_idx = int(np.argmax(np.where(after, hfb, -np.inf)))
        peak = hfb[peak_idx]
        overshoot = (peak - post) / step * 100
        res = hfb[peak_idx:] - post
        tr = t[peak_idx:]
        # Extrema of both signs (overshoot peak included) larger than 0.1 % of the step.
        ext = [0] + [i for i in range(1, len(res) - 1)
                     if (res[i] - res[i - 1]) * (res[i + 1] - res[i]) < 0 and abs(res[i]) > 1e-3 * abs(step)]
        if len(ext) >= 3:
            half = np.diff(tr[ext[:4]]).mean()  # first four extrema (small late extrema are irregular)
            pct = ", ".join(f"{res[i] / step * 100:+.2f}" for i in ext[:5])
            ring = f"{1 / (2 * half) / 1e3:.1f} kHz from {len(ext)} extrema above 0.1 % (first: {pct} % of the step)"
        elif len(ext) == 2:
            ring = f"one undershoot of {res[ext[1]] / step * 100:+.2f} % of the step, no further extremum above 0.1 %"
        else:
            ring = "no extremum above 0.1 % of the step after the overshoot peak"
        out = np.where(np.abs(hfb - post) > 0.01 * abs(step))[0]
        t_settle = (t[out[-1]] - 0.5e-3) * 1e6 if out.size else 0.0
        print(f"  chtr = {s.step_value*1e9:g} nF: step {step*1e3:.3f} mV (ideal 200 mV), peak {peak:.6f} V "
              f"at {t[peak_idx]*1e3:.4f} ms, overshoot {overshoot:.4f} %, "
              f"last 1 % settling {t_settle:.2f} us after the step, ringing: {ring}")


def swing_model(i_ma):
    """Output swing of the OPAx196 model below V+ (TI model fit, not checked against the datasheet).

    Needed headroom (V) = 10.9 mV + 40.8 mV/mA x I_out. Source: the CLAWP_OPAx196 subcircuit of
    OPAx196.LIB in C:\\cds_spb_home\\cdssetup\\pspTILibDir (via R72 = 1 kOhm). The short-circuit
    limits are +70.2 mA and -65 mA, so they are not the limit at 14 mA.
    """
    return 0.0109 + 0.0408 * i_ma


def headroom():
    """Needed and net headroom of U9A for the three heaters, and the HFB_A ceiling from the swing curve."""
    print("P-33a headroom of U9A (available = P5VP - HSH_A, needed = 10.9 mV + 40.8 mV/mA x I_out)")
    print("rhtr_Ohm  point      HFB_V  Iout_mA  P5VP_V  HSH_V   avail_V  needed_V  net_V   HFB_ceiling_V")
    for rhtr, name in RUNS.items():
        sec = read_csdf(ROOT / "sim-runs" / name / f"{name}.csd")[0]
        vh = sec.x
        hfb, hsh, p5 = sec["V(HFB_A)"], sec["V(HSH_A)"], sec["V(P5VP)"]
        hpix = sec["V(HPIX_A)"]
        # Load seen at HFB_A: heater plus TMUX1109 on-resistance (4.5 Ohm), in parallel with R20 + R22 (99.8 kOhm).
        r_eff = 1 / (1 / (rhtr + RONH) + 1 / R_FB)
        ceil = (p5[-1] - 0.0109) / (1 + (15 + 40.8) / r_eff)
        for label, i in (("AN-14 4.0", int(np.argmin(abs(hfb - 4.0)))), ("end 2.3 V", len(vh) - 1)):
            ima = (hsh[i] - hfb[i]) / 15 * 1e3  # U9A output current = shunt current (heater + feedback divider)
            avail = p5[i] - hsh[i]
            need = swing_model(ima)
            print(f"{rhtr:8d}  {label:9s} {hfb[i]:6.3f} {ima:6.3f} {p5[i]:7.4f} {hsh[i]:7.4f} {avail:8.4f} "
                  f"{need:8.4f} {avail-need:8.4f} {ceil:12.4f}")
    print("net headroom near 0 means the output stage sits on the swing curve (saturation)")


RONH = 4.5
R_FB = 99.8e3


def settling_check():
    """HFB_A error at the sweep points for the 600 Ohm heater, and VSUP_A offset against 1.1 vdrc_a - 7.5 mV."""
    for rhtr, name in RUNS.items():
        sec = read_csdf(ROOT / "sim-runs" / name / f"{name}.csd")[0]
        vh = sec.x
        err = sec["V(HFB_A)"] - 2 * vh
        m = (vh >= 0.5) & (vh <= 2.0)
        print(f"{rhtr} Ohm HFB_A - 2 vh_a over vh_a 0.5 to 2.0 V: min {err[m].min()*1e3:.4f} mV, "
              f"max {err[m].max()*1e3:.4f} mV (2 x 13.6 uV input offset = 0.0272 mV)")
    sec = read_csdf(ROOT / "sim-runs" / "P33c_vdrc" / "P33c_vdrc.csd")[0]
    x = sec.x
    off = sec["V(VSUP_A)"] - (1.1 * x - 7.5e-3)
    w = (x >= 0.46 - 1e-9) & (x <= 3.19 + 1e-9)
    print(f"P33c VSUP_A - (1.1 vdrc_a - 7.5 mV) over the window: min {off[w].min()*1e6:.1f} uV, "
          f"max {off[w].max()*1e6:.1f} uV")


if __name__ == "__main__":
    p33a()
    p33b()
    headroom()
    settling_check()
