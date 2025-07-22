import os
import csv
import json
import time
from itertools import product
from functools import wraps
import numpy as np
from pyvisa import ResourceManager
from GMOS_LIA.LabDevices import *
from GMOS_LIA.ResultPlotter import Plotter

class BaseSetup():
    _project_dir = os.path.join(os.getcwd(), "..")
    _measurement_results_dir = os.path.join(_project_dir, "measuremet_results")
    
    def __init__(self, res_man:ResourceManager, test_param_dict: dict):
        self._res_man = res_man
        tester_name = self.__class__.__name__
        self._start_time = timestr = time.strftime("%Y%m%d-%H%M%S")
        self._results_dir = os.path.join(
                        self._measurement_results_dir,
                        tester_name,
                        self._start_time)
        self._result_file = None
        self._devices = {}
        #load_setup_config(path="setup.json")
        with open("setup.json", 'r') as file:
            setup = json.load(file)
            self.initialize_tester_info(setup, test_param_dict)
    
    @classmethod
    def genResultFileName(cls, filename: str = None):
        result_index = 0
        if filename is not None:
            new_filename = filename
        else:
            new_filename = cls.__name__
        while True:
            if result_index == 0:
                yield new_filename
            else:
                yield f"{new_filename}_{result_index}"
            result_index += 1
    
    @staticmethod
    def setup_fixture(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            self.update_sweep_parameters(kwargs)
            with self.prepare_result_file(
                filename=kwargs.get("filename"),
                abspath=kwargs.get("abspath", False)
            ) as file:
                self._csv_writer = csv.writer(file)
                return func(self, *args, **kwargs)
        return wrapper
        
    def prepare_result_file(self, filename: str = None, abspath: bool = False):
        self.result_file = (filename, abspath)
        return open(f"{self._result_file}.csv", 'w', newline='')

    def update_sweep_parameters(self, parameters):
        for name, value in parameters.items():
            if name == "filename" or name == "abspath":
                continue
            elif value is not None:
                self.set_variable_parameter(value, name)
    
    def initialize_tester_info(self, setup, test_param_dict):
        connected_devices = setup[setup["connected devices"]]
        required_devices = setup["required devices"]
        for dev in required_devices:
            dev_address = connected_devices[dev]
            if "SMU" in dev:
                self._devices[dev] = SMU(self._res_man, dev_address, dev)
            elif "LIA" in dev:
                self._devices[dev] = LIA(self._res_man, dev_address, dev)
            else:
                raise NotImplementedError(f"Unsupported device name {dev}")

        if len(self._devices) != len(required_devices):
            raise Exception("Not all devices are connected")
        
        self._sleep_time    = setup["default sleep"]
        tester_name = self.__class__.__name__
        self._tester_info   = setup[tester_name]
        for key, value in self._tester_info.items():
            setattr(self, f"_{key.replace(' ','_')}", value)
            
        for name, param in test_param_dict.items():
            value = self._tester_info[param]
            self.set_variable_parameter(value, name)
                    
        plot_settings = setup["plotter"]
        self._plotter = Plotter(self._results_dir, plot_settings)
    
    def set_variable_parameter(self, value, param_name):
        sweep_type = self._tester_info["sweep type"]
        if not isinstance(value, list):
            value = [value]     # ensure iterable for product()
            setattr(self, f"_{param_name}", value)
        else:
            if sweep_type == "linear":
                setattr(self, f"_{param_name}", np.arange(*value))
            elif sweep_type == "log":
                setattr(self, f"_{param_name}", np.logspace(*value))
            else:
                raise Exception(f"Invalid sweep type {sweep_type}")
    
    #def load_setup_config(path="setup.json") -> FullConfig:
    #    with open(path, "r") as f:
    #        return FullConfig.parse_raw(f.read())

    @property
    def result_file(self) -> str:
        return self._result_file
    
    @result_file.setter
    def result_file(self, filename_and_abspath:tuple):
        cls = self.__class__
        filename, abspath = filename_and_abspath
        if filename is not None:
            if abspath is not None and abspath == True:
                sep_index = filename.rfind(os.sep)
                if sep_index != -1:
                    self._results_dir, _ = filename[:sep_index-1]
                    filename, _          = filename[sep_index+1:]
                    result_file_name = next(cls.genResultFileName(filename))
                else:
                    raise Exception("Invalid absolute path filename given")
            else:
                result_file_name = filename
        else:
            result_file_name = next(cls.genResultFileName())
        self._result_file = os.path.join(self._results_dir, result_file_name)
    
    @property
    def results_directory(self) -> str:
        return self._results_dir

    def record_measurement(self, measurment):
        self._csv_writer.writerow(measurment)
    
    def __enter__(self):
        os.makedirs(self._results_dir, exist_ok=True)
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        for device in self._devices.values():
            device.setOff()
        try:
            os.rmdir(self._results_dir)
        except OSError:
            pass
    
    def perform_measurements(self, *args, **kwargs):
        raise NotImplementedError
        
class IVTester(BaseSetup):
    def __init__(self, res_man):
        tester_parameter_dict = {
            "smu_voltage"    : "smu voltage"
        }
        super().__init__(res_man, tester_parameter_dict)
        self.smu = self._devices["Heater SMU"]

    def __enter__(self):
        super().__enter__()
        self.smu.setFunctionVoltageFixed()
        self.smu.setCurrentCompliance(self._compliance)
        return self
        
    def setOutput(self, out):
        self.smu.setVoltage(out)
    
    @BaseSetup.setup_fixture
    def perform_measurements(self, smu_voltage = None, filename:str = None, abspath:bool = False):
        for v_out in self._smu_voltage:
            self.setOutput(v_out)
            time.sleep(self._sleep_time)
            [V_meas, I_meas] = self.smu.getMeasurement()
            self.record_measurement([v_out, V_meas, I_meas])
        
class ThreeTTester(BaseSetup):
    def __init__(self, res_man):
        tester_parameter_dict = {
            #"heater_Icomp"      : "heater Icomp",
            #"drain_Vcomp"       : "drain Vcomp",
            #"drain_Idc"         : "drain Idc",
            "heater_voltage"    : "heater voltage",
            "lia_frequency"     : "lia frequency",
            "lia_amplitude"     : "lia amplitude",
            "lia_offset"        : "lia offset"
        }
        super().__init__(res_man, tester_parameter_dict)
        self.heater             = self._devices["Heater SMU"]
        self.drain              = self._devices["Drain SMU"]
        self.lia                = self._devices["LIA"]
            
    def __enter__(self):
        super().__enter__()
        self.heater.setFunctionVoltageFixed()
        self.heater.setCurrentCompliance(self._heater_Icomp)
        self.drain.setFunctionCurrentFixed()
        self.drain.setVoltageCompliance(self._drain_Vcomp)
        return self
    
    def setOutput(self, heater_voltage:float ,frequency:float, amplitude:float, offset:float):
        self.heater.setVoltage(heater_voltage)
        self.lia.setOutputFrequency(frequency)
        self.lia.setOutputAmplitude(amplitude)
        self.lia.setOutputOffset(offset)
        self.drain.setCurrent(self._drain_Idc)
    
    @BaseSetup.setup_fixture
    def perform_measurements(self, heater_voltage = None ,lia_frequency = None, lia_amplitude = None, lia_offset = None, filename: str = None, abspath: bool = False):        
        for hv, f, amp, off in product(self._heater_voltage, self._lia_frequency, self._lia_amplitude, self._lia_offset):
            self.setOutput(hv, f, amp, off)
            time.sleep(self._sleep_time)
            lia_meas = self.lia.getLIAMeasurment()
            self.record_measurement([hv, lia_meas.X ,lia_meas.R])
        time.sleep(self._heater_sleep)

    def plot(self, plot_filename:str = None):
        if plot_filename is  None:
            self._plotter.plot_2d(self._result_file)
        else:
            res_file_path = os.path.join(self._results_dir, plot_filename)
            self._plotter.plot_2d(res_file_path)