import csv
import json
import time
from functools import wraps
import numpy as np
import matplotlib.pyplot as plt
import os
from GMOS_LIA.LabDevices import *

class BaseSetup():
    _project_dir = os.path.join(os.getcwd(), "..")
    _measuremet_results_dir = os.path.join(_project_dir, "measuremet_results")
    _devices = {}
    
    def __init__(self, res_man):
        self.res_man = res_man
        self._results_dir = None
        self._result_file = None
        self._start_time = timestr = time.strftime("%Y%m%d-%H%M%S")
        self._o_list = None
        
        with open("setup_3T.json", 'r') as file:
            setup = json.load(file)
            connected_devices = setup[setup["connected devices"]]
            required_devices = setup["required devices"]
            
            for dev in required_devices:
                dev_address = connected_devices[dev]
                if "SMU" in dev:
                    self._devices[dev] = SMU(self.res_man, dev_address, dev)
                elif "LIA" in dev:
                    self._devices[dev] = LIA(self.res_man, dev_address, dev)
                else:
                    raise NotImplementedError(f"Unsupported device name {dev}")
    
            if len(self._devices) != len(required_devices):
                raise Exception("Not all devices are connected")
            self._tester_info = setup[setup["tester name"]]
    
    @staticmethod
    def setup_fixture(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            print(kwargs)
            
            if "filename" in kwargs:
                filename = kwargs["filename"]
                if "abspath" in kwargs and kwargs["abspath"] == True:
                    self._result_file = filename
                else:
                    self._result_file = os.path.join(self._results_dir, filename)
                
            os.makedirs(self._result_file, exist_ok=True)
            
            result = func(self, *args, **kwargs)
            return result
        return wrapper
        
    #def getOutputs(self, ):
    
    def plot_2d(self, filename : str = None, abspath=False):
        if filename != None:
            if abspath:
                res_file_path = filename
            else:
                res_file_path = os.path.join(self._results_dir, filename)
        else:
            res_file_path = self._result_file
            
        with open(f"{res_file_path}.csv", 'r') as file:
            reader = csv.reader(file)
            header = next(reader)
            header = [h.strip() for h in header]
            Xcol_idx = header.index('Heater [V]')
            Ycol_idx = header.index('LIA.R [V]')
            data = []
            for row in reader:
                y_data = float(row[Ycol_idx])
                x_data = float(row[Xcol_idx])
                data.append((y_data,x_data))
                
        [Y, X] = list(zip(*data))
        fig, ax = plt.subplots()
        ax.plot(X, Y, marker='o')
        #ax.set_yscale('log')
        plt.title(file_title)
        plt.xlabel('Heater [V]')
        plt.ylabel('LIA.R [V]')
        plt.grid(True)
        plt.savefig(f"{res_file_path}.png")
        plt.close()

    def __enter__(self):
        raise NotImplementedError
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        raise NotImplementedError
    
    def execute(self, *args, **kwargs):
        raise NotImplementedError
        
class IVTester(BaseSetup):
    def __init__(self, res_man):
        ivtester_info = super().__init__(res_man)
        self._o_list_def     = ivtester_info["output list"]
        self._compliance     = ivtester_info["compliance"]
        self._mode           = ivtester_info["output mode"]
        self._sleep_time     = ivtester_info["default sleep"]
        self._sweep_type     = ivtester_info["sweep type"]

    def __enter__(self):
        self._results_dir = os.path.join(self._measuremet_results_dir, "IVTester", self._start_time)
        os.makedirs(self._results_dir, exist_ok=True)
        self._result_file = os.path.join(self._results_dir, "IV")
        
        if self._sweep_type == "linear":
            self.O_list = np.arange(*self._o_list_def)
            
        elif self._sweep_type == "log":
            O_list = np.logspace(*self._o_list_def)
            
        else:
            raise Exception(f"Invalid sweep time selected {self._sweep_type}")
        
        if self._mode == "VOLT":
            self.smu.setFunctionVoltageFixed()
            self.smu.setCurrentCompliance(self._compliance)
            
        elif self._mode == "CURR":
            self.smu.setFunctionCurrentFixed()
            self.smu.setVoltageCompliance(self._compliance)
        else:
            raise Exception(f"Invalid output mode selected {self._mode}")
        
        self.smu.setOutputFloating()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.smu.setOff()
        
    def setOutput(self, out):
        if self._mode == "VOLT":
            self.smu.setVoltage(out)
        elif self._mode == "CURR":
            self.smu.setCurrent(out)
        else:
            raise Exception(f"Output mode not supported: {self._mode}")
    
    def execute(self, filename : str = None, output_list : np.ndarray = None):
        if filename != None:
            if abspath:
                res_file = filename
            else:
                res_file = os.path.join(self._results_dir, filename)
        else:
            res_file = self._results_file
            
        if output_list != None:
            o_list = output_list
        else:
            o_list = self.O_list
            
        self.smu.setOn()
        
        with open(f"{res_file}.csv", 'w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow([f"Set {self._mode}","V (V)" , "I (A)"])
            for O_set in o_list:
                self.setOutput(O_set)
                time.sleep(self._sleep_time)
                [V_meas, I_meas] = self.smu.getMeasurement()
                writer.writerow([O_set, V_meas, I_meas])
        
class Tester3T(BaseSetup):
    def __init__(self, res_man):
        super().__init__(res_man)
        self._heater_icomp  = self._tester_info["heater Icomp"]
        self._drain_vcomp   = self._tester_info["drain Vcomp"]
        self._drain_idc     = self._tester_info["drain Idc"]
        self._heater_sleep  = self._tester_info["heater sleep"]
        self._lia_frequency = self._tester_info["lia frequency"]
        self._lia_amplitude = self._tester_info["lia amplitude"]
        self._lia_offset    = self._tester_info["lia offset"]
        self._gate_sweep     = self._tester_info["gate sweep"]
        
        self._sleep_time    = self._tester_info["default sleep"]
        
        self.heater         = self._devices["Heater SMU"]
        self.drain          = self._devices["Drain SMU"]
        self.lia            = self._devices["LIA"]
            
    def __enter__(self):
        self._results_dir = os.path.join(self._measuremet_results_dir, "Tester3T", self._start_time)
        
        self.heater.setFunctionVoltageFixed()
        self.heater.setCurrentCompliance(self._heater_icomp)
    
        self.drain.setFunctionCurrentFixed()
        self.drain.setVoltageCompliance(self._drain_vcomp)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.heater.setOff()
        self.drain.setOff()
        self.lia.setOff()
    
    @BaseSetup.setup_fixture
    def execute(self, frequency : float = None,amplitude : float = None, offset : float = None, filename : str = None, abspath=False, output_list : np.ndarray = None):
        
        if output_list is not None:
            o_list = output_list
        else:
            o_list = np.arange(self._gate_sweep)
        
        if frequency is not None:
            self._lia_frequency = frequency
            
        if amplitude is not None:
            self._lia_amplitude = amplitude
            
        if offset is not None:
            self._lia_offset = offset
        
        self.lia.setOutputFrequency(self._lia_frequency)
        self.lia.setOutputAmplitude(self._lia_amplitude)
        self.lia.setOutputOffset(self._lia_offset)
        
        self.drain.setCurrent(self._drain_idc)
        self.drain.setOn()
        
        self.heater.setOn()
        time.sleep(self._heater_sleep)
        
        with open(f"{res_file}.csv", 'w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(["Heater [V]", "LIA.X [V]", "LIA.R [V]"])
            for hv in o_list:
                self.heater.setVoltage(hv)
                time.sleep(self._sleep_time)
                lia_meas = self.lia.getLIAMeasurment()
                print(f"heater = {hv}, liaX = {lia_meas.X}, liaR = {lia_meas.R}")
                writer.writerow([hv, lia_meas.X ,lia_meas.R])