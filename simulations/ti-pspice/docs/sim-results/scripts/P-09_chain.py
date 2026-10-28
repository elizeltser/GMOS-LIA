"""P-09 full chain on a single 5 V rail (circuits/chain_ss.cir).

Reads two runs under sim-runs/:
  P09a_chain  chain_ss.cir, asin = 15 mV, fast settings, .TRAN 0 0.15 0 5u,
              .STEP PARAM p LIST 0 90, bias point on, .IC VX = VY = 2.5 V.
  P09b_cm     circuits/chain_ss_P09b.cir (asin = 0, vdiff = 10 mV),
              .DC LIN PARAM vcm 0 5 0.02.

P09a settled values: time-weighted trapezoid mean over the last 20 whole
periods of 517 Hz (38.685 ms, from 111.315 ms to 150 ms). The mean is taken on
the raw PSpice points with the window ends interpolated. A uniform 0.5 us grid
is printed as a check. The window before (72.63 ms to 111.32 ms) is the
settling check. The settling bias follows the P-08 model (tau = 10 ms, cout =
1 uF, R3 = 10 kOhm).

Stage transfer: a least-squares fit of a DC term and the 1f, 2f, 3f sinusoids
on the 0.5 us grid of the same window gives the complex amplitude of each
node. The ratio of two nodes gives the stage gain and phase.

Ideal values (no bandwidth, no switch delay except the Y reference timing):
  H(f) = 11 V/V x H_HP(f) x H_LP(f), from the Sallen-Key nodal results for
  chain_ss.cir (C1 = C2, R17 feedback, R18 to VREF; C3 to VREF, C4 feedback,
  R21 = R22).
  VX - 2.5 V = -(2A/pi) |H| cos(p + phi)
  VY - 2.5 V = -(2A/pi) |H| cos(p + phi + w tau), tau = 482.6 us
  A = asin = 15 mV (differential sine amplitude), phi = arg H(517 Hz).

Run from the project root:
    python docs/sim-results/scripts/P-09_chain.py
"""

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools"))
from csdf import read_csdf  # noqa: E402

PLOT = ROOT / "docs/sim-results/plots/P-09_chain.png"

F = 517.0
T = 1.0 / F
W = 2 * np.pi * F
NPER = 20
TW = NPER * T
TAU = 10e3 * 1e-6                       # R3 x cout = 10 kOhm x 1 uF
TAU_Y = 482.6e-6                        # Y reference delay in V_SELY
A_IN = 15e-3                            # asin (differential sine amplitude)
VREF = 2.5
GAIN_INA = 11.0
T_END = 0.15

# Stage values of circuits/chain_ss.cir
C1 = C2 = 33e-9
R17, R18 = 4.64e3, 18.7e3
C3, C4 = 33e-9, 130e-9
R21, R22 = 4.64e3, 4.64e3


def h_hp(f):
    s = 1j * 2 * np.pi * f
    return s * s * C1 * C2 / (s * s * C1 * C2 + s * (C1 + C2) / R18 + 1 / (R17 * R18))


def h_lp(f):
    s = 1j * 2 * np.pi * f
    return 1 / (s * s * R21 * R22 * C3 * C4 + s * C3 * (R21 + R22) + 1)


def h_chain(f):
    return GAIN_INA * h_hp(f) * h_lp(f)


def ideal_dc(p_deg, amp=A_IN):
    """Ideal demodulated DC of VX and VY relative to 2.5 V (sine input)."""
    h = h_chain(F)
    phi = np.angle(h)
    mag = abs(h)
    p = np.radians(p_deg)
    vx = -(2 / np.pi) * mag * amp * np.cos(p + phi)
    vy = -(2 / np.pi) * mag * amp * np.cos(p + phi + W * TAU_Y)
    return vx, vy


def tw_mean(t, y, t0, t1):
    """Time-weighted trapezoid mean of raw points, window ends interpolated."""
    inside = (t > t0) & (t < t1)
    tt = np.concatenate([[t0], t[inside], [t1]])
    yy = np.interp(tt, t, y)
    return np.trapezoid(yy, tt) / (t1 - t0)


def grid_mean(t, y, t0, t1, dt=0.5e-6):
    tg = np.arange(t0, t1, dt)
    return np.mean(np.interp(tg, t, y))


def fit_fundamental(t, y, t0, t1, dt=0.5e-6, nharm=3):
    """Least-squares DC plus harmonics on a uniform grid. Returns (dc, Z1)
    where y ~ dc + Re[Z1 exp(j W t)] + harmonics. |Z1| is the amplitude and
    angle(Z1) the phase referenced to cos(W t)."""
    tg = np.arange(t0, t1, dt)
    yg = np.interp(tg, t, y)
    cols = [np.ones_like(tg)]
    for k in range(1, nharm + 1):
        cols.append(np.cos(k * W * tg))
        cols.append(np.sin(k * W * tg))
    M = np.column_stack(cols)
    coef, *_ = np.linalg.lstsq(M, yg, rcond=None)
    a1, b1 = coef[1], coef[2]
    return coef[0], a1 - 1j * b1


def load(name):
    return read_csdf(str(ROOT / f"sim-runs/{name}/{name}.csd"))


def section_for(secs, step):
    for s in secs:
        if s.step_value is not None and abs(s.step_value - step) < 1e-9:
            return s
    raise KeyError(step)


def main():
    t1 = T_END
    t0 = t1 - TW
    tp0 = t0 - TW
    lines = []
    lines.append(f"Window: {t0*1e3:.4f} ms to {t1*1e3:.4f} ms ({TW*1e3:.4f} ms = {NPER} periods)")
    lines.append(f"Prior window: {tp0*1e3:.4f} ms to {t0*1e3:.4f} ms")
    lines.append("")

    p09a = load("P09a_chain")
    results = {}
    for p in (0.0, 90.0):
        s = section_for(p09a, p)
        t = np.asarray(s.x, float)
        data = {}
        for sig in ["V(INP)", "V(INN)", "V(VDIFF)", "V(HPF)", "V(VSAMPLE)", "V(VX)", "V(VY)"]:
            y = np.asarray(s[sig], float)
            data[sig] = dict(
                m=tw_mean(t, y, t0, t1),
                mp=tw_mean(t, y, tp0, t0),
                mg=grid_mean(t, y, t0, t1),
                z1=fit_fundamental(t, y, t0, t1)[1],
                y=y,
            )
        results[p] = (t, data)
        lines.append(f"== P09a p = {p:g} deg (section step {s.step_value:g})")
        lines.append("| Node | TW mean (V) | Prior window (V) | Last minus prior (uV) | Grid mean (V) | Grid minus TW (uV) |")
        lines.append("|---|---|---|---|---|---|")
        for sig, d in data.items():
            lines.append(
                f"| {sig} | {d['m']:.7f} | {d['mp']:.7f} | {(d['m']-d['mp'])*1e6:.2f} "
                f"| {d['mg']:.7f} | {(d['mg']-d['m'])*1e6:.3f} |"
            )
        lines.append("")

    # Settling check: window difference and bias from the first-order model
    lines.append("== Settling check (tau = 10 ms)")
    lines.append("| p (deg) | Node | Last minus prior (uV) | B from data (uV) | B from model (uV) | Settled value (V) |")
    lines.append("|---|---|---|---|---|---|")
    f_model = (TAU / TW) * (1 - np.exp(-TW / TAU)) * np.exp(-t0 / TAU)
    for p in (0.0, 90.0):
        _, data = results[p]
        for sig in ["V(VX)", "V(VY)", "V(VSAMPLE)", "V(HPF)", "V(VDIFF)"]:
            d = data[sig]
            diff = d["m"] - d["mp"]
            b_data = diff / (1 - np.exp(TW / TAU))
            if sig in ("V(VX)", "V(VY)"):
                b_model = (VREF - d["m"]) * f_model
            else:
                b_model = 0.0
            vss = d["m"] - b_data
            lines.append(
                f"| {p:g} | {sig} | {diff*1e6:.2f} | {b_data*1e6:.3f} | {b_model*1e6:.3f} | {vss:.7f} |"
            )
    lines.append(f"Model factor F = {f_model:.4e}")
    lines.append("")

    # Stage fits at p = 0 (the input is the differential INP - INN)
    _, d0 = results[0.0]
    z_in = d0["V(INP)"]["z1"] - d0["V(INN)"]["z1"]
    lines.append("== Stage fits at 517 Hz (p = 0 deg, 1f fundamental, 3 harmonics fitted)")
    lines.append("| Stage | Measured abs (V/V) | Measured phase (deg) | Ideal abs (V/V) | Ideal phase (deg) |")
    lines.append("|---|---|---|---|---|")
    lines.append(f"| Input INP - INN amplitude (mV) | {abs(z_in)*1e3:.5f} | {np.degrees(np.angle(z_in)):.3f} | {A_IN*1e3:.5f} | ref |")
    stage_rows = [
        ("VDIFF / (INP - INN)", d0["V(VDIFF)"]["z1"] / z_in, GAIN_INA, 0.0),
        ("HPF / VDIFF", d0["V(HPF)"]["z1"] / d0["V(VDIFF)"]["z1"], abs(h_hp(F)), np.degrees(np.angle(h_hp(F)))),
        ("VSAMPLE / HPF", d0["V(VSAMPLE)"]["z1"] / d0["V(HPF)"]["z1"], abs(h_lp(F)), np.degrees(np.angle(h_lp(F)))),
        ("VSAMPLE / (INP - INN), total", d0["V(VSAMPLE)"]["z1"] / z_in, abs(h_chain(F)), np.degrees(np.angle(h_chain(F)))),
    ]
    for name, g, ia, ip in stage_rows:
        lines.append(f"| {name} | {abs(g):.6f} | {np.degrees(np.angle(g)):.3f} | {ia:.6f} | {ip:.3f} |")
    lines.append("")
    phi_meas = np.degrees(np.angle(d0["V(VSAMPLE)"]["z1"] / z_in))

    # Demodulator outputs against the ideal
    lines.append("== Demodulator outputs (TW means, relative to 2.5 V)")
    lines.append("| p (deg) | VX meas (mV) | VX ideal (mV) | VX diff (mV) | VY meas (mV) | VY ideal (mV) | VY diff (mV) | R meas (mV) | R ideal (mV) | R diff (%) |")
    lines.append("|---|---|---|---|---|---|---|---|---|---|")
    summary = {}
    for p in (0.0, 90.0):
        _, d = results[p]
        vx = d["V(VX)"]["m"] - VREF
        vy = d["V(VY)"]["m"] - VREF
        vxi, vyi = ideal_dc(p)
        r = np.hypot(vx, vy)
        ri = np.hypot(vxi, vyi)
        summary[p] = dict(vx=vx, vy=vy, vxi=vxi, vyi=vyi, r=r, ri=ri)
        lines.append(
            f"| {p:g} | {vx*1e3:.4f} | {vxi*1e3:.4f} | {(vx-vxi)*1e3:+.4f} | {vy*1e3:.4f} "
            f"| {vyi*1e3:.4f} | {(vy-vyi)*1e3:+.4f} | {r*1e3:.4f} | {ri*1e3:.4f} | {100*(r-ri)/ri:+.3f} |"
        )
    lines.append("")
    s0, s90 = summary[0.0], summary[90.0]
    R_meas = s0["r"]
    phi_x = np.degrees(np.arcsin(np.clip(s90["vx"] / R_meas, -1, 1)))
    phi_y = np.degrees(np.arcsin(np.clip(s0["vy"] / R_meas, -1, 1))) + 90.0 - np.degrees(W * TAU_Y)
    lines.append(
        f"Front-end phase from VX at p = 90 deg: {phi_x:.3f} deg. From VY at p = 0 deg, "
        f"after the Y timing term: {phi_y:.3f} deg. From the VSAMPLE fit: {phi_meas:.3f} deg. "
        f"Ideal: {np.degrees(np.angle(h_chain(F))):.3f} deg."
    )
    lines.append("")

    # Full-run means (no settled window), to trace the value 2.402 V quoted by the dispatcher
    t0p, d0p = results[0.0]
    yvx = d0p["V(VX)"]["y"]
    lines.append(
        f"Full run (0 to 150 ms) VX at p = 0 deg: point mean {np.mean(yvx):.6f} V, "
        f"time-weighted mean {tw_mean(t0p, yvx, 0.0, T_END):.6f} V."
    )
    lines.append("")

    # Duty and switch-delay terms on the VSAMPLE DC offset (quirk, -0.103 and -0.048 mV/V)
    for p in (0.0, 90.0):
        _, d = results[p]
        off_v = d["V(VSAMPLE)"]["m"] - VREF
        term_mv = (-0.103 - 0.048) * off_v
        lines.append(
            f"VSAMPLE DC offset at p = {p:g} deg: {off_v*1e6:.3f} uV. "
            f"Duty and switch-delay term: {term_mv*1e3:.6f} uV."
        )
    lines.append("")

    # P09b common-mode sweep
    p09b = load("P09b_cm")
    s = p09b[0]
    x = np.asarray(s.x, float)
    y = np.asarray(s["V(VDIFF)"], float)
    target = VREF + GAIN_INA * 10e-3
    y_mid = np.interp(2.5, x, y)
    ok = np.abs(y - target) <= 1e-3
    i0 = int(np.argmin(np.abs(x - 2.5)))
    lo = i0
    while lo > 0 and ok[lo - 1]:
        lo -= 1
    hi = i0
    while hi < len(x) - 1 and ok[hi + 1]:
        hi += 1
    lines.append("== P09b common-mode sweep (vdiff = 10 mV, asin = 0, 0.02 V steps)")
    lines.append(f"VDIFF at vcm = 2.5 V: {y_mid:.6f} V. Target 2.5 V + 110 mV = {target:.6f} V.")
    lines.append(
        f"VDIFF within 1 mV of the target: vcm {x[lo]:.2f} V to {x[hi]:.2f} V "
        f"(grid points, the true edges lie within one step outside)."
    )
    lines.append("")
    lines.append("| vcm (V) | VDIFF (V) | VDIFF minus target (mV) |")
    lines.append("|---|---|---|")
    for v in [0.0, 1.5, 1.9, 2.0, 2.02, 2.04, 2.06, 2.08, 2.1, 2.5, 2.9, 2.92, 2.94, 2.96, 2.98, 3.0, 3.1, 3.5, 5.0]:
        yv = np.interp(v, x, y)
        lines.append(f"| {v:.2f} | {yv:.6f} | {(yv-target)*1e3:+.4f} |")
    lines.append("")

    text = "\n".join(lines)
    print(text)

    fig, ax = plt.subplots(2, 1, figsize=(7, 7))
    t, d = results[0.0]
    ax[0].plot(t * 1e3, d["V(VX)"]["y"], label="VX, p = 0 deg")
    ax[0].plot(t * 1e3, d["V(VY)"]["y"], label="VY, p = 0 deg")
    ax[0].axhline(VREF + summary[0.0]["vxi"], color="k", ls=":", lw=0.8, label="ideal VX")
    ax[0].set_xlabel("time (ms)")
    ax[0].set_ylabel("V (V)")
    ax[0].legend(fontsize=7)
    ax[0].set_title("P09a, full run (p = 0 deg)")
    ax[1].plot(x, y, label="VDIFF")
    ax[1].axhline(target, color="k", ls=":", lw=0.8)
    ax[1].set_xlabel("vcm (V)")
    ax[1].set_ylabel("VDIFF (V)")
    ax[1].set_title("P09b, VDIFF against common mode")
    fig.tight_layout()
    fig.savefig(PLOT, dpi=120)


if __name__ == "__main__":
    main()
