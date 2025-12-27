import pyvisa
from pyvisa.resources import MessageBasedResource, TCPIPInstrument, Resource
from typing import Union, Optional


class VisaInstrument:

    def __init__(self,
                 visa_resource: Union[MessageBasedResource, TCPIPInstrument],
                 timeout: int = 20000) -> None:
        """Simple, typed wrapper around a pyvisa MessageBasedResource or TCPIPInstrument.
        The wrapper lazily opens the resource in the context manager. Timeout
        is expressed in milliseconds to match pyvisa's API (int or float).
        """
        self._visa_resource = visa_resource
        self._timeout = timeout
        self.reset()

    def reset(self) -> None:
        """Send reset and clear error state of visa device."""
        self.write("*RST; *CLS")

    def write(self, message: str) -> None:
        """Write ASCII/string message to the resource."""
        self._visa_resource.write(message)

    def query(self, message: str) -> str:
        """Query the resource and return a string response."""
        if self._visa_resource is None:
            raise RuntimeError("Resource is not open")
        return str(self._visa_resource.query(message))

    def read_raw(self, size: Optional[int] = None) -> bytes:
        """Read raw bytes from the resource. If `size` is provided, read that many bytes."""
        if size is None:
            return self._visa_resource.read_raw()
        return self._visa_resource.read_raw(size)
