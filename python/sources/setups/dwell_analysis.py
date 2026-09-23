"""
Quantify per-session R drift and cold-start-to-cold-start shift from the
isolated-dwell monitor CSVs (marked with 'ISOLATED START' / 'ISOLATED END'
note events, no other instrument calls in between).

Pure post-processing over stored CSVs: no instruments are touched. Reuses
``parse_monitor_csv``/``_fit_window`` from ``heater_slope_table``.
"""

import logging
import os
from dataclasses import dataclass, field
from datetime import datetime

import numpy as np

from config import ATEConfig, DwellAnalysisConfig

from .heater_slope_table import _fit_window, parse_monitor_csv
from .setup_base import SetupBase

logger = logging.getLogger(__name__)


@dataclass
class DwellResult:
    run: str
    t_start_s: float
    t_end_s: float
    duration_h: float
    n: int
    n_eff: float
    x_start_v: float
    x_end_v: float
    total_change_v: float
    drift_v_per_s: float
    drift_se_v_per_s: float
    block_drifts_uv_per_s: list[tuple[float, float, float]] = field(
        default_factory=list)


def analyze_dwell(path: str, block_s: float = 1800.0) -> DwellResult:
    mon = parse_monitor_csv(path)
    x = mon.r * np.cos(np.radians(mon.theta_deg))
    run = os.path.splitext(os.path.basename(path))[0]
    t_start = t_end = None
    for _, ts, pieces in mon.events:
        for piece in pieces:
            if "ISOLATED START" in piece:
                t_start = ts
            if "ISOLATED END" in piece:
                t_end = ts
    if t_start is None or t_end is None:
        raise ValueError(f"{run}: missing ISOLATED START/END markers")
    sel = (mon.t >= t_start) & (mon.t <= t_end)
    tw, xw = mon.t[sel], x[sel]
    if len(tw) < 20:
        raise ValueError(f"{run}: isolated window has only {len(tw)} samples")
    slope, se_slope, x_end, _, n_eff = _fit_window(tw, xw, tw[-1])

    blocks = []
    t0 = tw[0]
    while t0 < tw[-1]:
        bsel = (tw >= t0) & (tw < t0 + block_s)
        if bsel.sum() > 100:
            bslope, bse, _, _, _ = _fit_window(tw[bsel], xw[bsel], tw[bsel][-1])
            blocks.append((float(t0 - tw[0]), bslope * 1e6, bse * 1e6))
        t0 += block_s

    return DwellResult(
        run=run, t_start_s=float(tw[0]), t_end_s=float(tw[-1]),
        duration_h=float(tw[-1] - tw[0]) / 3600, n=len(xw), n_eff=n_eff,
        x_start_v=float(xw[0]), x_end_v=x_end,
        total_change_v=x_end - float(xw[0]),
        drift_v_per_s=slope, drift_se_v_per_s=se_slope,
        block_drifts_uv_per_s=blocks,
    )


def markdown_report(results: list[DwellResult], cfg: DwellAnalysisConfig) -> str:
    lines = [
        "# Isolated-dwell characterization", "",
        "Per session, every instrument call stops after the phase auto-zero "
        "(`ISOLATED START`) until a single closing `read_drain_state` "
        "(`ISOLATED END`); X = R cos(theta) is fit linearly over that window "
        "only. `x_start_v` is the first isolated sample, so cross-session "
        "differences are a genuine cold-start shift, not a settling artifact.",
        "", "## Per-session drift", "",
        "| session | duration (h) | N | N_eff | X_start (V) | X_end (V) | "
        "total change (mV) | drift (uV/s) | +/- (uV/s) |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for r in results:
        lines.append(
            f"| {r.run} | {r.duration_h:.2f} | {r.n} | {r.n_eff:.0f} | "
            f"{r.x_start_v:+.5f} | {r.x_end_v:+.5f} | "
            f"{r.total_change_v * 1e3:+.2f} | {r.drift_v_per_s * 1e6:+.3f} | "
            f"{r.drift_se_v_per_s * 1e6:.3f} |")

    lines += ["", "## 30-minute block drift within each session (uV/s)", ""]
    for r in results:
        lines.append(f"**{r.run}**")
        for t0, sl, se in r.block_drifts_uv_per_s:
            lines.append(f"- t={t0 / 3600:.2f} h: {sl:+.3f} +/- {se:.3f}")
        lines.append("")

    starts = np.array([r.x_start_v for r in results])
    lines += [
        "## Cold-start-to-cold-start shift", "",
        f"X_start across {len(starts)} cold starts: "
        f"range {(starts.max() - starts.min()) * 1e3:.2f} mV, "
        f"mean {starts.mean():+.5f} V, "
        f"sample std {starts.std(ddof=1) * 1e3:.2f} mV.",
        "",
        "Successive-session differences (mV): " +
        ", ".join(f"{(starts[i+1]-starts[i])*1e3:+.2f}"
                  for i in range(len(starts) - 1)),
    ]
    if cfg.local_slope_v_per_v:
        eq_mv = 1e3 * (starts.max() - starts.min()) / abs(cfg.local_slope_v_per_v)
        diffs_eq_mv = [
            1e3 * (starts[i + 1] - starts[i]) / cfg.local_slope_v_per_v
            for i in range(len(starts) - 1)
        ]
        lines += [
            "", f"Using the local heater sensitivity "
            f"{cfg.local_slope_v_per_v:.0f} V/V at this Vgs/heater point, "
            f"the cold-start range is equivalent to about {eq_mv:.3f} mV of "
            f"heater voltage (successive shifts: " +
            ", ".join(f"{d:+.3f}" for d in diffs_eq_mv) + " mV).",
        ]
    return "\n".join(lines) + "\n"


class DwellAnalysis(SetupBase):
    def __init__(self, output_name: str = None, ate_config: ATEConfig = None,  # type: ignore
                 config: DwellAnalysisConfig = None) -> None:  # type: ignore
        super().__init__(output_name=output_name, ate_config=ate_config)
        self.config: DwellAnalysisConfig = config or DwellAnalysisConfig()
        self.results_dir = os.path.join(
            "Results", "DwellAnalysis", datetime.now().strftime("%Y%m%d_%H%M%S"))
        os.makedirs(self.results_dir, exist_ok=True)

    def run(self) -> None:
        if not self.config.dwell_csvs:
            raise ValueError("dwell_csvs is empty")
        results = [analyze_dwell(path, self.config.block_s)
                  for path in self.config.dwell_csvs]
        report = os.path.join(self.results_dir, "dwell_report.md")
        with open(report, "w") as f:
            f.write(markdown_report(results, self.config))
        logger.info(f"Wrote dwell analysis for {len(results)} session(s) to "
                    f"{self.results_dir}")
