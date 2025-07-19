import code
import numpy as np
import os
from itertools import product
from pyvisa import ResourceManager
from GMOS_LIA.LabDevices import SMU, LIA
from GMOS_LIA.LIASetup import IVTester, ThreeTTester

def resource_manager(func):
    def wrapper(*args):
        rm = ResourceManager()
        print(f"Connected to the following devices:\n\t {rm.list_resources()}")
        result = func(rm, *args)
        rm.close() 
        return result
    return wrapper

@resource_manager
def GMOS_3T_NOCATALIST1(visa_manager):
    with ThreeTTester(visa_manager) as t3t:
        freq_list   = [200, 500, 800,1e3]
        amp_list    = [20e-3, 50e-3, 80e-3, 100e-3]
        off_list    = [800e-3, 900e-3, 1, 1.1]
        res_dir = os.path.join(os.getcwd(), "..", "measuremet_results" ,"3T-Tester", "20250710-154821")
        for freq, amp, off in product(freq_list, amp_list, off_list):
                    fname = f"3T-Tester-f_{freq}-amp_{amp:.3f}-off_{off:.1f}".replace(".", "")
                    fdir = os.path.join(res_dir,fname)
                    #t3t.perform_measurements(
                    #freq=freq,
                    #amp=amp,
                    #off=off,
                    #filename=f"{fname}.csv",
                    #output_list=np.arange(2.5, 5.1, 0.1)
                    #)
                    t3t.plot_2d(filename=fdir,abspath=True)

@resource_manager
def GMOS_3T_NOCATALIST(visa_manager):
    with ThreeTTester(visa_manager) as t3t:
        hv_list     = np.arange(3.5, 4, 0.1)
        amp_list    = [20e-3, 50e-3, 80e-3, 100e-3]
        off_list    = np.arange(0.8, 0.9, 10e-3)
        for hv, amp, off in product(hv_list, amp_list, off_list):
            fname = f"3T-Tester-hv_{hv:.2f}-amp_{amp:.3f}-off_{off:.3f}".replace(".", "")
            t3t.execute(filename=fname, heater=hv, amplitude=amp, offset=off)
            t3t.plot(fname)

@resource_manager
def cli():
    console = code.InteractiveConsole(locals=globals())
    console.interact(banner="Entering interactive console. Type 'exit()' or Ctrl+D to quit.")  