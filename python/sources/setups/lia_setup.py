"""
LIA Measurement setup
"""

import csv
import logging
import os
import queue
import sys
import termios
import threading
import time
import tty
from datetime import datetime

import ATE
import numpy as np
import pyvisa
from config import (
    ATEConfig,
    LIAGasResponseInteractiveConfig,
    LIAInstrumentConfig,
    LIAReadoutConfig,
    LIASnapConfig,
)
from mcp_server.errors import PhaseZeroError
from plotting import plot_channels_timeseries_marks

from .setup_base import SetupBase

logger = logging.getLogger(__name__)

_VALID_MODES = (
    "readout",
    "scan_noise",
    "snap_only",
    "snap_sweep",
    "gas_response_interactive",
)

_ModeConfig = LIASnapConfig | LIAReadoutConfig | LIAGasResponseInteractiveConfig

# Discrete LIA time constants (seconds) paired with their enum values, sorted ascending.
_TIME_CONSTANTS_S: list[tuple[float, "ATE.TimeConstant"]] = [
    (1e-6, ATE.TimeConstant.US1),
    (3e-6, ATE.TimeConstant.US3),
    (1e-5, ATE.TimeConstant.US10),
    (3e-5, ATE.TimeConstant.US30),
    (1e-4, ATE.TimeConstant.US100),
    (3e-4, ATE.TimeConstant.US300),
    (1e-3, ATE.TimeConstant.MS1),
    (3e-3, ATE.TimeConstant.MS3),
    (1e-2, ATE.TimeConstant.MS10),
    (3e-2, ATE.TimeConstant.MS30),
    (1e-1, ATE.TimeConstant.MS100),
    (3e-1, ATE.TimeConstant.MS300),
    (1.0, ATE.TimeConstant.S1),
    (3.0, ATE.TimeConstant.S3),
    (10.0, ATE.TimeConstant.S10),
    (30.0, ATE.TimeConstant.S30),
    (1e3, ATE.TimeConstant.KS1),
    (3e3, ATE.TimeConstant.KS3),
    (1e4, ATE.TimeConstant.KS10),
    (3e4, ATE.TimeConstant.KS30),
]


def _round_up_time_constant(tau: float) -> tuple[float, ATE.TimeConstant]:
    """Round tau up to the closest available LIA time constant; return (value, enum)."""
    above = [(t, tc) for t, tc in _TIME_CONSTANTS_S if t >= tau]
    if above:
        return above[0]
    return _TIME_CONSTANTS_S[-1]


def _lia_timing(
    f_ref: float,
) -> tuple[float, ATE.TimeConstant, float, float, float, float]:
    """Derive LIA timing parameters from tau = 1.5/f_ref.

    Returns (tau_rounded, tc_enum, enbw, settling_time, measurement_time,
    sample_interval).
    """
    tau = 1.5 / f_ref
    tau_rounded, tc_enum = _round_up_time_constant(tau)
    enbw = 0.078 / tau_rounded
    settling_time = (10.05 * tau_rounded) * 1.2  # take another 10%
    measurement_time = 200.0 * tau_rounded
    sample_interval = 2.0 * tau_rounded
    return tau_rounded, tc_enum, enbw, settling_time, measurement_time, sample_interval


def _print_progress(elapsed: float, total: float, width: int = 30) -> None:
    frac = min(1.0, elapsed / total) if total > 0 else 1.0
    filled = int(frac * width)
    bar = "#" * filled + "-" * (width - filled)
    remaining = max(0.0, total - elapsed)
    print(
        f"\r[{bar}] {frac * 100:5.1f}% | elapsed {elapsed:6.1f}s | "
        f"remaining {remaining:6.1f}s",
        end="",
        flush=True,
    )


def sigma_phase_zero(
    lia: "ATE.LIA",
    n_samples: int = 30,
    sample_interval: float = 2.0,
    sigma_tolerance_deg: float = 0.2,
    max_iterations: int = 5,
) -> dict:
    """Auto-phase, then sample theta ``n_samples`` times and check that its
    standard deviation is below ``sigma_tolerance_deg``; retries up to
    ``max_iterations`` times.

    Unlike ``DifferentialCalibration._phase_zero`` (which checks a single
    post-settle theta sample against an absolute tolerance), this checks
    stability across a run of samples — needed when the pass/fail criterion
    is "phase noise has settled", not just "phase is near zero".

    Returns ``{"converged": True, "iterations", "sigma_deg", "mean_theta_deg",
    "samples"}`` on success. Raises ``PhaseZeroError`` if not converged within
    ``max_iterations``.
    """
    last_sigma_deg = float("inf")
    for iteration in range(1, max_iterations + 1):
        lia.auto_phase()
        samples = []
        for _ in range(n_samples):
            _x, _y, theta = lia.snap(0, 1, 3)  # 0=X, 1=Y, 3=Theta
            samples.append(theta)
            time.sleep(sample_interval)
        sigma_deg = float(np.std(samples))
        mean_theta_deg = float(np.mean(samples))
        logger.info(
            f"Phase auto-zero attempt {iteration}/{max_iterations}: "
            f"sigma={sigma_deg:.4f}deg (tolerance {sigma_tolerance_deg:g}deg), "
            f"mean theta={mean_theta_deg:.4f}deg"
        )
        if sigma_deg <= sigma_tolerance_deg:
            return {
                "converged": True,
                "iterations": iteration,
                "sigma_deg": sigma_deg,
                "mean_theta_deg": mean_theta_deg,
                "samples": samples,
            }
        last_sigma_deg = sigma_deg
    raise PhaseZeroError(max_iterations, last_sigma_deg)


def _watch_for_marks_or_esc(
    mark_queue: "queue.Queue[None]", stop_event: threading.Event
) -> None:
    """Start a daemon thread reading raw keypresses from stdin: Enter pushes
    onto ``mark_queue`` (one entry per press), Esc sets ``stop_event``.

    Puts the terminal in cbreak mode so each key is seen the instant it's
    pressed, instead of only after a newline (needed to tell Enter and Esc
    apart without the operator having to type a full line). Restores the
    original terminal settings once ``stop_event`` fires. Runs alongside a
    sampling loop, checking the queue/event each cycle.
    """
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)

    def _watcher():
        try:
            tty.setcbreak(fd)
            while not stop_event.is_set():
                ch = sys.stdin.read(1)
                if ch in ("\r", "\n"):
                    mark_queue.put(None)
                elif ch == "\x1b":
                    stop_event.set()
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

    threading.Thread(target=_watcher, daemon=True).start()


class LIAMeasurementSetup(SetupBase):
    def __init__(
        self,
        output_name: str = None,  # type: ignore
        mode: str = "readout",
        ate_config: ATEConfig = None,  # type: ignore
        config: _ModeConfig = None,  # type: ignore
    ) -> None:
        super().__init__(output_name=output_name, ate_config=ate_config)
        if mode not in _VALID_MODES:
            raise ValueError(f"mode must be one of {_VALID_MODES}, got {mode!r}")
        self.mode = mode
        stem = (
            output_name
            if output_name
            else f"{mode}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )
        self.data_file = os.path.join(self.results_dir, f"{stem}.csv")
        # snap_only / snap_sweep mode parameters
        self.snap_config: LIASnapConfig = (
            config if isinstance(config, LIASnapConfig) else LIASnapConfig()
        )
        # readout / scan_noise mode parameters
        self.readout_config: LIAReadoutConfig = (
            config if isinstance(config, LIAReadoutConfig) else LIAReadoutConfig()
        )
        # gas_response_interactive mode parameters
        self.gas_response_interactive_config: LIAGasResponseInteractiveConfig = (
            config
            if isinstance(config, LIAGasResponseInteractiveConfig)
            else LIAGasResponseInteractiveConfig()
        )

    @SetupBase.setup_ate
    def run(self):
        if self.mode == "readout":
            self.lia_readout()
        if self.mode == "scan_noise":
            self.noise_scan()
        if self.mode == "snap_only":
            self.snap_only()
        if self.mode == "snap_sweep":
            self.snap_sweep()
        if self.mode == "gas_response_interactive":
            self.gas_response_interactive()

    @staticmethod
    def _configure_lia_scu(
        lia: "ATE.LIA", scu1: "ATE.SCU", scu2: "ATE.SCU", cfg: LIAInstrumentConfig
    ) -> None:
        """Apply the shared LIA + SCU bias settings from ``cfg`` (no ``*RST``)."""
        # LIA signal configuration
        lia.set_offset(cfg.offset)
        lia.set_amplitude(cfg.amplitude)
        lia.set_sensitivity(cfg.sensitivity)

        # LIA filter and input settings
        lia.set_filter_slope(cfg.filter_slope)
        lia.set_time_constant(cfg.time_constant)
        lia.set_input_coupling(cfg.input_coupling)
        lia.set_input_source(cfg.input_source)
        lia.set_input_range(cfg.input_range)

        # SCU1: voltage mode
        scu1.set_source_function(
            ATE.SourceFunction.VOLTAGE, cfg.scu_compliance, channel=1
        )
        scu1.set_voltage(cfg.v_scu1, channel=1)
        scu1.enable_output(channel=1)

        # SCU2: voltage mode
        scu2.set_source_function(
            ATE.SourceFunction.VOLTAGE, cfg.scu_compliance, channel=1
        )
        scu2.set_voltage(cfg.v_scu2, channel=1)
        scu2.enable_output(channel=1)

    def _run_readout(
        self,
        lia_frequency: float,
        csv_path: str,
        time_const: ATE.TimeConstant,
        measurement_time: float,
        sample_interval: float,
        settling_time: float = 250.0,
    ) -> None:

        cfg = self.readout_config
        n_cycles = max(1, int(measurement_time / sample_interval))

        with ATE.LIA(rm=self.rm) as lia, ATE.SCU("SCU1", rm=self.rm) as scu1, ATE.SCU(
            "SCU2", rm=self.rm
        ) as scu2:
            lia.reset()
            scu1.reset()
            scu2.reset()

            self._configure_lia_scu(lia, scu1, scu2, cfg)
            lia.set_frequency(lia_frequency)
            lia.set_time_constant(time_const)

            logger.info("Dummy read and let LIA settle")
            _, _, _ = lia.snap(0, 1, 3)  # 0=X, 1=Y, 3=Theta

            logger.info("Zero LIA phase")
            lia.auto_phase()

            logger.info(f"Letting signals to settle ({settling_time:g}s)")
            time.sleep(settling_time)

            logger.info(
                f"Measuring {n_cycles} samples @ {sample_interval:g}s "
                f"(~{measurement_time:g}s) → {csv_path}"
            )
            with open(csv_path, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["time", "X", "Y", "Theta"])
                start = time.time()
                for i in range(n_cycles):
                    x, y, theta = lia.snap(0, 1, 3)  # 0=X, 1=Y, 3=Theta
                    elapsed = time.time() - start
                    writer.writerow([elapsed, x, y, theta])
                    _print_progress(elapsed, measurement_time)
                    next_t = start + (i + 1) * sample_interval
                    sleep_for = next_t - time.time()
                    if sleep_for > 0:
                        time.sleep(sleep_for)
                _print_progress(time.time() - start, measurement_time)
                print()

            lia.reset()
            scu1.reset()
            scu2.reset()

    def lia_readout(self):
        lia_frequency = self.readout_config.lia_frequency
        logger.info("Starting LIAMeasurementSetup (readout)")
        tau, tc, enbw, settling_time, measurement_time, sample_interval = _lia_timing(
            lia_frequency
        )
        logger.info(
            f"f_ref={lia_frequency} Hz: tau={tau:g}s ({tc.name}), ENBW={enbw:g} Hz, "
            f"settling={settling_time:g}s, meas={measurement_time:g}s, "
            f"dt={sample_interval:g}s"
        )
        self._run_readout(
            lia_frequency,
            csv_path=self.data_file,
            time_const=tc,
            measurement_time=measurement_time,
            sample_interval=sample_interval,
            settling_time=settling_time,
        )
        logger.info("LIA measurement complete.")

    def _snap_capture(
        self,
        csv_path: str,
        duration: float,
        sample_interval: float,
        set_frequency: float = None,  # type: ignore
        settle: float = 0.0,
        auto_phase: bool = False,
        autophase_settle: float = 0.0,
    ) -> None:
        """Open the instruments without reset, capture a setup snapshot, then snap
        X/Y/R at fixed intervals into ``csv_path``.

        Never issues ``*RST``. If ``self.snap_config.configure_instruments`` is
        set, the LIA + SCU bias settings from ``self.snap_config`` are applied
        first (LIA, then both SCUs); otherwise the live configuration is left
        untouched, as if set up by hand beforehand. Either way, the LIA
        reference frequency (``set_frequency``) is optionally changed next,
        then it waits ``settle`` seconds (e.g. thermal settling). If
        ``auto_phase`` is set, an LIA auto-phase is triggered after that,
        followed by a further ``autophase_settle`` wait, before capturing
        starts. The PSU is never reconfigured here, so it otherwise keeps
        providing ESD protection while its settings are read.
        """
        n_cycles = max(1, int(duration / sample_interval))

        # Bypass the context manager: ATEBase.__exit__ calls reset() (*RST).
        # We open the VISA resources manually and close them without resetting.
        opened = []
        try:
            lia = self.open_no_reset(ATE.LIA(rm=self.rm))
            opened.append(lia)
            psu = self.open_no_reset(ATE.PSU(rm=self.rm))
            opened.append(psu)
            scu1 = self.open_no_reset(ATE.SCU("SCU1", rm=self.rm))
            opened.append(scu1)
            scu2 = self.open_no_reset(ATE.SCU("SCU2", rm=self.rm))
            opened.append(scu2)
        except Exception:
            for device in opened:
                device.resource.close()
            raise
        try:
            # *IDN? puts the SR860 into remote mode without altering its configuration.
            idn = lia.idn().strip()
            logger.info(f"LIA IDN: {idn}")
            # HP6624A has no IDN string (returns "\n"); the query still establishes
            # remote communication without changing the PSU's configuration.
            psu_idn = psu.idn().strip()
            logger.info(f"PSU IDN: {psu_idn!r}")

            if self.snap_config.configure_instruments:
                logger.info("Applying LIA + SCU bias configuration from snap_config")
                self._configure_lia_scu(lia, scu1, scu2, self.snap_config)

            if set_frequency is not None:
                logger.info(f"Setting LIA reference frequency to {set_frequency:g} Hz")
                lia.set_frequency(set_frequency)
                if settle > 0:
                    logger.info(f"Settling for {settle:g}s")
                    time.sleep(settle)
                if auto_phase:
                    logger.info("Auto-phasing LIA")
                    lia.auto_phase()
                    if autophase_settle > 0:
                        logger.info(
                            f"Settling for {autophase_settle:g}s after auto-phase"
                        )
                        time.sleep(autophase_settle)

            # Capture the LIA config, all four PSU channels (ch2=ESD, ch4=fan),
            # and both B2962 SMUs. Clear first so the snapshot reflects only this run.
            self.snapshot.devices.clear()
            self.snapshot_lia(lia)
            for ch in (1, 2, 3, 4):
                self.snapshot_psu(psu, channel=ch)
            self.snapshot_scu(scu1)
            self.snapshot_scu(scu2)
            logger.info(f"Setup snapshot:\n{self.snapshot}")

            with open(csv_path, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerows(self.snapshot.as_rows(width=4))
                writer.writerow(["time", "X", "Y", "R"])
                start = time.time()
                for i in range(n_cycles):
                    x, y, r = lia.snap(0, 1, 2)  # 0=X, 1=Y, 2=R
                    elapsed = time.time() - start
                    writer.writerow([elapsed, x, y, r])
                    _print_progress(elapsed, duration)
                    next_t = start + (i + 1) * sample_interval
                    sleep_for = next_t - time.time()
                    if sleep_for > 0:
                        time.sleep(sleep_for)
                _print_progress(time.time() - start, duration)
                print()
        finally:
            lia.resource.close()
            psu.resource.close()
            scu1.resource.close()
            scu2.resource.close()

    def snap_only(self):
        """Snap X, Y, R from the SR860 at fixed intervals for a given duration.

        Never resets any instrument. By default assumes the LIA is already set
        up by hand; set ``configure_instruments`` on the config to apply the
        LIA + SCU bias settings first instead.
        """
        cfg = self.snap_config
        logger.info(
            f"Starting LIA snap_only: duration={cfg.duration:g}s, "
            f"dt={cfg.sample_interval:g}s → {self.data_file}"
        )
        self._snap_capture(self.data_file, cfg.duration, cfg.sample_interval)
        logger.info("LIA snap_only complete.")

    @staticmethod
    def _shutdown_all_devices(rm: "pyvisa.ResourceManager") -> None:  # type: ignore
        """De-energize the whole setup once a run is done, so no output voltage
        remains. Order matters: SR860 (LIA) first — its DC offset and sine
        amplitude are explicitly zeroed, since ``*RST`` alone isn't guaranteed
        to — then both Keysight B2962A SCUs, then the HP6624A PSU last (this
        also drops ESD/fan/heater channels, so only call this once a run is
        fully finished).
        """
        logger.info("Shutting down setup: SR860 -> Keysight SCUs -> HP6624A PSU")

        with ATE.LIA(rm=rm) as lia:
            lia.set_amplitude(0)
            lia.set_offset(0)
            # __exit__ also issues *RST on close.

        with ATE.SCU("SCU1", rm=rm) as scu1:
            scu1.disable_output(channel=1)
            scu1.set_voltage(0, channel=1)

        with ATE.SCU("SCU2", rm=rm) as scu2:
            scu2.disable_output(channel=1)
            scu2.set_voltage(0, channel=1)

        with ATE.PSU(rm=rm) as psu:
            for ch in (1, 2, 3, 4):
                psu.disable_output(ch)

        logger.info("Shutdown complete; no output voltage should remain.")

    def snap_sweep(self):
        """Run a LIA snap capture at each reference frequency, saving one CSV per
        frequency into ``Results/LIAMeasurementSetup/<folder>/``.

        Frequencies, folder and settle time come from ``self.snap_config``
        (set from the CLI's ``--config``). By default assumes the LIA
        (amplitude, sensitivity, etc.) is already set up and only changes the
        reference frequency between captures; set ``configure_instruments`` on
        the config to also apply the LIA + SCU bias settings before each
        capture. Once the sweep finishes (or fails), all devices are reset so
        no output voltage remains on the setup.
        """
        cfg = self.snap_config
        if not cfg.frequencies:
            raise ValueError("snap_sweep requires cfg.frequencies to be set")
        folder = (
            cfg.sweep_folder or f"snap_sweep_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )
        out_dir = os.path.join(self.results_dir, folder)
        os.makedirs(out_dir, exist_ok=True)
        logger.info(f"Starting LIA snap sweep over {cfg.frequencies} Hz → {out_dir}")
        try:
            for i, f in enumerate(cfg.frequencies):
                csv_path = os.path.join(out_dir, f"{f:g}Hz.csv")
                logger.info(f"--- f={f:g} Hz → {csv_path} ---")
                is_first = i == 0
                try:
                    self._snap_capture(
                        csv_path,
                        cfg.duration,
                        cfg.sample_interval,
                        set_frequency=f,
                        settle=cfg.first_settle if is_first else cfg.settle,
                        auto_phase=is_first and cfg.first_auto_phase,
                        autophase_settle=cfg.first_autophase_settle
                        if is_first
                        else 0.0,
                    )
                except Exception:
                    logger.exception(
                        f"Capture at f={f:g} Hz failed; skipping to next frequency"
                    )
        finally:
            self._shutdown_all_devices(self.rm)
        logger.info("LIA snap sweep complete.")

    def noise_scan(self):
        logger.info("Starting LIAMeasurementSetup (noise scan)")
        frequencies = self.readout_config.frequencies
        logger.info(f"Scanning in range {frequencies}")
        result_paths = [
            os.path.join(self.results_dir, f"scan_noise_f{f}.csv") for f in frequencies
        ]
        for f, fp in zip(frequencies, result_paths):
            tau, tc, enbw, settling_time, measurement_time, sample_interval = (
                _lia_timing(f)
            )
            logger.info(
                f"Measurement f={f} Hz: tau={tau:g}s ({tc.name}), ENBW={enbw:g} Hz, "
                f"settling={settling_time:g}s, meas={measurement_time:g}s, "
                f"dt={sample_interval:g}s"
            )
            self._run_readout(
                lia_frequency=f,
                csv_path=fp,
                time_const=tc,
                measurement_time=measurement_time,
                sample_interval=sample_interval,
                settling_time=settling_time,
            )
        logger.info("LIA measurement complete.")

        logger.info("Starting noise analysis")
        R_avg = []
        phase_avg = []
        X_std = []
        Y_std = []
        R_std = []

        logger.info(
            "Loop over all result and calculate phase average and standard deviation."
        )
        for fp in result_paths:
            with open(fp, mode="r") as f:
                reader = csv.DictReader(f)
                theta_vals, x_vals, y_vals, r_vals = [], [], [], []
                for row in reader:
                    theta_vals.append(float(row["Theta"]))
                    x_vals.append(float(row["X"]))
                    y_vals.append(float(row["Y"]))
                    r_vals.append(np.sqrt(float(row["X"]) ** 2 + float(row["Y"]) ** 2))
                R_avg.append(np.average(r_vals))
                phase_avg.append(np.average(theta_vals))
                X_std.append(np.std(x_vals))
                Y_std.append(np.std(y_vals))
                R_std.append(np.std(r_vals))

        logger.info("Store results")
        summary_filename = os.path.join(self.results_dir, "std_phase.csv")
        with open(summary_filename, mode="w", newline="") as fn:
            writer = csv.writer(fn)
            writer.writerow(
                [
                    "f_ref [Hz]",
                    "R_avg [V]",
                    "R_std [V]",
                    "Phase_avg [deg]",
                    "X_std [V]",
                    "Y_std [V]",
                ]
            )
            for f, r_avg, r_std, p_avg, x_std, y_std in zip(
                frequencies, R_avg, R_std, phase_avg, X_std, Y_std
            ):
                writer.writerow([f, r_avg, r_std, p_avg, x_std, y_std])

    def _capture_gas_response_interactive(
        self,
        lia: "ATE.LIA",
        csv_path: str,
        sample_interval: float,
        mark_label_prefix: str = "mark",
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, list[tuple[int, str]]]:
        """Snap X/Y/R once per ``sample_interval`` into a single continuous CSV
        with ``index``/``event`` columns, until the operator stops it.

        The operator can mark any number of points: every Enter press marks
        the current row as ``f"{mark_label_prefix}_N"`` (N = 1, 2, 3, ...) without
        pausing or
        ending the capture, and pressing Esc stops recording. Sampling
        starts immediately and never pauses while waiting for a keypress.
        Returns ``(t, x, y, r, marks)`` where ``marks`` is a list of
        ``(index, label)`` pairs in the order they were pressed.
        """
        t_samples: list[float] = []
        x_samples: list[float] = []
        y_samples: list[float] = []
        r_samples: list[float] = []
        marks: list[tuple[int, str]] = []
        mark_queue: "queue.Queue[None]" = queue.Queue()
        stop_event = threading.Event()
        _watch_for_marks_or_esc(mark_queue, stop_event)

        print(
            f"Recording... press Enter to mark ({mark_label_prefix}_N), "
            "Esc to stop and start analysis."
        )
        with open(csv_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerows(self.snapshot.as_rows(width=6))
            writer.writerow(["index", "time", "X", "Y", "R", "event"])
            start = time.time()
            i = 0
            while not stop_event.is_set():
                x, y, r = lia.snap(0, 1, 2)  # 0=X, 1=Y, 2=R
                elapsed = time.time() - start
                row_events = []
                while True:
                    try:
                        mark_queue.get_nowait()
                    except queue.Empty:
                        break
                    label = f"{mark_label_prefix}_{len(marks) + 1}"
                    marks.append((i, label))
                    row_events.append(label)
                    logger.info(f"{label} marked at index {i} (t={elapsed:.2f}s)")
                writer.writerow([i, elapsed, x, y, r, ";".join(row_events)])
                f.flush()
                t_samples.append(elapsed)
                x_samples.append(x)
                y_samples.append(y)
                r_samples.append(r)
                i += 1
                if stop_event.is_set():
                    break
                next_t = start + i * sample_interval
                sleep_for = next_t - time.time()
                if sleep_for > 0:
                    stop_event.wait(sleep_for)
            print()
        return (
            np.array(t_samples),
            np.array(x_samples),
            np.array(y_samples),
            np.array(r_samples),
            marks,
        )

    def gas_response_interactive(self) -> None:
        """Manually-gated capture at a fixed (``temperature``, ``lia_frequency``)
        operating point, with an unbounded number of operator-marked events.

        After the initial Enter press starts recording, every further Enter
        press marks the current row (``cfg.mark_label_prefix`` + an
        incrementing number) without stopping the capture, and pressing Esc
        stops recording and moves straight into plotting/analysis — so the
        operator decides on the fly how many insertions/removals to mark and
        when the run is done.
        """
        cfg = self.gas_response_interactive_config
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        stem = cfg.session_folder or f"gas_response_interactive_{timestamp}"
        out_dir = os.path.join(self.results_dir, stem)
        os.makedirs(out_dir, exist_ok=True)
        logger.info(
            f"Starting LIA gas_response_interactive @ {cfg.temperature:g}V, "
            f"{cfg.lia_frequency:g}Hz -> {out_dir}"
        )

        try:
            with ATE.LIA(rm=self.rm) as lia, ATE.SCU(
                "SCU1", rm=self.rm
            ) as scu1, ATE.SCU("SCU2", rm=self.rm) as scu2:
                lia.reset()
                scu1.reset()
                scu2.reset()

                self._configure_lia_scu(lia, scu1, scu2, cfg)
                lia.set_frequency(cfg.lia_frequency)
                lia.set_phase(0)

                psu = self.open_no_reset(ATE.PSU(rm=self.rm))
                try:
                    logger.info(
                        f"Setting temperature: {cfg.temperature:g}V (heater ch1/ch3)"
                    )
                    psu.set_voltage(1, cfg.temperature)
                    psu.set_voltage(3, cfg.temperature)

                    if cfg.v_scu1_start is not None:
                        logger.info(
                            f"Setting SCU1 starting bias: {cfg.v_scu1_start:g}V"
                        )
                        scu1.set_voltage(cfg.v_scu1_start, channel=1)
                    if cfg.v_scu2_start is not None:
                        logger.info(
                            f"Setting SCU2 starting bias: {cfg.v_scu2_start:g}V"
                        )
                        scu2.set_voltage(cfg.v_scu2_start, channel=1)

                    logger.info(f"Settling for {cfg.settle:g}s")
                    time.sleep(cfg.settle)

                    self.snapshot.devices.clear()
                    self.snapshot_lia(lia)
                    self.snapshot_psu(psu, channel=1)
                    self.snapshot_psu(psu, channel=3)
                    self.snapshot_scu(scu1)
                    self.snapshot_scu(scu2)
                    logger.info(f"Setup snapshot:\n{self.snapshot}")

                    input("Press Enter to begin measurement...")

                    gas_csv_path = os.path.join(out_dir, "gas_response.csv")
                    logger.info(f"Recording gas response -> {gas_csv_path}")
                    t, x, y, r, marks = self._capture_gas_response_interactive(
                        lia,
                        gas_csv_path,
                        cfg.sample_interval,
                        mark_label_prefix=cfg.mark_label_prefix,
                    )

                    plot_channels_timeseries_marks(gas_csv_path, t, x, y, r, marks)
                finally:
                    psu.resource.close()
        finally:
            self._shutdown_all_devices(self.rm)
        logger.info("LIA gas_response_interactive complete.")
