"""P-17 square-wave excitation through the band-pass (circuits/chain_ss.cir).

Reads two runs under sim-runs/:
  P17sq_square  circuits/chain_ss_P17sq.cir (asin = 0, asq = 15 mV, a square of
                +/-15 mV differential), .TRAN 0 0.15 0 2u, .IC VX = VY = 2.5 V.
  P17sin_sine   chain_ss.cir (asin = 15 mV, asq = 0), same analysis.

Settled values: time-weighted trapezoid mean over the last 20 whole periods of
517 Hz (38.685 ms, from 111.315 ms to 150 ms). The window before it is the
settling check.

Harmonic check: a least-squares fit of a DC term and the 1f to 7f sinusoids of
VSAMPLE on a 0.5 us grid over the same window. The input square has harmonic
amplitudes 4 A / (n pi) (A = asq = 15 mV) with the same phase reference as the
sine (sin convention). The ratio of the VSAMPLE harmonic to the input harmonic
is the measured H(n f). It is compared with the ideal chain H(n f).

Ideal sums (from the ideal transfer function, n odd up to 3999):
  VX - 2.5 V = -(8A/pi^2) sum_n |H_n| cos(phi_n) / n^2
  VY - 2.5 V = -(8A/pi^2) sum_n |H_n| cos(phi_n + n w tau) / n^2,  tau = 482.6 us
  The entry's VY value (+5.00 mV) uses tau = T/4. This script prints both.

Run from the project root:
    python docs/sim-results/scripts/P-17_square.py
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

PLOT = ROOT / "docs/sim-results/plots/P-17_square.png"

F = 517.0
T = 1.0 / F
W = 2 * np.pi * F
TW = 20 * T
T_END = 0.15
T0 = T_END - TW
TP0 = T0 - TW
TAU = 10e3 * 1e-6
TAU_Y = 482.6e-6
A = 15e-3                  # asq = asin = 15 mV
VREF = 2.5
DT = 0.5e-6

# Ideal chain (same stage values as P-09_chain.py)
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
    return 11.0 * h_hp(f) * h_lp(f)


def tw_mean(t, y, t0, t1):
    inside = (t > t0) & (t < t1)
    tt = np.concatenate([[t0], t[inside], [t1]])
    yy = np.interp(tt, t, y)
    return np.trapezoid(yy, tt) / (t1 - t0)


def fit_harmonics(t, y, t0, t1, nmax=7):
    """DC plus harmonics 1..nmax. Returns dc and the complex amplitudes Z_k with
    y ~ dc + Re[Z_k exp(j k W t)] summed over k (sin convention of the input)."""
    tg = np.arange(t0, t1, DT)
    yg = np.interp(tg, t, y)
    cols = [np.ones_like(tg)]
    for k in range(1, nmax + 1):
        cols.append(np.cos(k * W * tg))
        cols.append(np.sin(k * W * tg))
    M = np.column_stack(cols)
    coef, *_ = np.linalg.lstsq(M, yg, rcond=None)
    z = {}
    for k in range(1, nmax + 1):
        a, b = coef[2 * k - 1], coef[2 * k]
        z[k] = a - 1j * b
    return coef[0], z


def ideal_sums(amp, tau_y, nmax=3999, h=None):
    ns = np.arange(1, nmax + 1, 2)
    H = np.array([h_chain(n * F) for n in ns])
    amp_n = (4 * amp / (ns * np.pi)) * np.abs(H)
    vx = -(2 / np.pi) * np.sum(amp_n / ns * np.cos(np.angle(H)))
    vy = -(2 / np.pi) * np.sum(amp_n / ns * np.cos(np.angle(H) + ns * W * tau_y))
    return vx, vy


def load(name):
    secs = read_csdf(str(ROOT / f"sim-runs/{name}/{name}.csd"))
    return secs[0]


def main():
    lines = []
    lines.append(f"Window: {T0*1e3:.4f} ms to {T_END*1e3:.4f} ms ({TW*1e3:.4f} ms = 20 periods)")
    lines.append(f"Prior window: {TP0*1e3:.4f} ms to {T0*1e3:.4f} ms")
    lines.append("")

    runs = {}
    for name in ("P17sq_square", "P17sin_sine"):
        s = load(name)
        t = np.asarray(s.x, float)
        d = {}
        for sig in ["V(VSAMPLE)", "V(VX)", "V(VY)"]:
            y = np.asarray(s[sig], float)
            d[sig] = dict(
                m=tw_mean(t, y, T0, T_END),
                mp=tw_mean(t, y, TP0, T0),
                y=y,
            )
        dc, z = fit_harmonics(t, d["V(VSAMPLE)"]["y"], T0, T_END)
        d["V(VSAMPLE)"]["z"] = z
        d["V(VSAMPLE)"]["dc"] = dc
        runs[name] = (t, d)

    # Settling
    lines.append("== Settling check (tau = 10 ms)")
    lines.append("| Run | Node | TW mean (V) | Last minus prior (uV) | B from data (uV) |")
    lines.append("|---|---|---|---|---|")
    fac = np.exp(TW / TAU)
    for name, (_, d) in runs.items():
        for sig in ["V(VSAMPLE)", "V(VX)", "V(VY)"]:
            diff = d[sig]["m"] - d[sig]["mp"]
            b = diff / (1 - fac)
            lines.append(f"| {name} | {sig} | {d[sig]['m']:.7f} | {diff*1e6:.2f} | {b*1e6:.3f} |")
    lines.append("")

    # Demodulator outputs
    _, dq = runs["P17sq_square"]
    _, ds = runs["P17sin_sine"]
    vxq = dq["V(VX)"]["m"] - VREF
    vyq = dq["V(VY)"]["m"] - VREF
    vxs = ds["V(VX)"]["m"] - VREF
    vys = ds["V(VY)"]["m"] - VREF
    ideal_sq_vx, ideal_sq_vy = ideal_sums(A, TAU_Y)
    ideal_sq_vx_nom, ideal_sq_vy_nom = ideal_sums(A, T / 4)
    # ideal sine, fundamental only
    H1 = h_chain(F)
    ideal_sin_vx = -(2 / np.pi) * abs(H1) * A * np.cos(np.angle(H1))
    ideal_sin_vy = -(2 / np.pi) * abs(H1) * A * np.cos(np.angle(H1) + W * TAU_Y)
    ideal_fund_vx = -(8 * A / np.pi ** 2) * abs(H1) * np.cos(np.angle(H1))
    ideal_fund_vy = -(8 * A / np.pi ** 2) * abs(H1) * np.cos(np.angle(H1) + W * TAU_Y)

    lines.append("== Demodulator outputs, TW means relative to 2.5 V (mV)")
    lines.append("| Quantity | Measured | Ideal, full sum (tau = 482.6 us) | Diff | Diff (%) | Entry value |")
    lines.append("|---|---|---|---|---|---|")
    lines.append(f"| Square VX - 2.5 V | {vxq*1e3:.4f} | {ideal_sq_vx*1e3:.4f} | {(vxq-ideal_sq_vx)*1e3:+.4f} | {100*(vxq-ideal_sq_vx)/abs(ideal_sq_vx):+.3f} | -132.94 |")
    lines.append(f"| Square VY - 2.5 V | {vyq*1e3:.4f} | {ideal_sq_vy*1e3:.4f} | {(vyq-ideal_sq_vy)*1e3:+.4f} | - | +5.00 (tau = T/4, ideal {ideal_sq_vy_nom*1e3:.4f}) |")
    lines.append(f"| Square R | {np.hypot(vxq, vyq)*1e3:.4f} | {np.hypot(ideal_sq_vx, ideal_sq_vy)*1e3:.4f} | {(np.hypot(vxq,vyq)-np.hypot(ideal_sq_vx,ideal_sq_vy))*1e3:+.4f} | - | 133.03 |")
    lines.append(f"| Sine VX - 2.5 V | {vxs*1e3:.4f} | {ideal_sin_vx*1e3:.4f} | {(vxs-ideal_sin_vx)*1e3:+.4f} | {100*(vxs-ideal_sin_vx)/abs(ideal_sin_vx):+.3f} | - |")
    lines.append(f"| Sine VY - 2.5 V | {vys*1e3:.4f} | {ideal_sin_vy*1e3:.4f} | {(vys-ideal_sin_vy)*1e3:+.4f} | - | - |")
    lines.append("")
    ratio = vxq / vxs
    ideal_ratio = ideal_sq_vx / ideal_sin_vx
    lines.append(f"Square / sine VX ratio: measured {ratio:.5f}, ideal {ideal_ratio:.5f} (entry 1.2570). Difference {100*(ratio-ideal_ratio)/ideal_ratio:+.3f} %.")
    lines.append("")

    # Fundamental-only comparison from the measured square run
    z = dq["V(VSAMPLE)"]["z"]
    z_in = {k: (4 * A / (k * np.pi)) * np.exp(-1j * np.pi / 2) for k in (1, 3, 5, 7)}
    H_meas = {k: z[k] / z_in[k] for k in (1, 3, 5, 7)}
    H_ideal = {k: h_chain(k * F) for k in (1, 3, 5, 7)}
    lines.append("== Harmonic transfer of VSAMPLE from the square run (input harmonic 4A/(n pi), A = 15 mV)")
    lines.append("| n | Freq (Hz) | |H| meas (V/V) | |H| ideal (V/V) | Diff (%) | Phase meas (deg) | Phase ideal (deg) | Diff (deg) |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for k in (1, 3, 5, 7):
        hm, hi = H_meas[k], H_ideal[k]
        dphi = np.degrees(np.angle(hm / hi))
        lines.append(
            f"| {k} | {k*F:.0f} | {abs(hm):.5f} | {abs(hi):.5f} | {100*(abs(hm)-abs(hi))/abs(hi):+.3f} "
            f"| {np.degrees(np.angle(hm)):.3f} | {np.degrees(np.angle(hi)):.3f} | {dphi:+.3f} |"
        )
    lines.append("")
    # Sine run: VSAMPLE fundamental against input A
    _, dsin = runs["P17sin_sine"]
    zs = dsin["V(VSAMPLE)"]["z"][1]
    hs = zs / (A * np.exp(-1j * np.pi / 2))
    lines.append(f"Sine run, VSAMPLE fundamental: |H| = {abs(hs):.5f} V/V (ideal {abs(H1):.5f}), phase = {np.degrees(np.angle(hs)):.3f} deg (ideal {np.degrees(np.angle(H1)):.3f} deg).")
    lines.append(f"Sine run, VSAMPLE DC level: {dsin['V(VSAMPLE)']['m']:.7f} V. Square run: {dq['V(VSAMPLE)']['m']:.7f} V.")
    lines.append("")

    # Fundamental-only check and X shift
    H1m = z[1] / z_in[1]
    vx_fund_meas = -(8 * A / np.pi ** 2) * abs(H1m) * np.cos(np.angle(H1m))
    lines.append("== X shift from the harmonics")
    lines.append("| Quantity | Value (mV) | Shift (%) |")
    lines.append("|---|---|---|")
    lines.append(f"| VX fundamental only, measured fit (mV) | {vx_fund_meas*1e3:.4f} | - |")
    lines.append(f"| VX fundamental only, ideal (mV) | {ideal_fund_vx*1e3:.4f} | - |")
    lines.append(f"| VX square, measured (mV) | {vxq*1e3:.4f} | {100*(vxq/vx_fund_meas-1):+.3f} (vs measured fundamental) |")
    lines.append(f"| VX square, ideal full sum (mV) | {ideal_sq_vx*1e3:.4f} | {100*(ideal_sq_vx/ideal_fund_vx-1):+.3f} (vs ideal fundamental) |")
    lines.append("")

    # Ideal sums with the measured harmonics 1..7 and ideal above 7
    ns = np.arange(1, 8, 2)
    part_meas = -(2 / np.pi) * sum((4 * A / (n * np.pi)) * abs(H_meas[n]) * np.cos(np.angle(H_meas[n])) / n for n in ns)
    part_ideal = -(2 / np.pi) * sum((4 * A / (n * np.pi)) * abs(H_ideal[n]) * np.cos(np.angle(H_ideal[n])) / n for n in ns)
    vy_fund_meas = -(8 * A / np.pi ** 2) * abs(H_meas[1]) * np.cos(np.angle(H_meas[1]) + W * TAU_Y)
    vy_fund_ideal = -(8 * A / np.pi ** 2) * abs(H_ideal[1]) * np.cos(np.angle(H_ideal[1]) + W * TAU_Y)
    lines.append(f"VY fundamental only, measured fit: {vy_fund_meas*1e3:.4f} mV, ideal: {vy_fund_ideal*1e3:.4f} mV, difference {(vy_fund_meas-vy_fund_ideal)*1e3:+.4f} mV.")
    vy_part_meas = -(2 / np.pi) * sum((4 * A / (n * np.pi)) * abs(H_meas[n]) * np.cos(np.angle(H_meas[n]) + n * W * TAU_Y) / n for n in ns)
    vy_part_ideal = -(2 / np.pi) * sum((4 * A / (n * np.pi)) * abs(H_ideal[n]) * np.cos(np.angle(H_ideal[n]) + n * W * TAU_Y) / n for n in ns)
    lines.append(f"VY sum over n = 1 to 7: measured {vy_part_meas*1e3:.4f} mV, ideal {vy_part_ideal*1e3:.4f} mV, difference {(vy_part_meas-vy_part_ideal)*1e3:+.4f} mV.")
    lines.append(f"Sum over n = 1 to 7 only: measured {part_meas*1e3:.4f} mV, ideal {part_ideal*1e3:.4f} mV. Difference {(part_meas-part_ideal)*1e3:+.4f} mV.")
    lines.append(f"Ideal sum from n = 9 upward: {(ideal_sq_vx-part_ideal)*1e3:+.4f} mV.")
    lines.append("")

    # Amplifier-free check: how much the Y timing moves the square VY
    lines.append(f"Y timing term on the square VY: ideal with tau = 482.6 us {ideal_sq_vy*1e3:.4f} mV, with tau = T/4 {ideal_sq_vy_nom*1e3:.4f} mV, shift {(ideal_sq_vy-ideal_sq_vy_nom)*1e3:+.4f} mV.")
    lines.append("")

    text = "\n".join(lines)
    print(text)

    fig, ax = plt.subplots(1, 2, figsize=(8, 3.6))
    ns_plot = [1, 3, 5, 7]
    ax[0].semilogy(ns_plot, [abs(H_meas[k]) for k in ns_plot], "o", label="measured (square run)")
    ax[0].semilogy(ns_plot, [abs(H_ideal[k]) for k in ns_plot], "x", label="ideal")
    ax[0].set_xlabel("harmonic n")
    ax[0].set_ylabel("|H(n f)| (V/V)")
    ax[0].legend(fontsize=7)
    ax[0].set_title("Band-pass gain at odd harmonics")
    t, dd = runs["P17sq_square"]
    m = (t > T0) & (t <= T_END)
    ax[1].plot((t[m] - T0) * 1e3, dd["V(VX)"]["y"][m] - VREF, label="VX - 2.5 V, square")
    ax[1].plot((t[m] - T0) * 1e3, dd["V(VY)"]["y"][m] - VREF, label="VY - 2.5 V, square")
    ax[1].set_xlabel("time in last window (ms)")
    ax[1].set_ylabel("V (V)")
    ax[1].legend(fontsize=7)
    ax[1].set_title("Square run, last 20 periods")
    fig.tight_layout()
    fig.savefig(PLOT, dpi=120)


if __name__ == "__main__":
    main()
