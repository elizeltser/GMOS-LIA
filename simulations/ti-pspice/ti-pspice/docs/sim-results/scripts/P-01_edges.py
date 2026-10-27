"""Edge table for run P01_D_edges (index entry P-01, edge measurement).

Run from the project root:
    python docs/sim-results/scripts/P-01_edges.py

Reads sim-runs/P01_D_edges/P01_D_edges.csd (6 ms to 10 ms, 10 ns maximum step)
and prints:
  1. Plausibility checks (job status, ERROR lines, signals, time spacing).
  2. For each reference edge in the window: the SEL 2.5 V crossing, and the
     instant the switch output changes state.
  3. For each switch change: the VX_DEMOD or VY_DEMOD step, the times to reach
     50 % and 90 % of the step, and the slew between those points.

Definitions:
  - SEL is the reference square wave: N01577 (Y, V_V6) and N00261 (X, V_V2).
  - Switch output: N01681 (Y switch, input N00890) and N00695 (X switch).
  - The switch "follows" the input N00890, or "holds" at 2.5 V. The switch
    instant is where the distance of the switch output from its pre-change
    level equals half the distance between the pre- and post-change levels.
    The post-change level is N00890 (follow) or 2.5 V (hold), evaluated at
    each sample.
  - The demodulator step is VY_DEMOD (Y) or VX_DEMOD (X). Its pre-level is its
    value at the switch instant. Its post-level is its value 1 us later.
  - Slew rate = 0.4 x |step| / (t90 - t50), the average slope between the
    50 % and 90 % points.
"""

import os
import re
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from csdf import read_csdf  # noqa: E402

RUN = "P01_D_edges"
RUN_DIR = os.path.join(ROOT, "sim-runs", RUN)
CSD = os.path.join(RUN_DIR, RUN + ".csd")
OUT = os.path.join(RUN_DIR, RUN + ".out")

WINDOW = (6.0e-3, 10.0e-3)   # s, saved part of the run
VMID = 2.5                   # V, hold level of the switch and SEL threshold
SEARCH = 1.0e-6              # s, window after SEL crossing for the switch change
POST_DT = 1.0e-6             # s, demodulator post-change level taken this long after the switch
CHECK_DT = 0.5e-6            # s, window around each reference edge for time spacing

CHANNELS = {
    # name: (SEL node, switch output, switch input, demodulator output)
    "Y": ("V(N01577)", "V(N01681)", "V(N00890)", "V(VY_DEMOD)"),
    "X": ("V(N00261)", "V(N00695)", "V(N00890)", "V(VX_DEMOD)"),
}


def crossings(t, x, level):
    """Linear-interpolated times where x crosses level. Returns (time, +1 rising or -1 falling)."""
    s = np.sign(x - level)
    out = []
    for i in np.where(s[:-1] * s[1:] < 0)[0]:
        tc = t[i] + (level - x[i]) * (t[i + 1] - t[i]) / (x[i + 1] - x[i])
        out.append((tc, 1 if x[i + 1] > x[i] else -1))
    return out


def switch_instant(t, sw, vin, tc):
    """Time at which the switch output has moved half-way to its new state after tc."""
    i0 = np.searchsorted(t, tc)
    i1 = np.searchsorted(t, tc + SEARCH)
    tt = t[i0 - 1:i1 + 1]
    vs = sw[i0 - 1:i1 + 1]
    vi = vin[i0 - 1:i1 + 1]
    vsw0 = np.interp(tc, t, sw)
    vin0 = np.interp(tc, t, vin)
    follow_pre = abs(vsw0 - vin0) < abs(vsw0 - VMID)
    if follow_pre:
        lpre, lpost = vi, np.full_like(vi, VMID)
        names = ("follow", "hold")
    else:
        lpre, lpost = np.full_like(vi, VMID), vi
        names = ("hold", "follow")
    g = np.abs(vs - lpre) - 0.5 * np.abs(lpost - lpre)
    k = np.where((g[:-1] < 0) & (g[1:] >= 0))[0]
    if len(k) == 0:
        return None
    j = k[0]
    tsw = tt[j] + (0.0 - g[j]) * (tt[j + 1] - tt[j]) / (g[j + 1] - g[j])
    post_level = np.interp(tsw, tt, lpost)
    return tsw, names[0], names[1], np.interp(tsw, tt, lpre), post_level


def demod_step(t, v, tsw):
    """Step of a demodulator output after tsw, with 50 % and 90 % times and slew."""
    pre = np.interp(tsw, t, v)
    post = np.interp(tsw + POST_DT, t, v)
    step = post - pre
    i0 = np.searchsorted(t, tsw)
    i1 = np.searchsorted(t, tsw + POST_DT)
    tt = t[i0 - 1:i1 + 1]
    f = (v[i0 - 1:i1 + 1] - pre) / step   # fraction of the step, 0 at tsw, 1 at the end

    def first(level):
        k = np.where((f[:-1] < level) & (f[1:] >= level))[0]
        if len(k) == 0:
            return np.nan
        j = k[0]
        return tt[j] + (level - f[j]) * (tt[j + 1] - tt[j]) / (f[j + 1] - f[j])

    t50 = first(0.5)
    t90 = first(0.9)
    slew = 0.4 * abs(step) / (t90 - t50) * 1e-6   # V/us
    return step, t50 - tsw, t90 - tsw, slew


def plausibility(section, t):
    print("== Plausibility checks ==")
    with open(OUT, encoding="utf-8", errors="replace") as fh:
        text = fh.read()
    done = "Total job time" in text
    errors = re.findall(r"^ERROR.*$", text, flags=re.M)
    print("job status (Total job time in .out): %s" % ("done" if done else "NOT DONE"))
    print("ERROR lines in .out: %d" % len(errors))
    needed = [v for pair in CHANNELS.values() for v in pair]
    missing = [n for n in needed if n not in section]
    print("signals present: %s" % ("all %d" % len(set(needed)) if not missing else "missing " + ", ".join(missing)))
    print("time window: %.6f s to %.6f s, %d points" % (t[0], t[-1], len(t)))
    print()


def main():
    section = read_csdf(CSD)[0]
    t = section.x
    in_win = (t >= WINDOW[0]) & (t <= WINDOW[1])
    plausibility(section, t)

    print("== Time spacing around the reference edges ==")
    for name, (sel, _, _, _) in CHANNELS.items():
        for tc, _ in crossings(t, section[sel], VMID):
            if not (WINDOW[0] <= tc <= WINDOW[1]):
                continue
            a = np.searchsorted(t, tc - CHECK_DT)
            b = np.searchsorted(t, tc + CHECK_DT)
            dt = np.diff(t[a:b + 1])
            print("%s edge at %.6f ms: max step %.3f ns" % (name, tc * 1e3, dt.max() * 1e9))
    print()

    rows_sw = []
    rows_dm = []
    for name, (sel, sw, vin, dm) in CHANNELS.items():
        for tc, direction in crossings(t, section[sel], VMID):
            if not (WINDOW[0] <= tc <= WINDOW[1]):
                continue
            res = switch_instant(t, section[sw], section[vin], tc)
            if res is None:
                rows_sw.append((name, tc, direction, None))
                continue
            tsw, pre, post, lpre, lpost = res
            rows_sw.append((name, tc, direction, (tsw, pre, post, lpre, lpost)))
            step, t50, t90, slew = demod_step(t, section[dm], tsw)
            rows_dm.append((name, tsw, step, t50, t90, slew, dm))

    print("== Reference edges and switch changes ==")
    print("| Ch | SEL edge | SEL 2.5 V crossing (ms) | Switch change (ms) | Switch - SEL (ns) | Switch state before to after | Switch level pre / post (V) |")
    print("|---|---|---|---|---|---|---|")
    for name, tc, direction, res in rows_sw:
        edge = "rising" if direction > 0 else "falling"
        if res is None:
            print("| %s | %s | %.6f | not found | - | - | - |" % (name, edge, tc * 1e3))
            continue
        tsw, pre, post, lpre, lpost = res
        print("| %s | %s | %.6f | %.6f | %.1f | %s to %s | %.4f / %.4f |" % (
            name, edge, tc * 1e3, tsw * 1e3, (tsw - tc) * 1e9, pre, post, lpre, lpost))
    print()

    print("== Demodulator steps after each switch change ==")
    print("| Output | Switch change (ms) | Step (V) | t50 after switch (ns) | t90 after switch (ns) | Slew, 50 % to 90 % (V/us) |")
    print("|---|---|---|---|---|---|")
    slews = {}
    for name, tsw, step, t50, t90, slew, dm in rows_dm:
        print("| %s | %.6f | %+.4f | %.2f | %.2f | %.3f |" % (dm, tsw * 1e3, step, t50 * 1e9, t90 * 1e9, slew))
        slews.setdefault(dm, []).append(slew)
    print()
    for dm, vals in slews.items():
        print("%s: mean slew %.3f V/us over %d steps (min %.3f, max %.3f)" % (
            dm, np.mean(vals), len(vals), np.min(vals), np.max(vals)))
    print()
    plot_y_edge(section, t)


PLOT_Y = os.path.join(ROOT, "docs", "sim-results", "plots", "P-01_y_edge.png")


def plot_y_edge(section, t):
    """VY_DEMOD and V(N01577) around the first rising Y edge in the window (1 us span)."""
    sel_y = CHANNELS["Y"][0]
    tc = next(tc for tc, d in crossings(t, section[sel_y], VMID)
              if d > 0 and WINDOW[0] <= tc <= WINDOW[1])
    m = (t >= tc - 0.2e-6) & (t <= tc + 0.8e-6)
    tu = (t[m] - tc) * 1e9
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(7, 5), sharex=True)
    a1.plot(tu, section[sel_y][m], color="tab:green", lw=1.0)
    a1.axhline(VMID, color="k", ls=":", lw=0.8)
    a1.set_ylabel("V(N01577) [V]")
    a1.set_title("P-01 run D: Y reference edge and VY_DEMOD (1 us window)")
    a1.grid(alpha=0.3)
    a2.plot(tu, section["V(VY_DEMOD)"][m], color="tab:purple", lw=1.0)
    a2.set_ylabel("V(VY_DEMOD) [V]")
    a2.set_xlabel("time from the SEL 2.5 V crossing [ns]")
    a2.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(PLOT_Y, dpi=150)
    print("wrote %s" % PLOT_Y)


if __name__ == "__main__":
    main()
