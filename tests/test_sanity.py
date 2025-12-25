import pytest
from GMOS_LIA.visa_device_wrapper import VisaInstrument
from GMOS_LIA.stanford_research_sr860 import LIA 
from GMOS_LIA.keysight_b2962a import SMU
from GMOS_LIA.hp_6624a import PSU

address_list = ('GPIB0::14::INSTR', 'GPIB0::22::INSTR', 'GPIB0::23::INSTR')
idn_list = (
            '\n',
            'Keysight Technologies,B2962A,MY52350661,2.2.1744.8725\n',
            'Keysight Technologies,B2962A,MY52350537,2.0.1613.9020\n'
            )


def test_gpib_devices(resource_manager):
    connected_address = resource_manager.list_resources()
    print(f"[PyVISA] resource manager has detected: {address_list} avaliable addresses serial")
    assert set(address_list).issubset(set(connected_address))
    for address, idn in zip(address_list, idn_list):
        dev = resource_manager.open_resource(address)
        assert idn == dev.query('*IDN?')
        dev.close()

    dev.close()
def test_ip_devices(resource_manager):
    dev = resource_manager.open_resource('TCPIP::132.68.54.149::INSTR')
    assert 'Stanford_Research_Systems,SR860,003693,V1.51\n' == dev.query('*IDN?')
    dev.close()
    dev = resource_manager.open_resource('TCPIP::132.68.54.234::INSTR')
    assert 'KEYSIGHT TECHNOLOGIES,DSO9104A,MY53130118,06.00.00901\n' == dev.query('*IDN?')
    dev.close()