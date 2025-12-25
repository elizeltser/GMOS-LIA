import pyvisa
import os
from time import strftime
from abc import ABC, abstractmethod

class SetupBase(ABC):
    """ Template for definition of setup definition - an aggregation of tests for a specific setup connection.
    Setup must support 'with SomeSetup as su:' pythonic statements, documentation for all setup commands sent to a log as well as documentation of the measurement results """
    def __init__(self, resource_manager: pyvisa.ResourceManager):
        self._resource_manager = pyvisa.ResourceManager()
        self._start_time = strftime("%Y%m%d-%H%M%S")
        self._results_dir = os.path.join("measurments", self.__class__.__name__)
        self._devices = {}
        self._resource_manager = resource_manager

        
    def __enter__(self):
        self.enter_prologue()
        yield self
        self.enter_epilogue()

    @abstractmethod
    def enter_prologue(self):
        pass

    @abstractmethod
    def enter_epilogue(self):
        pass

    @abstractmethod
    def exit_extension(self):
        pass
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.exit_extension()
        try:
            os.rmdir(self._results_dir)
        except OSError:
            pass

