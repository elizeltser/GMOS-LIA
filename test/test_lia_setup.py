import pytest
from pyvisa import ResourceManager
import numpy as np
from GMOS_LIA.LabDevices import SMU, LIA
from GMOS_LIA.LIASetup import IVTester, ThreeTTester

def test_lia_wrapper(resource_manager):
    lia = LIA(resource_manager, "MOCK0::LIA::INSTR", "testLIA")
    lia.setOutputFrequency(1234.5)
    lia.setOutputAmplitude(0.12)
    lia.setOff()

def test_smu_init(resource_manager):
    smu = SMU(resource_manager, "MOCK0::SMU::INSTR", "test SMU")
    
#def test_ivtester_init(resource_manager):
#    with IVTester(resource_manager) as iv_tester:
#        iv_tester.execute()
    
def test_GMOS_fixture(resource_manager):
    with ThreeTTester(resource_manager) as t3t:
        t3t.execute()