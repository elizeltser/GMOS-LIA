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
#        iv_tester.perform_measurements()
@pytest.mark.parametrize("heater_voltage, frequency, amplitude, offset",
    [(1, 2, 3, [4,6,1]),
    (None, 2, [5,7,1], 3)])
def test_ThreeTTester(resource_manager, heater_voltage, frequency, amplitude, offset):
    with ThreeTTester(resource_manager) as t3t:
        t3t.perform_measurements(
                    heater_voltage=heater_voltage,
                    lia_frequency=frequency,
                    lia_amplitude=amplitude,
                    lia_offset=offset)