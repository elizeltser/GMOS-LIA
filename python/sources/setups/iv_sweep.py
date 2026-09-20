"""
Linear I-V Sweep setup.
"""

import logging
from typing import List

import numpy as np
import ATE
from config import ATEConfig, IVSweepConfig

from .setup_base import SetupBase

logger = logging.getLogger(__name__)


class IVSweep(SetupBase):
    def __init__(
        self,
        output_name: str = None,  # type: ignore
        ate_config: ATEConfig = None,  # type: ignore
        config: IVSweepConfig = None,  # type: ignore
    ) -> None:
        super().__init__(output_name=output_name, ate_config=ate_config)
        cfg = config or IVSweepConfig()
        self.scu_tag: str = cfg.scu_tag
        self.start: float = cfg.start
        self.stop: float = cfg.stop
        self.step: float = cfg.step
        self.mode: str = cfg.mode  # 'voltage' or 'current'
        self.scale: str = cfg.scale  # 'linear' or 'log'
        self.compliance: float = cfg.compliance

    @SetupBase.setup_ate
    def run(self) -> None:
        logger.info(
            f"Starting IVSweep (scale={self.scale}, mode={self.mode}, "
            f"{self.start}→{self.stop} step={self.step})"
        )
        if self.scale == "linear":
            set_values: np.ndarray = np.arange(
                self.start, self.stop + self.step, self.step
            )
        elif self.scale == "log":
            # step is the relative per-point fraction: V_{n+1} = V_n * (1 + step)
            n = (
                int(
                    (np.log10(self.stop) - np.log10(self.start))
                    / np.log10(1 + self.step)
                )
                + 1
            )
            set_values = np.logspace(np.log10(self.start), np.log10(self.stop), n)
        else:
            raise ValueError("Invalid scale type. Use 'linear' or 'log'.")
        voltages: List[float] = []
        currents: List[float] = []

        with ATE.SCU(self.scu_tag, rm=self.rm) as scu:
            scu.reset()
            scu.enable_output(1)
            scu.set_measurement_function(
                ATE.MeasurementFunction.CURRENT, 1
            )  # Measure current
            if self.mode == "voltage":
                scu.set_source_function(ATE.SourceFunction.VOLTAGE, self.compliance, 1)
            elif self.mode == "current":
                scu.set_source_function(ATE.SourceFunction.CURRENT, self.compliance, 1)
            if self.mode == "voltage":
                for v in set_values:
                    scu.set_voltage(v, 1)
                    # Wait and measure
                    measured_v: float = scu.get_voltage(1)
                    measured_i: float = float(
                        scu.measure_spot().split(",")[1]
                    )  # Assuming format
                    voltages.append(measured_v)
                    currents.append(measured_i)

        logger.info(f"Sweep complete. {len(voltages)} points measured.")
        data = {
            "set_voltage": set_values,
            "measured_voltage": voltages,
            "measured_current": currents,
        }
        self.save_results(data, "linear_iv_sweep")
