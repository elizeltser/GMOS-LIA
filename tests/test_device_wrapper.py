import pytest
from GMOS_LIA.visa_device_wrapper import VisaInstrument
from GMOS_LIA.stanford_research_sr860 import LIA 
from GMOS_LIA.keysight_b2962a import SMU
from GMOS_LIA.hp_6624a import PSU

    
def test_lia_wrapper(mock_resource_manager):
    lia_resource = mock_resource_manager.open_resource('MOCK0::LIA::INSTR')
    lia = LIA(lia_resource)
    lia.set_frequency(1234.5)
    lia.set_amplitude(0.12)
    lia.set_offset(0.2)
    lia.auto_phase()
    lia.get_measurement()
    lia.set_off()

    
def test_smu_init(mock_resource_manager):
    smu_resource = mock_resource_manager.open_resource('MOCK0::SMU::INSTR')
    smu = SMU(smu_resource)
    smu.set_output_floating()
    smu.set_current_compliance(100e-3)
    smu.set_voltage(5)
    smu.set_on()
    smu.get_measurement()
    smu.set_off()
