"""
Keysight B2962A Source Measure Unit wrapper.
"""

from enum import Enum
from typing import List

from . import ATEBase


class SourceMode(Enum):
    FIXED = 'FIX'
    LIST = 'LIST'
    SWEEP = 'SWE'

class MeasurementFunction(Enum):
    VOLTAGE = 'VOLT'
    CURRENT = 'CURR'
    RESISTANCE = 'RES'

class B2962A(ATEBase):
    def __init__(self, tag: str = 'SCU1', rm=None) -> None:
        super().__init__(tag, rm)
        self.channels: List[int] = [1, 2]  # B2962A has 2 channels

    def set_voltage(self, voltage: float, channel: int = 1) -> None:
        """Set DC voltage level for channel"""
        self.write(f':SOUR{channel}:VOLT:LEV {voltage}')

    def get_voltage(self, channel: int = 1) -> float:
        """Get DC voltage level"""
        return float(self.query(f':SOUR{channel}:VOLT:LEV?'))

    def set_current(self, current: float, channel: int = 1) -> None:
        """Set DC current level for channel"""
        self.write(f':SOUR{channel}:CURR:LEV {current}')

    def get_current(self, channel: int = 1) -> float:
        """Get DC current level"""
        return float(self.query(f':SOUR{channel}:CURR:LEV?'))

    def set_source_mode(self, mode: SourceMode, channel: int = 1) -> None:
        """Set source mode"""
        if mode == SourceMode.FIXED:
            self.write(f':SOUR{channel}:VOLT:MODE FIX')
        # Add LIST and SWEEP if needed

    def enable_output(self, channel: int = 1) -> None:
        """Enable output for channel"""
        self.write(f':OUTP{channel} ON')

    def disable_output(self, channel: int = 1) -> None:
        """Disable output for channel"""
        self.write(f':OUTP{channel} OFF')

    def enable_protection(self, channel: int = 1) -> None:
        """Enable over voltage/current protection"""
        self.write(f':OUTP{channel}:PROT:STAT ON')

    def disable_protection(self, channel: int = 1) -> None:
        """Disable over voltage/current protection"""
        self.write(f':OUTP{channel}:PROT:STAT OFF')

    def set_measurement_function(self, func: MeasurementFunction, channel: int = 1) -> None:
        """Enable measurement function"""
        self.write(f':SENS{channel}:FUNC:ON "{func.value}"')

    def measure_spot(self) -> str:
        """Execute spot measurement"""
        return self.query(':MEAS?')

    def set_aperture_time(self, time: float, channel: int = 1, mode: str = 'VOLT') -> None:
        """Set measurement aperture time"""
        self.write(f':SENS{channel}:{mode}:APER {time}')

    def set_nplc(self, nplc: float, channel: int = 1, mode: str = 'VOLT') -> None:
        """Set integration time in NPLC"""
        self.write(f':SENS{channel}:{mode}:NPLC {nplc}')

    def initiate_measurement(self) -> None:
        """Initiate trigger system"""
        self.write(':INIT')

    def abort_measurement(self) -> None:
        """Abort trigger system"""
        self.write(':ABOR')

    def fetch_data(self) -> str:
        """Fetch data from buffer"""
        return self.query(':FETC?')

    def read_data(self) -> str:
        """Initiate and fetch data"""
        return self.query(':READ?')