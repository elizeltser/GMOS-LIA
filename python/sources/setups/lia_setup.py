"""
LIA Measurement setup
"""

import csv
import logging
import os
import time
from datetime import datetime

import ATE
import numpy as np
import pdb

from .setup_base import SetupBase

logger = logging.getLogger(__name__)

_VALID_MODES = ("readout", "scan_noise", "snap_only")

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
    """For 0.1 Hz <= f_ref <= 40 Hz, derive LIA timing parameters from tau = 1.5/f.

    Returns (tau_rounded, tc_enum, enbw, settling_time, measurement_time, sample_interval).
    """
    if not (0.1 <= f_ref <= 40.0):
        raise ValueError(f"f_ref={f_ref} Hz outside supported range [0.1, 40] Hz")
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


class LIAMeasurementSetup(SetupBase):
    def __init__(self, output_name: str = None, mode: str = "readout",  # type: ignore
                 duration: float = 60.0, sample_interval: float = 1.0) -> None:
        super().__init__(output_name=output_name)
        if mode not in _VALID_MODES:
            raise ValueError(f"mode must be one of {_VALID_MODES}, got {mode!r}")
        self.mode = mode
        stem = output_name if output_name else f'{mode}_{datetime.now().strftime("%Y%m%d_%H%M%S")}'
        self.data_file = os.path.join(self.results_dir, f'{stem}.csv')
#        self.f_lst = [round(n, 3) for n in np.logspace(start=np.log10(0.1), stop=np.log10(40), num=5)]
        self.f_lst = [round(np.log(8.944), 3)]
        # snap_only mode parameters
        self.duration: float = duration
        self.sample_interval: float = sample_interval

    @SetupBase.setup_ate
    def run(self):
        if self.mode == "readout":
            self.lia_readout()
        if self.mode == "scan_noise":
            self.noise_scan()
        if self.mode == "snap_only":
            self.snap_only()

    def _run_readout(self, lia_frequency: float, csv_path: str, time_const: ATE.TimeConstant,
                     measurement_time: float, sample_interval: float,
                     settling_time: float = 250.0) -> None:

        v_scu1 = 1.11
        v_scu2 = 1.09
        n_cycles = max(1, int(measurement_time / sample_interval))

        with ATE.LIA(rm=self.rm) as lia, ATE.SCU('SCU1', rm=self.rm) as scu1, ATE.SCU('SCU2', rm=self.rm) as scu2:
            lia.reset()
            scu1.reset()
            scu2.reset()

            # LIA signal configuration
            lia.set_offset(2.5)
            lia.set_amplitude(10e-3)
            lia.set_frequency(lia_frequency)
            lia.set_sensitivity(ATE.Sensitivity.UV100)

            # LIA filter and input settings
            lia.set_filter_slope(ATE.FilterSlope.DB24)
            lia.set_time_constant(time_const)
            lia.set_input_coupling(ATE.InputCoupling.DC)
            lia.set_input_source(ATE.InputSource.A)

            # SCU1: voltage mode, 10µA compliance
            scu1.set_source_function(ATE.SourceFunction.VOLTAGE, 10e-6, channel=1)
            scu1.set_voltage(v_scu1, channel=1)
            scu1.enable_output(channel=1)

            # SCU2: voltage mode, 10µA compliance
            scu2.set_source_function(ATE.SourceFunction.VOLTAGE, 10e-6, channel=1)
            scu2.set_voltage(v_scu2, channel=1)
            scu2.enable_output(channel=1)

            logger.info("Dummy read and let LIA settle")
            _, _, _ = lia.snap(0, 1, 3)  # 0=X, 1=Y, 3=Theta

            logger.info("Zero LIA phase")
            lia.auto_phase()

            logger.info(f"Letting signals to settle ({settling_time:g}s)")
            time.sleep(settling_time)
            pdb.set_trace()

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

    def lia_readout(self, lia_frequency: float = 1.0):
        logger.info("Starting LIAMeasurementSetup (readout)")
        tau, tc, enbw, settling_time, measurement_time, sample_interval = _lia_timing(lia_frequency)
        logger.info(f"f_ref={lia_frequency} Hz: tau={tau:g}s ({tc.name}), ENBW={enbw:g} Hz, "
                    f"settling={settling_time:g}s, meas={measurement_time:g}s, dt={sample_interval:g}s")
        self._run_readout(lia_frequency, csv_path=self.data_file, time_const=tc,
                          measurement_time=measurement_time, sample_interval=sample_interval,
                          settling_time=settling_time)
        logger.info("LIA measurement complete.")

    def snap_only(self):
        """Snap X, Y, R, Theta from the SR860 at fixed intervals for a given duration.

        Does not reset or reconfigure any instrument — assumes the LIA is already set up.
        """
        duration = self.duration
        sample_interval = self.sample_interval
        logger.info(f"Starting LIA snap_only: duration={duration:g}s, dt={sample_interval:g}s → {self.data_file}")
        n_cycles = max(1, int(duration / sample_interval))

        # Bypass the context manager: ATEBase.__exit__ calls reset() (*RST).
        # We open the VISA resource manually and close it without resetting,
        # so the LIA's current configuration is preserved.
        lia = ATE.LIA(rm=self.rm)
        lia.resource = self.rm.open_resource(lia.address)  # pyright: ignore[reportAttributeAccessIssue]
        lia.resource.timeout = 5000
        try:
            # *IDN? puts the SR860 into remote mode without altering its configuration.
            idn = lia.idn().strip()
            logger.info(f"LIA IDN: {idn}")
            with open(self.data_file, 'w', newline='') as f:
                writer = csv.writer(f)
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
        logger.info("LIA snap_only complete.")

    def noise_scan(self):
        logger.info("Starting LIAMeasurementSetup (noise scan)")
        logger.info(f"Scanning in range {self.f_lst}")
        result_paths = [os.path.join(self.results_dir, f"scan_noise_f{f}.csv") for f in self.f_lst]
        for f, fp in zip(self.f_lst, result_paths):
            tau, tc, enbw, settling_time, measurement_time, sample_interval = _lia_timing(f)
            logger.info(f"Measurement f={f} Hz: tau={tau:g}s ({tc.name}), ENBW={enbw:g} Hz, "
                        f"settling={settling_time:g}s, meas={measurement_time:g}s, dt={sample_interval:g}s")
            self._run_readout(lia_frequency=f, csv_path=fp, time_const=tc,
                              measurement_time=measurement_time, sample_interval=sample_interval,
                              settling_time=settling_time)
        logger.info("LIA measurement complete.")

        logger.info("Starting noise analysis")
        phase_avg = []
        X_std = []
        Y_std = []

        logger.info("Loop over all result and calculate phase average and standard deviation.")
        for fp in result_paths:
            with open(fp, mode='r') as f:
                reader = csv.DictReader(f)
                theta_vals, x_vals, y_vals = [], [], []
                for row in reader:
                    theta_vals.append(float(row["Theta"]))
                    x_vals.append(float(row["X"]))
                    y_vals.append(float(row["Y"]))
                phase_avg.append(np.average(theta_vals))
                X_std.append(np.std(x_vals))
                Y_std.append(np.std(y_vals))

        logger.info("Store results")
        summary_filename = os.path.join(self.results_dir, "std_phase.csv")
        with open(summary_filename, mode='w', newline='') as fn:
            writer = csv.writer(fn)
            writer.writerow(["f_ref [Hz]", "Phase_avg [deg]", "X_std [V^2]", "Y_std [V^2]"])
            for f, p_avg, x_std, y_std in zip(self.f_lst, phase_avg, X_std, Y_std):
                writer.writerow([f, p_avg, x_std, y_std])

