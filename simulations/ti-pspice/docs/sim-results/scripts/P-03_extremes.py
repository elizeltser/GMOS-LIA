"""P-03 demodulator extremes: steady values against absolute values and transients.

The 50-period absolute max and min of a demodulator output can come from short
transients at the reference edges, not from the steady waveform. This script:

1. Compares the steady extremes (from the two-period cache, sim-runs/<run>/<run>_waves.npz)
   with the theory of the README, for every step.
2. Streams the raw .csd file of two chosen steps (P03a ost = 0.4 V, P03b ost = 0.25 V),
   takes the 1 us grid over the last 50 periods, and subtracts the steady waveform at the
   same phase. The largest excursion of this difference is the transient. The script reports
   its height, its time within the window, its duration and the nearest reference edge.
3. Fits the 1f component of V(VX) and V(VY) from the two-period cache, and compares it with
   the predicted 1f amplitude (4/pi) x ost x 1/(2 pi f tau) at f = 517 Hz, tau = 0.1 s.

Run from the project root:
    python docs/sim-results/scripts/P-03_extremes.py
"""

import importlib.util
import math
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]
PLOT_DIR = ROOT / "docs/sim-results/plots"

F_OSC = 517.0
T = 1.0 / F_OSC
T_END = 1.0
N_PER = 50
DT = 1e-6
MID = 2.5
AMP = 2.0
TAU = 0.1
T_HALF_OFFSET = 482.6e-6   # delay of the Y reference (V6)
FLOOR_TOL = 0.01           # V, excursion above which a sample counts as transient

# Load the parser from the offset script (a module name with a hyphen cannot be imported directly)
_spec = importlib.util.spec_from_file_location("p03off", ROOT / "docs/sim-results/scripts/P-03_offset.py")
p03off = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(p03off)

RUNS = {
    "P03a_ost_p0": {"demod": "V(VX_DEMOD)", "label": "VX_DEMOD", "p": 0.0, "chan": "vx"},
    "P03b_ost_p90": {"demod": "V(VY_DEMOD)", "label": "VY_DEMOD", "p": 90.0, "chan": "vy"},
}
TRANSIENT_STEPS = {"P03a_ost_p0": 0.4, "P03b_ost_p90": 0.25}


def theory_range(name, ost):
    """Steady theory of the demodulator output, from the judge's analysis."""
    a = abs(ost)
    if name == "P03a_ost_p0":
        return 0.5 - a, 2.5 + a          # X demodulator at p = 0
    return 2.5 - a, 4.5 + a              # Y demodulator at p = 90


def steady_table():
    out = {}
    for name in RUNS:
        w = np.load(ROOT / "sim-runs" / name / f"{name}_waves.npz")
        ost = w["ost"]
        dem = w["dem"]
        rows = []
        for i in range(len(ost)):
            lo_th, hi_th = theory_range(name, ost[i])
            rows.append((ost[i], dem[i].min(), dem[i].max(), lo_th, hi_th,
                         np.percentile(dem[i], 0.1), np.percentile(dem[i], 99.9)))
        out[name] = rows
    return out


def phase_of(t_rel):
    """Position of times t_rel (s, relative to the window start) in the two-period cache."""
    return np.mod(t_rel, 2 * T)


def edge_distance(t_abs):
    """Distance in us from each time to the nearest X edge and to the nearest Y edge."""
    half = T / 2
    a = np.mod(t_abs, half)
    dx = np.minimum(a, half - a)
    ay = np.mod(t_abs - T_HALF_OFFSET, half)
    dy = np.minimum(ay, half - ay)
    return dx * 1e6, dy * 1e6


def transient(name, target):
    """Stream the raw section at the step target and locate the largest transient."""
    cfg = RUNS[name]
    csd = ROOT / "sim-runs" / name / f"{name}.csd"
    sec = None
    for s in p03off.iter_sections(csd):
        if s["step"] is not None and abs(s["step"] - target) < 1e-6:
            sec = s
            break
    if sec is None:
        raise SystemExit(f"step {target} not found in {name}")
    t = np.asarray(sec["x"])
    names = sec["names"]
    idx = {n.upper(): i for i, n in enumerate(names)}
    raw = np.asarray(sec["vals"][idx[cfg["demod"].upper()]])

    # Window: last 50 periods, 1 us grid
    t1 = T_END - N_PER * T
    grid = np.linspace(t1, T_END, round((T_END - t1) / DT) + 1)
    yg = np.interp(grid, t, raw)

    # Steady reference from the two-period cache, at the same phase
    w = np.load(ROOT / "sim-runs" / name / f"{name}_waves.npz")
    ost_all = w["ost"]
    i = int(np.argmin(np.abs(ost_all - target)))
    cache_t = w["t"]
    cache_dem = w["dem"][i]
    tw = T_END - 2 * T
    ref = np.interp(phase_of(grid - tw), cache_t, cache_dem)
    exc = yg - ref

    k_hi = int(np.argmax(exc))
    k_lo = int(np.argmin(exc))
    sel = np.abs(exc) > FLOOR_TOL
    dx, dy = edge_distance(grid)

    # Count separate events (runs of samples above the tolerance)
    events = []
    if sel.any():
        edges = np.diff(np.concatenate(([0], sel.astype(int), [0])))
        starts = np.where(edges == 1)[0]
        ends = np.where(edges == -1)[0]
        for s0, s1 in zip(starts, ends):
            seg = exc[s0:s1]
            kk = s0 + int(np.argmax(np.abs(seg)))
            events.append({
                "t_ms": (grid[s0] - t1) * 1e3,
                "dur_us": (s1 - s0) * DT * 1e6,
                "peak_V": float(exc[kk]),
                "t_peak_ms": (grid[kk] - t1) * 1e3,
                "near": "X" if dx[kk] < dy[kk] else "Y",
                "d_edge_us": float(min(dx[kk], dy[kk])),
            })

    # Steady extremes of the 50-period window and the reference extremes
    res = {
        "name": name, "ost": target,
        "abs_min": float(yg.min()), "abs_max": float(yg.max()),
        "p01": float(np.percentile(yg, 0.1)), "p999": float(np.percentile(yg, 99.9)),
        "ref_min": float(ref.min()), "ref_max": float(ref.max()),
        "exc_hi": float(exc[k_hi]), "t_hi_ms": float((grid[k_hi] - t1) * 1e3),
        "exc_lo": float(exc[k_lo]), "t_lo_ms": float((grid[k_lo] - t1) * 1e3),
        "events": events,
        "n_events": len(events),
        "n_samples": int(sel.sum()),
        "abs_min_t_ms": float((grid[int(np.argmin(yg))] - t1) * 1e3),
        "abs_max_t_ms": float((grid[int(np.argmax(yg))] - t1) * 1e3),
        "edge_max_hi": ("X" if dx[k_hi] < dy[k_hi] else "Y", float(min(dx[k_hi], dy[k_hi]))),
        "edge_max_lo": ("X" if dx[k_lo] < dy[k_lo] else "Y", float(min(dx[k_lo], dy[k_lo]))),
    }
    return res


def first_harmonic(name, k=1):
    w = np.load(ROOT / "sim-runs" / name / f"{name}_waves.npz")
    t = w["t"]
    ost = w["ost"]
    out = []
    for i in range(len(ost)):
        amps = []
        for chan in ("vx", "vy"):
            y = w[chan][i]
            cols = [np.ones_like(t), np.sin(2 * np.pi * F_OSC * t), np.cos(2 * np.pi * F_OSC * t),
                    np.sin(4 * np.pi * F_OSC * t), np.cos(4 * np.pi * F_OSC * t)]
            c, *_ = np.linalg.lstsq(np.column_stack(cols), y, rcond=None)
            amps.append(math.hypot(c[1], c[2]) * 1e3)
        out.append((ost[i], amps[0], amps[1]))
    return out


def predicted_1f_per_volt():
    return (4.0 / math.pi) / (2 * math.pi * F_OSC * TAU) * 1e3   # mV per V


def main():
    print("== Steady extremes from the two-period cache, theory and absolute values")
    tab = steady_table()
    for name, rows in tab.items():
        print(name)
        print("ost  steady_min  theory_min  steady_max  theory_max  p0.1  p99.9")
        for r in rows:
            print(f"{r[0]:+.3f} {r[1]:.5f} {r[3]:+.5f} {r[2]:.5f} {r[4]:.5f} {r[5]:.5f} {r[6]:.5f}")
        print()

    print("== Transient analysis of the two raw sections (last 50 periods)")
    trans = {}
    for name, target in TRANSIENT_STEPS.items():
        r = transient(name, target)
        trans[name] = r
        print(f"{name} ost = {target:+.2f} V, {RUNS[name]['label']}")
        print(f"  absolute min {r['abs_min']:.5f} V at {r['abs_min_t_ms']:.4f} ms in window, "
              f"absolute max {r['abs_max']:.5f} V at {r['abs_max_t_ms']:.4f} ms")
        print(f"  steady (cache) min {r['ref_min']:.5f} V, max {r['ref_max']:.5f} V")
        print(f"  percentile 0.1 {r['p01']:.5f} V, 99.9 {r['p999']:.5f} V")
        print(f"  largest excursion up {r['exc_hi']*1e3:+.3f} mV at {r['t_hi_ms']:.4f} ms "
              f"(nearest {r['edge_max_hi'][0]} edge {r['edge_max_hi'][1]:.3f} us)")
        print(f"  largest excursion down {r['exc_lo']*1e3:+.3f} mV at {r['t_lo_ms']:.4f} ms "
              f"(nearest {r['edge_max_lo'][0]} edge {r['edge_max_lo'][1]:.3f} us)")
        print(f"  samples with |excursion| > {FLOOR_TOL*1e3:.0f} mV: {r['n_samples']} us, {r['n_events']} events")
        for e in r["events"]:
            print(f"    event at {e['t_ms']:.4f} ms, duration {e['dur_us']:.2f} us, "
                  f"peak {e['peak_V']*1e3:+.1f} mV at {e['t_peak_ms']:.4f} ms, "
                  f"nearest {e['near']} edge {e['d_edge_us']:.3f} us")
        print()

    print("== 1f ripple from the cache against the derived value")
    print(f"predicted 1f amplitude = (4/pi)/(2 pi f tau) = {predicted_1f_per_volt():.4f} mV per V")
    for name in ("P03a_ost_p0", "P03b_ost_p90"):
        rows = first_harmonic(name)
        print(name)
        print("ost  VX_1f_mV  VX_1f/|ost|  VY_1f_mV  VY_1f/|ost|")
        for ost, ax, ay in rows:
            if abs(ost) < 1e-9:
                continue
            if abs(ost) <= 0.41:
                print(f"{ost:+.3f} {ax:.4f} {ax/abs(ost):.4f} {ay:.4f} {ay/abs(ost):.4f}")
        print()

    # Figure: steady and absolute demodulator extremes against ost, with theory
    PLOT_DIR.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.5), sharey=True)
    for ax, name in zip(axes, RUNS):
        rows = tab[name]
        ost = np.array([r[0] for r in rows])
        ax.plot(ost, [r[2] for r in rows], "^", ms=4, color="tab:red", label="steady max (2-period cache)")
        ax.plot(ost, [r[1] for r in rows], "v", ms=4, color="tab:purple", label="steady min (2-period cache)")
        lo_th = [theory_range(name, o)[0] for o in ost]
        hi_th = [theory_range(name, o)[1] for o in ost]
        ax.plot(ost, hi_th, "k--", lw=0.8, label="theory max")
        ax.plot(ost, lo_th, "k:", lw=0.8, label="theory min (before clipping)")
        ax.axhline(0, color="k", lw=0.6)
        ax.axhline(5.0, color="k", lw=0.6, ls="--")
        ax.set_title(f"{RUNS[name]['label']} steady extremes ({name})", fontsize=9)
        ax.set_xlabel("ost [V]")
        ax.grid(alpha=0.3)
        ax.legend(fontsize=7, loc="best")
    axes[0].set_ylabel("voltage [V]")
    fig.tight_layout()
    fig.savefig(PLOT_DIR / "P-03_demod_steady_vs_theory.png", dpi=150)
    plt.close(fig)
    print(f"wrote {PLOT_DIR / 'P-03_demod_steady_vs_theory.png'}")


if __name__ == "__main__":
    main()
