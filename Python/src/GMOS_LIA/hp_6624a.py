import pyvisa
from GMOS_LIA.visa_device_wrapper import VisaInstrument

class PSU(VisaInstrument):

    def _start_power_supply(self):
        self.write("VSET 1,5.5")
        self.write("ISET 1,1")
        self.write("VSET 3,5.5")
        self.write("ISET 3,1")
        self.write("OUT 1,1")
        self.write("OUT 3,1")

    def _end_power_supply(self):
        self.write("VSET 1,0")
        self.write("ISET 1,0")
        self.write("VSET 3,0")
        self.write("ISET 3,0")
        self.write("OUT 3,0")

    def _start_esd_prot(self):
        self.write("VSET 2,5")
        self.write("ISET 2,700E-3")
        self.write("OUT 2,1")

        
    def _start_fan(self):
        self.write("VSET 4,7")
        self.write("ISET 4,1.5")
        self.write("OUT 4,1")

        
    def _end_esd_prot(self):
        self.write("VSET 2,0")
        self.write("ISET 2,0")
        self.write("OUT 2,0")

        
    def _end_fan(self):
        self.write("VSET 4,0")
        self.write("ISET 4,0")
        self.write("OUT 4,0")


    def enable_setup(self, start_fan: bool = True, start_power: bool = False):
        self._start_esd_prot()
        if (start_fan):
            self._start_fan()
        if (start_power):
            self._start_power_supply()

            
    def disable_setup(self):
        self._end_esd_prot()
        self._end_fan()
        self._end_power_supply()
