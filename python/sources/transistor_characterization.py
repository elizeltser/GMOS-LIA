"""
Per-transistor VGS characterization sweep, driven directly through
``OperatingPointSession`` (the same class the ``gmos-operating-point`` MCP
server wraps), bypassing the MCP transport for a long unattended batch run.

For each VDD in ``PARAMS.vdd_voltages`` (the SCU voltage-source level passed
to ``set_drain_voltage``, applied identically to SCU1 and SCU2) x each heater
voltage in ``PARAMS.heater_voltages`` (applied to PSU ch1 and ch3
simultaneously -- LIA offset/VGS is a single shared knob for both
transistors, so one VGS sweep produces data for both SCU1 and SCU2 at once),
sweeps the LIA DC offset (== shared VGS) from ``vgs_start`` to ``vgs_stop``,
and at each point reads SCU1/SCU2 drain current with a sigma-gated averaging
protocol: take ``n_samples`` (default 10) current readings, and only accept
the point once the sample standard deviation is at most ``sigma_max_a``
(default 0.01 uA), retrying up to ``max_retries`` times otherwise. Rows where
the gate was never satisfied are still written, flagged ``reliable=False``.

Writes one raw CSV of every (vdd, heater_voltage, channel, vgs) point, then
runs an offline analysis pass (``analyze_csv``) that, per (vdd,
heater_voltage, channel), fits the subthreshold-exponential region to
extract:
  - SS (subthreshold swing, dVGS/d(log10 ID)) and the slope factor m,
    calibrated against a known room-temperature reference point (fixed vdd,
    the coolest heater voltage)
  - Vth, from where the curve departs the exponential fit
  - the VGS window where ID falls in [5, 10] uA (operating window)
  - VDS = VDD - ID*RL at every point, flagging VDS < 130 mV
and writes a summary CSV plus per-(vdd, channel) plots.

Run from the repo root:
    .venv/bin/python python/sources/transistor_characterization.py
Or from python/:
    ../.venv/bin/python sources/transistor_characterization.py

All the numeric knobs below can be overridden with CLI flags; see --help.
"""

import argparse
import csv
import logging
import math
import os
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime

# Match run_experiment.sh / .mcp.json: force the pure-Python VISA backend so
# no NI-VISA install is required. Must happen before pyvisa is imported by
# anything below.
os.environ.setdefault("PYVISA_LIBRARY", "@py")

# Add python/sources/ to path so ATE/config/mcp_server are importable as
# top-level packages, matching main.py's convention -- lets this script run
# from either the repo root or python/sources/.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np

from mcp_server import bounds
from mcp_server.operating_point_session import OperatingPointSession

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

BOLTZMANN_K = 1.380649e-23  # J/K
ELEMENTARY_Q = 1.602176634e-19  # C

# Physically plausible subthreshold-swing band used to sanity-bound the
# exponential-region detector below: ideal SS at room temp is
# ln(10)*kT/q =~ 59.6mV/dec (m=1); real devices run m~1-3, and this dataset
# spans several heater temperatures, so allow a generous 20-400mV/dec. Local
# slopes outside this band (near-flat/saturated stretches) are excluded from
# candidacy rather than being allowed to look like the "most consistent" run.
_SS_PLAUSIBLE_MIN_V_PER_DEC = 0.02
_SS_PLAUSIBLE_MAX_V_PER_DEC = 0.4

_CSV_FIELDS = [
    "timestamp", "vdd_v", "heater_voltage_v", "channel", "vgs_v",
    "mean_iscu_a", "sigma_iscu_a", "n_samples", "retries_used", "reliable",
    "mean_vscu_v", "mean_vd_measured_v", "vd_formula_v",
    "vd_below_130mv",
]


@dataclass
class SweepParams:
    """All tunable knobs for the sweep. Defaults reflect the decisions made
    for this run: heater 2.80/2.85/2.90V (both channels together), VDD
    2.9/3.1/3.3V on both SCU1/SCU2 (applied identically to both channels,
    same convention as heater_voltages), room temperature 296.15K (23C, no
    logged ambient sensor in this repo)."""

    heater_voltages: list[float] = field(default_factory=lambda: [2.80, 2.85, 2.90])
    vdd_voltages: list[float] = field(default_factory=lambda: [2.9, 3.1, 3.3])
    vgs_start_v: float = 0.85
    vgs_stop_v: float = 1.10
    vgs_step_v: float = 0.005  # 51 points over the default range

    n_samples: int = 10
    sample_interval_s: float = 0.2
    sigma_max_a: float = 1e-8  # 0.01 uA
    max_retries: int = 3
    retry_wait_s: float = 1.0

    offset_settle_s: float = 0.5   # wait after set_offset before sampling
    heater_settle_s: float = 30.0  # wait after set_heater_voltage

    room_temp_k: float = 296.15
    # Which (vdd, heater_voltage, channel) point is treated as the "known
    # room temperature" reference for solving m from SS. Heater can't go
    # below 2.8V (bounds.py hard floor), so the lowest achievable heater
    # voltage stands in for room temp -- an approximation, flagged in the
    # analysis output rather than assumed silently. m is a device/physics
    # constant independent of VDD, so a single reference VDD (the lowest
    # swept) is used regardless of which VDD a given SS was measured at.
    room_temp_heater_v: float = 2.80

    vd_flag_min_v: float = 0.130  # user's feasibility flag, independent of
    # bounds.VD_MIN_V (0.120V) which the session's own warnings use.
    id_window_lo_a: float = 5e-6
    id_window_hi_a: float = 10e-6

    session_folder: str | None = None


def vgs_points(p: SweepParams) -> list[float]:
    n = round((p.vgs_stop_v - p.vgs_start_v) / p.vgs_step_v)
    return [round(p.vgs_start_v + i * p.vgs_step_v, 6) for i in range(n + 1)]


def sigma_gated_read(
    session: OperatingPointSession, channel: str, p: SweepParams
) -> dict:
    """Read ``channel``'s drain current as the mean of ``p.n_samples``
    ``read_drain_state`` calls, retrying the whole batch up to
    ``p.max_retries`` times until the sample sigma is <= ``p.sigma_max_a``.
    Always returns a result; ``reliable`` is False if the gate was never
    satisfied (the last attempt's mean/sigma are still reported)."""
    last_currents: list[float] = []
    last_vscu: list[float] = []
    last_vd: list[float] = []
    sigma = float("inf")
    for attempt in range(1, p.max_retries + 1):
        currents, vscus, vds = [], [], []
        for k in range(p.n_samples):
            if k:
                time.sleep(p.sample_interval_s)
            state = session.read_drain_state(channel)
            currents.append(state["iscu_a"])
            vscus.append(state["vscu_v"])
            vds.append(state["vd_v"])
        sigma = float(np.std(currents, ddof=1)) if len(currents) > 1 else 0.0
        last_currents, last_vscu, last_vd = currents, vscus, vds
        if sigma <= p.sigma_max_a:
            return {
                "mean_iscu_a": float(np.mean(currents)),
                "sigma_iscu_a": sigma,
                "n_samples": len(currents),
                "retries_used": attempt - 1,
                "reliable": True,
                "mean_vscu_v": float(np.mean(vscus)),
                "mean_vd_measured_v": float(np.mean(vds)),
            }
        logger.warning(
            f"{channel}: sigma={sigma * 1e9:.2f}nA exceeds gate "
            f"{p.sigma_max_a * 1e9:.2f}nA on attempt {attempt}/{p.max_retries}"
        )
        if attempt < p.max_retries:
            time.sleep(p.retry_wait_s)
    logger.warning(
        f"{channel}: sigma gate never satisfied after {p.max_retries} attempts "
        f"(last sigma={sigma * 1e9:.2f}nA); recording as unreliable"
    )
    return {
        "mean_iscu_a": float(np.mean(last_currents)),
        "sigma_iscu_a": sigma,
        "n_samples": len(last_currents),
        "retries_used": p.max_retries,
        "reliable": False,
        "mean_vscu_v": float(np.mean(last_vscu)),
        "mean_vd_measured_v": float(np.mean(last_vd)),
    }


def run_sweep(p: SweepParams) -> str:
    """Run the full (vdd x heater_voltage x VGS x channel) sweep and return
    the raw CSV path."""
    stem = (
        p.session_folder
        or f"transistor_characterization_{datetime.now():%Y%m%d_%H%M%S}"
    )
    out_dir = os.path.join("Results", "TransistorCharacterization", stem)
    os.makedirs(out_dir, exist_ok=True)
    csv_path = os.path.join(out_dir, "sweep_raw.csv")
    logger.info(f"Starting transistor characterization sweep -> {out_dir}")

    points = vgs_points(p)
    lowest_heater = min(p.heater_voltages)
    logger.info(
        f"{len(points)} VGS points ({p.vgs_start_v}-{p.vgs_stop_v}V, "
        f"step {p.vgs_step_v}V) x {len(p.heater_voltages)} heater voltages "
        f"x {len(p.vdd_voltages)} VDD voltages x 2 channels"
    )

    session = OperatingPointSession(output_name="transistor_characterization")
    try:
        session.open_instruments()
        session.configure_signal()

        with open(csv_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=_CSV_FIELDS)
            writer.writeheader()

            for vdd_v in p.vdd_voltages:
                logger.info(f"=== VDD -> {vdd_v}V (SCU1/SCU2) ===")
                # Re-bias at the lowest VGS and coolest heater setting
                # before changing VDD: the heater may still be at the
                # previous VDD pass's hottest value, and combined with a
                # higher VDD that could push current above the
                # set_drain_voltage safety-rollback threshold. Heater can't
                # go below its 2.8V hard floor (bounds.py), so "coolest" is
                # the lowest configured heater_voltages entry, not off.
                session.set_offset(min(points))
                session.set_heater_voltage(1, lowest_heater)
                session.set_heater_voltage(3, lowest_heater)
                time.sleep(p.heater_settle_s)

                for channel in ("SCU1", "SCU2"):
                    result = session.set_drain_voltage(channel, vdd_v)
                    if result["warnings"]:
                        logger.info(
                            f"{channel} VDD={vdd_v}V warnings: {result['warnings']}"
                        )

                for heater_v in p.heater_voltages:
                    logger.info(f"--- heater -> {heater_v}V (both ch1/ch3) ---")
                    session.set_heater_voltage(1, heater_v)
                    session.set_heater_voltage(3, heater_v)
                    time.sleep(p.heater_settle_s)

                    for vgs in points:
                        session.set_offset(vgs)
                        time.sleep(p.offset_settle_s)
                        for channel in ("SCU1", "SCU2"):
                            r = sigma_gated_read(session, channel, p)
                            vd_formula = (
                                vdd_v
                                - bounds.SERIES_RESISTANCE_OHM * r["mean_iscu_a"]
                            )
                            row = {
                                "timestamp": datetime.now().isoformat(
                                    timespec="seconds"
                                ),
                                "vdd_v": vdd_v,
                                "heater_voltage_v": heater_v,
                                "channel": channel,
                                "vgs_v": vgs,
                                "mean_iscu_a": r["mean_iscu_a"],
                                "sigma_iscu_a": r["sigma_iscu_a"],
                                "n_samples": r["n_samples"],
                                "retries_used": r["retries_used"],
                                "reliable": r["reliable"],
                                "mean_vscu_v": r["mean_vscu_v"],
                                "mean_vd_measured_v": r["mean_vd_measured_v"],
                                "vd_formula_v": vd_formula,
                                "vd_below_130mv": vd_formula < p.vd_flag_min_v,
                            }
                            writer.writerow(row)
                            f.flush()
                            flag = (
                                " *** VDS<130mV ***" if row["vd_below_130mv"] else ""
                            )
                            rel = "" if r["reliable"] else " [UNRELIABLE]"
                            logger.info(
                                f"VDD={vdd_v}V heater={heater_v}V {channel} "
                                f"VGS={vgs:.4f}V ID={r['mean_iscu_a'] * 1e6:.3f}uA "
                                f"(sigma={r['sigma_iscu_a'] * 1e9:.2f}nA) "
                                f"Vd={vd_formula * 1e3:.1f}mV{flag}{rel}"
                            )
    finally:
        # Safety: drop VGS and drain bias back to a low/safe point before
        # closing, in addition to close_session()'s own de-energize.
        try:
            session.set_offset(p.vgs_start_v)
        except Exception:
            logger.exception("failed to reset offset before close")
        session.close()

    logger.info(f"Sweep complete. Raw CSV: {csv_path}")
    return csv_path


# --------------------------------------------------------------------------
# Analysis
# --------------------------------------------------------------------------

def _fit_exponential_region(vgs: np.ndarray, id_: np.ndarray) -> dict:
    """Fit log10(ID) vs VGS over the largest contiguous run of points whose
    local slope (between consecutive points) is both physically plausible
    (``_SS_PLAUSIBLE_MIN_V_PER_DEC``-``_SS_PLAUSIBLE_MAX_V_PER_DEC``) and
    within 20% of the median of those plausible slopes -- i.e. the
    subthreshold-exponential region -- then report SS, the fit window, and
    Vth as the VGS where the fit departs the data by more than 10% relative
    error (first point outside the contiguous run, or the last point if the
    whole sweep stayed exponential).

    The plausibility band matters: a flat/saturated stretch (current capped
    by VDD/RL, or instrument-quantized duplicate readings) also has a
    locally ~constant slope, just an enormous one (tiny d(log10 ID) for a
    large dVGS) -- without this band that plateau can end up looking like
    the "most consistent" run and getting fit as if it were exponential,
    producing a nonsense SS of several V/decade. Requiring individual
    segment slopes to fall in the real SS range before even considering them
    for the median/contiguity test excludes those plateaus outright.
    """
    order = np.argsort(vgs)
    vgs, id_ = vgs[order], id_[order]
    valid = id_ > 0
    vgs, id_ = vgs[valid], id_[valid]
    log_id = np.log10(id_)

    if len(vgs) < 3:
        return {"ss_v_per_dec": float("nan"), "vth_v": float("nan"),
                "fit_lo_v": float("nan"), "fit_hi_v": float("nan"), "r2": float("nan")}

    # Saturated/flat stretches (current capped by VDD/RL, or duplicate
    # samples) give a zero d(log10 ID) denominator; ignore the resulting
    # inf/nan warning here, `candidate` below excludes them anyway.
    with np.errstate(divide="ignore", invalid="ignore"):
        local_slope = np.diff(vgs) / np.diff(log_id)
    candidate = np.isfinite(local_slope) & (
        np.abs(local_slope) >= _SS_PLAUSIBLE_MIN_V_PER_DEC
    ) & (np.abs(local_slope) <= _SS_PLAUSIBLE_MAX_V_PER_DEC)
    median_slope = (
        float(np.median(local_slope[candidate])) if candidate.any() else float("nan")
    )

    # Longest contiguous run of points (as index ranges over local_slope)
    # within 20% of the median plausible local slope.
    within = candidate & (
        np.abs(local_slope - median_slope) <= 0.2 * abs(median_slope)
    )
    best_start = best_len = cur_start = cur_len = 0
    for i, ok in enumerate(within):
        if ok:
            if cur_len == 0:
                cur_start = i
            cur_len += 1
            if cur_len > best_len:
                best_start, best_len = cur_start, cur_len
        else:
            cur_len = 0
    if best_len == 0:
        return {"ss_v_per_dec": float("nan"), "vth_v": float("nan"),
                "fit_lo_v": float("nan"), "fit_hi_v": float("nan"), "r2": float("nan")}
    lo_idx, hi_idx = best_start, best_start + best_len  # index into vgs (points)

    fit_vgs = vgs[lo_idx:hi_idx + 1]
    fit_log_id = log_id[lo_idx:hi_idx + 1]
    if len(fit_vgs) < 2:
        return {"ss_v_per_dec": float("nan"), "vth_v": float("nan"),
                "fit_lo_v": float("nan"), "fit_hi_v": float("nan"), "r2": float("nan")}

    # VGS = slope*log10(ID) + intercept
    slope, intercept = np.polyfit(fit_log_id, fit_vgs, 1)
    ss = float(slope)  # V/decade
    pred = slope * fit_log_id + intercept
    ss_res = float(np.sum((fit_vgs - pred) ** 2))
    ss_tot = float(np.sum((fit_vgs - np.mean(fit_vgs)) ** 2))
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else float("nan")

    # Vth: first point past the fit window where the exponential
    # extrapolation departs the data by >10% in VGS terms, else the last
    # swept point.
    vth = float(vgs[hi_idx])
    for j in range(hi_idx + 1, len(vgs)):
        predicted_vgs = slope * log_id[j] + intercept
        if abs(predicted_vgs - vgs[j]) > 0.10 * abs(predicted_vgs):
            vth = float(vgs[j])
            break
    else:
        if hi_idx + 1 >= len(vgs):
            vth = float(vgs[-1])

    return {
        "ss_v_per_dec": ss, "vth_v": vth,
        "fit_lo_v": float(fit_vgs[0]), "fit_hi_v": float(fit_vgs[-1]), "r2": r2,
    }


def analyze_csv(csv_path: str, p: SweepParams) -> str:
    """Read the raw sweep CSV, fit each (vdd, heater_voltage, channel)
    curve, and write a summary CSV + plots alongside it. Returns the summary
    CSV path."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    rows: list[dict] = []
    with open(csv_path, newline="") as f:
        for row in csv.DictReader(f):
            row["vdd_v"] = float(row["vdd_v"])
            row["heater_voltage_v"] = float(row["heater_voltage_v"])
            row["vgs_v"] = float(row["vgs_v"])
            row["mean_iscu_a"] = float(row["mean_iscu_a"])
            row["vd_formula_v"] = float(row["vd_formula_v"])
            row["reliable"] = row["reliable"] == "True"
            rows.append(row)

    out_dir = os.path.dirname(csv_path)
    summary_path = os.path.join(out_dir, "summary.csv")
    groups: dict[tuple[float, float, str], list[dict]] = {}
    for row in rows:
        key = (row["vdd_v"], row["heater_voltage_v"], row["channel"])
        groups.setdefault(key, []).append(row)

    # -- room-temperature reference SS, for m -------------------------------
    # m is a device/physics constant independent of VDD, so a single
    # reference VDD (the lowest swept) is used regardless of which VDD a
    # given SS was later measured at.
    ref_vdd = min(p.vdd_voltages)
    ref_fits: dict[str, dict] = {}
    for channel in ("SCU1", "SCU2"):
        ref_rows = groups.get((ref_vdd, p.room_temp_heater_v, channel))
        if ref_rows:
            vgs = np.array([r["vgs_v"] for r in ref_rows])
            id_ = np.array([r["mean_iscu_a"] for r in ref_rows])
            ref_fits[channel] = _fit_exponential_region(vgs, id_)
    logger.warning(
        f"m calibration uses VDD={ref_vdd}V, heater={p.room_temp_heater_v}V as "
        f"a stand-in for room temperature ({p.room_temp_k}K) -- bounds.py's "
        f"heater floor is 2.8V so a true unheated/room-temp curve isn't "
        f"reachable through this session; treat m as approximate."
    )

    summary_rows = []
    with open(summary_path, "w", newline="") as f:
        fieldnames = [
            "vdd_v", "heater_voltage_v", "channel", "ss_v_per_dec", "ss_fit_r2",
            "vth_v", "fit_lo_v", "fit_hi_v", "m", "t_pixel_k",
            "window_vgs_lo_v", "window_vgs_hi_v", "n_vd_below_130mv",
            "n_unreliable_points",
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for (vdd_v, heater_v, channel), group_rows in sorted(groups.items()):
            vgs = np.array([r["vgs_v"] for r in group_rows])
            id_ = np.array([r["mean_iscu_a"] for r in group_rows])
            fit = _fit_exponential_region(vgs, id_)

            m = float("nan")
            t_pixel = float("nan")
            ref = ref_fits.get(channel)
            if ref and not math.isnan(ref["ss_v_per_dec"]):
                m = ref["ss_v_per_dec"] * ELEMENTARY_Q / (
                    math.log(10) * BOLTZMANN_K * p.room_temp_k
                )
                if not math.isnan(fit["ss_v_per_dec"]) and m > 0:
                    t_pixel = fit["ss_v_per_dec"] * ELEMENTARY_Q / (
                        math.log(10) * m * BOLTZMANN_K
                    )

            in_window = (id_ >= p.id_window_lo_a) & (id_ <= p.id_window_hi_a)
            window_lo = float(vgs[in_window].min()) if in_window.any() else float("nan")
            window_hi = float(vgs[in_window].max()) if in_window.any() else float("nan")

            n_below = sum(1 for r in group_rows if r["vd_formula_v"] < p.vd_flag_min_v)
            n_unreliable = sum(1 for r in group_rows if not r["reliable"])

            writer.writerow({
                "vdd_v": vdd_v, "heater_voltage_v": heater_v, "channel": channel,
                "ss_v_per_dec": fit["ss_v_per_dec"], "ss_fit_r2": fit["r2"],
                "vth_v": fit["vth_v"], "fit_lo_v": fit["fit_lo_v"],
                "fit_hi_v": fit["fit_hi_v"], "m": m, "t_pixel_k": t_pixel,
                "window_vgs_lo_v": window_lo, "window_vgs_hi_v": window_hi,
                "n_vd_below_130mv": n_below, "n_unreliable_points": n_unreliable,
            })
            summary_rows.append((vdd_v, heater_v, channel, fit, m, t_pixel))
            ss_mv = fit["ss_v_per_dec"] * 1e3
            logger.info(
                f"VDD={vdd_v}V heater={heater_v}V {channel}: SS={ss_mv:.1f}mV/dec "
                f"(R2={fit['r2']:.4f}) Vth~{fit['vth_v']:.4f}V m={m:.3f} "
                f"Tpixel={t_pixel:.1f}K window=[{window_lo:.4f},{window_hi:.4f}]V "
                f"Vd<130mV points={n_below} unreliable={n_unreliable}"
            )

    plots_dir = os.path.join(
        "Plots", "TransistorCharacterization", os.path.basename(out_dir)
    )
    os.makedirs(plots_dir, exist_ok=True)
    for vdd_v in p.vdd_voltages:
        for channel in ("SCU1", "SCU2"):
            fig, (ax_lin, ax_log) = plt.subplots(1, 2, figsize=(11, 4.5))
            for heater_v in p.heater_voltages:
                group_rows = groups.get((vdd_v, heater_v, channel))
                if not group_rows:
                    continue
                vgs = np.array([r["vgs_v"] for r in group_rows])
                id_ = np.array([r["mean_iscu_a"] for r in group_rows])
                order = np.argsort(vgs)
                ax_lin.plot(
                    vgs[order], id_[order] * 1e6, "o-", ms=3, label=f"{heater_v}V"
                )
                ax_log.semilogy(
                    vgs[order], id_[order], "o-", ms=3, label=f"{heater_v}V"
                )
            ax_lin.axhspan(
                p.id_window_lo_a * 1e6, p.id_window_hi_a * 1e6,
                color="green", alpha=0.1,
            )
            ax_lin.set_xlabel("VGS (V)")
            ax_lin.set_ylabel("ID (uA)")
            ax_lin.set_title(f"VDD={vdd_v}V {channel}: ID vs VGS")
            ax_lin.legend(fontsize=8)
            ax_log.set_xlabel("VGS (V)")
            ax_log.set_ylabel("ID (A)")
            ax_log.set_title(f"VDD={vdd_v}V {channel}: log(ID) vs VGS")
            ax_log.legend(fontsize=8)
            fig.tight_layout()
            plot_path = os.path.join(
                plots_dir, f"vdd{vdd_v:g}V_{channel}_id_vs_vgs.png"
            )
            fig.savefig(plot_path, dpi=150)
            plt.close(fig)
            logger.info(f"Plot saved to: {plot_path}")

    logger.info(f"Summary CSV: {summary_path}")
    return summary_path


def parse_args() -> SweepParams:
    p = SweepParams()
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--heater-voltages", type=float, nargs="+", default=p.heater_voltages
    )
    ap.add_argument(
        "--vdd-voltages", type=float, nargs="+", default=p.vdd_voltages
    )
    ap.add_argument("--vgs-start", type=float, default=p.vgs_start_v)
    ap.add_argument("--vgs-stop", type=float, default=p.vgs_stop_v)
    ap.add_argument("--vgs-step", type=float, default=p.vgs_step_v)
    ap.add_argument("--n-samples", type=int, default=p.n_samples)
    ap.add_argument("--sigma-max-a", type=float, default=p.sigma_max_a)
    ap.add_argument("--room-temp-k", type=float, default=p.room_temp_k)
    ap.add_argument("--session-folder", type=str, default=None)
    ap.add_argument(
        "--analyze-only", type=str, default=None,
        help="Skip the hardware sweep and re-analyze an existing raw CSV path",
    )
    args = ap.parse_args()

    p.heater_voltages = args.heater_voltages
    p.vdd_voltages = args.vdd_voltages
    p.vgs_start_v = args.vgs_start
    p.vgs_stop_v = args.vgs_stop
    p.vgs_step_v = args.vgs_step
    p.n_samples = args.n_samples
    p.sigma_max_a = args.sigma_max_a
    p.room_temp_k = args.room_temp_k
    p.session_folder = args.session_folder
    p._analyze_only = args.analyze_only  # type: ignore[attr-defined]
    return p


def main() -> None:
    p = parse_args()
    analyze_only = getattr(p, "_analyze_only", None)
    if analyze_only:
        analyze_csv(analyze_only, p)
        return
    csv_path = run_sweep(p)
    analyze_csv(csv_path, p)


if __name__ == "__main__":
    main()
