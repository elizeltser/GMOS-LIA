"""
SetupBase: base class for all experiment setups.
"""

import csv
import logging
import os
from datetime import datetime
from functools import wraps
from time import sleep
from typing import Dict, Any, List

import pyvisa
import ATE

logger = logging.getLogger(__name__)


class SetupBase:
    """
    Base class for experiment setups.
    """

    def __init__(self, devices: Dict[str, Any] = None, params: Dict[str, Any] = None, output_name: str = None) -> None:  # type: ignore
        self.devices: Dict[str, Any] = devices or {}
        self.params: Dict[str, Any] = params or {}
        self.output_name: str | None = output_name
        self.results_dir: str = os.path.join('Results', self.__class__.__name__)
        os.makedirs(self.results_dir, exist_ok=True)
        self.rm: pyvisa.ResourceManager = pyvisa.ResourceManager()

    @staticmethod
    def setup_ate(test_method):
        """Setup ATE devices: reset, enable ESD protection, etc."""
        @wraps(test_method)
        def wrapper(self, *args, **kwargs):
            logger.info("Setting up ESD protection (PSU ch2) and fan (PSU ch4)")
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
                while psu.opc() != '\n':
                    sleep(0.1)  # Wait for PSU to be ready
                logger.info("PSU ready. Running experiment.")
                result = test_method(self, *args, **kwargs)
                # After test, disable outputs
                logger.info("Experiment complete. Disabling PSU outputs.")
                psu.reset()
                #psu.disable_output(2)
                #psu.disable_output(4)
            return result
        return wrapper

    @setup_ate
    def run(self) -> None:
        """Run the experiment"""
        raise NotImplementedError

    def save_results(self, data: Dict[str, List], filename: str) -> str:
        """Save results to CSV"""
        stem = self.output_name if self.output_name else f'{filename}_{datetime.now().strftime("%Y%m%d_%H%M%S")}'
        filepath: str = os.path.join(self.results_dir, f'{stem}.csv')
        with open(filepath, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=data.keys())
            writer.writeheader()
            for row in zip(*data.values()):
                writer.writerow(dict(zip(data.keys(), row)))
        logger.info(f"Results saved to {filepath}")
        return filepath
