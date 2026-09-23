"""
Recompute heater-sensitivity points and slopes from stored monitor CSVs.

Pure post-processing over the ``monitor_*.csv`` files written by the MCP
operating-point session's continuous monitor: no instruments are touched.

Every reported point is derived from the settled window at the end of a dwell
(the time the operator waited after the last setpoint change), never from a
live tool reading. A "point" is a note row that records a measurement (it
contains ``R=`` and the ch1 heater readback as ``ch1=X`` or ``pt(X)``); the
dwell start is the last logged setpoint change (``offset ->``, ``heater chN ->``
or ``SCUN voltage ->``) before it.
"""

import csv
import logging
import os
import re
from dataclasses import dataclass, field
from datetime import datetime

import numpy as np

from config import ATEConfig, HeaterSlopeTableConfig

from .setup_base import SetupBase

logger = logging.getLogger(__name__)

_READBACK_RE = re.compile(r"\(readback (-?\d*\.\d+)V\)")
_CHANGE_RES = {
    "offset": re.compile(r"^offset -> (-?\d*\.?\d+)V"),
    "heater": re.compile(r"^heater ch(\d) -> (-?\d*\.?\d+)V"),
    "scu": re.compile(r"^SCU(\d) voltage -> (-?\d*\.?\d+)V"),
}
_PHASE_RE = re.compile(r"^auto-phase converged")
_MEAS_RE = re.compile(r"(?<![A-Za-z|])R=")
_CH1_RES = (re.compile(r"ch1=(\d\.\d+)"), re.compile(r"pt\((\d\.\d+)\)"))
_VD_RE = re.compile(r"Vd\s+(-?\d*\.\d+|-?\d+)\s*/\s*(-?\d*\.\d+|-?\d+)")
_NOTE_R_RE = re.compile(r"signed R=([+-]?\d*\.\d+)")

# Flags that remove a point from slope pairs. "drifting" is reported only.
EXCLUDING_FLAGS = ("over_range", "phase_suspect", "short_settle", "ch1_mismatch")


@dataclass
class Monitor:
    """A parsed monitor CSV."""

    path: str
    vgs0_v: float
    t: np.ndarray
    r: np.ndarray
    theta_deg: np.ndarray
    # (sample row index, time_s, ordered list of event pieces)
    events: list[tuple[int, float, list[str]]] = field(default_factory=list)


def parse_monitor_csv(path: str) -> Monitor:
    with open(path, newline="") as f:
        rows = list(csv.reader(f))
    header_at = next(i for i, row in enumerate(rows) if row and row[0] == "index")
    vgs0 = float("nan")
    for row in rows[:header_at]:
        if row and row[0] == "reference_dc_V":
            vgs0 = float(row[1])
    t, r, theta = [], [], []
    events: list[tuple[int, float, list[str]]] = []
    for row in rows[header_at + 1:]:
        if len(row) < 4 or not row[0].strip():
            continue
        idx, ts = int(row[0]), float(row[1])
        t.append(ts)
        r.append(float(row[2]))
        theta.append(float(row[3]))
        if len(row) > 4 and row[4].strip():
            events.append((idx, ts, [p.strip() for p in row[4].split(" | ")]))
    return Monitor(path, vgs0, np.array(t), np.array(r), np.array(theta), events)


@dataclass
class Point:
    run: str
    visit: int
    vgs_v: float
    ch1_v: float
    t_change_s: float
    t_end_s: float
    settle_s: float
    window_s: float
    n: int
    n_eff: float
    mean_x_v: float
    sigma_x_v: float
    x_end_v: float
    se_x_end_v: float
    drift_uv_per_s: float
    drift_se_uv_per_s: float
    mean_r_v: float
    note_signed_r_v: float | None
    vd: tuple[float, float] | None
    flags: list[str]


def _fit_window(t: np.ndarray, x: np.ndarray, t_end: float):
    """Linear fit x(t) over the window, evaluated at ``t_end``.

    Autocorrelation of the residuals shrinks the effective sample size, and
    every regression standard error is inflated by sqrt(n / n_eff).
    """
    n = len(x)
    tc = t - t.mean()
    sxx = float(np.sum(tc**2))
    slope = float(np.sum(tc * (x - x.mean())) / sxx)
    resid = x - (x.mean() + slope * tc)
    sd_resid = float(resid.std(ddof=2))
    rho = 0.0
    if n > 3 and resid.std() > 0:
        rho = float(np.corrcoef(resid[:-1], resid[1:])[0, 1])
    n_eff = n * (1 - rho) / (1 + rho) if rho > 0 else float(n)
    n_eff = max(2.0, min(float(n), n_eff))
    infl = np.sqrt(n / n_eff)
    x_end = float(x.mean() + slope * (t_end - t.mean()))
    se_end = sd_resid * infl * np.sqrt(1 / n + (t_end - t.mean()) ** 2 / sxx)
    se_slope = sd_resid * infl / np.sqrt(sxx)
    return slope, se_slope, x_end, float(se_end), n_eff


def extract_points(mon: Monitor, run: str, cfg: HeaterSlopeTableConfig) -> list[Point]:
    """One ``Point`` per measurement note in ``mon``."""
    x_all = mon.r * np.cos(np.radians(mon.theta_deg))
    vgs = mon.vgs0_v
    visit = 0
    t_change = float(mon.t[0]) if len(mon.t) else 0.0
    t_phase: float | None = None
    r_at_phase: float | None = None
    ch1_readback: float | None = None  # logged readback, newer logs only
    points: list[Point] = []

    for _idx, ts, pieces in mon.events:
        for piece in pieces:
            m_off = _CHANGE_RES["offset"].match(piece)
            if m_off:
                vgs = float(m_off.group(1))
                visit += 1
                t_change = ts
                continue
            m_heat = _CHANGE_RES["heater"].match(piece)
            if m_heat or _CHANGE_RES["scu"].match(piece):
                t_change = ts
                m_rb = _READBACK_RE.search(piece)
                if m_heat and m_heat.group(1) == "1" and m_rb:
                    ch1_readback = float(m_rb.group(1))
                continue
            if _PHASE_RE.match(piece):
                t_phase = ts
                near = mon.r[(mon.t >= ts - 30.0) & (mon.t <= ts)]
                r_at_phase = float(near.mean()) if len(near) else None
                continue
            if not _MEAS_RE.search(piece):
                continue
            ch1 = next((float(m.group(1)) for rx in _CH1_RES
                        if (m := rx.search(piece))), None)
            if ch1 is None:
                logger.warning(
                    f"{run}: measurement note without ch1 readback: {piece[:60]!r}")
                continue

            t_start = max(t_change, t_phase if t_phase is not None else -np.inf)
            t_lo = max(ts - cfg.window_s, t_start)
            sel = (mon.t >= t_lo) & (mon.t < ts)
            if sel.sum() < 10:
                logger.warning(
                    f"{run}: <10 samples before note at t={ts:.0f}s; skipped")
                continue
            tw, xw, rw = mon.t[sel], x_all[sel], mon.r[sel]
            slope, se_slope, x_end, se_end, n_eff = _fit_window(tw, xw, ts)

            flags: list[str] = []
            settle = ts - t_change
            if settle < cfg.min_settle_s:
                flags.append("short_settle")
            if float(rw.mean()) > cfg.overrange_fraction * cfg.full_scale_v:
                flags.append("over_range")
            if r_at_phase is not None and r_at_phase < cfg.phase_min_r_v:
                flags.append("phase_suspect")
            if abs(slope) * 1e6 > cfg.settled_drift_uv_per_s:
                flags.append("drifting")
            if ch1_readback is not None and abs(ch1_readback - ch1) > 5e-4:
                flags.append("ch1_mismatch")
            vd_m = _VD_RE.search(piece)
            vd = (float(vd_m.group(1)), float(vd_m.group(2))) if vd_m else None
            if vd is not None and min(vd) < cfg.vd_flag_v:
                flags.append("vd_low")
            note_r = _NOTE_R_RE.search(piece)

            points.append(Point(
                run=run, visit=visit, vgs_v=vgs, ch1_v=ch1,
                t_change_s=t_change, t_end_s=ts, settle_s=settle,
                window_s=float(tw[-1] - tw[0]), n=int(sel.sum()), n_eff=n_eff,
                mean_x_v=float(xw.mean()), sigma_x_v=float(xw.std(ddof=1)),
                x_end_v=x_end, se_x_end_v=se_end,
                drift_uv_per_s=slope * 1e6, drift_se_uv_per_s=se_slope * 1e6,
                mean_r_v=float(rw.mean()),
                note_signed_r_v=float(note_r.group(1)) if note_r else None,
                vd=vd, flags=flags,
            ))
    return points


@dataclass
class Slope:
    run: str
    visit: int
    vgs_v: float
    a: Point
    b: Point
    d_ch1_v: float
    d_x_v: float
    slope_v_per_v: float
    sigma_stat_v_per_v: float
    sigma_ch1_v_per_v: float
    sigma_total_v_per_v: float


def build_slopes(points: list[Point], cfg: HeaterSlopeTableConfig) -> list[Slope]:
    """Adjacent-ch1 slopes within each (run, visit) among unflagged points.

    The slope's statistical error comes from the two end-of-window standard
    errors. The heater-readback resolution enters as an independent
    uniform-quantization error (resolution / sqrt(12) per reading) on the
    ch1 difference.
    """
    groups: dict[tuple[str, int], list[Point]] = {}
    for p in points:
        if any(f in EXCLUDING_FLAGS for f in p.flags):
            continue
        groups.setdefault((p.run, p.visit), []).append(p)
    out: list[Slope] = []
    sigma_v = cfg.heater_resolution_v / np.sqrt(12.0)
    for (run, visit), pts in groups.items():
        # Keep the latest measurement per distinct ch1 readback in the visit.
        latest: dict[float, Point] = {}
        for p in sorted(pts, key=lambda q: q.t_end_s):
            latest[p.ch1_v] = p
        ordered = sorted(latest.values(), key=lambda q: q.ch1_v)
        for a, b in zip(ordered[:-1], ordered[1:]):
            dv = b.ch1_v - a.ch1_v
            dx = b.x_end_v - a.x_end_v
            slope = dx / dv
            s_stat = np.hypot(a.se_x_end_v, b.se_x_end_v) / abs(dv)
            s_ch1 = abs(slope) * np.sqrt(2.0) * sigma_v / abs(dv)
            out.append(Slope(run, visit, a.vgs_v, a, b, dv, dx, slope,
                             float(s_stat), float(s_ch1),
                             float(np.hypot(s_stat, s_ch1))))
    return out


_POINT_COLS = [
    "run", "visit", "vgs_v", "ch1_v", "settle_s", "window_s", "n", "n_eff",
    "mean_x_v", "sigma_x_v", "x_end_v", "se_x_end_v", "drift_uv_per_s",
    "drift_se_uv_per_s", "mean_r_v", "note_signed_r_v", "delta_vs_note_v",
    "vd_scu1_v", "vd_scu2_v", "flags",
]
_SLOPE_COLS = [
    "run", "visit", "vgs_v", "ch1_a_v", "ch1_b_v", "d_ch1_v", "x_a_v", "x_b_v",
    "d_x_v", "slope_v_per_v", "sigma_stat", "sigma_ch1_res", "sigma_total",
    "rel_err_pct", "settle_a_s", "settle_b_s", "n_a", "n_b",
]


def points_table(points: list[Point]) -> dict[str, list]:
    cols: dict[str, list] = {c: [] for c in _POINT_COLS}
    for p in points:
        cols["run"].append(p.run)
        cols["visit"].append(p.visit)
        cols["vgs_v"].append(p.vgs_v)
        cols["ch1_v"].append(p.ch1_v)
        cols["settle_s"].append(round(p.settle_s, 1))
        cols["window_s"].append(round(p.window_s, 1))
        cols["n"].append(p.n)
        cols["n_eff"].append(round(p.n_eff, 1))
        cols["mean_x_v"].append(p.mean_x_v)
        cols["sigma_x_v"].append(p.sigma_x_v)
        cols["x_end_v"].append(p.x_end_v)
        cols["se_x_end_v"].append(p.se_x_end_v)
        cols["drift_uv_per_s"].append(round(p.drift_uv_per_s, 3))
        cols["drift_se_uv_per_s"].append(round(p.drift_se_uv_per_s, 3))
        cols["mean_r_v"].append(p.mean_r_v)
        cols["note_signed_r_v"].append(
            "" if p.note_signed_r_v is None else p.note_signed_r_v)
        cols["delta_vs_note_v"].append(
            "" if p.note_signed_r_v is None else p.mean_x_v - p.note_signed_r_v)
        cols["vd_scu1_v"].append("" if p.vd is None else p.vd[0])
        cols["vd_scu2_v"].append("" if p.vd is None else p.vd[1])
        cols["flags"].append(" ".join(p.flags))
    return cols


def slopes_table(slopes: list[Slope]) -> dict[str, list]:
    cols: dict[str, list] = {c: [] for c in _SLOPE_COLS}
    for s in slopes:
        cols["run"].append(s.run)
        cols["visit"].append(s.visit)
        cols["vgs_v"].append(s.vgs_v)
        cols["ch1_a_v"].append(s.a.ch1_v)
        cols["ch1_b_v"].append(s.b.ch1_v)
        cols["d_ch1_v"].append(round(s.d_ch1_v, 4))
        cols["x_a_v"].append(s.a.x_end_v)
        cols["x_b_v"].append(s.b.x_end_v)
        cols["d_x_v"].append(s.d_x_v)
        cols["slope_v_per_v"].append(s.slope_v_per_v)
        cols["sigma_stat"].append(s.sigma_stat_v_per_v)
        cols["sigma_ch1_res"].append(s.sigma_ch1_v_per_v)
        cols["sigma_total"].append(s.sigma_total_v_per_v)
        cols["rel_err_pct"].append(
            round(100 * s.sigma_total_v_per_v / abs(s.slope_v_per_v), 2)
            if s.slope_v_per_v else "")
        cols["settle_a_s"].append(round(s.a.settle_s, 1))
        cols["settle_b_s"].append(round(s.b.settle_s, 1))
        cols["n_a"].append(s.a.n)
        cols["n_b"].append(s.b.n)
    return cols


def markdown_report(points: list[Point], slopes: list[Slope],
                    cfg: HeaterSlopeTableConfig) -> str:
    lines = [
        "# Heater-sensitivity slopes recomputed from monitor logs", "",
        f"Window: last {cfg.window_s:g} s of each dwell (fewer if the dwell was "
        f"shorter). Point value = linear fit of X = R cos(theta) evaluated at "
        f"the end of the dwell; SE from the fit residuals with lag-1 "
        f"autocorrelation correction (n_eff). Heater-readback resolution "
        f"{cfg.heater_resolution_v * 1e3:g} mV enters as a uniform "
        f"quantization error. Points flagged {', '.join(EXCLUDING_FLAGS)} are "
        f"excluded from slopes.", "",
        "## Slopes", "",
        "| run | visit | Vgs (V) | ch1 a -> b (V) | slope (V/V) | +/- total | "
        "stat | ch1 res | settle a/b (s) | N a/b |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for s in slopes:
        lines.append(
            f"| {s.run} | {s.visit} | {s.vgs_v:.3f} | "
            f"{s.a.ch1_v:.3f} -> {s.b.ch1_v:.3f} | {s.slope_v_per_v:+.4g} | "
            f"{s.sigma_total_v_per_v:.2g} | {s.sigma_stat_v_per_v:.2g} | "
            f"{s.sigma_ch1_v_per_v:.2g} | {s.a.settle_s:.0f}/{s.b.settle_s:.0f} | "
            f"{s.a.n}/{s.b.n} |")
    lines += ["", "## Points", "",
              "| run | visit | Vgs (V) | ch1 (V) | settle (s) | N | N_eff | "
              "X_end (V) | SE (V) | sigma (V) | drift (uV/s) | Vd (V) | flags |",
              "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for p in points:
        vd = "" if p.vd is None else f"{p.vd[0]:g}/{p.vd[1]:g}"
        lines.append(
            f"| {p.run} | {p.visit} | {p.vgs_v:.3f} | {p.ch1_v:.3f} | "
            f"{p.settle_s:.0f} | {p.n} | {p.n_eff:.0f} | {p.x_end_v:+.5g} | "
            f"{p.se_x_end_v:.2g} | {p.sigma_x_v:.2g} | {p.drift_uv_per_s:+.3g} | "
            f"{vd} | {' '.join(p.flags)} |")
    return "\n".join(lines) + "\n"


class HeaterSlopeTable(SetupBase):
    def __init__(self, output_name: str = None, ate_config: ATEConfig = None,  # type: ignore
                 config: HeaterSlopeTableConfig = None) -> None:  # type: ignore
        super().__init__(output_name=output_name, ate_config=ate_config)
        self.config: HeaterSlopeTableConfig = config or HeaterSlopeTableConfig()
        self.results_dir = os.path.join(
            "Results", "HeaterSlopeTable", datetime.now().strftime("%Y%m%d_%H%M%S"))
        os.makedirs(self.results_dir, exist_ok=True)

    def run(self) -> None:
        if not self.config.monitor_csvs:
            raise ValueError("monitor_csvs is empty")
        points: list[Point] = []
        for path in self.config.monitor_csvs:
            mon = parse_monitor_csv(path)
            run = os.path.splitext(os.path.basename(path))[0]
            found = extract_points(mon, run, self.config)
            logger.info(f"{run}: {len(found)} measurement point(s)")
            points.extend(found)
        slopes = build_slopes(points, self.config)
        for stem, table in (("points", points_table(points)),
                            ("slopes", slopes_table(slopes))):
            with open(os.path.join(self.results_dir, f"{stem}.csv"), "w",
                      newline="") as f:
                writer = csv.writer(f)
                writer.writerow(list(table))
                writer.writerows(zip(*table.values()))
        report = os.path.join(self.results_dir, "slope_table.md")
        with open(report, "w") as f:
            f.write(markdown_report(points, slopes, self.config))
        logger.info(f"Wrote {len(points)} points and {len(slopes)} slopes to "
                    f"{self.results_dir}")
