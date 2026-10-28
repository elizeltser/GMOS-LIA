"""P-12 driver output impedance at the demodulator input (DI-06).

Reads sim-runs/P12_rser/P12_rser.csd. The run used circuits/lia_v3_fast_P10a0.cir
(lia_v3_fast.cir with vampl = 0.2 V), 0.15 s, output capacitors 1 uF (tau = 10 ms),
.STEP PARAM rser LIST 1m 10 100 1k, probes V(VX), V(VY), V(N00890).

Settled value: time-weighted trapezoid mean over the last 20 whole periods of
517 Hz (38.68 ms, from 111.32 ms to 150 ms). The mean is taken on the raw PSpice
points with interpolated window ends, because point means are biased
(docs/simulation-quirks.md). The settling bias is removed with the P-08 model,
V_ss = (m - 2.5 V F) / (1 - F), and the window of the same length before the
last one is printed as the settling check.

Ideal theory (switch: S1 = N00890 to D when SEL is low, S2 = REF when SEL is high;
vendor/README.md). Channel X is in its -1 state (output REF) when V2 is high,
that is for (t mod T) < T/2. Channel Y is in its -1 state for
((t - 482.6 us) mod T) < T/2. A channel in its -1 state draws (V(N00890) - 2.5 V)
/ 10 kOhm. With n channels in the -1 state and eps = rser / 10 kOhm, the node obeys

    V(N00890) - 2.5 V = u / (1 + n eps),   u = Vin - Vref = A sin(2 pi f t),

so the residual r = V(N00890) - Vin = -u n eps / (1 + n eps). The output of a
channel is 2.5 V + u k in its +1 state and 2.5 V - u k in its -1 state, with
k = 1 / (1 + n eps). The period mean of the outputs gives the deltas. The closed
forms of the entry (quarter-period edges, no timing error) are printed as well.

Node check: r is compared with the ideal node model over the last period, and the
steps of V(N00890) at the reference edges are compared with eps (Vin - Vref).

Run from the project root:
    python docs/sim-results/scripts/P-12_rser.py
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

CSD = ROOT / "sim-runs/P12_rser/P12_rser.csd"
PLOT = ROOT / "docs/sim-results/plots/P-12_rser.png"

F = 517.0
T = 1.0 / F
A = 0.2                  # Vampl, V
VR = 2.5                 # reference, V
R_DEM = 10e3             # R2 and R4, ohm
T_DELAY_Y = 482.6e-6     # Y reference delay, s
T_STOP = 0.15            # run end, s
N_PER = 20               # settled window, whole periods
TAU = 10e3 * 1e-6        # R3 x C1 = 10 kOhm x 1 uF, s
RSER_BASE = 1e-3         # baseline step, ohm
D_DEG = 360.0 * (T / 4 - T_DELAY_Y) / T   # Y timing error, 0.1785 deg (P-08)

# Values quoted in the entry (P-12 Expected table), in mV and percent
ENTRY_DVX = {10: 0.1275, 100: 1.2544, 1000: 11.091}
ENTRY_DVY = {10: 0.0, 100: -0.0062, 1000: -0.482}     # 10 Ohm: "below 0.001 mV"
ENTRY_GX = {10: -0.100, 100: -0.985, 1000: -8.71}     # percent
TOL_MV_FLOOR = 0.005
TOL_REL = 0.02


def window_mean(t, y, t0, t1):
    """Time-weighted trapezoid mean on the raw points, ends interpolated."""
    inside = (t > t0) & (t < t1)
    tt = np.concatenate(([t0], t[inside], [t1]))
    yy = np.concatenate(([np.interp(t0, t, y)], y[inside], [np.interp(t1, t, y)]))
    return float(np.trapezoid(yy, tt) / (t1 - t0))


def settle_factor(t0, tw, tau):
    """Window mean of exp(-t/tau) from t0 to t0 + tw, relative to the start value of 1."""
    return (tau / tw) * (1 - math.exp(-tw / tau)) * math.exp(-t0 / tau)


def channel_states(t, tdy=T_DELAY_Y):
    """Return (nx, ny): 1 when the channel is in its -1 state."""
    nx = (np.mod(t, T) < T / 2).astype(int)
    ny = (np.mod(t - tdy, T) < T / 2).astype(int)
    return nx, ny


def node_model(t, eps):
    """Ideal residual V(N00890) - Vin, in V."""
    nx, ny = channel_states(t)
    n = nx + ny
    u = A * np.sin(2 * np.pi * F * t)
    return -u * n * eps / (1 + n * eps)


def theory_period_means(eps, n_grid=2_000_000, tdy=T_DELAY_Y):
    """Exact period mean of both demodulator outputs minus 2.5 V (V), piecewise ideal.

    tdy is the Y reference delay used for the Y edge (default 482.6 us).
    """
    t = np.linspace(0.0, T, n_grid, endpoint=False)
    nx, ny = channel_states(t, tdy)
    n = nx + ny
    u = A * np.sin(2 * np.pi * F * t)
    k = 1.0 / (1.0 + n * eps)
    x_out = np.where(nx == 1, VR - u * k, VR + u * k)
    y_out = np.where(ny == 1, VR - u * k, VR + u * k)
    return float(x_out.mean() - VR), float(y_out.mean() - VR)


def closed_form(eps):
    """Entry formulas with quarter-period edges (no 0.18 deg timing error)."""
    g1 = 1.0 / (1.0 + eps)
    g2 = 1.0 / (1.0 + 2.0 * eps)
    c = A / (2 * math.pi)
    return -c * (1 + 2 * g1 + g2), c * (2 * g1 - g2 - 1)


def eps_of(rser):
    return rser / R_DEM


def settled(sec):
    t = sec.x
    tend = float(t[-1])
    tw = N_PER * T
    t0 = tend - tw
    tp0 = t0 - tw
    f = settle_factor(t0, tw, TAU)
    res = {"rser": sec.step_value, "t0": t0, "t_end": tend, "points": len(t), "F": f}
    for name in ("V(VX)", "V(VY)"):
        y = sec[name]
        m = window_mean(t, y, t0, tend)
        prior = window_mean(t, y, tp0, t0)
        key = "vx" if name == "V(VX)" else "vy"
        res[key + "_raw"] = m
        res[key + "_dprior"] = m - prior
        res[key] = (m - VR * f) / (1 - f)
    return res


def edge_list(t_first, t_last):
    """Reference edges inside [t_first, t_last]: X up/down at 0 and T/2, Y at 482.6 us and +T/2."""
    edges = []
    k0 = int(math.floor(t_first / T)) - 1
    k1 = int(math.ceil(t_last / T)) + 1
    for k in range(k0, k1 + 1):
        for label, e in (("X up", k * T), ("X down", k * T + T / 2),
                         ("Y up", T_DELAY_Y + k * T), ("Y down", T_DELAY_Y + T / 2 + k * T)):
            if t_first + 3e-6 <= e <= t_last - 3e-6:
                edges.append((label, e))
    return sorted(edges, key=lambda x: x[1])


def step_check(sec, eps):
    """Steps of the residual r = V(N00890) - Vin at each reference edge of the last period."""
    t = sec.x
    node = sec["V(N00890)"]
    r = node - (VR + A * np.sin(2 * np.pi * F * t))
    t_first = T_STOP - T
    rows = []
    for label, e in edge_list(t_first, T_STOP):
        pre = (e - 3e-6, e - 0.5e-6)
        post = (e + 0.5e-6, e + 3e-6)
        meas = window_mean(t, r, *post) - window_mean(t, r, *pre)
        g_pre = np.linspace(*pre, 2001)
        g_post = np.linspace(*post, 2001)
        th = (np.trapezoid(node_model(g_post, eps), g_post) / (post[1] - post[0])
              - np.trapezoid(node_model(g_pre, eps), g_pre) / (pre[1] - pre[0]))
        u_e = A * math.sin(2 * math.pi * F * e)
        ref = eps * u_e                       # eps (Vin - Vref) at the edge
        rows.append((label, e, meas, th, ref))
    return rows


def residual_check(sec, eps):
    """Max and RMS of r - model over the last period, away from the edges (+/- 10 us)."""
    t = sec.x
    node = sec["V(N00890)"]
    r = node - (VR + A * np.sin(2 * np.pi * F * t))
    t_first = T_STOP - T
    m = (t >= t_first) & (t <= T_STOP)
    edges = [e for _, e in edge_list(t_first, T_STOP)]
    keep = np.ones(m.sum(), dtype=bool)
    tt = t[m]
    for e in edges:
        keep &= np.abs(tt - e) > 10e-6
    d = (r[m] - node_model(tt, eps))[keep]
    return float(np.max(np.abs(d))), float(np.sqrt(np.mean(d * d))), int(keep.sum())


def main():
    secs = read_csdf(str(CSD))
    by = {round(s.step_value, 9): s for s in secs}
    rsers = sorted(by)
    base_sec = by[round(RSER_BASE, 9)]
    base = settled(base_sec)

    print(f"T = {T*1e3:.6f} ms, Y timing error d = {D_DEG:.5f} deg, T/2 = {T/2*1e6:.3f} us")
    print(f"Window: {N_PER} periods = {N_PER*T*1e3:.4f} ms, from {base['t0']*1e3:.4f} ms to "
          f"{base['t_end']*1e3:.4f} ms. Points per run: "
          + ", ".join(f"{r:g} ohm: {len(by[round(r, 9)].x)}" for r in rsers))
    print(f"Settling factor F = {base['F']:.4e} (tau = {TAU*1e3:.1f} ms).")
    print()

    results = {}
    for r in rsers:
        results[r] = settled(by[round(r, 9)])

    print("Settled means (V), trapezoid on raw points, bias removed")
    print(f"{'rser (ohm)':>12}{'VX (V)':>14}{'VY (V)':>14}{'VX - 2.5 V (mV)':>17}{'VY - 2.5 V (mV)':>17}")
    for r in rsers:
        s = results[r]
        print(f"{r:>12g}{s['vx']:>14.7f}{s['vy']:>14.7f}{(s['vx']-VR)*1e3:>17.5f}{(s['vy']-VR)*1e3:>17.5f}")
    print()

    print("Settling check: last window minus the window of the same length before it (mV)")
    print(f"{'rser (ohm)':>12}{'dVX raw':>12}{'dVY raw':>12}{'bias VX (uV)':>14}{'bias VY (uV)':>14}")
    for r in rsers:
        s = results[r]
        print(f"{r:>12g}{s['vx_dprior']*1e3:>12.5f}{s['vy_dprior']*1e3:>12.5f}"
              f"{base['F']*(VR-s['vx_raw'])*1e6:>14.3f}{base['F']*(VR-s['vy_raw'])*1e6:>14.3f}")
    print()

    b_th = theory_period_means(eps_of(RSER_BASE))
    b_cf = closed_form(eps_of(RSER_BASE))
    rows = []
    print("Deltas relative to rser = 1 mOhm (mV). Theory is the exact period mean with the "
          "0.18 deg Y timing error, the closed form is the entry formula (quarter edges).")
    hdr = (f"{'rser (ohm)':>11}{'dVX meas':>11}{'dVX theory':>12}{'dVX closed':>12}{'dVX entry':>11}"
           f"{'dVY meas':>11}{'dVY theory':>12}{'dVY closed':>12}{'dVY entry':>11}")
    print(hdr)
    for r in rsers:
        if abs(r - RSER_BASE) < 1e-12:
            continue
        s = results[r]
        eps = eps_of(r)
        th = theory_period_means(eps)
        dth = (th[0] - b_th[0], th[1] - b_th[1])
        cf = closed_form(eps)
        dcf = (cf[0] - b_cf[0], cf[1] - b_cf[1])
        dvx = (s["vx"] - base["vx"]) * 1e3
        dvy = (s["vy"] - base["vy"]) * 1e3
        r_int = int(round(r))
        print(f"{r:>11g}{dvx:>11.5f}{dth[0]*1e3:>12.5f}{dcf[0]*1e3:>12.5f}{ENTRY_DVX[r_int]:>11.4f}"
              f"{dvy:>11.5f}{dth[1]*1e3:>12.5f}{dcf[1]*1e3:>12.5f}{ENTRY_DVY[r_int]:>11.4f}")
        rows.append((r, dvx, dvy, dth, dcf))
    print()

    print("Effect of the Y edge delay on the VY delta (mV). The Y edge is at 482.6 us plus the extra delay.")
    print("235 ns is the total Y switching delay found in P-01 and P-04 (126 ns constant plus 111 ns slew).")
    print(f"{'rser (ohm)':>11}{'dVY meas':>11}{'0 ns':>11}{'126 ns':>11}{'235 ns':>11}")
    b_y = {}
    for extra in (0.0, 126e-9, 235e-9):
        b_y[extra] = theory_period_means(eps_of(RSER_BASE), tdy=T_DELAY_Y + extra)[1]
    for r, dvx, dvy, _, _ in rows:
        cells = []
        for extra in (0.0, 126e-9, 235e-9):
            th = theory_period_means(eps_of(r), tdy=T_DELAY_Y + extra)[1]
            cells.append((th - b_y[extra]) * 1e3)
        print(f"{r:>11g}{dvy:>11.5f}{cells[0]:>11.5f}{cells[1]:>11.5f}{cells[2]:>11.5f}")
    print()

    print("Gain error of the X channel relative to rser = 1 mOhm (percent)")
    print(f"{'rser (ohm)':>11}{'meas':>12}{'theory':>12}{'entry':>10}")
    gain_rows = []
    for r in rsers:
        if abs(r - RSER_BASE) < 1e-12:
            continue
        s = results[r]
        g_meas = 100.0 * ((s["vx"] - VR) / (base["vx"] - VR) - 1.0)
        th = theory_period_means(eps_of(r))
        g_th = 100.0 * (th[0] / b_th[0] - 1.0)
        gain_rows.append((r, g_meas, g_th))
        print(f"{r:>11g}{g_meas:>12.4f}{g_th:>12.4f}{ENTRY_GX[int(round(r))]:>10.3f}")
    print()

    print("Pass check against the entry table: tolerance = max(2 % of the entry value, 0.005 mV)")
    print(f"{'rser (ohm)':>11}{'quantity':>10}{'measured (mV)':>15}{'entry (mV)':>12}{'diff (mV)':>11}"
          f"{'tol (mV)':>10}{'result':>9}")
    all_pass = True
    for r, dvx, dvy, _, _ in rows:
        ri = int(round(r))
        for name, meas, exp in (("dVX", dvx, ENTRY_DVX[ri]), ("dVY", dvy, ENTRY_DVY[ri])):
            tol = max(TOL_REL * abs(exp), TOL_MV_FLOOR)
            ok = abs(meas - exp) <= tol
            all_pass &= ok
            print(f"{r:>11g}{name:>10}{meas:>15.5f}{exp:>12.5f}{meas-exp:>11.5f}{tol:>10.5f}"
                  f"{'pass' if ok else 'FAIL':>9}")
    print(f"All delta checks pass: {all_pass}")
    print()

    print("Node steps of r = V(N00890) - Vin at the reference edges of the last period")
    print("Steps are the change of the mean in [e+0.5 us, e+3 us] minus the mean in [e-3 us, e-0.5 us].")
    print(f"{'rser (ohm)':>11}{'edge':>9}{'t (ms)':>10}{'step meas (mV)':>16}{'step theory (mV)':>18}"
          f"{'eps(Vin-Vref) (mV)':>20}{'meas/(eps u)':>14}")
    step_rows = {}
    for r in rsers:
        if abs(r - RSER_BASE) < 1e-12:
            continue
        for label, e, meas, th, ref in step_check(by[round(r, 9)], eps_of(r)):
            if abs(ref) < 1e-9:
                ratio = float("nan")
            else:
                ratio = meas / ref
            step_rows.setdefault(r, []).append((label, e, meas, th, ref))
            print(f"{r:>11g}{label:>9}{e*1e3:>10.4f}{meas*1e3:>16.5f}{th*1e3:>18.5f}"
                  f"{ref*1e3:>20.5f}{ratio:>14.4f}")
    print()

    print("Node model check over the last period, away from the edges (+/- 10 us)")
    print(f"{'rser (ohm)':>11}{'max |diff| (mV)':>17}{'rms diff (mV)':>15}{'points':>9}")
    for r in rsers:
        if abs(r - RSER_BASE) < 1e-12:
            continue
        mx, rms, n = residual_check(by[round(r, 9)], eps_of(r))
        print(f"{r:>11g}{mx*1e3:>17.5f}{rms*1e3:>15.5f}{n:>9d}")
    print()

    # Plot: deltas against rser, and the node residual at 1 kOhm over the last period
    fig, ax = plt.subplots(2, 1, figsize=(8, 8))
    xs = [row[0] for row in rows]
    ax[0].semilogx(xs, [row[1] for row in rows], "o", label="VX delta, measured")
    ax[0].semilogx(xs, [row[2] for row in rows], "s", label="VY delta, measured")
    grid = np.logspace(1, 3, 50)
    th_x = [(theory_period_means(eps_of(g))[0] - b_th[0]) * 1e3 for g in grid]
    th_y = [(theory_period_means(eps_of(g))[1] - b_th[1]) * 1e3 for g in grid]
    ax[0].semilogx(grid, th_x, "-", label="VX delta, theory")
    ax[0].semilogx(grid, th_y, "--", label="VY delta, theory")
    ax[0].set_xlabel("series resistance rser (ohm)")
    ax[0].set_ylabel("change from rser = 1 mOhm (mV)")
    ax[0].set_title("P-12 output deltas, Vampl = 0.2 V, cout = 1 uF")
    ax[0].legend(fontsize=8)
    s = by[round(1000.0, 9)]
    t = s.x
    m = (t >= T_STOP - T) & (t <= T_STOP)
    res = s["V(N00890)"] - (VR + A * np.sin(2 * np.pi * F * t))
    tm = (t[m] - (T_STOP - T)) * 1e6
    ax[1].plot(tm, res[m] * 1e3, lw=0.7, label="r measured")
    ax[1].plot(tm, node_model(t[m], eps_of(1000.0)) * 1e3, lw=0.7, label="r model")
    ax[1].set_xlabel("time in last period (us)")
    ax[1].set_ylabel("V(N00890) - Vin (mV)")
    ax[1].set_title("Node residual at rser = 1 kOhm, last period")
    ax[1].legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(PLOT, dpi=120)
    print(f"plot written: {PLOT}")


if __name__ == "__main__":
    main()
