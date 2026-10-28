"""P-16 overload recovery of the front end (circuits/chain_ss.cir).

Reads sim-runs/P16_2u/P16_2u.csd. This is the run with .TRAN 0 0.3 0 2u and
.STEP PARAM aburst LIST 0 0.5 (the 5 us runs failed, see docs/simulation-quirks.md).
Section with step 0 is the reference. Section with step 0.5 is the overload.

Burst: 10 periods at f_osc = 517 Hz, from tburst = 50 / f_osc = 96.7118 ms to
t_end = tburst + 10 / f_osc = 116.0542 ms.

Method
  - Both sections are interpolated onto a uniform 2 us grid from 95 ms to 300 ms.
    The difference d(t) = V(aburst = 0.5) - V(aburst = 0) is formed per probe.
  - Check: d(t) before the burst must be zero (same circuit, same sine).
  - Recovery time (raw): last time with |d| >= 1 mV, measured from t_end.
    This is the entry's rule. The raw d includes the 2f ripple of the outputs.
  - Envelope: a centred one-period (1/f_osc) mean of d removes the ripple.
    Its last 1 mV crossing is given as a check.
  - VSAMPLE recovery time t_VS (raw). Predicted VX/VY recovery:
    t_pred = t_VS + tau ln(dV / 1 mV), dV = |envelope d| at t_VS,
    tau = 10 ms (fast RC, cout = 1 uF, the run as made).
    Scaled to tau = 0.1 s: t_VS + 10 x (t_meas - t_VS) for the measured value,
    and t_VS + 0.1 s ln(dV / 1 mV) for the prediction.
  - Decay constants from log-linear fits of the envelope (HPF, VX, VY).
  - Saturation memory: envelope of HPF and VDIFF after t_end, and the DC
    level of HPF in the first milliseconds after the burst.

Run from the project root:
    python docs/sim-results/scripts/P-16_overload.py
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

CSD = ROOT / "sim-runs/P16_2u/P16_2u.csd"
PLOT = ROOT / "docs/sim-results/plots/P-16_recovery.png"

F_OSC = 517.0
N_BURST = 10
T_BURST = 50 / F_OSC
T_END = T_BURST + N_BURST / F_OSC
T_PER = 1 / F_OSC
DT = 2e-6
THR = 1e-3                  # V, recovery threshold
TAU_FAST = 10e-3            # s, 10 kOhm x 1 uF, run as made
TAU_DESIGN = 0.1            # s, 10 kOhm x 10 uF, design value
PROBES = ["V(VDIFF)", "V(HPF)", "V(VSAMPLE)", "V(VX)", "V(VY)"]


def centred_mean(t, d, width):
    """Centred moving mean over a window of the given width (s), on a uniform grid."""
    n = int(round(width / DT))
    if n % 2 == 0:
        n += 1
    k = np.ones(n) / n
    pad = n // 2
    dp = np.concatenate([np.full(pad, d[0]), d, np.full(pad, d[-1])])
    return np.convolve(dp, k, mode="valid")


def sliding_max(y, width):
    """Centred sliding maximum of |y| over a window of the given width (s)."""
    from numpy.lib.stride_tricks import sliding_window_view
    n = int(round(width / DT))
    if n % 2 == 0:
        n += 1
    pad = n // 2
    yp = np.concatenate([np.zeros(pad), np.abs(y), np.zeros(pad)])
    return sliding_window_view(yp, n).max(axis=1)


def last_exceed(t, d, t0, thr=THR):
    """Last time after t0 with |d| >= thr. Returns NaN if none."""
    m = (t >= t0) & (np.abs(d) >= thr)
    if not np.any(m):
        return float("nan")
    return float(t[np.where(m)[0][-1]])


def fit_tau(t, y, t_a, t_b):
    """Log-linear fit of |y| on [t_a, t_b]. Returns tau (s), or NaN."""
    m = (t >= t_a) & (t <= t_b) & (np.abs(y) > 0)
    if np.count_nonzero(m) < 10:
        return float("nan")
    slope = np.polyfit(t[m], np.log(np.abs(y[m])), 1)[0]
    return -1.0 / slope if slope < 0 else float("nan")


def ms(x):
    return f"{1e3 * x:.4f}"


def theory_poles():
    """Free-response poles of the linear HP and LP chain (ideal op amps), from circuits/chain_ss.cir.

    Nodes: A = N07625, B = N07629 (= HPF, buffer), C = N08401, D = N08020 (= VSAMPLE, buffer).
    Element values (chain_ss.cir): C1 = C2 = 33 nF, R17 = 4.64 kOhm, R18 = 18.7 kOhm,
    R22 = R21 = 4.64 kOhm, C4 = 130 nF, C3 = 33 nF. Sources set to zero.
    Returns a list of (f0 in Hz, decay constant in ms, Q) for the complex pole pairs.
    """
    C1 = C2 = 33e-9
    R17, R18 = 4.64e3, 18.7e3
    R22 = R21 = 4.64e3
    C4, C3 = 130e-9, 33e-9
    g17, g18, g22, g21 = 1 / R17, 1 / R18, 1 / R22, 1 / R21
    # (A + s B) x = 0, x = [V_A, V_B, V_C, V_D]
    A = np.array([
        [g17, -g17, 0.0, 0.0],
        [0.0, g18, 0.0, 0.0],
        [0.0, -g22, g22 + g21, -g21],
        [0.0, 0.0, -g21, g21],
    ])
    B = np.array([
        [C1 + C2, -C2, 0.0, 0.0],
        [-C2, C2, 0.0, 0.0],
        [0.0, 0.0, C4, -C4],
        [0.0, 0.0, 0.0, C3],
    ])
    # s x = -B^-1 A x
    s_poles = np.linalg.eigvals(-np.linalg.solve(B, A))
    out = []
    for sp in s_poles:
        if sp.imag > 1e-6:
            sigma = -sp.real
            w0 = abs(sp)
            out.append((w0 / (2 * math.pi), 1e3 / sigma, w0 / (2 * sigma)))
    return sorted(out)


def main():
    secs = read_csdf(str(CSD))
    ref = next(s for s in secs if abs(s.step_value - 0.0) < 1e-12)
    ovl = next(s for s in secs if abs(s.step_value - 0.5) < 1e-12)
    print(f"reference section: {ref.step}, {len(ref.x)} points, t = {ref.x[0]:.6g} to {ref.x[-1]:.6g} s")
    print(f"overload section : {ovl.step}, {len(ovl.x)} points, t = {ovl.x[0]:.6g} to {ovl.x[-1]:.6g} s")
    print(f"burst: {T_BURST*1e3:.4f} ms to {T_END*1e3:.4f} ms (t_end)")
    print()

    t = np.arange(0.095, 0.300 + DT / 2, DT)
    d = {}
    for p in PROBES:
        yr = np.interp(t, ref.x, ref[p])
        yo = np.interp(t, ovl.x, ovl[p])
        d[p] = yo - yr

    # 1. Identical before the burst
    pre = t < T_BURST - 1e-6
    print("=== 1. Difference before the burst (must be ~0) ===")
    for p in PROBES:
        print(f"{p:<12} max |d| for t < burst = {np.max(np.abs(d[p][pre]))*1e6:.4f} uV")
    print()

    # 2. Raw and envelope recovery times
    print("=== 2. Recovery times after t_end (threshold 1 mV) ===")
    print(f"{'probe':<12}{'raw last |d|>=1mV (ms after t_end)':>36}{'envelope (ms after t_end)':>27}{'|d| at t_end (mV)':>20}")
    env = {}
    rec_raw = {}
    for p in PROBES:
        env[p] = centred_mean(t, d[p], T_PER)
        rr = last_exceed(t, d[p], T_END)
        re_ = last_exceed(t, env[p], T_END)
        rec_raw[p] = rr
        i_end = np.searchsorted(t, T_END)
        rr_s = f"{(rr - T_END)*1e3:>36.4f}" if not math.isnan(rr) else f"{'never >= 1 mV':>36}"
        re_s = f"{(re_ - T_END)*1e3:>27.4f}" if not math.isnan(re_) else f"{'never':>27}"
        print(f"{p:<12}{rr_s}{re_s}{abs(d[p][i_end])*1e3:>20.4f}")
    print()

    # 3. VX and VY prediction from VSAMPLE recovery
    print("=== 3. VX and VY prediction, t_pred = t_VS + tau ln(dV / 1 mV) ===")
    t_vs = rec_raw["V(VSAMPLE)"]
    i_vs = int(np.searchsorted(t, t_vs))
    print(f"t_VS (raw recovery of VSAMPLE) = {t_vs*1e3:.4f} ms, {1e3*(t_vs-T_END):.4f} ms after t_end")
    print(f"{'probe':<8}{'dV at t_VS, centred mean (mV)':>30}{'dV raw (mV)':>13}{'t_meas (ms)':>13}"
          f"{'t_pred (ms)':>13}{'error (% of t_meas - t_end)':>28}{'fit tau (ms)':>14}")
    for p in ("V(VX)", "V(VY)"):
        dV = abs(env[p][i_vs])
        dV_raw = abs(d[p][i_vs])
        if dV <= THR:
            print(f"{p:<8}{dV*1e3:>30.4f}  already below 1 mV at t_VS")
            continue
        t_pred = t_vs + TAU_FAST * math.log(dV / THR)
        err = 100 * (t_pred - rec_raw[p]) / (rec_raw[p] - T_END)
        tau_fit = fit_tau(t, env[p], t_vs, rec_raw[p] + 0.02)
        print(f"{p:<8}{dV*1e3:>30.4f}{dV_raw*1e3:>13.4f}{(rec_raw[p]-T_END)*1e3+1e3*T_END:>13.4f}"
              f"{t_pred*1e3:>13.4f}{err:>28.2f}{tau_fit*1e3:>14.3f}")
    print("(t_meas and t_pred are absolute times in ms; error is relative to the time after t_end)")
    print()
    print("Scaled to tau = 0.1 s (RC part x 10, dV unchanged):")
    for p in ("V(VX)", "V(VY)"):
        dV = abs(env[p][i_vs])
        if dV <= THR:
            continue
        t_meas_scaled = t_vs + (rec_raw[p] - t_vs) * (TAU_DESIGN / TAU_FAST)
        t_pred_scaled = t_vs + TAU_DESIGN * math.log(dV / THR)
        print(f"  {p:<8} measured (scaled) {1e3*(t_meas_scaled-T_END):.2f} ms after t_end, "
              f"predicted {1e3*(t_pred_scaled-T_END):.2f} ms after t_end")
    print()

    # 4. Saturation memory in VDIFF and HPF
    print("=== 4. Saturation memory (envelope after t_end) ===")
    i_end = int(np.searchsorted(t, T_END))
    offsets_ms = [0.0, 0.1, 0.5, 1, 2, 3, 5, 8, 10, 15, 20, 30]
    print(f"{'t - t_end (ms)':>16}{'VDIFF raw (mV)':>16}{'HPF raw (mV)':>14}{'HPF env (mV)':>14}"
          f"{'VSAMPLE env (mV)':>18}{'VX env (mV)':>13}")
    for o in offsets_ms:
        k = int(np.searchsorted(t, T_END + o * 1e-3))
        print(f"{o:>16.2f}{1e3*d['V(VDIFF)'][k]:>16.4f}{1e3*d['V(HPF)'][k]:>14.4f}"
              f"{1e3*env['V(HPF)'][k]:>14.4f}{1e3*env['V(VSAMPLE)'][k]:>18.4f}{1e3*env['V(VX)'][k]:>13.4f}")
    print()
    # Sliding-maximum envelope of the fast transient. Its window starts one period after
    # t_end, so no burst sample enters the fit. The fit window is t_end + 1 ms to t_end + 4 ms.
    env_hpf = sliding_max(d["V(HPF)"], T_PER)
    env_vs = sliding_max(d["V(VSAMPLE)"], T_PER)
    tau_hpf = fit_tau(t, env_hpf, T_END + 1e-3, T_END + 4e-3)
    tau_vs = fit_tau(t, env_vs, T_END + 1e-3, T_END + 4e-3)
    print(f"HPF max-envelope decay constant, t_end + 1 ms to t_end + 4 ms: {tau_hpf*1e3:.4f} ms "
          f"(Q / (pi f0) with Q = 1 and f0 = 517 Hz gives {1e3/(math.pi*F_OSC):.4f} ms)")
    print(f"VSAMPLE max-envelope decay constant, same window: {tau_vs*1e3:.4f} ms")
    vdiff_max_after = np.max(np.abs(d["V(VDIFF)"][i_end + int(1e-3 / DT):]))
    print(f"max |VDIFF difference| after t_end + 1 ms: {vdiff_max_after*1e3:.4f} mV")
    print()

    # 5. Linear theory of the fast decay (HP and LP poles, no burst)
    print("=== 5. Linear theory: free-response poles of the HP and LP chain ===")
    for f0, tau_ms, Q in theory_poles():
        print(f"pole pair: f0 = {f0:.2f} Hz, Q = {Q:.4f}, decay constant tau = Q / (pi f0) = {tau_ms:.4f} ms")
    print(f"index estimate (Q = 1 at f_osc): {1e3/(math.pi*F_OSC):.4f} ms")
    print()

    # 6. Replay test: the LP stage is linear, so VSAMPLE difference should equal the
    #    LP transfer function applied to the simulated HPF difference, if the LP op amp
    #    does not add memory of its own.
    from scipy.signal import lsim
    C3, C4 = 33e-9, 130e-9
    R21 = R22 = 4.64e3
    g21, g22 = 1 / R21, 1 / R22
    num = [g21 * g22]
    den = [C3 * C4, C3 * (g21 + g22), g21 * g22]   # highest power first
    m_rep = t >= T_END - 5e-3
    tr = t[m_rep]
    u = d["V(HPF)"][m_rep]
    _, y_rep, _ = lsim((num, den), U=u, T=tr)
    y_sim = d["V(VSAMPLE)"][m_rep]
    k_end = int(np.searchsorted(tr, T_END))
    print("=== 6. Replay of the simulated HPF difference through the linear LP stage ===")
    print(f"{'t - t_end (ms)':>16}{'VSAMPLE sim (mV)':>18}{'LP replay (mV)':>16}{'difference (mV)':>17}")
    for o in (0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 8.0, 10.0):
        k = int(np.searchsorted(tr, T_END + o * 1e-3))
        print(f"{o:>16.2f}{1e3*y_sim[k]:>18.4f}{1e3*y_rep[k]:>16.4f}{1e3*(y_sim[k]-y_rep[k]):>17.4f}")
    n_env = int(round(T_PER / DT)) | 1
    yp_s = np.concatenate([np.zeros(n_env // 2), np.abs(y_sim), np.zeros(n_env // 2)])
    yp_r = np.concatenate([np.zeros(n_env // 2), np.abs(y_rep), np.zeros(n_env // 2)])
    from numpy.lib.stride_tricks import sliding_window_view
    env_s = sliding_window_view(yp_s, n_env).max(axis=1)
    env_r = sliding_window_view(yp_r, n_env).max(axis=1)
    tau_s = fit_tau(tr, env_s, T_END + 2e-3, T_END + 8e-3)
    tau_r = fit_tau(tr, env_r, T_END + 2e-3, T_END + 8e-3)
    print(f"max-envelope decay, t_end + 2 ms to t_end + 8 ms: simulated VSAMPLE {tau_s*1e3:.4f} ms, "
          f"LP replay {tau_r*1e3:.4f} ms, linear pole theory 0.6032 ms (lowest)")
    rec_r = last_exceed(tr, y_rep, T_END)
    print(f"last |LP replay| >= 1 mV after t_end: {(rec_r - T_END)*1e3:.4f} ms (simulated VSAMPLE: "
          f"{(rec_raw['V(VSAMPLE)'] - T_END)*1e3:.4f} ms)")
    print()

    # 7. Plot
    fig, ax = plt.subplots(figsize=(7.5, 4.6))
    m = t >= T_END - 1e-3
    tt = (t[m] - T_END) * 1e3
    for p in PROBES:
        ax.semilogy(tt, np.maximum(sliding_max(d[p], T_PER)[m], 1e-9) * 1e3, lw=0.9,
                    label=f"{p} max envelope")
    ax.axhline(1.0, color="k", ls="--", lw=0.8, label="1 mV")
    ax.set_xlabel("time after end of burst (ms)")
    ax.set_ylabel("|difference| (mV), max over one period")
    ax.set_xlim(-1, 60)
    ax.set_ylim(1e-3, 3e3)
    ax.set_title("P-16: recovery after 10-period overload burst (aburst 0.5 V minus 0)")
    ax.legend(fontsize=7)
    ax.grid(True, which="both", lw=0.3)
    fig.tight_layout()
    PLOT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(PLOT, dpi=130)
    print(f"plot written: {PLOT}")


if __name__ == "__main__":
    main()
