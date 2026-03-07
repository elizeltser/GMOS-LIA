"""
Experiment setups for GMOS testing.
"""

import os
from functools import wraps
from datetime import datetime
from time import sleep
import csv
from typing import Dict, Any, List

import pyvisa
from .. import ATE

from .iv_sweep import IVSweep
from .signal_pulse_burst import SignalPulseBurst
from .noise_measurement import NoiseMeasurement

class SetupBase:
    """
    Base class for experiment setups.
    """

    def __init__(self, devices: Dict[str, Any] = None, params: Dict[str, Any] = None) -> None:  # type: ignore
        self.devices: Dict[str, Any] = devices or {}
        self.params: Dict[str, Any] = params or {}
        self.results_dir: str = os.path.join('Results', self.__class__.__name__)
        os.makedirs(self.results_dir, exist_ok=True)
        self.rm: pyvisa.ResourceManager = pyvisa.ResourceManager()

    @staticmethod
    def setup_ate(test_method):
        """Setup ATE devices: reset, enable ESD protection, etc."""
        @wraps(test_method)
        def wrapper(self, *args, **kwargs):
            # Enable PSU for ESD protection
            with ATE.PSU(tag="PSU", rm=self.rm) as psu:
                psu.reset()
                # Start ESD protection by setting safe voltages/currents
                psu.set_voltage(2, 5.0)
                psu.set_current(2, 0.7)
                psu.enable_output(2)
                # Start fan power supply
                psu.set_voltage(4, 7.0)
                psu.set_current(4, 1.5)
                psu.enable_output(4)
                while psu.opc() != '1':
                    sleep(0.1)  # Wait for PSU to be ready
                yield  # Run the test method
                # After test, disable outputs
                psu.disable_output(2)
                psu.disable_output(4)
            return test_method(self, *args, **kwargs)
        return wrapper

    @setup_ate
    def run(self) -> None:
        """Run the experiment"""
        raise NotImplementedError

    def save_results(self, data: Dict[str, List], filename: str) -> str:
        """Save results to CSV"""
        filepath: str = os.path.join(self.results_dir, f'{filename}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv')
        with open(filepath, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=data.keys())
            writer.writeheader()
            for row in zip(*data.values()):
                writer.writerow(dict(zip(data.keys(), row)))
        return filepath
    
__all__ = ['SignalPulseBurst', 'IVSweep', 'NoiseMeasurement']