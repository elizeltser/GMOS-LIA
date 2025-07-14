import pyvisa as pyv
from collections import namedtuple

LIA_measurment = namedtuple('LIAMeas', ['X', 'Y', 'R', 'theta'])

class LIA_consants():
    output_channel1 = 0
    output_channel2 = 1
    output_channel_xy = 0
    output_channel_rth = 1

class Instrument:
    res_man = None
    def __init__(self, res_man : pyv.ResourceManager, gpib_address, inst_name):
        """ connected to device: {self.dev_name} at address {gpib_address} """
        self.inst = res_man.open_resource(gpib_address)
        self.reset()
        self.dev_name = self.inst.query("*IDN?")
        self.inst_name = inst_name
        
    def __str__(self):
        return f"{self.dev_name} as instance {self.inst}"
        
    def reset(self):
        self.inst.write("*RST")
        self.inst.write("*CLS")
        
    def __del__(self):
        """{self.inst_name} instance is closed"""
        self.inst.close()

class LIA(Instrument):
    def __init__(self, res_man, gpib_address, inst_name):
        """ [Instrument] Connected to LIA name: '{self.inst_name}' """
        super().__init__(res_man, gpib_address, inst_name)
    
    def setChannelOutputFunction(self, output_channel, output_function):
        self.inst.write(f'COUT {output_channel}, {output_function}')
    
    def setOutputFrequency(self, frequency):
        self.inst.write(f'FREQ {frequency}')
        
    def setOutputAmplitude(self, amplitude):
        self.inst.write(f'SLVL {amplitude}')

    def setOutputOffset(self, offset):
        self.inst.write(f'SOFF {offset}')

    def autoPhase(self):
        self.inst.write(f'APHS')
        
    def getLIAMeasurment(self):
        return LIA_measurment(*self.inst.query('SNAPD?').strip().split(","))
    
    def setOff(self):
        self.setOutputOffset(0)
        self.setOutputAmplitude(0)
        
class SMU(Instrument):
    def __init__(self, res_man, gpib_address, inst_name):
        """ [Instrument] Connected to SMU name: '{self.inst_name}' """
        super().__init__(res_man, gpib_address, inst_name)
        self.setOutputFloating()
        
    def setFunctionVoltageFixed(self):
        """ Set SMU function to fixed voltage source """
        self.inst.write('FUNC:MODE VOLT')
        self.inst.write('SOUR:VOLT:MODE FIX')
        
    def setFunctionCurrentFixed(self):
        """ Set SMU function to fixed current source """
        self.inst.write('FUNC:MODE CURR')
        self.inst.write('SOUR:CURR:MODE FIX')
    
    def setVoltage(self, voltage):
        """ Set SMU output voltage """
        self.inst.write(f'SOUR:VOLT {voltage}')
        
    def setCurrent(self, current):
        """ Set SMU output current """
        self.inst.write(f'SOUR:CURR {current}')
            
    def setOn(self):
        """ Power on the SMU output """
        self.inst.write('OUTP 1')
    
    def setOff(self):
        """ Power off the SMU output """
        self.inst.write('OUTP 0')
        
    def setVoltageCompliance(self, comp):
        """ Set SMU output voltage compliance """
        self.inst.write(f'SENS:VOLT:PROT {comp}')

    def setCurrentCompliance(self, comp):
        """ Set SMU output current compliance """
        self.inst.write(f'SENS:CURR:PROT {comp}')
    
    def getMeasurement(self):
        """ Read SMU current and voltage """
        current = float(self.inst.query('MEAS:CURR:DC?').strip())
        voltage = float(self.inst.query('MEAS:VOLT:DC?').strip())
        return [voltage, current]
        
    def setOutputFloating(self):
        """ Set SMU output to floating when off """
        self.inst.write("OUTP:LOW FLO")
