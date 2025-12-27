import pyvisa
from pyvisa.resources import MessageBasedResource
import numpy as np
import time
import pdb

from GMOS_LIA.hp_6624a import PSU

rm = pyvisa.ResourceManager()
inst = rm.open_resource('GPIB0::14::INSTR')   # change IP accordingly

inst.timeout = 20_000   # 20 seconds

#def main():
#    # -------------------------------
#    # Connect to instrument
#    # -------------------------------
#
#    def scpi(cmd):
#        print("->", cmd)
#        assert isinstance(inst, MessageBasedResource)
#        return inst.write(cmd)
#
#    def scpi_query(cmd):
#        print("?", cmd)
#        assert isinstance(inst, MessageBasedResource)
#        return inst.query(cmd)
#
#    # -------------------------------
#    # Instrument setup
#    # -------------------------------
#    scpi("*RST")
#    scpi("*CLS")
#
#    # Set measurement mode to current
#    scpi(':SENS:FUNC "CURR"')
#    scpi(":SENS:CURR:RANG 10e-3")       # choose a suitable range
#    scpi(":SENS:CURR:APER 0.00005")     # 50 µs aperture (example)
#
#    # -------------------------------
#    # Trigger configuration
#    # -------------------------------
#    interval = 0.001   # 1 ms
#    samples  = 1000
#
#    scpi(":TRIG:ACQ:SOUR TIM")          # use internal timer as trigger source
#    scpi(f":TRIG:ACQ:TIM {interval}")   # time between samples
#    scpi(f":TRIG:ACQ:COUN {samples}")   # number of samples
#
#    # -------------------------------
#    # Arms the system and starts acquisition
#    # -------------------------------
#    scpi(":INIT:IMM")
#
#    # Block until done
#    scpi("*WAI")
#
#    # -------------------------------
#    # Fetch measurement results
#    # -------------------------------
#    raw = scpi_query(":FETC:ARR:CURR?")
#    currents = np.array([float(x) for x in raw.split(",")])
#
#    print(f"Captured {len(currents)} samples")
#    print("First 10:", currents[:10])

def main():
    pass
#    psu = PSU(inst)
#    psu.enable_setup(start_power=True)
#    time.sleep(5)
#    psu.disable_setup()

if __name__ == "__main__":
    main()    