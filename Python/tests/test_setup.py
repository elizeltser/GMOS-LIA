import pytest
import time
import numpy as np
from GMOS_LIA.stanford_research_sr860 import LIA_channel, LIA_function
from GMOS_LIA.keysight_b2962a import SMU

def test_stm32_connection(stm32_device):
    stm32_device.send_command('PING')
    
def test_stm32_version(stm32_device):
    version = stm32_device.send_query('version')
    assert version == "1.0.0", f"Unexpected STM32 version: {version}"

@pytest.mark.usefixtures("power_supply")
def test_sample():
    time.sleep(10)
    assert True
    pass


@pytest.mark.usefixtures("esd_protection")
def test_flicker_noise(devices):
    devheater = devices["Drain"]
    pass

@pytest.mark.usefixtures("esd_protection")
def test_heater_resistance(devices):
    heater = devices["Heater"]
    heater.set_function_voltage_fixed()
    heater.set_current_compliance('1')
    heater.set_voltage('0')
    heater.set_on()
    time.sleep(1)
    voltages = np.linspace(0, 2, 21)
    resistances = []
    for v in voltages:
        heater.set_voltage(str(v))
        time.sleep(0.2)
        curr = float(heater.get_current())
        if curr != 0:
            resistances.append(v / curr)
        else:
            resistances.append(np.inf)
    heater.set_off()
    print("Voltages:", voltages)
    print("Resistances:", resistances)


@pytest.mark.usefixtures("esd_protection")
class Test2TLIA:
    @pytest.mark.parametrize('lia_frequency, heater_voltage',
                        [("200e3", "0"),
                         ("400e3", "0"),
                         ("700e3", "0"),
                         ("1000e3", "0"),
                         ("200e3", "700e-3"),
                         ("400e3", "700e-3"),
                         ("700e3", "700e-3"),
                         ("1000e3", "700e-3"),
                         ("200e3", "1.5"),
                         ("400e3", "1.5"),
                         ("700e3", "1.5"),
                         ("1000e3", "1.5"),
                         ("200e3", "2"),
                         ("400e3", "2"),
                         ("700e3", "2"),
                         ("1000e3", "2")])
    def test_lia_sweep(self,
                       result_file,
                       devices,
                       lia_frequency,
                       heater_voltage):
        # device setup
        lia = devices["LIA"]
        heater = devices["Heater"]
        lia.set_channel_function(LIA_channel.OCH1, LIA_function.RTHeta)
        lia.set_frequency(lia_frequency)
        lia.set_amplitude('50e-3')

        heater.set_function_voltage_fixed()
        heater.set_voltage('0')
        heater.set_current_compliance('700e-3')
        heater.set_on()

        # result_file.writerow(["Vapplied", "R", "Theta"])

        # Test execution
        # heater.set_voltage(heater_voltage)
        # time.sleep(2)
        # for offset in np.logspace(0.0, 1.7, 400)/ 100:
        #     lia.set_offset(np.round(offset, 2))
        #     time.sleep(0.1)
        #     meas = lia.get_measurement()
        #     result_file.writerow([offset, meas.X, meas.Theta])

    def test_heater_resistance(self,
                       result_file,
                       devices):
        heater = devices["Heater"]
        