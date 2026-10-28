"""P-02 input phase sweep analysis for the LIA baseline circuit.

The first run parses the 207 MB CSDF file once and caches the per-step
numbers to sim-runs/P02_phase/P02_steps.csv. Later runs read only that CSV.
The script then computes the settled values, the settling check and the
settling-bias correction, fits the cos and sin terms over the phase, checks
the pass limits, tests a slew-delay model and writes three plots.

Run from the project root:
    python docs/sim-results/scripts/P-02_phase.py
    python docs/sim-results/scripts/P-02_phase.py --rebuild   (re-parse the .csd)
"""

import math
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools"))
from csdf import read_csdf  # noqa: E402

CSD = ROOT / "sim-runs/P02_phase/P02_phase.csd"
CACHE = ROOT / "sim-runs/P02_phase/P02_steps.csv"
PLOT_DIR = ROOT / "docs/sim-results/plots"

F_OSC = 517.0              # Hz, input and reference frequency
T = 1.0 / F_OSC            # s, period
N_PER = 50                 # periods in the averaging window
DT_GRID = 1e-6             # s, grid spacing (as in P-01)
T_END = 1.0                # s, run length
VDC = 5.0                  # V, supply
AMP = 2.0                  # V, input amplitude
TD_Y = 482.6e-6            # s, delay of the Y reference
K = 2.0 * AMP / math.pi    # V, theory radius R = 2A/pi
MID = 2.5                  # V, signal midpoint
D_DEG = 360.0 * (T / 4.0 - TD_Y) / T   # deg, theory Y timing error d
OMEGA = 2.0 * math.pi * F_OSC
SETTLE_K = 0.097e-3 / 1.27  # V/V, bias of the last-50-period mean (P-01), per V of |V - 2.5|
T_RAMP = 100e-9            # s, reference ramp time
SR_OPAMP = 20.19e6         # V/s, slew of the demodulator output (P-01 edge run)
STEP_Y = 4.0               # V, demodulator step at the Y edges at p = 0 (P-01)

COLS = ["p_deg", "vx_last", "vy_last", "vx_prev", "vy_prev",
        "vx_pp_mV", "vy_pp_mV", "vx_2f_mV", "vy_2f_mV", "vx_t0", "vy_t0", "n_points"]


def trap_mean(t, y):
    return float(np.sum(0.5 * (y[1:] + y[:-1]) * np.diff(t)) / (t[-1] - t[0]))


def window(t_raw, y_raw, t_start, t_stop):
    """Interpolate onto a grid of 1 us spacing over [t_start, t_stop]; return grid, values, mean."""
    n = round((t_stop - t_start) / DT_GRID) + 1
    grid = np.linspace(t_start, t_stop, n)
    yg = np.interp(grid, t_raw, y_raw)
    return grid, yg, trap_mean(grid, yg)


def amp_at(grid, y, f, k):
    """Amplitude of the k-th harmonic of f in y, least squares on the grid."""
    cols = [np.ones_like(grid)]
    for kk in (k,):
        cols.append(np.sin(2 * np.pi * kk * f * grid))
        cols.append(np.cos(2 * np.pi * kk * f * grid))
    coef, *_ = np.linalg.lstsq(np.column_stack(cols), y, rcond=None)
    return float(np.hypot(coef[1], coef[2]))


def build_cache():
    """Parse the .csd once and write one row per step."""
    rows = []
    sections = read_csdf(str(CSD))
    for s in sections:
        t = s.x
        assert abs(t[-1] - T_END) < 1e-12, f"step ends at {t[-1]}"
        vx, vy = s["V(VX)"], s["V(VY)"]
        t1 = T_END - N_PER * T
        t0 = T_END - 2 * N_PER * T
        grid, vx1, mvx1 = window(t, vx, t1, T_END)
        _, vy1, mvy1 = window(t, vy, t1, T_END)
        _, _, mvx0 = window(t, vx, t0, t1)
        _, _, mvy0 = window(t, vy, t0, t1)
        rows.append([
            s.step_value, mvx1, mvy1, mvx0, mvy0,
            (vx1.max() - vx1.min()) * 1e3, (vy1.max() - vy1.min()) * 1e3,
            amp_at(grid, vx1, F_OSC, 2) * 1e3, amp_at(grid, vy1, F_OSC, 2) * 1e3,
            float(vx[0]), float(vy[0]), len(t),
        ])
    arr = np.array(rows)
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    np.savetxt(CACHE, arr, delimiter=",", header=",".join(COLS), comments="",
               fmt="%.10g")
    print(f"parsed {len(rows)} sections, wrote {CACHE}")


def load_cache():
    d = np.genfromtxt(CACHE, delimiter=",", names=True)
    return d[np.argsort(d["p_deg"])]


def wrap180(x):
    return (x + 180.0) % 360.0 - 180.0


def lsq(p_deg, y, extra=None):
    th = np.radians(p_deg)
    cols = [np.ones_like(th), np.cos(th), np.sin(th)]
    if extra is not None:
        cols.append(extra)
    X = np.column_stack(cols)
    coef, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ coef
    rms = float(np.sqrt(np.mean(resid ** 2)))
    return coef, resid, rms


def main():
    if "--rebuild" in sys.argv or not CACHE.exists():
        build_cache()
    d = load_cache()
    p_all = d["p_deg"]
    n_all = len(p_all)

    # Settled values with the P-01 bias correction (toward the final value)
    vx =d["vx_last"] + SETTLE_K * (d["vx_last"] - MID)
    vy = d["vy_last"] + SETTLE_K * (d["vy_last"] - MID)
    dvx_settle = (d["vx_last"] - d["vx_prev"]) * 1e3
    dvy_settle = (d["vy_last"] - d["vy_prev"]) * 1e3
    bias_vx = (vx - d["vx_last"]) * 1e3
    bias_vy = (vy - d["vy_last"]) * 1e3

    # Distinct phases: 360 deg repeats 0 deg, so the fit uses p < 360
    dist = p_all < 359.5
    p = p_all[dist]
    vxf, vyf = vx[dist], vy[dist]

    print(f"Theory: K = 2A/pi = {K:.6f} V, d = {D_DEG:.5f} deg, "
          f"Y timing error = {(T / 4 - TD_Y) * 1e9:.1f} ns")
    print(f"Steps read: {n_all}, distinct phases in fit: {len(p)}")
    print(f"Max |settling bias| applied: VX {np.max(np.abs(bias_vx)):.4f} mV, "
          f"VY {np.max(np.abs(bias_vy)):.4f} mV")
    print(f"Max settling check (raw, last 50 minus previous 50): "
          f"VX {np.max(np.abs(dvx_settle)):.4f} mV, VY {np.max(np.abs(dvy_settle)):.4f} mV")
    print(f"Max ripple p-p (raw): VX {np.max(d['vx_pp_mV']):.4f} mV, "
          f"VY {np.max(d['vy_pp_mV']):.4f} mV")
    print(f"Max 2f amplitude: VX {np.max(d['vx_2f_mV']):.4f} mV, "
          f"VY {np.max(d['vy_2f_mV']):.4f} mV")
    print(f"VX, VY at t = 0: {np.min(d['vx_t0']):.6f} to {np.max(d['vx_t0']):.6f} V, "
          f"{np.min(d['vy_t0']):.6f} to {np.max(d['vy_t0']):.6f} V")
    print()

    # Per step table
    dr = math.radians(D_DEG)
    th_all = np.radians(p_all)
    R = np.hypot(vx - MID, vy - MID)
    # Ideal theory exactly as written: VX - 2.5 = -K cos p, VY - 2.5 = K sin(p - d).
    # Its own magnitude is K sqrt(cos^2 p + sin^2(p - d)), which differs from K by up to 0.16 %.
    R_th = np.hypot(K * np.cos(th_all), K * np.sin(th_all - dr))
    R_err_pct = (R - K) / K * 100.0            # against the brief's R = K
    R_err_th_pct = (R - R_th) / R_th * 100.0   # against the ideal theory at the same p
    phase = np.degrees(np.arctan2(vy - MID, MID - vx))
    phase_th_line = p_all - D_DEG              # the brief's p - d
    phase_th_atan = np.degrees(np.arctan2(np.sin(th_all - dr), np.cos(th_all)))  # atan2 of the ideal theory
    phase_err = wrap180(phase - phase_th_atan)  # error against the same atan2 formula
    phase_err_line = wrap180(phase - phase_th_line)
    print("| p (deg) | VX (V) | VY (V) | R (V) | R err vs K (%) | R err vs ideal (%) | phase (deg) | phase err (deg) |")
    print("|---|---|---|---|---|---|---|---|")
    for i in range(n_all):
        print(f"| {p_all[i]:.0f} | {vx[i]:.6f} | {vy[i]:.6f} | {R[i]:.6f} | {R_err_pct[i]:+.4f} | "
              f"{R_err_th_pct[i]:+.4f} | {phase[i]:.4f} | {phase_err[i]:+.4f} |")
    print()
    print(f"Ideal R (hypot of theory) range: {R_th.min():.6f} to {R_th.max():.6f} V")
    print(f"Phase error against p - d (brief's line), range: {phase_err_line.min():+.4f} to {phase_err_line.max():+.4f} deg")
    print(f"Phase error against atan2 of theory, range: {phase_err.min():+.4f} to {phase_err.max():+.4f} deg")
    print(f"Mean R err vs ideal (all 25): {R_err_th_pct.mean():+.4f} %, std {R_err_th_pct.std():.4f} %")
    print()

    # Repeatability: 0 deg against 360 deg
    i0 = int(np.where(p_all == 0)[0][0])
    i360 = int(np.where(p_all == 360)[0][0])
    print(f"Repeatability 360 minus 0 deg: VX {(vx[i360] - vx[i0]) * 1e3:+.4f} mV, "
          f"VY {(vy[i360] - vy[i0]) * 1e3:+.4f} mV")
    print()

    # Least-squares fit: VX - 2.5 = -Rx cos(p - phx), VY - 2.5 = Ry sin(p - phy)
    cx, rx_res, rms_x = lsq(p, vxf)
    cy, ry_res, rms_y = lsq(p, vyf)
    a, b = cx[1], cx[2]
    Rx = math.hypot(a, b)
    phx = math.degrees(math.atan2(-b, -a))
    A_, B_ = cy[1], cy[2]
    Ry = math.hypot(A_, B_)
    phy = math.degrees(math.atan2(-A_, B_))
    print("Base fit (24 phases):")
    print(f"  VX: offset {cx[0]:.6f} V, Rx = {Rx:.6f} V, phx = {phx:+.4f} deg, RMS {rms_x * 1e3:.4f} mV")
    print(f"  VY: offset {cy[0]:.6f} V, Ry = {Ry:.6f} V, phy = {phy:+.4f} deg, RMS {rms_y * 1e3:.4f} mV")
    print(f"  Theory: R = {K:.6f} V, phx = 0, phy = d = {D_DEG:.4f} deg")
    print()

    # Slew model: extra term sin p |sin p| for X and cos p |cos p| for Y.
    # Predicted size from P-01: R * omega * (D/2) with D = 4 V / SR at p = 0.
    d_half = STEP_Y / SR_OPAMP / 2.0          # s, slew delay at p = 0 (about 99 ns)
    pred_mV = K * OMEGA * d_half * 1e3        # mV, predicted coefficient
    th = np.radians(p)
    shape_x = np.sin(th) * np.abs(np.sin(th))
    shape_y = np.cos(th) * np.abs(np.cos(th))
    cxs, rxs_res, rms_xs = lsq(p, vxf, shape_x)
    cys, rys_res, rms_ys = lsq(p, vyf, shape_y)
    print(f"Slew model: predicted coefficient {pred_mV:+.4f} mV for both channels "
          f"(slew delay {d_half * 1e9:.2f} ns at p = 0)")
    print(f"  VX + S_x sin p|sin p|: S_x = {cxs[3] * 1e3:+.4f} mV, RMS {rms_xs * 1e3:.4f} mV, "
          f"Rx = {math.hypot(cxs[1], cxs[2]):.6f} V, phx = {math.degrees(math.atan2(-cxs[2], -cxs[1])):+.4f} deg")
    print(f"  VY + S_y cos p|cos p|: S_y = {cys[3] * 1e3:+.4f} mV, RMS {rms_ys * 1e3:.4f} mV, "
          f"Ry = {math.hypot(cys[1], cys[2]):.6f} V, phy = {math.degrees(math.atan2(-cys[1], cys[2])):+.4f} deg")
    print()

    # Residuals against ideal theory (mV)
    vx_th = MID - K * np.cos(np.radians(p))
    vy_th = MID + K * np.sin(np.radians(p) - dr)
    res_x = (vxf - vx_th) * 1e3
    res_y = (vyf - vy_th) * 1e3
    print("Residuals against ideal theory (mV): mean, RMS, max |res|")
    print(f"  VX: {res_x.mean():+.4f}, {np.sqrt(np.mean(res_x ** 2)):.4f}, {np.max(np.abs(res_x)):.4f}")
    print(f"  VY: {res_y.mean():+.4f}, {np.sqrt(np.mean(res_y ** 2)):.4f}, {np.max(np.abs(res_y)):.4f}")
    print()
    print("Residual fit to slew model shapes, residual = c0 + a cos p + b sin p + S shape:")
    print(f"  VX residual, shape sin p|sin p|: S = {cxs[3] * 1e3:+.4f} mV")
    print(f"  VY residual, shape cos p|cos p|: S = {cys[3] * 1e3:+.4f} mV")
    print()

    # Pass checks
    r_ok = np.abs(R_err_pct) < 0.5
    ph_ok = np.abs(phase_err_line) < 1.0
    print(f"Pass R within 0.5 %: {int(r_ok.sum())} of {n_all} steps")
    print(f"Pass phase within 1 deg: {int(ph_ok.sum())} of {n_all} steps")
    print(f"R error range vs K (all): {R_err_pct.min():+.4f} to {R_err_pct.max():+.4f} %")
    print()
    print()

    # Plots
    PLOT_DIR.mkdir(parents=True, exist_ok=True)
    pp = np.linspace(0, 360, 721)
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8, 6), sharex=True)
    ax1.plot(pp, (MID - K * np.cos(np.radians(pp))), "k--", lw=0.9, label="theory 2.5 - K cos p")
    ax1.plot(p_all, vx, "o", ms=4, color="tab:blue", label="measured (settled, corrected)")
    ax1.set_ylabel("VX [V]")
    ax1.legend(fontsize=8, loc="best")
    ax2.plot(pp, (MID + K * np.sin(np.radians(pp) - dr)), "k--", lw=0.9,
             label="theory 2.5 + K sin(p - d)")
    ax2.plot(p_all, vy, "o", ms=4, color="tab:orange", label="measured (settled, corrected)")
    ax2.set_ylabel("VY [V]")
    ax2.set_xlabel("input phase p [deg]")
    ax2.legend(fontsize=8, loc="best")
    ax1.set_title("P-02: VX and VY against input phase")
    for ax in (ax1, ax2):
        ax.grid(alpha=0.3)
        ax.set_xticks(range(0, 361, 45))
    fig.tight_layout()
    fig.savefig(PLOT_DIR / "P-02_vx_vy_vs_p.png", dpi=150)
    plt.close(fig)

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8, 6), sharex=True)
    # Plot the residual after the fitted offset, cos and sin terms (extended fit),
    # so the slew shape can be compared directly with the points.
    th_p = np.radians(p)
    base_x = cxs[0] + cxs[1] * np.cos(th_p) + cxs[2] * np.sin(th_p)
    base_y = cys[0] + cys[1] * np.cos(th_p) + cys[2] * np.sin(th_p)
    pl_x = (vxf - base_x) * 1e3
    pl_y = (vyf - base_y) * 1e3
    ax1.axhline(0, color="k", lw=0.7)
    ax1.plot(p, pl_x, "o", ms=4, color="tab:blue", label="measured - fitted offset, cos and sin")
    ax1.plot(pp, cxs[3] * 1e3 * np.sin(np.radians(pp)) * np.abs(np.sin(np.radians(pp))),
             "--", color="tab:red", lw=0.9, label=f"slew fit S_x = {cxs[3] * 1e3:+.3f} mV")
    ax1.set_ylabel("VX residual [mV]")
    ax1.set_ylim(-1.3, 1.3)
    ax1.legend(fontsize=8)
    ax2.axhline(0, color="k", lw=0.7)
    ax2.plot(p, pl_y, "o", ms=4, color="tab:orange", label="measured - fitted offset, cos and sin")
    ax2.plot(pp, cys[3] * 1e3 * np.cos(np.radians(pp)) * np.abs(np.cos(np.radians(pp))),
             "--", color="tab:red", lw=0.9, label=f"slew fit S_y = {cys[3] * 1e3:+.3f} mV")
    ax2.set_ylabel("VY residual [mV]")
    ax2.set_ylim(-1.3, 1.3)
    ax2.set_xlabel("input phase p [deg]")
    ax2.legend(fontsize=8)
    ax1.set_title("P-02: residual after the fitted cos and sin terms")
    for ax in (ax1, ax2):
        ax.grid(alpha=0.3)
        ax.set_xticks(range(0, 361, 45))
    fig.tight_layout()
    fig.savefig(PLOT_DIR / "P-02_residuals.png", dpi=150)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(5.5, 5.5))
    circ = np.radians(np.linspace(0, 360, 721))
    ax.plot(MID - K * np.cos(circ), MID + K * np.sin(circ - dr), "k--", lw=0.9,
            label="theory (radius R = 1.2732 V)")
    sc = ax.scatter(vx, vy, c=p_all, cmap="viridis", s=28, zorder=3, label="measured")
    cb = fig.colorbar(sc, ax=ax, shrink=0.8)
    cb.set_label("p [deg]")
    ax.set_xlabel("VX [V]")
    ax.set_ylabel("VY [V]")
    ax.set_title("P-02: VX against VY")
    ax.set_aspect("equal", adjustable="datalim")
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8, loc="upper right")
    fig.tight_layout()
    fig.savefig(PLOT_DIR / "P-02_xy.png", dpi=150)
    plt.close(fig)
    print(f"wrote plots to {PLOT_DIR}")


if __name__ == "__main__":
    main()
