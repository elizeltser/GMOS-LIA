"""
Linear I-V Sweep setup.
"""

from typing import List

import numpy as np
import ATE

from . import SetupBase


class IVSweep(SetupBase):
    def __init__(self, scu_tag: str = 'SCU1', start: float = 0, stop: float = 5, step: float = 0.1, scale: str = 'linear', mode: str = 'voltage') -> None:
        super().__init__()
        self.scu_tag: str = scu_tag
        self.start: float = start
        self.stop: float = stop
        self.step: float = step
        self.mode: str = mode  # 'voltage' or 'current'
        self.scale: str = scale  # 'linear' or 'log'

    @SetupBase.setup_ate
    def run(self) -> None:
        if self.scale == 'linear':
            set_values: np.ndarray = np.arange(self.start, self.stop + self.step, self.step)
        elif self.scale == 'log':
            set_values: np.ndarray = np.logspace(np.log10(self.start), np.log10(self.stop), int((np.log10(self.stop) - np.log10(self.start)) / np.log10(1 + self.step / self.start)))
        else:
            raise ValueError("Invalid scale type. Use 'linear' or 'log'.")
        set_values: np.ndarray = np.arange(self.start, self.stop + self.step, self.step)
        voltages: List[float] = []
        currents: List[float] = []

        with ATE.SCU(self.scu_tag, rm=self.rm) as scu:
            scu.reset()
            scu.enable_output(1)
            scu.set_measurement_function(ATE.MeasurementFunction.CURRENT, 1)  # Measure current
            if self.mode == 'voltage':
                scu.set_source_mode(ATE.SourceMode.FIXED, 1)
                for v in set_values:
                    scu.set_voltage(v, 1)
                    # Wait and measure
                    measured_v: float = scu.get_voltage(1)
                    measured_i: float = float(scu.measure_spot().split(',')[1])  # Assuming format
                    voltages.append(measured_v)
                    currents.append(measured_i)
            # Similar for current mode

        data = {'set_voltage': set_values, 'measured_voltage': voltages, 'measured_current': currents}
        self.save_results(data, 'linear_iv_sweep')