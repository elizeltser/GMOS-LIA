"""
LIA Measurement setup
"""

import csv
import logging
import os
import statistics
import time

import numpy as np

import ATE

from .setup_base import SetupBase

logger = logging.getLogger(__name__)

_VALID_MODES = ("readout", "phase_zero")


class LIAMeasurementSetup(SetupBase):
    def __init__(self, output_name: str = None, mode: str = "readout") -> None:  # type: ignore
        super().__init__(output_name=output_name)
        if mode not in _VALID_MODES:
            raise ValueError(f"mode must be one of {_VALID_MODES}, got {mode!r}")
        self.mode = mode
        self.data_file = os.path.join(self.results_dir, f'{output_name}.csv')

    @SetupBase.setup_ate
    def run(self):
        if self.mode == "readout":
            self.lia_readout()
        elif self.mode == "phase_zero":
            self.phase_zero()

    def lia_readout(self):
        logger.info("Starting LIAMeasurementSetup (readout)")

        with ATE.LIA(rm=self.rm) as lia, ATE.SCU('SCU1', rm=self.rm) as scu1, ATE.SCU('SCU2', rm=self.rm) as scu2:
            lia.reset()
            scu1.reset()
            scu2.reset()

            # LIA signal configuration
            lia.set_offset(2.0)
            lia.set_amplitude(0.025)
            lia.set_frequency(35)

            # LIA filter and input settings
            lia.set_filter_slope(ATE.FilterSlope.DB18)
            lia.set_time_constant(ATE.TimeConstant.S1)
            lia.set_input_coupling(ATE.InputCoupling.DC)
            lia.set_input_source(ATE.InputSource.A_MINUS_B)

            # SCU1: voltage mode, 3V, 10µA compliance
            scu1.set_source_function(ATE.SourceFunction.VOLTAGE, 10e-6, channel=1)
            scu1.set_voltage(3.0, channel=1)
            scu1.enable_output(channel=1)

            # SCU2: voltage mode, 3V, 10µA compliance
            scu2.set_source_function(ATE.SourceFunction.VOLTAGE, 10e-6, channel=1)
            scu2.set_voltage(3.0, channel=1)
            scu2.enable_output(channel=1)

            # Allow signals to settle (several time constants)
            time.sleep(1.0)

            # Zero phase
            lia.auto_phase()

            # Continuous measurement: 5s at 10ms intervals → X and R
            logger.info(f"Measuring for 10s → {self.data_file}")
            with open(self.data_file, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['time', 'X', 'Y', 'Theta'])
                start = time.time()
                end = start + 10.0
                while time.time() < end:
                    x, y, theta = lia.snap(0, 1, 3)  # 0=X, 1=R 3=THeta
                    writer.writerow([time.time() - start, x, y, theta])
                    time.sleep(0.01)

            lia.reset()
            scu1.reset()
            scu2.reset()
            logger.info("LIA measurement complete.")

    def phase_zero(self):
        logger.info("Starting LIAMeasurementSetup (phase_zero)")

        v_start, v_stop, v_step = 2.75, 3.25, 0.010
        step_duration = 2.0
        sample_interval = 0.010
        compliance = 1e-3  # 1 mA

        voltages = np.arange(v_start, v_stop + 1e-9, v_step)
        n_steps = len(voltages) ** 2
        logger.info(f"Sweeping {n_steps} points, ETA ~{n_steps * step_duration / 60:.0f} min")

        with ATE.LIA(rm=self.rm) as lia, ATE.SCU('SCU1', rm=self.rm) as scu1, ATE.SCU('SCU2', rm=self.rm) as scu2:
            lia.reset()
            scu1.reset()
            scu2.reset()

            # LIA signal configuration (per phase_zero spec)
            lia.set_offset(2.0)
            lia.set_amplitude(0.010)
            lia.set_frequency(20)

            lia.set_filter_slope(ATE.FilterSlope.DB12)
            lia.set_time_constant(ATE.TimeConstant.S1)
            lia.set_input_coupling(ATE.InputCoupling.DC)
            lia.set_input_source(ATE.InputSource.A_MINUS_B)

            # SCUs: voltage mode, 1 mA compliance, start at v_start
            for scu in (scu1, scu2):
                scu.set_source_function(ATE.SourceFunction.VOLTAGE, compliance, channel=1)
                scu.set_measurement_function(ATE.MeasurementFunction.CURRENT, channel=1)
                scu.set_voltage(v_start, channel=1)
                scu.enable_output(channel=1)

            time.sleep(1.0)

            # Fix phase reference once so later drift across the sweep is meaningful.
            lia.auto_phase()

            logger.info(f"Logging samples → {self.data_file}")
            best = None  # (stdev, v1, v2)
            t0 = time.time()
            with open(self.data_file, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['time', 'v_scu1', 'v_scu2', 'i_scu1', 'i_scu2', 'theta'])

                for v1 in voltages:
                    scu1.set_voltage(float(v1), channel=1)
                    for v2 in voltages:
                        scu2.set_voltage(float(v2), channel=1)
                        time.sleep(0.05)  # settle

                        phases = []
                        step_end = time.time() + step_duration
                        while time.time() < step_end:
                            i1 = scu1.measure_current(channel=1)
                            i2 = scu2.measure_current(channel=1)
                            theta = lia.get_output(3)
                            writer.writerow([time.time() - t0, float(v1), float(v2), i1, i2, theta])
                            phases.append(theta)
                            time.sleep(sample_interval)

                        if len(phases) >= 2:
                            sigma = statistics.stdev(phases)
                            if best is None or sigma < best[0]:
                                best = (sigma, float(v1), float(v2))

            if best is not None:
                sigma, v1_best, v2_best = best
                logger.info(f"Least-erratic phase at SCU1={v1_best:.3f} V, SCU2={v2_best:.3f} V (stdev={sigma:.4g}°)")
                summary_path = self.data_file.replace('.csv', '.summary.txt')
                with open(summary_path, 'w') as sf:
                    sf.write(f"v_scu1_best={v1_best}\nv_scu2_best={v2_best}\nphase_stdev={sigma}\n")
                logger.info(f"Summary written to {summary_path}")

            lia.reset()
            scu1.reset()
            scu2.reset()
            logger.info("LIA phase_zero complete.")
