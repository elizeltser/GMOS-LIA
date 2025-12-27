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
def GMOS_3T_NOCATALIST(visa_manager):
    with ThreeTTester(visa_manager) as t3t:
        t3t.perform_measurements()
        t3t.plot()

@resource_manager
def cli():
    console = code.InteractiveConsole(locals=globals())
    console.interact(banner="Entering interactive console. Type 'exit()' or Ctrl+D to quit.")  