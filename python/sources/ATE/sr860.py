"""
SR860 Lock-in Amplifier wrapper.
"""

from enum import Enum

from .ate_base import ATEBase


class Sensitivity(Enum):
    V1 = 0
    MV500 = 1
    MV200 = 2
    MV100 = 3
    MV50 = 4
    MV20 = 5
    MV10 = 6
    MV5 = 7
    MV2 = 8
    MV1 = 9
    UV500 = 10
    UV200 = 11
    UV100 = 12
    UV50 = 13
    UV20 = 14
    UV10 = 15
    UV5 = 16
    UV2 = 17
    UV1 = 18
    NV500 = 19
    NV200 = 20
    NV100 = 21
    NV50 = 22
    NV20 = 23
    NV10 = 24
    NV5 = 25
    NV2 = 26
    NV1 = 27

class TimeConstant(Enum):
    US1 = 0
    US3 = 1
    US10 = 2
    US30 = 3
    US100 = 4
    US300 = 5
    MS1 = 6
    MS3 = 7
    MS10 = 8
    MS30 = 9
    MS100 = 10
    MS300 = 11
    S1 = 12
    S3 = 13
    S10 = 14
    S30 = 15
    KS1 = 16
    KS3 = 17
    KS10 = 18
    KS30 = 19

class FilterSlope(Enum):
    DB6 = 0
    DB12 = 1
    DB18 = 2
    DB24 = 3

class InputSource(Enum):
    A         = 0
    A_MINUS_B = 1
    I_1MEG    = 2
    I_100MEG  = 3

class InputCoupling(Enum):
    AC = 0
    DC = 1

class SR860(ATEBase):
    def __init__(self, tag: str = 'LIA', rm=None) -> None:
        super().__init__(tag, rm)

    def set_frequency(self, freq):
        """Set reference frequency in Hz"""
        self.write(f'FREQ {freq}')

    def get_frequency(self):
        """Get reference frequency"""
        return float(self.query('FREQ?'))

    def set_phase(self, phase):
        """Set reference phase in degrees"""
        self.write(f'PHAS {phase}')

    def get_phase(self):
        """Get reference phase"""
        return float(self.query('PHAS?'))

    def set_amplitude(self, amp):
        """Set sine output amplitude"""
        self.write(f'SLVL {amp}')

    def get_amplitude(self):
        """Get sine output amplitude"""
        return float(self.query('SLVL?'))

    def set_offset(self, offset):
        """Set sine output DC level"""
        self.write(f'SOFF {offset}')

    def get_offset(self):
        """Get sine output DC level"""
        return float(self.query('SOFF?'))

    def set_sensitivity(self, sens: Sensitivity):
        """Set sensitivity"""
        self.write(f'SCAL {sens.value}')

    def get_sensitivity(self):
        """Get sensitivity"""
        return int(self.query('SCAL?'))

    def set_time_constant(self, tc: TimeConstant):
        """Set time constant"""
        self.write(f'OFLT {tc.value}')

    def get_time_constant(self):
        """Get time constant"""
        return int(self.query('OFLT?'))

    def set_filter_slope(self, slope: FilterSlope):
        """Set filter slope"""
        self.write(f'OFSL {slope.value}')

    def get_filter_slope(self):
        """Get filter slope"""
        return int(self.query('OFSL?'))

    def get_output(self, param):
        """Get parameter: 0=X, 1=Y, 2=R, 3=θ"""
        return float(self.query(f'OUTP? {param}'))

    def snap(self, *params):
        """Query multiple parameters"""
        cmd = 'SNAP? ' + ','.join(str(p) for p in params)
        return [float(x) for x in self.query(cmd).split(',')]

    def auto_phase(self):
        """Auto phase"""
        self.write('APHS')

    def auto_scale(self):
        """Auto scale"""
        self.write('ASCL')

    def auto_range(self):
        """Auto range"""
        self.write('ARNG')

    def set_input_source(self, source: InputSource):
        """Set input source (A, A-B, current)"""
        self.write(f'ISRC {source.value}')

    def set_input_coupling(self, coupling: InputCoupling):
        """Set input coupling (AC or DC)"""
        self.write(f'ICPL {coupling.value}')