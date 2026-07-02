"""
SetupBase: base class for all experiment setups.
"""

import csv
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from functools import wraps
from time import sleep
from typing import Dict, Any, List, TypeVar

import pyvisa
import ATE

logger = logging.getLogger(__name__)

D = TypeVar("D", bound=ATE.ATEBase)


@dataclass
class SetupSnapshot:
    """Snapshot of ATE instrument settings captured at measurement time.

    Settings are stored per device label (e.g. ``"LIA"``, ``"SCU1[ch1]"``) as an
    ordered mapping of setting name -> value. Meant to be stored on
    :class:`SetupBase` and written alongside measurement results.
    """

    devices: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    def add(self, label: str, settings: Dict[str, Any]) -> None:
        """Record (or overwrite) the settings for a device label."""
        self.devices[label] = settings

    def as_lines(self, prefix: str = "") -> List[str]:
        """Render the snapshot as human-readable lines, one setting per line."""
        lines: List[str] = []
        for label, settings in self.devices.items():
            lines.append(f"{prefix}[{label}]")
            for key, value in settings.items():
                lines.append(f"{prefix}  {key} = {value}")
        return lines

    def as_rows(self, width: int = 0) -> List[List[Any]]:
        """Render the snapshot as CSV rows: a device label row followed by one
        ``[setting, value]`` row per setting. If ``width`` is given, rows are
        right-padded with empty cells so they line up with the data columns.
        """
        rows: List[List[Any]] = []
        for label, settings in self.devices.items():
            rows.append([label])
            for key, value in settings.items():
                rows.append([key, value])
        if width > 0:
            rows = [row + [""] * (width - len(row)) for row in rows]
        return rows

    def __str__(self) -> str:
        if not self.devices:
            return "SetupSnapshot(empty)"
        return "\n".join(self.as_lines())


class SetupBase:
    """
    Base class for experiment setups.
    """

    def __init__(self, devices: Dict[str, Any] = None, params: Dict[str, Any] = None, output_name: str = None) -> None:  # type: ignore
        self.devices: Dict[str, Any] = devices or {}
        self.params: Dict[str, Any] = params or {}
        self.output_name: str | None = output_name
        self.results_dir: str = os.path.join('Results', self.__class__.__name__)
        os.makedirs(self.results_dir, exist_ok=True)
        self.rm: pyvisa.ResourceManager = pyvisa.ResourceManager()
        self.snapshot: SetupSnapshot = SetupSnapshot()

    @staticmethod
    def setup_ate(test_method):
        """Setup ATE devices: reset, enable ESD protection, etc."""
        @wraps(test_method)
        def wrapper(self, *args, **kwargs):
            logger.info("Setting up ESD protection (PSU ch2) and fan (PSU ch4)")
            with ATE.PSU(tag="PSU", rm=self.rm) as psu:
                psu.reset()
                # Start ESD protection by setting safe voltages/currents
                psu.set_voltage(2, 5.0)
                psu.set_current(2, 0.7)
                psu.enable_output(2)
                # Start fan power supply
                psu.set_voltage(4, 7.0)
                psu.set_current(4, 1.5)
                psu.enable_output(4)
                while psu.opc() != '\n':
                    sleep(0.1)  # Wait for PSU to be ready
                logger.info("PSU ready. Running experiment.")
                result = test_method(self, *args, **kwargs)
                # After test, disable outputs
                logger.info("Experiment complete. Disabling PSU outputs.")
                psu.reset()
                #psu.disable_output(2)
                #psu.disable_output(4)
            return result
        return wrapper

    @setup_ate
    def run(self) -> None:
        """Run the experiment"""
        raise NotImplementedError

    def snapshot_lia(self, lia: "ATE.LIA", label: str = "LIA") -> Dict[str, Any]:
        """Read the current SR860 (LIA) configuration into ``self.snapshot``.

        Captures amplitude, frequency, phase and the reference DC offset along
        with sensitivity, time constant, input range and filter slope. Enum
        settings are stored as their names for readability.
        """
        settings: Dict[str, Any] = {
            "frequency_Hz": lia.get_frequency(),
            "phase_deg": lia.get_phase(),
            "amplitude_V": lia.get_amplitude(),
            "reference_dc_V": lia.get_offset(),
            "sensitivity": ATE.Sensitivity(lia.get_sensitivity()).name,
            "time_constant": ATE.TimeConstant(lia.get_time_constant()).name,
            "input_range": ATE.InputRange(lia.get_input_range()).name,
            "filter_slope": ATE.FilterSlope(lia.get_filter_slope()).name,
        }
        self.snapshot.add(label, settings)
        return settings

    def snapshot_scu(self, scu: "ATE.SCU", channel: int = 1, label: str = None) -> Dict[str, Any]:  # type: ignore
        """Read a B2962A (SCU) channel's voltage setting and current compliance."""
        label = label or scu.tag
        settings: Dict[str, Any] = {
            "voltage_V": scu.get_voltage(channel),
            "current_compliance_A": scu.get_current_compliance(channel),
        }
        self.snapshot.add(f"{label}[ch{channel}]", settings)
        return settings

    def snapshot_psu(self, psu: "ATE.PSU", channel: int, label: str = "PSU") -> Dict[str, Any]:
        """Read an HP6624A (PSU) channel's programmed voltage and current compliance."""
        settings: Dict[str, Any] = {
            "voltage_V": psu.get_programmed_voltage(channel),
            "current_compliance_A": psu.get_programmed_current(channel),
        }
        self.snapshot.add(f"{label}[ch{channel}]", settings)
        return settings

    def open_no_reset(self, device: D) -> D:
        """Open a device's VISA resource without the context manager.

        ``ATEBase.__exit__`` issues ``*RST``; opening the resource manually and
        closing it later without a reset preserves the device's live
        configuration, which is required when snapshotting an already-configured
        instrument (e.g. an active PSU providing ESD protection).
        """
        device.resource = self.rm.open_resource(device.address)  # type: ignore[assignment]
        device.resource.timeout = 5000
        return device

    def save_results(self, data: Dict[str, List], filename: str, include_snapshot: bool = True) -> str:
        """Save results to CSV.

        If ``include_snapshot`` is set and a setup snapshot has been captured, the
        instrument settings are prepended as CSV rows (a device label row followed
        by ``setting,value`` rows) so the measurement conditions travel with the data.
        """
        stem = self.output_name if self.output_name else f'{filename}_{datetime.now().strftime("%Y%m%d_%H%M%S")}'
        filepath: str = os.path.join(self.results_dir, f'{stem}.csv')
        with open(filepath, 'w', newline='') as f:
            writer = csv.writer(f)
            if include_snapshot and self.snapshot.devices:
                writer.writerows(self.snapshot.as_rows(width=len(data)))
            writer.writerow(list(data.keys()))
            for row in zip(*data.values()):
                writer.writerow(row)
        logger.info(f"Results saved to {filepath}")
        return filepath
