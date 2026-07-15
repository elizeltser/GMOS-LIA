"""
LIA Measurement setup
"""

import csv
import logging
import os
import threading
import time
from dataclasses import replace
from datetime import datetime
from typing import Callable

import ATE
import numpy as np
from config import (
    ATEConfig,
    HeaterConfig,
    LIAGasResponseConfig,
    LIAInstrumentConfig,
    LIAReadoutConfig,
    LIASnapConfig,
)

from .setup_base import SetupBase

logger = logging.getLogger(__name__)

_VALID_MODES = ("readout", "scan_noise", "snap_only", "snap_sweep", "gas_response")

# Discrete LIA time constants (seconds) paired with their enum values, sorted ascending.
_TIME_CONSTANTS_S: list[tuple[float, "ATE.TimeConstant"]] = [
    (1e-6, ATE.TimeConstant.US1),   (3e-6, ATE.TimeConstant.US3),
    (1e-5, ATE.TimeConstant.US10),  (3e-5, ATE.TimeConstant.US30),
    (1e-4, ATE.TimeConstant.US100), (3e-4, ATE.TimeConstant.US300),
    (1e-3, ATE.TimeConstant.MS1),   (3e-3, ATE.TimeConstant.MS3),
    (1e-2, ATE.TimeConstant.MS10),  (3e-2, ATE.TimeConstant.MS30),
    (1e-1, ATE.TimeConstant.MS100), (3e-1, ATE.TimeConstant.MS300),
    (1.0,  ATE.TimeConstant.S1),    (3.0,  ATE.TimeConstant.S3),
    (10.0, ATE.TimeConstant.S10),   (30.0, ATE.TimeConstant.S30),
    (1e3,  ATE.TimeConstant.KS1),   (3e3,  ATE.TimeConstant.KS3),
    (1e4,  ATE.TimeConstant.KS10),  (3e4,  ATE.TimeConstant.KS30),
]


def _round_up_time_constant(tau: float) -> tuple[float, ATE.TimeConstant]:
    """Round tau up to the closest available LIA time constant; return (value, enum)."""
    above = [(t, tc) for t, tc in _TIME_CONSTANTS_S if t >= tau]
    if above:
        return above[0]
    return _TIME_CONSTANTS_S[-1]


def _lia_timing(f_ref: float) -> tuple[float, ATE.TimeConstant, float, float, float, float]:
    """Derive LIA timing parameters from tau = 1.5/f_ref.

    Returns (tau_rounded, tc_enum, enbw, settling_time, measurement_time, sample_interval).
    """
    tau = 1.5 / f_ref
    tau_rounded, tc_enum = _round_up_time_constant(tau)
    enbw = 0.078 / tau_rounded
    settling_time = ( 10.05 * tau_rounded ) * 1.2 # take another 10%
    measurement_time = 200.0 * tau_rounded
    sample_interval = 2.0 * tau_rounded
    return tau_rounded, tc_enum, enbw, settling_time, measurement_time, sample_interval


def _print_progress(elapsed: float, total: float, width: int = 30) -> None:
    frac = min(1.0, elapsed / total) if total > 0 else 1.0
    filled = int(frac * width)
    bar = "#" * filled + "-" * (width - filled)
    remaining = max(0.0, total - elapsed)
    print(f"\r[{bar}] {frac * 100:5.1f}% | elapsed {elapsed:6.1f}s | remaining {remaining:6.1f}s",
          end="", flush=True)


def _watch_for_enter(prompt: str) -> threading.Event:
    """Start a daemon thread blocked on ``input()``; set the returned Event once Enter is pressed.

    Lets a sampling loop keep running (checking the event each cycle) while
    concurrently waiting for the operator's next keypress, instead of having
    to choose between sampling and waiting.
    """
    stop_event = threading.Event()

    def _watcher():
        input(prompt)
        stop_event.set()

    threading.Thread(target=_watcher, daemon=True).start()
    return stop_event


class LIAMeasurementSetup(SetupBase):
    def __init__(self, output_name: str = None, mode: str = "readout",  # type: ignore
                 ate_config: ATEConfig = None,  # type: ignore
                 config: LIASnapConfig | LIAReadoutConfig | LIAGasResponseConfig = None) -> None:  # type: ignore
        super().__init__(output_name=output_name, ate_config=ate_config)
        if mode not in _VALID_MODES:
            raise ValueError(f"mode must be one of {_VALID_MODES}, got {mode!r}")
        self.mode = mode
        stem = output_name if output_name else f'{mode}_{datetime.now().strftime("%Y%m%d_%H%M%S")}'
        self.data_file = os.path.join(self.results_dir, f'{stem}.csv')
        # snap_only / snap_sweep mode parameters
        self.snap_config: LIASnapConfig = config if isinstance(config, LIASnapConfig) else LIASnapConfig()
        # readout / scan_noise mode parameters
        self.readout_config: LIAReadoutConfig = config if isinstance(config, LIAReadoutConfig) else LIAReadoutConfig()
        # gas_response mode parameters
        self.gas_response_config: LIAGasResponseConfig = (
            config if isinstance(config, LIAGasResponseConfig) else LIAGasResponseConfig())

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
        if self.mode == "gas_response":
            self.gas_response()

    @staticmethod
    def _configure_lia_scu(lia: "ATE.LIA", scu1: "ATE.SCU", scu2: "ATE.SCU",
                           cfg: LIAInstrumentConfig) -> None:
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
        scu1.set_source_function(ATE.SourceFunction.VOLTAGE, cfg.scu_compliance, channel=1)
        scu1.set_voltage(cfg.v_scu1, channel=1)
        scu1.enable_output(channel=1)

        # SCU2: voltage mode
        scu2.set_source_function(ATE.SourceFunction.VOLTAGE, cfg.scu_compliance, channel=1)
        scu2.set_voltage(cfg.v_scu2, channel=1)
        scu2.enable_output(channel=1)

    def _run_readout(self, lia_frequency: float, csv_path: str, time_const: ATE.TimeConstant,
                     measurement_time: float, sample_interval: float,
                     settling_time: float = 250.0) -> None:

        cfg = self.readout_config
        n_cycles = max(1, int(measurement_time / sample_interval))

        with ATE.LIA(rm=self.rm) as lia, ATE.SCU('SCU1', rm=self.rm) as scu1, ATE.SCU('SCU2', rm=self.rm) as scu2:
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

            logger.info(f"Measuring {n_cycles} samples @ {sample_interval:g}s "
                        f"(~{measurement_time:g}s) → {csv_path}")
            with open(csv_path, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['time', 'X', 'Y', 'Theta'])
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
        tau, tc, enbw, settling_time, measurement_time, sample_interval = _lia_timing(lia_frequency)
        logger.info(f"f_ref={lia_frequency} Hz: tau={tau:g}s ({tc.name}), ENBW={enbw:g} Hz, "
                    f"settling={settling_time:g}s, meas={measurement_time:g}s, dt={sample_interval:g}s")
        self._run_readout(lia_frequency, csv_path=self.data_file, time_const=tc,
                          measurement_time=measurement_time, sample_interval=sample_interval,
                          settling_time=settling_time)
        logger.info("LIA measurement complete.")

    def _hill_climb_to_target(self, *,
                              get_value: Callable[[], float],
                              set_value: Callable[[float], None],
                              measure: Callable[[], float],
                              target: float,
                              tolerance: float,
                              step: float,
                              min_step: float,
                              max_steps: int,
                              settle: float,
                              label: str,
                              min_bound: float = None,  # type: ignore
                              max_bound: float = None,  # type: ignore
                              safety_check: Callable[[], None] = None,  # type: ignore
                              ) -> float:
        """Adjust a single settable value (via ``set_value``) to bring a measured
        quantity (via ``measure``) to ``target`` within ``tolerance``.

        Starts from ``get_value()`` and steps by ``step`` in one direction. If a
        step reduces the error, it keeps stepping the same direction; if it
        makes the error worse (or a bound is hit), it reverses direction and
        halves the step (stopping once ``step`` drops below ``min_step``). Also
        stops early once ``max_steps`` is exhausted. ``safety_check`` (if given)
        is called after every step and may raise to abort early (e.g. a heater
        current approaching its compliance limit).

        Returns the final value that was set (not necessarily within
        tolerance if the search couldn't get closer).
        """
        value = get_value()
        current = measure()
        error = target - current
        logger.info(f"[calib] {label}: start value={value:.6g}, "
                    f"measured={current:.3e}, target={target:.3e}, error={error:.3e}")
        if abs(error) <= tolerance:
            return value

        direction = 1.0
        for i in range(max_steps):
            new_value = value + direction * step
            if min_bound is not None:
                new_value = max(new_value, min_bound)
            if max_bound is not None:
                new_value = min(new_value, max_bound)
            hit_bound = new_value == value

            set_value(new_value)
            if settle > 0:
                time.sleep(settle)
            if safety_check is not None:
                safety_check()

            new_current = measure()
            new_error = target - new_current
            logger.info(f"[calib] {label} step {i}: value={new_value:.6g}, "
                        f"measured={new_current:.3e}, error={new_error:.3e}")
            if abs(new_error) <= tolerance:
                return new_value

            if hit_bound or abs(new_error) >= abs(error):
                direction = -direction
                step = step / 2.0
                if step < min_step:
                    logger.info(f"[calib] {label}: step size below minimum, stopping "
                                f"(final error={new_error:.3e})")
                    return new_value

            value, error = new_value, new_error

        logger.info(f"[calib] {label}: max steps reached (final error={error:.3e})")
        return value

    @staticmethod
    def _heater_safety_check(psu: "ATE.PSU", channel: int, compliance: float,
                             margin: float = 0.05) -> None:
        """Abort a heater's calibration step if its measured current is within
        ``margin`` of its configured current compliance (thermal runaway guard)."""
        measured = psu.get_output_current(channel)
        if measured >= compliance * (1 - margin):
            raise RuntimeError(f"heater ch{channel} current {measured:.4f}A near "
                               f"compliance {compliance:.4f}A; aborting")

    def _auto_calibrate_bias(self, psu: "ATE.PSU", scu1: "ATE.SCU", scu2: "ATE.SCU",
                             cfg: LIASnapConfig | LIAGasResponseConfig) -> None:
        """Closed-loop calibration of heater voltages and SCU bias voltages toward
        the target SCU drain currents in ``cfg.calibration``.

        Heater ch1 is paired with SCU2's current, heater ch3 with SCU1's
        current (cross-paired, confirmed against the physical setup — not
        matched by channel number). Runs a coarse heater hill-climb
        (alternating ch1/ch3 across up to ``max_rounds`` rounds, with a
        thermal settle between steps), then a fine SCU bias-voltage trim
        (near-instant settle, ``scu_voltage_step`` resolution). The resulting
        heater and SCU voltages are persisted back into ``self.ate_config``/
        ``cfg`` so later frequency points in the sweep keep this calibrated
        operating point.
        """
        cal = cfg.calibration
        ate = self.ate_config
        if ate.heater1 is None or ate.heater3 is None:
            logger.warning("Bias calibration enabled but heater1/heater3 are not "
                          "configured; skipping")
            return

        heater_specs = (
            (1, scu2, cal.target_current_scu2, ate.heater1,
             cal.heater1_min_voltage, cal.heater1_max_voltage, "heater1/SCU2"),
            (3, scu1, cal.target_current_scu1, ate.heater3,
             cal.heater3_min_voltage, cal.heater3_max_voltage, "heater3/SCU1"),
        )
        heater_voltages = {1: ate.heater1.voltage, 3: ate.heater3.voltage}

        for round_i in range(cal.max_rounds):
            for channel, scu, target, heater_cfg, min_v, max_v, label in heater_specs:
                heater_voltages[channel] = self._hill_climb_to_target(
                    get_value=lambda ch=channel: psu.get_programmed_voltage(ch),
                    set_value=lambda v, ch=channel: psu.set_voltage(ch, v),
                    measure=lambda s=scu: s.measure_current(channel=1),
                    target=target,
                    tolerance=cal.current_tolerance,
                    step=cal.heater_step_voltage,
                    min_step=cal.heater_min_step_voltage,
                    max_steps=cal.heater_max_steps,
                    settle=cal.heater_settle_time,
                    label=f"round {round_i + 1} {label}",
                    min_bound=min_v,
                    max_bound=max_v,
                    safety_check=lambda ch=channel, comp=heater_cfg.current: (
                        self._heater_safety_check(psu, ch, comp)),
                )

            i_scu1 = scu1.measure_current(channel=1)
            i_scu2 = scu2.measure_current(channel=1)
            if (abs(cal.target_current_scu1 - i_scu1) <= cal.current_tolerance and
                    abs(cal.target_current_scu2 - i_scu2) <= cal.current_tolerance):
                logger.info(f"[calib] converged after round {round_i + 1}")
                break
        else:
            logger.warning("[calib] heater search did not converge within max_rounds")

        scu_specs = (
            (scu1, cal.target_current_scu1, "SCU1"),
            (scu2, cal.target_current_scu2, "SCU2"),
        )
        scu_voltages = {}
        for scu, target, label in scu_specs:
            scu_voltages[label] = self._hill_climb_to_target(
                get_value=lambda s=scu: s.get_voltage(channel=1),
                set_value=lambda v, s=scu: s.set_voltage(v, channel=1),
                measure=lambda s=scu: s.measure_current(channel=1),
                target=target,
                tolerance=cal.final_current_tolerance,
                step=cal.scu_voltage_step,
                min_step=cal.scu_voltage_step,
                max_steps=cal.scu_max_steps,
                settle=cal.scu_settle_time,
                label=f"fine trim {label}",
            )

        new_heater1 = HeaterConfig(voltage=heater_voltages[1],
                                   current=ate.heater1.current)
        new_heater3 = HeaterConfig(voltage=heater_voltages[3],
                                   current=ate.heater3.current)
        self.ate_config = replace(ate, heater1=new_heater1, heater3=new_heater3)
        cfg.v_scu1 = scu_voltages["SCU1"]
        cfg.v_scu2 = scu_voltages["SCU2"]
        logger.info(f"[calib] calibration complete: heater1={heater_voltages[1]:.4f}V, "
                    f"heater3={heater_voltages[3]:.4f}V, "
                    f"v_scu1={scu_voltages['SCU1']:.6f}V, v_scu2={scu_voltages['SCU2']:.6f}V")

    def _snap_capture(self, csv_path: str, duration: float, sample_interval: float,
                      set_frequency: float = None, settle: float = 0.0,  # type: ignore
                      auto_phase: bool = False, autophase_settle: float = 0.0,
                      calibrate: bool = False) -> None:
        """Open the instruments without reset, capture a setup snapshot, then snap
        X/Y/R at fixed intervals into ``csv_path``.

        Never issues ``*RST``. If ``self.snap_config.configure_instruments`` is
        set, the LIA + SCU bias settings from ``self.snap_config`` are applied
        first (LIA, then both SCUs); otherwise the live configuration is left
        untouched, as if set up by hand beforehand. Either way, the LIA
        reference frequency (``set_frequency``) is optionally changed next. If
        ``calibrate`` is set, closed-loop bias auto-calibration
        (:meth:`_auto_calibrate_bias`) runs next, adjusting heater and SCU
        voltages toward the target currents in
        ``self.snap_config.calibration``. Then it waits ``settle`` seconds
        (e.g. thermal settling). If ``auto_phase`` is set, an LIA
        auto-phase is triggered after that, followed by a further
        ``autophase_settle`` wait, before capturing starts. The PSU is never
        reconfigured here except by calibration, so it otherwise keeps
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
            scu1 = self.open_no_reset(ATE.SCU('SCU1', rm=self.rm))
            opened.append(scu1)
            scu2 = self.open_no_reset(ATE.SCU('SCU2', rm=self.rm))
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
                if calibrate:
                    logger.info("Running bias auto-calibration")
                    self._auto_calibrate_bias(psu, scu1, scu2, self.snap_config)
                if settle > 0:
                    logger.info(f"Settling for {settle:g}s")
                    time.sleep(settle)
                if auto_phase:
                    logger.info("Auto-phasing LIA")
                    lia.auto_phase()
                    if autophase_settle > 0:
                        logger.info(f"Settling for {autophase_settle:g}s after auto-phase")
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

            with open(csv_path, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerows(self.snapshot.as_rows(width=4))
                writer.writerow(['time', 'X', 'Y', 'R'])
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
        logger.info(f"Starting LIA snap_only: duration={cfg.duration:g}s, "
                    f"dt={cfg.sample_interval:g}s → {self.data_file}")
        self._snap_capture(self.data_file, cfg.duration, cfg.sample_interval)
        logger.info("LIA snap_only complete.")

    def _shutdown_all_devices(self) -> None:
        """De-energize the whole setup once a run is done, so no output voltage
        remains. Order matters: SR860 (LIA) first — its DC offset and sine
        amplitude are explicitly zeroed, since ``*RST`` alone isn't guaranteed
        to — then both Keysight B2962A SCUs, then the HP6624A PSU last (this
        also drops ESD/fan/heater channels, so only call this once a run is
        fully finished).
        """
        logger.info("Shutting down setup: SR860 -> Keysight SCUs -> HP6624A PSU")

        with ATE.LIA(rm=self.rm) as lia:
            lia.set_amplitude(0)
            lia.set_offset(0)
            # __exit__ also issues *RST on close.

        with ATE.SCU('SCU1', rm=self.rm) as scu1:
            scu1.disable_output(channel=1)
            scu1.set_voltage(0, channel=1)

        with ATE.SCU('SCU2', rm=self.rm) as scu2:
            scu2.disable_output(channel=1)
            scu2.set_voltage(0, channel=1)

        with ATE.PSU(rm=self.rm) as psu:
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
        folder = cfg.sweep_folder or f'snap_sweep_{datetime.now().strftime("%Y%m%d_%H%M%S")}'
        out_dir = os.path.join(self.results_dir, folder)
        os.makedirs(out_dir, exist_ok=True)
        logger.info(f"Starting LIA snap sweep over {cfg.frequencies} Hz → {out_dir}")
        try:
            for i, f in enumerate(cfg.frequencies):
                csv_path = os.path.join(out_dir, f"{f:g}Hz.csv")
                logger.info(f"--- f={f:g} Hz → {csv_path} ---")
                is_first = i == 0
                try:
                    self._snap_capture(csv_path, cfg.duration, cfg.sample_interval,
                                       set_frequency=f,
                                       settle=cfg.first_settle if is_first else cfg.settle,
                                       auto_phase=is_first and cfg.first_auto_phase,
                                       autophase_settle=cfg.first_autophase_settle if is_first else 0.0,
                                       calibrate=is_first and cfg.calibration.enabled)
                except Exception:
                    logger.exception(f"Capture at f={f:g} Hz failed; skipping to next frequency")
        finally:
            self._shutdown_all_devices()
        logger.info("LIA snap sweep complete.")

    def noise_scan(self):
        logger.info("Starting LIAMeasurementSetup (noise scan)")
        frequencies = self.readout_config.frequencies
        logger.info(f"Scanning in range {frequencies}")
        result_paths = [os.path.join(self.results_dir, f"scan_noise_f{f}.csv") for f in frequencies]
        for f, fp in zip(frequencies, result_paths):
            tau, tc, enbw, settling_time, measurement_time, sample_interval = _lia_timing(f)
            logger.info(f"Measurement f={f} Hz: tau={tau:g}s ({tc.name}), ENBW={enbw:g} Hz, "
                        f"settling={settling_time:g}s, meas={measurement_time:g}s, dt={sample_interval:g}s")
            self._run_readout(lia_frequency=f, csv_path=fp, time_const=tc,
                              measurement_time=measurement_time, sample_interval=sample_interval,
                              settling_time=settling_time)
        logger.info("LIA measurement complete.")

        logger.info("Starting noise analysis")
        R_avg = []
        phase_avg = []
        X_std = []
        Y_std = []
        R_std = []

        logger.info("Loop over all result and calculate phase average and standard deviation.")
        for fp in result_paths:
            with open(fp, mode='r') as f:
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
        with open(summary_filename, mode='w', newline='') as fn:
            writer = csv.writer(fn)
            writer.writerow(["f_ref [Hz]", "R_avg [V]", "R_std [V]", "Phase_avg [deg]", "X_std [V]", "Y_std [V]"])
            for f, r_avg, r_std, p_avg, x_std, y_std in zip(frequencies, R_avg, R_std, phase_avg, X_std, Y_std):
                writer.writerow([f, r_avg, r_std, p_avg, x_std, y_std])

    def _capture_until_stop(self, lia: "ATE.LIA", csv_path: str, sample_interval: float,
                            stop_event: threading.Event,
                            extra_snapshot_rows: list[list] = None) -> None:  # type: ignore
        """Snap X/Y/R at fixed intervals into ``csv_path`` until ``stop_event`` is set.

        Unlike ``_run_readout``/``_snap_capture`` (which run a fixed number of
        cycles), this has no preset duration: it keeps sampling until the
        operator presses Enter (via :func:`_watch_for_enter`, whose thread
        sets ``stop_event``). ``stop_event.wait(sleep_for)`` is used instead of
        ``time.sleep`` so a press interrupts the wait immediately rather than
        at the next scheduled sample tick. The file is flushed after every row
        so no data is lost if the run is interrupted.
        """
        with open(csv_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerows(self.snapshot.as_rows(width=4))
            if extra_snapshot_rows:
                writer.writerows(
                    row + [""] * (4 - len(row)) for row in extra_snapshot_rows)
            writer.writerow(['time', 'X', 'Y', 'R'])
            start = time.time()
            i = 0
            while not stop_event.is_set():
                x, y, r = lia.snap(0, 1, 2)  # 0=X, 1=Y, 2=R
                elapsed = time.time() - start
                writer.writerow([elapsed, x, y, r])
                f.flush()
                i += 1
                next_t = start + i * sample_interval
                sleep_for = next_t - time.time()
                if sleep_for > 0:
                    stop_event.wait(sleep_for)
            print()

    def gas_response(self) -> None:
        """Manually-gated single-frequency baseline -> gas-insertion capture.

        Configures the LIA/SCU bias for a single reference frequency,
        optionally runs closed-loop bias auto-calibration, then gates on three
        Enter presses from the operator: setup settled (start baseline
        recording), gas inserted (end baseline, start gas recording), and stop
        recording. Sampling never pauses while waiting for the next press.
        Writes ``baseline.csv`` and ``gas.csv`` (snap-format, matching
        ``snap_only``/``snap_sweep``) into a session folder under
        ``self.results_dir``.
        """
        cfg = self.gas_response_config
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        stem = cfg.session_folder or f'gas_response_{timestamp}'
        out_dir = os.path.join(self.results_dir, stem)
        os.makedirs(out_dir, exist_ok=True)
        baseline_csv = os.path.join(out_dir, "baseline.csv")
        gas_csv = os.path.join(out_dir, "gas.csv")
        logger.info(f"Starting LIA gas_response @ {cfg.lia_frequency:g} Hz "
                    f"-> {out_dir}")

        try:
            with ATE.LIA(rm=self.rm) as lia, \
                    ATE.SCU('SCU1', rm=self.rm) as scu1, \
                    ATE.SCU('SCU2', rm=self.rm) as scu2:
                lia.reset()
                scu1.reset()
                scu2.reset()

                self._configure_lia_scu(lia, scu1, scu2, cfg)
                lia.set_frequency(cfg.lia_frequency)

                logger.info("Dummy read and let LIA settle")
                _, _, _ = lia.snap(0, 1, 2)  # 0=X, 1=Y, 2=R

                if cfg.auto_phase:
                    logger.info("Zero LIA phase")
                    lia.auto_phase()
                    if cfg.autophase_settle > 0:
                        logger.info(f"Settling for {cfg.autophase_settle:g}s "
                                    "after auto-phase")
                        time.sleep(cfg.autophase_settle)

                if cfg.calibration.enabled:
                    psu = self.open_no_reset(ATE.PSU(rm=self.rm))
                    try:
                        logger.info("Running bias auto-calibration")
                        self._auto_calibrate_bias(psu, scu1, scu2, cfg)
                    finally:
                        psu.resource.close()

                if cfg.settle > 0:
                    logger.info(f"Settling for {cfg.settle:g}s")
                    time.sleep(cfg.settle)

                self.snapshot.devices.clear()
                self.snapshot_lia(lia)
                self.snapshot_scu(scu1)
                self.snapshot_scu(scu2)
                logger.info(f"Setup snapshot:\n{self.snapshot}")

                input("Press Enter once the setup has settled to begin "
                      "baseline recording...")

                logger.info(f"Recording baseline -> {baseline_csv}")
                stop_baseline = _watch_for_enter(
                    "Press Enter the instant gas is inserted...")
                self._capture_until_stop(
                    lia, baseline_csv, cfg.sample_interval, stop_baseline)

                gas_time = datetime.now()
                logger.info(f"Gas inserted at {gas_time.isoformat()}")

                logger.info(f"Recording gas exposure -> {gas_csv}")
                stop_gas = _watch_for_enter("Press Enter to stop recording...")
                self._capture_until_stop(
                    lia, gas_csv, cfg.sample_interval, stop_gas,
                    extra_snapshot_rows=[
                        ["gas_insertion_time_iso", gas_time.isoformat()],
                        ["gas_insertion_time_unix", gas_time.timestamp()],
                    ])
        finally:
            self._shutdown_all_devices()
        logger.info("LIA gas_response complete.")

