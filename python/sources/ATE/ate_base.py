"""
ATEBase: base class for all ATE device wrappers.
"""

import json
import logging
import os
from typing import TypeVar, Any, Dict, cast

import pyvisa

logger = logging.getLogger(__name__)

T = TypeVar("T", bound="ATEBase")


class ATEBase:
    """
    Base class for ATE devices.
    Handles VISA resource management and device initialization.
    """

    def __init__(self, tag: str, rm: pyvisa.ResourceManager = None) -> None:  # type: ignore
        self.tag: str = tag
        self.address: str = self._get_address(tag)
        self.resource: pyvisa.resources.MessageBasedResource = None  # type: ignore
        if rm is None:
            raise ValueError("ResourceManager must be provided")
        self.rm = rm

    def _get_address(self, tag: str) -> str:
        """Get address from devices.json"""
        devices_file: str = os.path.join(os.path.dirname(__file__), '..', '..', 'devices.json')
        with open(devices_file, 'r') as f:
            devices: Dict[str, str] = json.load(f)
        return devices[tag]

    def __enter__(self: T) -> T:
        logger.debug(f"Opening resource: {self.address} (tag={self.tag})")
        self.resource = cast(pyvisa.resources.MessageBasedResource, self.rm.open_resource(self.address))
        self.resource.timeout = 5000  # 5 seconds
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if self.resource:
            logger.debug(f"Closing resource: {self.address}")
            self.reset()
            self.resource.close()

    def query(self, cmd: str) -> str:
        """Send query command"""
        return self.resource.query(cmd)

    def write(self, cmd: str) -> None:
        """Send write command"""
        logger.debug(f">> {cmd}")
        self.resource.write(cmd)

    def read(self) -> str:
        """Read response"""
        return self.resource.read()

    def reset(self) -> None:
        """Reset device"""
        self.write('*RST')

    def clear_status(self) -> None:
        """Clear status"""
        self.write('*CLS')

    def idn(self) -> str:
        """Get identification"""
        return self.query('*IDN?')

    def opc(self) -> str:
        """Operation complete"""
        return self.query('*OPC?')
