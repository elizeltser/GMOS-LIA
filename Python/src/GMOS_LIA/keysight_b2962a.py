from GMOS_LIA.visa_device_wrapper import VisaInstrument
from dataclasses import dataclass

@dataclass
class SMU_measurment:
    V: float
    I: float

    
class SMU(VisaInstrument):
        
    def set_function_voltage_fixed(self) -> None:
        """ Set SMU function to fixed voltage source """
        self.write('FUNC:MODE VOLT')
        self.write('SOUR:VOLT:MODE FIX')
        
    def set_function_current_fixed(self) -> None:
        """ Set SMU function to fixed current source """
        self.write('FUNC:MODE CURR')
        self.write('SOUR:CURR:MODE FIX')
    
    def set_voltage(self, voltage) -> None:
        """ Set SMU output voltage """
        self.write(f'SOUR:VOLT {voltage}')
        
    def set_current(self, current) -> None:
        """ Set SMU output current """
        self.write(f'SOUR:CURR {current}')
            
    def set_on(self) -> None:
        """ Power on the SMU output """
        self.write('OUTP 1')
    
    def set_off(self) -> None:
        """ Power off the SMU output """
        self.write('OUTP 0')
        
    def set_voltage_compliance(self, comp) -> None:
        """ Set SMU output voltage compliance """
        self.write(f'SENS:VOLT:PROT {comp}')

    def set_current_compliance(self, comp) -> None:
        """ Set SMU output current compliance """
        self.write(f'SENS:CURR:PROT {comp}')
    
    def in_voltage_compliance(self) -> bool:
        return self.query(":SENS:VOLT:PROT:TRIP?").strip() == '1'
        
    def in_current_compliance(self) -> bool:
        return self.query(":SENS:CURR:PROT:TRIP?").strip() == '1'
    
    def get_measurement(self) -> SMU_measurment:
        """ Read SMU current and voltage """
        current = float(self.query('MEAS:CURR:DC?').strip())
        voltage = float(self.query('MEAS:VOLT:DC?').strip())
        return SMU_measurment(voltage, current)

    def timed_sample(self):
        """
        INIT:IMM  
        ↓ enters ARM layer  
        (waiting)
        ARM event happens (internal or external)
        ↓ transition to TRIGGER layer
        TRIGger events happen (internal or external)
        ↓
        N measurements collected            / use :IDLE? to check state
        ↓
        return to IDLE

        *RST
        :SOUR:FUNC CURR
        :SENS:FUNC "CURR"
        :SENS:CURR:RANG 10E-3

        :TRIG:ACQ:SOUR TIM
        :TRIG:ACQ:TIM 1E-4        ; 100 µs
        :TRIG:ACQ:COUN 200

        :INIT:IMM
        *WAI

        :FETC:ARR:CURR?
        """
        
        pass

        
    def set_output_floating(self) -> None:
        """ Set SMU output to floating when off """
        self.write("OUTP:LOW FLO")

