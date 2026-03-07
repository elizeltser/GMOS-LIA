"""
Signal Generated Pulse Burst setup.
"""
from typing import List

import time

import numpy as np
import ATE

from . import SetupBase


class SignalPulseBurst(SetupBase):
    def __init__(self, lia_freq=1000, lia_amp=1e-3, lia_offset=0, sg_width=1e-3, sg_amp=5, bias_current=1e-6) -> None:
        super().__init__()
        self.lia_freq = lia_freq
        self.lia_amp = lia_amp
        self.lia_offset = lia_offset
        self.sg_width = sg_width
        self.sg_amp = sg_amp
        self.bias_current = bias_current

    @SetupBase.setup_ate
    def run(self):
        frequencies = np.logspace(2, 5, 50)  # Example sweep
        x_data: List[float] = []
        y_data: List[float] = []

        with ATE.LIA(rm=self.rm) as lia, ATE.SCU('SCU1', rm=self.rm) as scu, ATE.SG(rm=self.rm) as sg:
            lia.reset()
            scu.reset()
            sg.reset()

            # Setup LIA
            lia.set_frequency(self.lia_freq)
            lia.set_amplitude(self.lia_amp)
            lia.set_offset(self.lia_offset)
            lia.set_sensitivity(ATE.Sensitivity.UV500)  # Example

            # Setup SCU for bias
            scu.set_current(self.bias_current, 1)
            scu.enable_output(1)

            # Setup SG for pulse
            sg.set_pulse_width(self.sg_width * 1e9, 'NS')  # Convert to ns
            sg.set_amplitude(self.sg_amp)

            for freq in frequencies:
                lia.set_frequency(freq)
                time.sleep(1)  # Wait for settling
                x, y = lia.snap(0, 1)  # X and Y
                x_data.append(x)
                y_data.append(y)

        data = {'frequency': frequencies, 'X': x_data, 'Y': y_data}
        self.save_results(data, 'signal_pulse_burst')