"""
Operating-point sweep setup.
"""

import csv
import logging
import os
import time
from datetime import datetime

import ATE
from config import HEATER_CHANNEL_FOR_SCU, ATEConfig, OperatingPointSweepConfig
from plotting import OperatingPointIVCompiler

from .lia_setup import LIAMeasurementSetup
from .setup_base import SetupBase

logger = logging.getLogger(__name__)


class OperatingPointSweep(SetupBase):
    """Locate the GMOS's optimal DC operating point.

    For every heater voltage (PSU ch1/ch3) x LIA offset combination, SCU1 and
    SCU2 are each swept independently through a log-scale voltage list (the
    other channel held at its own configured baseline voltage), measuring
    current at each step. Produces one "offsets overlaid" IV plot per heater
    voltage per channel, plus one "heater voltages overlaid" IV plot per
    channel at a single configured LIA offset.
    """

    def __init__(self, output_name: str = None, ate_config: ATEConfig = None,  # type: ignore
                 config: OperatingPointSweepConfig = None) -> None:  # type: ignore
        super().__init__(output_name=output_name, ate_config=ate_config)
        self.config: OperatingPointSweepConfig = config or OperatingPointSweepConfig()

    def _sweep_scu(self, scu: "ATE.SCU", csv_path: str) -> list[dict]:
        """Step ``scu`` through ``cfg.scu_voltages``, measuring current at
        each step after ``cfg.point_settle``. Returns the measured points
        (without the heater/offset/channel context, added by the caller).
        """
        cfg = self.config
        points: list[dict] = []
        with open(csv_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['set_voltage', 'measured_voltage', 'measured_current'])
            for v in cfg.scu_voltages:
                scu.set_voltage(v, channel=1)
                if cfg.point_settle > 0:
                    time.sleep(cfg.point_settle)
                measured_v = scu.get_voltage(channel=1)
                measured_i = scu.measure_current(channel=1)
                writer.writerow([v, measured_v, measured_i])
                points.append({'set_voltage': measured_v,
                               'measured_current': measured_i})
        return points

    @SetupBase.setup_ate
    def run(self) -> None:
        cfg = self.config
        if not cfg.heater_voltages:
            raise ValueError("OperatingPointSweep requires at least one heater voltage")
        if not cfg.lia_offsets:
            raise ValueError("OperatingPointSweep requires at least one lia offset")
        if not cfg.scu_voltages:
            raise ValueError("OperatingPointSweep requires at least one scu voltage")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        stem = cfg.session_folder or f'operating_point_sweep_{timestamp}'
        out_dir = os.path.join(self.results_dir, stem)
        os.makedirs(out_dir, exist_ok=True)
        logger.info(f"Starting OperatingPointSweep -> {out_dir}")

        rows: list[dict] = []
        try:
            with ATE.LIA(rm=self.rm) as lia, \
                    ATE.SCU('SCU1', rm=self.rm) as scu1, \
                    ATE.SCU('SCU2', rm=self.rm) as scu2:
                lia.reset()
                scu1.reset()
                scu2.reset()

                LIAMeasurementSetup._configure_lia_scu(lia, scu1, scu2, cfg)

                for heater_voltage in cfg.heater_voltages:
                    logger.info(f"--- Heater ch1/ch3 = {heater_voltage:g}V ---")
                    psu = self.open_no_reset(ATE.PSU(rm=self.rm))
                    try:
                        for heater_ch in HEATER_CHANNEL_FOR_SCU.values():
                            psu.set_voltage(heater_ch, heater_voltage)
                    finally:
                        psu.resource.close()
                    logger.info(f"Settling for {cfg.heater_settle:g}s")
                    time.sleep(cfg.heater_settle)

                    heater_dir = os.path.join(out_dir, f"{heater_voltage:g}V")
                    os.makedirs(heater_dir, exist_ok=True)

                    for offset in cfg.lia_offsets:
                        logger.info(f"--- offset={offset:g}V ---")
                        lia.set_offset(offset)
                        logger.info(f"Settling for {cfg.offset_settle:g}s")
                        time.sleep(cfg.offset_settle)

                        offset_dir = os.path.join(heater_dir, f"{offset:g}offset")
                        os.makedirs(offset_dir, exist_ok=True)

                        # Reset both SCUs to their baselines before sweeping either.
                        scu1.set_voltage(cfg.v_scu1, channel=1)
                        scu2.set_voltage(cfg.v_scu2, channel=1)

                        logger.info("Sweeping SCU1 (SCU2 held at baseline)")
                        scu1_points = self._sweep_scu(
                            scu1, os.path.join(offset_dir, "SCU1.csv"))
                        for p in scu1_points:
                            rows.append({'heater_voltage': heater_voltage,
                                        'lia_offset': offset, 'channel': 'SCU1', **p})

                        # Reset SCU1 to baseline before sweeping SCU2.
                        scu1.set_voltage(cfg.v_scu1, channel=1)

                        logger.info("Sweeping SCU2 (SCU1 held at baseline)")
                        scu2_points = self._sweep_scu(
                            scu2, os.path.join(offset_dir, "SCU2.csv"))
                        for p in scu2_points:
                            rows.append({'heater_voltage': heater_voltage,
                                        'lia_offset': offset, 'channel': 'SCU2', **p})

                        scu2.set_voltage(cfg.v_scu2, channel=1)

            anchor_csv = os.path.join(out_dir, "operating_point_sweep.csv")
            compiler = OperatingPointIVCompiler(rows, anchor_csv=anchor_csv)
            for path in compiler.compile_offset_overlays():
                logger.info(f"Plot saved to: {path}")
            for path in compiler.compile_heater_overlay(cfg.plot_offset_value):
                logger.info(f"Plot saved to: {path}")
        finally:
            LIAMeasurementSetup._shutdown_all_devices(self.rm)
        logger.info("OperatingPointSweep complete.")
