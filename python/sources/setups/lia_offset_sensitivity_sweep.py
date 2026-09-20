"""
LIA offset sensitivity sweep setup.
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
    LIAOffsetSensitivitySweepConfig,
)

from .lia_setup import LIAMeasurementSetup
from .setup_base import SetupBase

logger = logging.getLogger(__name__)

# (channel_name, psu heater channel)
_CHANNELS = (
    ("active", HEATER_CHANNEL_FOR_SCU["SCU1"]),
    ("blind", HEATER_CHANNEL_FOR_SCU["SCU2"]),
)


def _measure_current_avg(scu: "ATE.SCU", channel: int, n: int) -> tuple[float, float]:
    """Take ``n`` repeated ``measure_current()`` spot reads on ``scu``/``channel``
    and return ``(mean, mse)`` where ``mse`` is the mean squared error (variance)
    of the samples around their mean.
    """
    samples = [scu.measure_current(channel=channel) for _ in range(n)]
    mean = sum(samples) / len(samples)
    mse = sum((x - mean) ** 2 for x in samples) / len(samples)
    return mean, mse


class LIAOffsetSensitivitySweep(SetupBase):
    """Measure GMOS current sensitivity to a small heater-voltage (gate
    temperature) perturbation, at each point of a heater-voltage x SCU-bias
    x LIA-offset sweep, for the active and blind devices simultaneously
    (SCU/PSU-channel pairing: ``config.HEATER_CHANNEL_FOR_SCU``). LIA
    amplitude/frequency are fixed for the whole run; only the LIA DC
    reference offset is swept alongside the two bias/heater axes. Results
    are written to separate CSVs per channel.
    """

    def __init__(self, output_name: str = None, ate_config: ATEConfig = None,  # type: ignore
                 config: LIAOffsetSensitivitySweepConfig = None) -> None:  # type: ignore
        super().__init__(output_name=output_name, ate_config=ate_config)
        cfg = config or LIAOffsetSensitivitySweepConfig()
        self.config: LIAOffsetSensitivitySweepConfig = cfg

    def _measure_channel(self, scu: "ATE.SCU", heater_channel: int,
                          psu_voltage: float, scu_bias: float, offset: float,
                          writer) -> None:
        """Baseline-measure, bump this channel's own PSU heater voltage by
        ``psu_step``, settle, perturbed-measure, then restore the heater
        voltage to ``psu_voltage`` and settle again. Writes one CSV row for
        this point."""
        cfg = self.config

        baseline_mean, baseline_mse = _measure_current_avg(
            scu, channel=1, n=cfg.n_measurements)

        psu = self.open_no_reset(ATE.PSU(rm=self.rm))
        try:
            psu.set_voltage(heater_channel, psu_voltage + cfg.psu_step)
        finally:
            psu.resource.close()
        if cfg.step_settle > 0:
            time.sleep(cfg.step_settle)

        perturbed_mean, perturbed_mse = _measure_current_avg(
            scu, channel=1, n=cfg.n_measurements)

        psu = self.open_no_reset(ATE.PSU(rm=self.rm))
        try:
            psu.set_voltage(heater_channel, psu_voltage)
        finally:
            psu.resource.close()
        if cfg.step_settle > 0:
            time.sleep(cfg.step_settle)

        sensitivity = (perturbed_mean - baseline_mean) / cfg.psu_step
        writer.writerow([psu_voltage, scu_bias, offset,
                          baseline_mean, baseline_mse,
                          perturbed_mean, perturbed_mse,
                          cfg.psu_step, sensitivity])

    @SetupBase.setup_ate
    def run(self) -> None:
        cfg = self.config
        if not cfg.psu_voltages:
            raise ValueError(
                "LIAOffsetSensitivitySweep needs at least one psu voltage")
        if not cfg.scu_bias_voltages:
            raise ValueError(
                "LIAOffsetSensitivitySweep needs at least one scu bias voltage")
        if not cfg.lia_offsets:
            raise ValueError(
                "LIAOffsetSensitivitySweep needs at least one lia offset")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        stem = cfg.session_folder or f'lia_offset_sensitivity_sweep_{timestamp}'
        out_dir = os.path.join(self.results_dir, stem)
        os.makedirs(out_dir, exist_ok=True)
        logger.info(f"Starting LIAOffsetSensitivitySweep -> {out_dir}")

        header = ['psu_voltage', 'scu_bias_voltage', 'lia_offset',
                   'baseline_current', 'baseline_mse',
                   'perturbed_current', 'perturbed_mse',
                   'psu_step', 'sensitivity_A_per_V']

        try:
            with ATE.LIA(rm=self.rm) as lia, \
                    ATE.SCU('SCU1', rm=self.rm) as scu1, \
                    ATE.SCU('SCU2', rm=self.rm) as scu2:
                lia.reset()
                scu1.reset()
                scu2.reset()

                LIAMeasurementSetup._configure_lia_scu(lia, scu1, scu2, cfg)
                lia.set_frequency(cfg.lia_frequency)

                if cfg.initial_settle > 0:
                    logger.info(f"Initial settle for {cfg.initial_settle:g}s")
                    time.sleep(cfg.initial_settle)

                scus = {'active': scu1, 'blind': scu2}

                files = {
                    name: open(os.path.join(out_dir, f"{name}.csv"), 'w', newline='')
                    for name, _ in _CHANNELS
                }
                writers = {name: csv.writer(f) for name, f in files.items()}
                try:
                    for writer in writers.values():
                        writer.writerow(header)

                    for psu_voltage in cfg.psu_voltages:
                        logger.info(f"--- Heater ch1/ch3 = {psu_voltage:g}V ---")
                        psu = self.open_no_reset(ATE.PSU(rm=self.rm))
                        try:
                            for heater_ch in HEATER_CHANNEL_FOR_SCU.values():
                                psu.set_voltage(heater_ch, psu_voltage)
                        finally:
                            psu.resource.close()
                        logger.info(f"Settling for {cfg.heater_settle:g}s")
                        time.sleep(cfg.heater_settle)

                        for scu_bias in cfg.scu_bias_voltages:
                            logger.info(f"--- SCU bias = {scu_bias:g}V ---")
                            scu1.set_voltage(scu_bias, channel=1)
                            scu2.set_voltage(scu_bias, channel=1)
                            logger.info(f"Settling for {cfg.bias_settle:g}s")
                            time.sleep(cfg.bias_settle)

                            for offset in cfg.lia_offsets:
                                logger.info(f"--- offset={offset:g}V ---")
                                lia.set_offset(offset)
                                logger.info(f"Settling for {cfg.offset_settle:g}s")
                                time.sleep(cfg.offset_settle)

                                for name, heater_channel in _CHANNELS:
                                    self._measure_channel(
                                        scus[name], heater_channel,
                                        psu_voltage, scu_bias, offset,
                                        writers[name])
                finally:
                    for f in files.values():
                        f.close()
        finally:
            LIAMeasurementSetup._shutdown_all_devices(self.rm)
        logger.info("LIAOffsetSensitivitySweep complete.")
