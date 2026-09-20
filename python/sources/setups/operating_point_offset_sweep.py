"""
Operating-point offset sweep setup.
"""

import csv
import logging
import os
import time
from datetime import datetime

import ATE
from config import (
    HEATER_CHANNEL_FOR_SCU,
    ATEConfig,
    OperatingPointOffsetSweepConfig,
)
from plotting import OperatingPointOffsetCompiler

from .lia_setup import LIAMeasurementSetup
from .setup_base import SetupBase

logger = logging.getLogger(__name__)


class OperatingPointOffsetSweep(SetupBase):
    """Locate the GMOS's optimal LIA DC reference offset at a fixed SCU bias.

    SCU1/SCU2 are held at their configured baseline voltages (v_scu1/v_scu2)
    for the whole sweep -- unlike OperatingPointSweep, which sweeps a list of
    SCU voltages, this measures current at a single fixed SCU bias for every
    heater voltage (PSU ch1/ch3) x LIA offset combination. Produces one plot
    per channel of measured current vs LIA offset, overlaying every heater
    voltage.
    """

    def __init__(self, output_name: str = None, ate_config: ATEConfig = None,  # type: ignore
                 config: OperatingPointOffsetSweepConfig = None) -> None:  # type: ignore
        super().__init__(output_name=output_name, ate_config=ate_config)
        cfg = config or OperatingPointOffsetSweepConfig()
        self.config: OperatingPointOffsetSweepConfig = cfg

    def _measure_point(self, scu1: "ATE.SCU", scu2: "ATE.SCU",
                        writer, heater_voltage: float,
                        offset: float) -> list[dict]:
        """Set both SCUs to their configured baseline and measure current on
        each, writing a CSV row per channel. Returns the measured points
        (without heater/offset context, added by the caller)."""
        cfg = self.config
        scu1.set_voltage(cfg.v_scu1, channel=1)
        scu2.set_voltage(cfg.v_scu2, channel=1)
        if cfg.point_settle > 0:
            time.sleep(cfg.point_settle)

        points: list[dict] = []
        for name, scu, set_v in (('SCU1', scu1, cfg.v_scu1),
                                  ('SCU2', scu2, cfg.v_scu2)):
            measured_v = scu.get_voltage(channel=1)
            measured_i = scu.measure_current(channel=1)
            writer.writerow([heater_voltage, offset, name, set_v,
                             measured_v, measured_i])
            points.append({'channel': name, 'measured_current': measured_i})
        return points

    @SetupBase.setup_ate
    def run(self) -> None:
        cfg = self.config
        if not cfg.heater_voltages:
            raise ValueError(
                "OperatingPointOffsetSweep needs at least one heater voltage")
        if not cfg.lia_offsets:
            raise ValueError(
                "OperatingPointOffsetSweep needs at least one lia offset")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        stem = cfg.session_folder or f'operating_point_offset_sweep_{timestamp}'
        out_dir = os.path.join(self.results_dir, stem)
        os.makedirs(out_dir, exist_ok=True)
        logger.info(f"Starting OperatingPointOffsetSweep -> {out_dir}")

        rows: list[dict] = []
        anchor_csv = os.path.join(out_dir, "operating_point_offset_sweep.csv")
        try:
            with ATE.LIA(rm=self.rm) as lia, \
                    ATE.SCU('SCU1', rm=self.rm) as scu1, \
                    ATE.SCU('SCU2', rm=self.rm) as scu2:
                lia.reset()
                scu1.reset()
                scu2.reset()

                LIAMeasurementSetup._configure_lia_scu(lia, scu1, scu2, cfg)

                with open(anchor_csv, 'w', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow(['heater_voltage', 'lia_offset', 'channel',
                                     'set_voltage', 'measured_voltage',
                                     'measured_current'])

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

                        for offset in cfg.lia_offsets:
                            logger.info(f"--- offset={offset:g}V ---")
                            lia.set_offset(offset)
                            logger.info(f"Settling for {cfg.offset_settle:g}s")
                            time.sleep(cfg.offset_settle)

                            points = self._measure_point(scu1, scu2, writer,
                                                          heater_voltage, offset)
                            for p in points:
                                rows.append({'heater_voltage': heater_voltage,
                                            'lia_offset': offset, **p})

            compiler = OperatingPointOffsetCompiler(rows, anchor_csv=anchor_csv)
            for path in compiler.compile():
                logger.info(f"Plot saved to: {path}")
        finally:
            LIAMeasurementSetup._shutdown_all_devices(self.rm)
        logger.info("OperatingPointOffsetSweep complete.")
