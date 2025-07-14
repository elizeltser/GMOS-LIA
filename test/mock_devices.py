from collections import defaultdict
from pyvisa_mock.base.base_mocker import BaseMocker, scpi
from pyvisa_mock.base.register import register_resource

class MockLIA(BaseMocker):
    def __init__(self):
        super().__init__()
        self.frequency = 0.0
        self.amplitude = 0.0
        self.offset = 0.0
        self.channel_functions = {}

    @scpi("*IDN?")
    def idn(self) -> str:
        return "MockLIA,Model123,00001,1.0"

    @scpi("*RST")
    def reset(self) -> None:
        self.frequency = 0.0
        self.amplitude = 0.0
        self.offset = 0.0
        self.channel_functions.clear()
        self.X = 1
        self.Y = 2
        self.R = 3
        self.theta = 4

    @scpi("*CLS")
    def clear(self) -> None:
        return None

    @scpi("COUT <channel>, <function>")
    def set_output_function(self, channel: int, function: str) -> None:
        self.channel_functions[channel] = function

    @scpi("FREQ <frequency>")
    def set_frequency(self, frequency: float) -> None:
        self.frequency = frequency

    @scpi("SLVL <amplitude>")
    def set_amplitude(self, amplitude: float) -> None:
        self.amplitude = amplitude

    @scpi("SOFF <offset>")
    def set_offset(self, offset: float) -> None:
        self.offset = offset

    @scpi("SNAPD?")
    def  get_all_measurments(self) -> str:
        return f"{self.X}, {self.Y}, {self.R}, {self.theta}"
        
    @scpi("APHS")
    def auto_phase(self) -> str:
        return "0"  # dummy response

class MockSMU(BaseMocker):
    def __init__(self):
        super().__init__()
        self.resistance = 1e3
        self.source_type = "VOLT"
        self.source_mode = "FIXED"
        self.voltage = 0.0
        self.current = 0.0
        self.output_on = False
        self.v_compliance = None
        self.c_compliance = None
 
    @scpi("*IDN?")
    def idn(self) -> str:
        return "MockSMU,Model456,00002,2.0"

    @scpi("*RST")
    def reset(self) -> None:
        self.source_type = "VOLT"
        self.source_mode = "FIX"
        self.voltage = 0.0
        self.current = self.voltage // self.resistance
        self.output_on = False
        self.v_compliance = None
        self.c_compliance = None
        self.low_state = "GND"

    @scpi("*CLS")
    def clear(self) -> None:
        return None

    @scpi("FUNC:MODE VOLT")
    def set_mode_voltage(self) -> None:
        self.source_type = "VOLT"

    @scpi("FUNC:MODE CURR")
    def set_mode_current(self) -> None:
        self.source_type = "CURR"

    @scpi("SOUR:VOLT:MODE FIX")
    def set_voltage_mode(self) -> None:
        self.source_mode = "FIX"

    @scpi("SOUR:CURR:MODE FIX")
    def set_current_mode(self) -> None:
        self.source_mode = "FIX"

    @scpi("SOUR:VOLT <value>")
    def set_voltage(self, value: str) -> None:
        if self.source_type == "VOLT":
            self.voltage = float(value)
            self.current = min(self.voltage // self.resistance, self.c_compliance)
            self.voltage = self.current * self.resistance if self.current == self.c_compliance else self.voltage
        else:
            raise ValueError("Setting voltage when in current mode")

    @scpi("SOUR:CURR <value>")
    def set_current(self, value: str) -> None:
        if self.source_type == "CURR":
            self.current = float(value) 
            self.voltage = min(self.current * self.resistance, self.v_compliance)
            self.current = self.voltage // self.resistance if self.voltage == self.v_compliance else self.current
        else:
            raise ValueError("Setting current when in voltage mode")

    @scpi("OUTP:LOW <state>")
    def set_low_float(self, state: str) -> None:
        self.low_state = state
        return None

    @scpi("OUTP 1")
    def output_on_cmd(self) -> None:
        self.output_on = True

    @scpi("OUTP 0")
    def output_off_cmd(self) -> None:
        self.output_on = False

    @scpi("OUTP:STAT?")
    def query_output_state(self) -> str:
        return "1" if self.output_on else "0"

    @scpi("SENS:VOLT:PROT <value>")
    def set_voltage_compliance(self, value: float) -> None:
        self.v_compliance = value

    @scpi("SENS:CURR:PROT <value>")
    def set_current_compliance(self, value: float) -> None:
        self.c_compliance = value

    @scpi("MEAS:CURR:DC?")
    def measure_current(self) -> str:
        return str(self.current)

    @scpi("MEAS:VOLT:DC?")
    def measure_voltage(self) -> str:
        return str(self.voltage)
