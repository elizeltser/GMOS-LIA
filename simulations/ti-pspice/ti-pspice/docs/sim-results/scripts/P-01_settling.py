"""P-01 settling analysis for the LIA baseline circuit.

Reads the two CSDF files of P-01 (runs A and B), computes the settled VX and VY
over the last 50 periods and over the 50 periods before, compares them with
theory, measures the ripple and the reference edge timing, estimates the
switching delay, and writes one plot.

Run from the project root:
    python docs/sim-results/scripts/P-01_settling.py
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

F_OSC = 517.0              # Hz, input and reference frequency
T = 1.0 / F_OSC            # s, period
N_PER = 50                 # periods in the averaging window
DT_GRID = 1e-6             # s, nominal spacing of the uniform grid
VDC = 5.0                  # V, supply
AMP = 2.0                  # V, input amplitude
TD_Y = 482.6e-6            # s, delay of the Y reference (V_V6)
T_RAMP = 100e-9            # s, reference edge time (t_slope)
TAU_SW = 30e-9             # s, internal filter of the SPDT_PREC model (TAU)

RUNS = {
    "A": {"csd": ROOT / "sim-runs/P01_A_2s_from0/P01_A_2s_from0.csd",
          "t_end": 2.0, "wall_s": 143.0, "label": "A: 2 s from 0 V"},
    "B": {"csd": ROOT / "sim-runs/P01_B_1s_ic/P01_B_1s_ic.csd",
          "t_end": 1.0, "wall_s": 71.0, "label": "B: 1 s, .IC 2.5 V"},
}

PLOT_PATH = ROOT / "docs/sim-results/plots/P-01_settling.png"


def trap_mean(t, y):
    """Trapezoidal mean of y(t) on a uniform or non-uniform grid."""
    return float(np.sum(0.5 * (y[1:] + y[:-1]) * np.diff(t)) / (t[-1] - t[0]))


def window(t_raw, y_raw, t_start, t_stop):
    """Interpolate onto a grid of about 1 us spacing over [t_start, t_stop].

    The grid has exactly the requested end points, so an integer number of
    periods is covered. Returns the grid, the interpolated values and the mean.
    """
    n = round((t_stop - t_start) / DT_GRID) + 1
    grid = np.linspace(t_start, t_stop, n)
    yg = np.interp(grid, t_raw, y_raw)
    return grid, yg, trap_mean(grid, yg)


def rising_crossings(t, v, level):
    """Times of rising crossings of a level, by linear interpolation."""
    idx = np.where((v[:-1] < level) & (v[1:] >= level))[0]
    return t[idx] + (level - v[idx]) / (v[idx + 1] - v[idx]) * (t[idx + 1] - t[idx])


def falling_crossings(t, v, level):
    idx = np.where((v[:-1] > level) & (v[1:] <= level))[0]
    return t[idx] + (v[idx] - level) / (v[idx] - v[idx + 1]) * (t[idx + 1] - t[idx])


def edge_timing(t, ref, t_start, t_stop):
    """Rise 10 to 90 % time, and 50 % crossing offsets, of V(N00261) in a window."""
    m = (t >= t_start) & (t <= t_stop)
    tt, rr = t[m], ref[m]
    r10 = rising_crossings(tt, rr, 0.10 * VDC)
    r50 = rising_crossings(tt, rr, 0.50 * VDC)
    f50 = falling_crossings(tt, rr, 0.50 * VDC)
    r90 = rising_crossings(tt, rr, 0.90 * VDC)
    # 90 % point of the same edge: the first 90 % crossing after the first 10 % crossing
    after = r90[r90 > r10[0]] if len(r10) else r90
    rise_10_90 = (after[0] - r10[0]) if len(r10) and len(after) else float("nan")
    # Offsets from the nominal edges of the PULSE source: rise at k*T, fall at k*T + T/2
    rise_offset = (r50[0] - round(r50[0] / T) * T) if len(r50) else float("nan")
    fall_offset = ((f50[0] - (math.floor(f50[0] / T) * T + T / 2))) if len(f50) else float("nan")
    return rise_10_90, rise_offset, fall_offset


def harmonics(grid, y, f, orders=(1, 2, 3)):
    """Amplitudes of the harmonics of f in y on a grid spanning whole periods."""
    cols = [np.ones_like(grid)]
    for k in orders:
        cols.append(np.sin(2 * np.pi * k * f * grid))
        cols.append(np.cos(2 * np.pi * k * f * grid))
    coef, *_ = np.linalg.lstsq(np.column_stack(cols), y, rcond=None)
    amp = {}
    for i, k in enumerate(orders):
        amp[k] = float(np.hypot(coef[1 + 2 * i], coef[2 + 2 * i]))
    return amp


def edge_ringing(t, vxd, ref_t_edges, span=0.5e-6):
    """Largest deviation of VX_DEMOD from 2.5 V within span after each X edge."""
    out = []
    for te in ref_t_edges:
        m = (t >= te) & (t <= te + span)
        if m.any():
            out.append(float(np.max(np.abs(vxd[m] - 2.5))))
    return out


def main():
    k = 2.0 * AMP / math.pi                     # 4/pi for A = 2 V, V
    vx_th = 2.5 - k                             # X reference at the input phase
    d_deg = 360.0 * (T / 4.0 - TD_Y) / T        # timing error of Y, deg
    vy_th = 2.5 - k * math.sin(math.radians(d_deg))
    print(f"T = {T * 1e3:.6f} ms, T/4 = {T / 4 * 1e6:.3f} us")
    print(f"K = 2A/pi = {k:.6f} V")
    print(f"d = 360 x (T/4 - 482.6 us) / T = {d_deg:.5f} deg")
    print(f"VX theory = 2.5 - K = {vx_th:.6f} V")
    print(f"VY theory = 2.5 - K sin(d) = {vy_th:.6f} V")
    print()

    results = {}
    for run, cfg in RUNS.items():
        s = read_csdf(str(cfg["csd"]))[0]
        t = s.x
        vx, vy = s["V(VX)"], s["V(VY)"]
        vxd, ref = s["V(VX_DEMOD)"], s["V(N00261)"]
        t_end = cfg["t_end"]
        assert abs(t[-1] - t_end) < 1e-12, f"run {run} ends at {t[-1]}"

        t1 = t_end - N_PER * T
        t0 = t_end - 2 * N_PER * T
        grid1, vx1, mvx1 = window(t, vx, t1, t_end)
        _, vy1, mvy1 = window(t, vy, t1, t_end)
        _, _, mvx0 = window(t, vx, t0, t1)
        _, _, mvy0 = window(t, vy, t0, t1)

        ripple_pp = float(vx1.max() - vx1.min())
        ripple_pp_vy = float(vy1.max() - vy1.min())
        hx = harmonics(grid1, vx1, F_OSC)
        hy = harmonics(grid1, vy1, F_OSC)
        t_start_run = float(t[0])
        vx_ic = float(np.interp(t_start_run, t, vx))

        # Nearest X reference edges in the last period, for the ringing check
        k_last = round(t_end / T)
        edges = [(k_last - 1) * T, (k_last - 1) * T + T / 2]
        ring = edge_ringing(t, vxd, edges)
        r_10_90, r_rise50, r_fall50 = edge_timing(t, ref, t1, t_end)

        results[run] = dict(
            vx=mvx1, vy=mvy1, vx_prev=mvx0, vy_prev=mvy0,
            dvx_settle=mvx1 - mvx0, dvy_settle=mvy1 - mvy0,
            ripple_pp=ripple_pp, ripple_pp_vy=ripple_pp_vy,
            hx=hx, hy=hy, vx_ic=vx_ic,
            ring_mV=[x * 1e3 for x in ring],
            r_10_90_ns=r_10_90 * 1e9, r_rise50_ns=r_rise50 * 1e9,
            r_fall50_ns=r_fall50 * 1e9,
            sec_per_sim_s=cfg["wall_s"] / t_end,
            vx_fit_error_mV=(mvx1 - vx_th) * 1e3,
            vy_fit_error_mV=(mvy1 - vy_th) * 1e3,
            vy_eff_deg=math.degrees(math.asin(min(1.0, (2.5 - mvy1) / k))),
            t=t, vx_raw=vx, vy_raw=vy,
        )
        r = results[run]
        print(f"Run {cfg['label']}  window {t1:.6f} s to {t_end:.6f} s "
              f"({N_PER} periods), grid points {len(grid1)}")
        print(f"  VX mean last 50 periods    = {mvx1:.6f} V")
        print(f"  VY mean last 50 periods    = {mvy1:.6f} V")
        print(f"  VX mean 50 periods before  = {mvx0:.6f} V  (diff {r['dvx_settle'] * 1e3:+.4f} mV)")
        print(f"  VY mean 50 periods before  = {mvy0:.6f} V  (diff {r['dvy_settle'] * 1e3:+.4f} mV)")
        print(f"  VX at t = 0: {vx_ic:.6f} V (initial condition check)")
        print(f"  VX ripple p-p, last 50 periods = {ripple_pp * 1e3:.4f} mV")
        print(f"  VY ripple p-p, last 50 periods = {ripple_pp_vy * 1e3:.4f} mV")
        print("  Harmonic amplitudes (mV) of VX: " +
              ", ".join(f"{k}f = {v * 1e3:.4f}" for k, v in hx.items()))
        print("  Harmonic amplitudes (mV) of VY: " +
              ", ".join(f"{k}f = {v * 1e3:.4f}" for k, v in hy.items()))
        print(f"  V(N00261) rise 10-90 % = {r_10_90 * 1e9:.2f} ns, "
              f"rise 50 % offset = {r_rise50 * 1e9:+.2f} ns, fall 50 % offset = {r_fall50 * 1e9:+.2f} ns")
        print(f"  VX_DEMOD max deviation from 2.5 V within 0.5 us after X edges: "
              f"{', '.join(f'{x:.2f} mV' for x in r['ring_mV'])}")
        print(f"  Wall time {cfg['wall_s']:.0f} s for {t_end:.0f} s simulated = "
              f"{cfg['wall_s'] / t_end:.1f} s per simulated second")
        print()

    print("Comparison (mV)")
    a, b = results["A"], results["B"]
    print(f"  VX  A - B = {(a['vx'] - b['vx']) * 1e3:+.4f} mV")
    print(f"  VY  A - B = {(a['vy'] - b['vy']) * 1e3:+.4f} mV")
    eps_y = T / 4.0 - TD_Y                      # s, nominal Y timing error (0.959 us)
    for run in ("A", "B"):
        r = results[run]
        # Average Y switching delay that would explain the measured VY alone.
        # VY = 2.5 - K sin(w (eps - delay)), so delay = eps - asin((2.5 - VY) / K) / w.
        delay_y = eps_y - math.asin((2.5 - r["vy"]) / k) / (2 * math.pi * F_OSC)
        r["delay_y_ns"] = delay_y * 1e9
        print(f"  {run}: VX - theory = {r['vx_fit_error_mV']:+.4f} mV, "
              f"VY - theory = {r['vy_fit_error_mV']:+.4f} mV, "
              f"Y phase error equivalent = {r['vy_eff_deg']:.4f} deg (theory {d_deg:.4f} deg), "
              f"Y effective switching delay = {r['delay_y_ns']:.1f} ns")
    print()

    # Switching delay estimate from the 100 ns edges and the 30 ns TAU filter.
    # Ideal edges: rise at TD, fall at TD + T/2. The fall starts 100 ns late
    # because PW = 0.5/f does not include the edge times.
    def delays(th_rise, th_fall):
        d_rise = th_rise / VDC * T_RAMP + TAU_SW
        fall_start = T_RAMP + T / 2
        d_fall = fall_start + (VDC - th_fall) / VDC * T_RAMP + TAU_SW - T / 2
        return d_rise, d_fall

    print("Switching delay estimate (ideal edge = start of the PULSE rise, or TD + T/2 for the fall)")
    for label, (tr, tf) in {"rise at 1.8 V, fall at 1.0 V": (1.8, 1.0),
                            "rise at 1.0 V, fall at 1.8 V": (1.0, 1.8)}.items():
        d_r, d_f = delays(tr, tf)
        d_avg = 0.5 * (d_r + d_f)
        dvy = k * 2 * math.pi * F_OSC * d_avg
        print(f"  {label}: delay rise = {d_r * 1e9:.1f} ns, fall = {d_f * 1e9:.1f} ns, "
              f"mean = {d_avg * 1e9:.1f} ns, VY shift = {dvy * 1e3:+.4f} mV, "
              f"VX shift ~ {k * (2 * math.pi * F_OSC * d_avg) ** 2 / 2 * 1e3:.2e} mV")
    print()

    # Plot: VX and VY versus time, both runs, with theory lines
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8, 6), sharex=True)
    colors = {"A": "tab:blue", "B": "tab:orange"}
    for run in ("A", "B"):
        r = results[run]
        ax1.plot(r["t"], r["vx_raw"], lw=0.6, color=colors[run], label=RUNS[run]["label"])
        ax2.plot(r["t"], r["vy_raw"], lw=0.6, color=colors[run], label=RUNS[run]["label"])
    ax1.axhline(vx_th, color="k", ls="--", lw=0.8, label="theory")
    ax2.axhline(vy_th, color="k", ls="--", lw=0.8, label="theory")
    ax1.set_ylabel("V(VX) [V]")
    ax2.set_ylabel("V(VY) [V]")
    ax2.set_xlabel("time [s]")
    ax1.set_title("P-01: settling of VX and VY, runs A and B")
    ax1.legend(loc="center right", fontsize=8)
    ax2.legend(loc="center right", fontsize=8)
    ax1.grid(alpha=0.3)
    ax2.grid(alpha=0.3)
    fig.tight_layout()
    PLOT_PATH.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(PLOT_PATH, dpi=150)
    print(f"wrote {PLOT_PATH}")


if __name__ == "__main__":
    main()
