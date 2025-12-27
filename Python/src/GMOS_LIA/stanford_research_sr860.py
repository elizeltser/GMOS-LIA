from enum import Enum
from dataclasses import dataclass
from GMOS_LIA.visa_device_wrapper import VisaInstrument


@dataclass
class LIA_measurement:
    X: str
    Y: str
    R: str
    Theta: str


class LIA_channel(Enum):
    OCH1 = 0
    OCH2 = 1
    

class LIA_function(Enum):
    XY = 0
    RTHeta = 1


class LIA(VisaInstrument):
    
    def set_channel_function(self,
                                 output_channel:LIA_channel,
                                 output_function:LIA_function
        ) -> None:
        self.write(f'COUT {output_channel}, {output_function}')
    
    def set_frequency(self, frequency:float) -> None:
        self.write(f'FREQ {frequency}')
        
    def set_amplitude(self, amplitude:float) -> None:
        self.write(f'SLVL {amplitude}')

    def set_offset(self, offset:float) -> None:
        self.write(f'SOFF {offset}')

    def auto_phase(self) -> None:
        self.write(f'APHS')
        
    def get_measurement(self) -> LIA_measurement:
        return LIA_measurement(*self.query('SNAPD?').strip().split(","))
    
    def set_off(self) -> None:
        self.set_offset(0)
        self.set_amplitude(0)
        
