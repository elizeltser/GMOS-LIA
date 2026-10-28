"""P-03 offset sweep and dynamic range analysis for the LIA baseline circuit.

Two runs are analysed:
  P03a_ost_p0   circuits/lia_baseline.cir, p = 0 deg, ost = -2 to 2 V in 0.1 V steps
  P03b_ost_p90  circuits/lia_baseline_p90.cir, p = 90 deg, ost = -2 to 2 V in 0.25 V steps

The .csd files are large (493 MB and 206 MB). The first run streams each file
section by section, so the whole text is never held in memory. Per step numbers
go to sim-runs/<run>/<run>_steps.csv, and the last two periods of each waveform
go to sim-runs/<run>/<run>_waves.npz. Later runs read only these caches.

Run from the project root:
    python docs/sim-results/scripts/P-03_offset.py
    python docs/sim-results/scripts/P-03_offset.py --rebuild   (re-parse the .csd files)
"""

import math
import re
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]
PLOT_DIR = ROOT / "docs/sim-results/plots"

F_OSC = 517.0              # Hz, input and reference frequency
T = 1.0 / F_OSC            # s, period
N_PER = 50                 # periods in the averaging window
DT_GRID = 1e-6             # s, grid spacing (as in P-01 and P-02)
T_END = 1.0                # s, run length
MID = 2.5                  # V, signal midpoint
AMP = 2.0                  # V, input amplitude
VDC = 5.0                  # V, supply
K = 2.0 * AMP / math.pi    # V, theory radius
SETTLE_K = 0.097e-3 / 1.27  # V/V, settling bias of the last-50-period mean (P-01)

RUNS = {
    "P03a_ost_p0": {"demod": "V(VX_DEMOD)", "dem_label": "VX_DEMOD", "p_deg": 0.0},
    "P03b_ost_p90": {"demod": "V(VY_DEMOD)", "dem_label": "VY_DEMOD", "p_deg": 90.0},
}

STEP_RE = re.compile(r"=\s*([-+0-9.eE]+)")
CSV_COLS = ["ost", "n_points", "vx_last", "vy_last", "vx_prev", "vy_prev",
            "vx_max", "vx_min", "vy_max", "vy_min", "vx_pp_mV", "vy_pp_mV",
            "vx_2f_mV", "vy_2f_mV", "dem_mean", "dem_min", "dem_max", "dem_pp_mV",
            "vx_first", "vy_first"]


def iter_sections(path):
    """Yield one dict per .STEP section, reading the file line by line."""
    sec = None
    want_names = False
    pending = False
    with open(path, "r", errors="replace") as f:
        for line in f:
            if line.startswith("#H"):
                if sec is not None:
                    yield sec
                sec = {"step": None, "x": [], "vals": None, "names": None}
                want_names = False
                pending = False
            elif sec is None:
                continue
            elif line.startswith("SUBTITLE="):
                m = STEP_RE.search(line)
                sec["step"] = float(m.group(1)) if m else None
            elif line.startswith("#N"):
                want_names = True
            elif want_names:
                sec["names"] = re.findall(r"'([^']*)'", line)
                sec["vals"] = [[] for _ in sec["names"]]
                want_names = False
            elif line.startswith("#C"):
                sec["x"].append(float(line.split()[1]))
                pending = True
            elif pending:
                toks = line.split()
                for i, tok in enumerate(toks[: len(sec["names"])]):
                    sec["vals"][i].append(float(tok.split(":")[0]))
                pending = False
    if sec is not None:
        yield sec


def window(t_raw, y_raw, t_start, t_stop):
    """Interpolate onto a 1 us grid over [t_start, t_stop]. Return grid, values and trapezoidal mean."""
    n = round((t_stop - t_start) / DT_GRID) + 1
    grid = np.linspace(t_start, t_stop, n)
    yg = np.interp(grid, t_raw, y_raw)
    mean = float(np.sum(0.5 * (yg[1:] + yg[:-1]) * np.diff(grid)) / (grid[-1] - grid[0]))
    return grid, yg, mean


def amp_at(grid, y, f, k):
    """Amplitude of the k-th harmonic of f in y, least squares on the grid."""
    cols = [np.ones_like(grid), np.sin(2 * np.pi * k * f * grid), np.cos(2 * np.pi * k * f * grid)]
    coef, *_ = np.linalg.lstsq(np.column_stack(cols), y, rcond=None)
    return float(np.hypot(coef[1], coef[2]))


def analyse(sec, dem_name):
    t = np.asarray(sec["x"])
    idx = {n.upper(): i for i, n in enumerate(sec["names"])}
    sig = {
        "vx": np.asarray(sec["vals"][idx["V(VX)"]]),
        "vy": np.asarray(sec["vals"][idx["V(VY)"]]),
        "dem": np.asarray(sec["vals"][idx[dem_name.upper()]]),
    }
    t1 = T_END - N_PER * T
    t0 = T_END - 2 * N_PER * T
    row = {"ost": sec["step"], "n_points": len(t)}
    for key in ("vx", "vy"):
        g, yg, m = window(t, sig[key], t1, T_END)
        _, _, mp = window(t, sig[key], t0, t1)
        row[f"{key}_last"] = m
        row[f"{key}_prev"] = mp
        row[f"{key}_max"] = float(yg.max())
        row[f"{key}_min"] = float(yg.min())
        row[f"{key}_pp_mV"] = float(yg.max() - yg.min()) * 1e3
        row[f"{key}_2f_mV"] = amp_at(g, yg, F_OSC, 2) * 1e3
        row[f"{key}_first"] = float(sig[key][0])
    g, yg, m = window(t, sig["dem"], t1, T_END)
    row["dem_mean"] = m
    row["dem_min"] = float(yg.min())
    row["dem_max"] = float(yg.max())
    row["dem_pp_mV"] = float(yg.max() - yg.min()) * 1e3
    tw = T_END - 2 * T
    gw, vxw, _ = window(t, sig["vx"], tw, T_END)
    _, vyw, _ = window(t, sig["vy"], tw, T_END)
    _, demw, _ = window(t, sig["dem"], tw, T_END)
    waves = {"vx": vxw, "vy": vyw, "dem": demw, "t": gw - tw}
    if abs(t[-1] - T_END) > 1e-12:
        print(f"  warning: section at ost {sec['step']} ends at {t[-1]}")
    return row, waves


def build(name):
    cfg = RUNS[name]
    csd = ROOT / "sim-runs" / name / f"{name}.csd"
    rows, wave_list = [], []
    for sec in iter_sections(csd):
        row, waves = analyse(sec, cfg["demod"])
        rows.append(row)
        wave_list.append(waves)
        print(f"  {name} ost = {row['ost']:+.3f}: VX {row['vx_last']:.6f} V, VY {row['vy_last']:.6f} V")
    order = np.argsort([r["ost"] for r in rows])
    rows = [rows[i] for i in order]
    wave_list = [wave_list[i] for i in order]
    arr = np.array([[r[c] for c in CSV_COLS] for r in rows])
    csv = ROOT / "sim-runs" / name / f"{name}_steps.csv"
    np.savetxt(csv, arr, delimiter=",", header=",".join(CSV_COLS), comments="", fmt="%.10g")
    np.savez(ROOT / "sim-runs" / name / f"{name}_waves.npz",
             t=wave_list[0]["t"],
             ost=np.array([r["ost"] for r in rows]),
             vx=np.vstack([w["vx"] for w in wave_list]),
             vy=np.vstack([w["vy"] for w in wave_list]),
             dem=np.vstack([w["dem"] for w in wave_list]))
    print(f"wrote {len(rows)} steps to {csv}")


def load(name):
    csv = ROOT / "sim-runs" / name / f"{name}_steps.csv"
    npz = ROOT / "sim-runs" / name / f"{name}_waves.npz"
    if "--rebuild" in sys.argv or not csv.exists() or not npz.exists():
        build(name)
    d = np.genfromtxt(csv, delimiter=",", names=True)
    w = np.load(npz)
    return d, {k: w[k] for k in ("t", "ost", "vx", "vy", "dem")}


def corr(v):
    """Settling-bias correction (P-01): moves the last-50-period mean toward its final value."""
    return v + SETTLE_K * (v - MID)


def departure(ost, dev, thr):
    """Walk outward from ost = 0 on each side. Return the last ost within thr and the first ost outside it."""
    res = {}
    for sign, label in ((+1, "pos"), (-1, "neg")):
        sel = [i for i in np.argsort(np.abs(ost)) if np.sign(ost[i]) in (0, sign)]
        last_ok, first_bad = 0.0, None
        for i in sel:
            if abs(ost[i]) < 1e-9:
                continue
            if abs(dev[i]) > thr:
                first_bad = float(ost[i])
                break
            last_ok = float(ost[i])
        res[label] = (last_ok, first_bad)
    return res


def fmt_dep(d):
    out = []
    for label in ("pos", "neg"):
        last_ok, first_bad = d[label]
        fb = "none in sweep" if first_bad is None else f"{first_bad:+.2f} V"
        out.append(f"{label}: last ok {last_ok:+.2f} V, first outside {fb}")
    return "; ".join(out)


def ost0_index(ost):
    return int(np.argmin(np.abs(ost)))


def main():
    res = {}
    for name in RUNS:
        d, waves = load(name)
        ost = d["ost"]
        vx = corr(d["vx_last"])
        vy = corr(d["vy_last"])
        i0 = ost0_index(ost)
        res[name] = dict(d=d, waves=waves, ost=ost, vx=vx, vy=vy,
                         vx_max=corr(d["vx_max"]), vx_min=corr(d["vx_min"]),
                         vy_max=corr(d["vy_max"]), vy_min=corr(d["vy_min"]),
                         dvx=(vx - vx[i0]) * 1e3, dvy=(vy - vy[i0]) * 1e3,
                         dmax_x=(corr(d["vx_max"]) - corr(d["vx_max"])[i0]) * 1e3,
                         dmax_y=(corr(d["vy_max"]) - corr(d["vy_max"])[i0]) * 1e3,
                         i0=i0)

    print("Theory: K = 2A/pi =", f"{K:.6f} V; ideal VX = {MID - K:.6f} V (p = 0), VY = 2.5 V + K sin(p - d)")
    print()

    for name, r in res.items():
        d = r["d"]
        print(f"== {name} (p = {RUNS[name]['p_deg']:.0f} deg, ost0 index {r['i0']}, n steps {len(r['ost'])})")
        print("ost  VXmean VYmean dVX_mV dVY_mV settleVX settleVY VXmax VXmin VYmax VYmin VXpp VYpp VX2f VY2f demMin demMax demPP")
        for i in range(len(r["ost"])):
            print(f"{r['ost'][i]:+.3f} {r['vx'][i]:.6f} {r['vy'][i]:.6f} {r['dvx'][i]:+.4f} {r['dvy'][i]:+.4f} "
                  f"{(d['vx_last'][i]-d['vx_prev'][i])*1e3:+.4f} {(d['vy_last'][i]-d['vy_prev'][i])*1e3:+.4f} "
                  f"{r['vx_max'][i]:.6f} {r['vx_min'][i]:.6f} {r['vy_max'][i]:.6f} {r['vy_min'][i]:.6f} "
                  f"{d['vx_pp_mV'][i]:.4f} {d['vy_pp_mV'][i]:.4f} {d['vx_2f_mV'][i]:.4f} {d['vy_2f_mV'][i]:.4f} "
                  f"{d['dem_min'][i]:.5f} {d['dem_max'][i]:.5f} {d['dem_pp_mV'][i]:.2f}")
        print()

    print("Departure points (contiguous from ost = 0, deviation from the ost = 0 value, mV):")
    for name, r in res.items():
        for ch, dev in (("VX mean", r["dvx"]), ("VY mean", r["dvy"]),
                        ("VX max", r["dmax_x"]), ("VY max", r["dmax_y"])):
            for thr in (1.0, 0.1):
                print(f"  {name} {ch}, threshold {thr} mV: {fmt_dep(departure(r['ost'], dev, thr))}")
    print()

    # Plots
    PLOT_DIR.mkdir(parents=True, exist_ok=True)
    labels = {"P03a_ost_p0": "P03a, p = 0 deg, 0.1 V steps", "P03b_ost_p90": "P03b, p = 90 deg, 0.25 V steps"}
    colors = {"P03a_ost_p0": "tab:blue", "P03b_ost_p90": "tab:orange"}

    # Figure 1: deviation from ost = 0
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8, 6.5), sharex=True)
    for name, r in res.items():
        ax1.plot(r["ost"], r["dvx"], "o-", ms=3.5, lw=0.8, color=colors[name], label=labels[name])
        ax2.plot(r["ost"], r["dvy"], "o-", ms=3.5, lw=0.8, color=colors[name], label=labels[name])
    for ax, ch in ((ax1, "VX"), (ax2, "VY")):
        ax.axhline(0, color="k", lw=0.7)
        for lim, ls in ((1.0, "--"), (0.1, ":")):
            ax.axhline(lim, color="grey", ls=ls, lw=0.8)
            ax.axhline(-lim, color="grey", ls=ls, lw=0.8)
        ax.axvspan(-0.5, 0.5, color="green", alpha=0.07, label="input inside 0 to 5 V (|ost| <= 0.5 V)")
        ax.set_ylabel(f"{ch} minus value at ost = 0 [mV]")
        ax.grid(alpha=0.3)
        ax.legend(fontsize=8, loc="best")
    ax1.set_title("P-03: settled deviation against offset (dashed 1 mV, dotted 0.1 mV)")
    ax2.set_xlabel("ost [V]")
    ax1.set_ylim(-6, 6)
    ax2.set_ylim(-6, 6)
    fig.tight_layout()
    fig.savefig(PLOT_DIR / "P-03_dev_vs_ost.png", dpi=150)
    plt.close(fig)

    # Figure 2: max, mean and min against ost
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8, 6.5), sharex=True)
    for ax, name, ch in ((ax1, "P03a_ost_p0", "VX"), (ax2, "P03b_ost_p90", "VY")):
        r = res[name]
        ax.plot(r["ost"], r["vx" if ch == "VX" else "vy"], "o-", ms=3.5, lw=0.8, color="tab:green", label="mean of last 50 periods")
        ax.plot(r["ost"], r["vx_max" if ch == "VX" else "vy_max"], "^-", ms=3.5, lw=0.6, color="tab:red", label="max over last 50 periods")
        ax.plot(r["ost"], r["vx_min" if ch == "VX" else "vy_min"], "v-", ms=3.5, lw=0.6, color="tab:purple", label="min over last 50 periods")
        ax.set_ylabel(f"{ch} [V]")
        ax.set_title(f"{ch} from {name} ({labels[name].split(',')[1].strip()})", fontsize=9)
        ax.grid(alpha=0.3)
        ax.legend(fontsize=8, loc="best")
    ax2.set_xlabel("ost [V]")
    fig.tight_layout()
    fig.savefig(PLOT_DIR / "P-03_max_mean_min_vs_ost.png", dpi=150)
    plt.close(fig)

    # Figure 3: demodulator range against ost, with the input range
    fig, axes = plt.subplots(1, 2, figsize=(9, 4.2), sharey=True)
    for ax, name in zip(axes, RUNS):
        r = res[name]
        d = r["d"]
        dl = RUNS[name]["dem_label"]
        ax.plot(r["ost"], d["dem_max"], "^-", ms=3.5, lw=0.8, color="tab:red", label=f"absolute max of {dl} (50 periods)")
        ax.plot(r["ost"], d["dem_min"], "v-", ms=3.5, lw=0.8, color="tab:purple", label=f"absolute min of {dl} (50 periods)")
        ax.plot(r["ost"], MID + r["ost"] + AMP, ":", color="grey", lw=1.0, label="input max (2.5 + ost + 2) V")
        ax.plot(r["ost"], MID + r["ost"] - AMP, ":", color="k", lw=1.0, label="input min (2.5 + ost - 2) V")
        ax.axhline(0, color="k", lw=0.7)
        ax.axhline(VDC, color="k", lw=0.7, ls="--")
        ax.set_title(f"{dl} ({name})", fontsize=9)
        ax.set_xlabel("ost [V]")
        ax.grid(alpha=0.3)
        ax.legend(fontsize=7, loc="best")
    axes[0].set_ylabel("voltage [V]")
    axes[0].set_ylim(-3, 8)
    fig.tight_layout()
    fig.savefig(PLOT_DIR / "P-03_demod_range_vs_ost.png", dpi=150)
    plt.close(fig)

    # Figure 4: demodulator waveforms over two periods at selected offsets
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.5), sharey=True)
    for ax, name in zip(axes, RUNS):
        r = res[name]
        w = r["waves"]
        # The demodulator of each run feeds one channel: VX_DEMOD feeds VX, VY_DEMOD feeds VY
        dev = r["dvx"] if name == "P03a_ost_p0" else r["dvy"]
        dep = departure(r["ost"], dev, 1.0)
        dep_pos = dep["pos"][0]
        selected = [0.0, dep_pos, 2.0, -2.0]
        for val, col in zip(selected, ["k", "tab:orange", "tab:green", "tab:red"]):
            i = int(np.argmin(np.abs(r["ost"] - val)))
            ax.plot(w["t"] * 1e3, w["dem"][i], lw=0.9, color=col, label=f"ost = {r['ost'][i]:+.2f} V")
        ax.axhline(0, color="k", lw=0.7)
        ax.axhline(VDC, color="k", lw=0.7, ls="--")
        ax.set_title(f"{RUNS[name]['dem_label']} over two periods ({name})", fontsize=9)
        ax.set_xlabel("time within the last two periods [ms]")
        ax.grid(alpha=0.3)
        ax.legend(fontsize=8, loc="best")
    axes[0].set_ylabel("demodulator output [V]")
    fig.tight_layout()
    fig.savefig(PLOT_DIR / "P-03_demod_waveforms.png", dpi=150)
    plt.close(fig)
    print(f"wrote plots to {PLOT_DIR}")


if __name__ == "__main__":
    main()
