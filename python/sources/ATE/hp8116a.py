"""
HP 8116A Signal Generator wrapper.
"""

from . import ATEBase
from enum import Enum

class TriggerMode(Enum):
    NORM = 1
    TRIG = 2
    GATE = 3
    E_WID = 4
    I_SWP = 5
    E_SWP = 6
    I_BUR = 7
    E_BUR = 8

class TriggerSlope(Enum):
    OFF = 0
    POS = 1
    NEG = 2

class WaveformType(Enum):
    DC = 0
    SINE = 1
    TRIANG = 2
    SQUARE = 3
    PULSE = 4

class PhaseMode(Enum):
    ZERO = 0
    NEG_90 = 1

class HP8116A(ATEBase):
    def __init__(self, tag: str = 'SG', rm=None) -> None:
        super().__init__(tag, rm)

    def set_frequency(self, freq, unit='HZ'):
        """Set frequency"""
        self.write(f'FRQ {freq} {unit}')

    def set_amplitude(self, amp, unit='V'):
        """Set amplitude"""
        self.write(f'AMP {amp} {unit}')

    def set_offset(self, offset, unit='V'):
        """Set DC offset"""
        self.write(f'OFS {offset} {unit}')

    def set_pulse_width(self, width, unit='NS'):
        """Set pulse width"""
        self.write(f'WID {width} {unit}')

    def set_duty_cycle(self, duty):
        """Set duty cycle in %"""
        self.write(f'DTY {duty} %')

    def set_burst_count(self, count):
        """Set burst count"""
        self.write(f'BUR {count}')

    def set_sweep_time(self, time, unit='S'):
        """Set sweep time per decade"""
        self.write(f'SWT {time} {unit}')

    def set_sweep_start(self, start, unit='HZ'):
        """Set sweep start frequency"""
        self.write(f'STA {start} {unit}')

    def set_sweep_stop(self, stop, unit='HZ'):
        """Set sweep stop frequency"""
        self.write(f'STP {stop} {unit}')

    # Waveform modes, etc. can be added if needed