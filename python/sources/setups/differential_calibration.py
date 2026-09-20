"""
Differential-method phase-zero / drift calibration setup.
"""

import csv
import logging
import os
import time
from datetime import datetime

import ATE
import numpy as np
from config import ATEConfig, DifferentialCalibrationConfig
from plotting import plot_channels_timeseries_marks

from .lia_setup import LIAMeasurementSetup
from .setup_base import SetupBase

logger = logging.getLogger(__name__)


class DifferentialCalibration(SetupBase):
    """Find a heater-voltage (PSU ch1/ch3) operating point where the LIA's
    demodulated X output is both phase-locked (auto-zeroed) and drift-free,
    before a differential-method measurement run.

    Startup mirrors ``gas_response_interactive``: heater ch1/ch3 to
    ``temperature``, LIA reference from config, then ``initial_settle``.
    Phase is auto-zeroed (retried up to ``phase_zero_max_retries`` times).
    X/Y/theta are then sampled every ``sample_interval`` into one continuous
    CSV for the whole run, with a plaintext ``notes`` column narrating every
    action taken. Every ``window_duration`` seconds the slope of X vs time is
    checked; if it exceeds ``slope_threshold_v_per_s``, a bounded
    coordinate-descent search adjusts PSU ch1 then ch3 (increase then
    decrease) in ``psu_step`` increments up to ``psu_step_max`` away from
    ``temperature``, re-auto-zeroing and re-measuring after every step, until
    the slope converges or the search space is exhausted (in which case the
    best configuration found is applied as a best-effort result). Finally, a
    ``final_validation_duration`` (default 10 min) observation-only window
    runs at the resulting voltage to confirm the drift stays low over a
    longer horizon than the 30s search windows, with no further adjustment.
    """

    def __init__(
        self,
        output_name: str = None,  # type: ignore
        ate_config: ATEConfig = None,  # type: ignore
        config: DifferentialCalibrationConfig = None,  # type: ignore
    ) -> None:
        super().__init__(output_name=output_name, ate_config=ate_config)
        self.config: DifferentialCalibrationConfig = (
            config or DifferentialCalibrationConfig()
        )

    def _set_heater(self, channel: int, voltage: float) -> None:
        psu = self.open_no_reset(ATE.PSU(rm=self.rm))
        try:
            psu.set_voltage(channel, voltage)
        finally:
            psu.resource.close()

    def _sample_row(self, lia: "ATE.LIA", note: str = "") -> tuple[float, float, float]:
        """Snap X/Y/theta, write one CSV row (with an optional plaintext
        note), and record it for the final plot."""
        x, y, theta = lia.snap(0, 1, 3)  # 0=X, 1=Y, 3=Theta
        elapsed = time.time() - self._t0
        self._writer.writerow([self._row_index, elapsed, x, y, theta, note])
        self._csv_file.flush()
        self._t_all.append(elapsed)
        self._x_all.append(x)
        self._y_all.append(y)
        self._theta_all.append(theta)
        if note:
            self._marks.append((self._row_index, note))
            logger.info(note)
        self._row_index += 1
        return x, y, theta

    def _sample_for(
        self, lia: "ATE.LIA", duration: float, first_note: str = ""
    ) -> tuple[list[float], list[float]]:
        """Sample every ``sample_interval`` for ``duration`` seconds.

        Continuously recomputes the slope of X vs (window-relative) time as
        samples arrive, logged at DEBUG. Returns the window-relative
        ``(t, x)`` sample lists.
        """
        cfg = self.config
        n = max(1, int(duration / cfg.sample_interval))
        window_start = time.time()
        t_vals: list[float] = []
        x_vals: list[float] = []
        for i in range(n):
            x, _y, _theta = self._sample_row(lia, first_note if i == 0 else "")
            t_vals.append(time.time() - window_start)
            x_vals.append(x)
            if len(x_vals) >= 2:
                slope = float(np.polyfit(t_vals, x_vals, 1)[0])
                logger.debug(
                    f"Running slope estimate: {slope * 1e6:.3f} uV/s "
                    f"({len(x_vals)} samples)"
                )
            next_t = window_start + (i + 1) * cfg.sample_interval
            sleep_for = next_t - time.time()
            if sleep_for > 0:
                time.sleep(sleep_for)
        return t_vals, x_vals

    def _phase_zero(self, lia: "ATE.LIA") -> None:
        """Auto-phase, wait, and check theta settled within tolerance;
        retries up to ``phase_zero_max_retries`` times before raising."""
        cfg = self.config
        for attempt in range(1, cfg.phase_zero_max_retries + 1):
            lia.auto_phase()
            self._sample_row(
                lia, f"Auto-phase attempt {attempt}/{cfg.phase_zero_max_retries}"
            )
            self._sample_for(lia, cfg.phase_zero_wait)
            _x, _y, theta = self._sample_row(lia)
            theta_ok = abs(theta) <= cfg.theta_tolerance_deg
            note = (
                f"theta={theta:.4f}deg (tolerance {cfg.theta_tolerance_deg:g}deg): "
                f"{'settled' if theta_ok else 'retrying'}"
            )
            self._marks.append((self._row_index - 1, note))
            logger.info(note)
            if theta_ok:
                return
        raise RuntimeError(
            f"Phase auto-zero failed to settle within "
            f"{cfg.phase_zero_max_retries} attempts"
        )

    def _measure_window(
        self, lia: "ATE.LIA", note: str = "", duration: float | None = None
    ) -> float:
        cfg = self.config
        t_vals, x_vals = self._sample_for(
            lia, duration if duration is not None else cfg.window_duration,
            first_note=note,
        )
        if len(t_vals) < 2:
            return 0.0
        return float(np.polyfit(t_vals, x_vals, 1)[0])

    def _search_and_correct(self, lia: "ATE.LIA") -> None:
        cfg = self.config
        baseline_slope = self._measure_window(
            lia, f"Baseline window ({cfg.window_duration:g}s) start"
        )
        self._sample_row(
            lia, f"Baseline window end; slope={baseline_slope * 1e6:.3f} uV/s"
        )
        if abs(baseline_slope) <= cfg.slope_threshold_v_per_s:
            self._sample_row(
                lia, "Baseline slope within tolerance; no PSU adjustment needed"
            )
            return

        best_channel: int | None = None
        best_offset = 0.0
        best_abs_slope = abs(baseline_slope)

        for channel in (1, 3):
            for direction in (1, -1):
                sign = "+" if direction > 0 else "-"
                offset = 0.0
                prev_abs_slope = abs(baseline_slope)
                while True:
                    candidate_offset = offset + direction * cfg.psu_step
                    if abs(candidate_offset) > cfg.psu_step_max + 1e-9:
                        self._sample_row(
                            lia,
                            f"ch{channel} dir {sign}: reached max step bound "
                            f"({cfg.psu_step_max * 1e3:g}mV) without convergence",
                        )
                        break

                    new_voltage = cfg.temperature + candidate_offset
                    self._set_heater(channel, new_voltage)
                    self._sample_row(
                        lia,
                        f"PSU ch{channel} step {sign}: "
                        f"{cfg.temperature + offset:.4f}V -> {new_voltage:.4f}V",
                    )
                    self._phase_zero(lia)
                    new_slope = self._measure_window(
                        lia,
                        f"Measurement window ({cfg.window_duration:g}s) at "
                        f"ch{channel}={new_voltage:.4f}V",
                    )
                    self._sample_row(
                        lia,
                        f"Window end at ch{channel}={new_voltage:.4f}V; "
                        f"slope={new_slope * 1e6:.3f} uV/s",
                    )

                    if abs(new_slope) < best_abs_slope:
                        best_channel, best_offset, best_abs_slope = (
                            channel,
                            candidate_offset,
                            abs(new_slope),
                        )

                    if abs(new_slope) <= cfg.slope_threshold_v_per_s:
                        self._sample_row(
                            lia,
                            f"Calibration converged: ch{channel}={new_voltage:.4f}V, "
                            f"slope={new_slope * 1e6:.3f} uV/s",
                        )
                        return

                    if abs(new_slope) < prev_abs_slope:
                        self._sample_row(
                            lia,
                            f"Slope improved ({prev_abs_slope * 1e6:.3f} -> "
                            f"{abs(new_slope) * 1e6:.3f} uV/s); continuing ch{channel} "
                            f"dir {sign}",
                        )
                        offset = candidate_offset
                        prev_abs_slope = abs(new_slope)
                        continue
                    else:
                        reverted_voltage = cfg.temperature + offset
                        self._set_heater(channel, reverted_voltage)
                        self._sample_row(
                            lia,
                            f"Slope worsened ({prev_abs_slope * 1e6:.3f} -> "
                            f"{abs(new_slope) * 1e6:.3f} uV/s); reverted ch{channel} "
                            f"to {reverted_voltage:.4f}V",
                        )
                        break

                self._set_heater(channel, cfg.temperature)
                self._sample_row(
                    lia,
                    f"Restored ch{channel} to nominal {cfg.temperature:.4f}V "
                    "before next attempt",
                )

        if best_channel is not None:
            final_voltage = cfg.temperature + best_offset
            self._set_heater(best_channel, final_voltage)
            self._phase_zero(lia)
            self._sample_row(
                lia,
                f"Calibration did not converge; applying best-effort "
                f"ch{best_channel}={final_voltage:.4f}V, "
                f"|slope|={best_abs_slope * 1e6:.3f} uV/s",
            )
        else:
            self._sample_row(
                lia,
                "Calibration did not converge; keeping nominal temperature "
                "(no improvement found)",
            )

    def _final_validation(self, lia: "ATE.LIA") -> None:
        """Observation-only window at the resulting operating point: keeps
        sampling and fits the slope, but makes no further PSU adjustment —
        just confirms the chosen point holds up over a longer horizon than
        the 30s search windows."""
        cfg = self.config
        slope = self._measure_window(
            lia,
            f"Final validation window ({cfg.final_validation_duration:g}s) start; "
            "no further adjustment will be made",
            duration=cfg.final_validation_duration,
        )
        verdict = (
            "within tolerance"
            if abs(slope) <= cfg.slope_threshold_v_per_s
            else "ABOVE tolerance"
        )
        self._sample_row(
            lia,
            f"Final validation window end; slope={slope * 1e6:.3f} uV/s "
            f"(threshold {cfg.slope_threshold_v_per_s * 1e6:.3f} uV/s): {verdict}",
        )

    @SetupBase.setup_ate
    def run(self) -> None:
        cfg = self.config
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        stem = cfg.session_folder or f"differential_calibration_{timestamp}"
        out_dir = os.path.join(self.results_dir, stem)
        os.makedirs(out_dir, exist_ok=True)
        csv_path = os.path.join(out_dir, "calibration.csv")
        logger.info(
            f"Starting DifferentialCalibration @ {cfg.temperature:g}V, "
            f"{cfg.lia_frequency:g}Hz -> {csv_path}"
        )

        self._t_all: list[float] = []
        self._x_all: list[float] = []
        self._y_all: list[float] = []
        self._theta_all: list[float] = []
        self._marks: list[tuple[int, str]] = []

        try:
            with ATE.LIA(rm=self.rm) as lia, ATE.SCU(
                "SCU1", rm=self.rm
            ) as scu1, ATE.SCU("SCU2", rm=self.rm) as scu2:
                lia.reset()
                scu1.reset()
                scu2.reset()

                LIAMeasurementSetup._configure_lia_scu(lia, scu1, scu2, cfg)
                lia.set_frequency(cfg.lia_frequency)
                lia.set_phase(0)

                logger.info(f"Setting heater ch1/ch3 to {cfg.temperature:g}V")
                self._set_heater(1, cfg.temperature)
                self._set_heater(3, cfg.temperature)

                psu = self.open_no_reset(ATE.PSU(rm=self.rm))
                try:
                    self.snapshot.devices.clear()
                    self.snapshot_lia(lia)
                    self.snapshot_psu(psu, channel=1)
                    self.snapshot_psu(psu, channel=3)
                    self.snapshot_scu(scu1)
                    self.snapshot_scu(scu2)
                finally:
                    psu.resource.close()
                logger.info(f"Setup snapshot:\n{self.snapshot}")

                with open(csv_path, "w", newline="") as f:
                    self._csv_file = f
                    self._writer = csv.writer(f)
                    self._writer.writerows(self.snapshot.as_rows(width=6))
                    self._writer.writerow(["index", "time", "X", "Y", "theta", "notes"])
                    self._t0 = time.time()
                    self._row_index = 0

                    self._sample_for(
                        lia,
                        cfg.initial_settle,
                        first_note=f"Heater ch1/ch3 set to {cfg.temperature:g}V; "
                        f"settling {cfg.initial_settle:g}s",
                    )
                    self._phase_zero(lia)
                    self._search_and_correct(lia)
                    self._final_validation(lia)

                plot_channels_timeseries_marks(
                    csv_path,
                    np.array(self._t_all),
                    np.array(self._x_all),
                    np.array(self._y_all),
                    np.array(self._theta_all),
                    self._marks,
                    labels=("X (V)", "Y (V)", "Theta (deg)"),
                )
        finally:
            LIAMeasurementSetup._shutdown_all_devices(self.rm)
        logger.info("DifferentialCalibration complete.")
