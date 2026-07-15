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
from pyvisa.constants import StatusCode
import ATE
from config import ATEConfig

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

    def __init__(self, devices: Dict[str, Any] = None, params: Dict[str, Any] = None,  # type: ignore
                 output_name: str = None, ate_config: ATEConfig = None) -> None:  # type: ignore
        self.devices: Dict[str, Any] = devices or {}
        self.params: Dict[str, Any] = params or {}
        self.output_name: str | None = output_name
        self.ate_config: ATEConfig = ate_config or ATEConfig()
        if self.ate_config.debug_device_io:
            logging.getLogger("ATE.ate_base").setLevel(logging.DEBUG)
            logger.info("Debug device I/O logging enabled: every SCPI write/query will be logged")
        self.results_dir: str = os.path.join('Results', self.__class__.__name__)
        os.makedirs(self.results_dir, exist_ok=True)
        self.rm: pyvisa.ResourceManager = pyvisa.ResourceManager()
        self.snapshot: SetupSnapshot = SetupSnapshot()

    @staticmethod
    def setup_ate(test_method):
        """Ensure ESD protection (PSU ch2) and fan (PSU ch4) are on, and drive
        heater channels (ch1/ch3) if configured. Never issues ``*RST``: that
        would wipe every PSU channel, including heaters the operator may have
        set up manually. Re-asserting voltage/current/output-on for an
        already-enabled channel is a no-op, so this is safe to run every time.
        """
        @wraps(test_method)
        def wrapper(self, *args, **kwargs):
            cfg: ATEConfig = self.ate_config
            logger.info("Ensuring ESD protection (PSU ch2) and fan (PSU ch4) are on")
            psu = self.open_no_reset(ATE.PSU(tag="PSU", rm=self.rm))
            try:
                psu.set_voltage(2, cfg.esd_voltage)
                psu.set_current(2, cfg.esd_current)
                psu.enable_output(2)
                psu.set_voltage(4, cfg.fan_voltage)
                psu.set_current(4, cfg.fan_current)
                psu.enable_output(4)
                for channel, heater in ((1, cfg.heater1), (3, cfg.heater3)):
                    if heater is not None:
                        logger.info(f"Setting heater ch{channel}: {heater.voltage}V / {heater.current}A")
                        psu.set_voltage(channel, heater.voltage)
                        psu.set_current(channel, heater.current)
                        psu.enable_output(channel)
                while psu.opc() != '\n':
                    sleep(0.1)  # Wait for PSU to be ready
                logger.info("PSU ready. Running experiment.")
                result = test_method(self, *args, **kwargs)
                logger.info("Experiment complete.")
            finally:
                psu.resource.close()
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
        """Read a B2962A (SCU) channel's voltage setting, current compliance,
        and measured (actual) current draw."""
        label = label or scu.tag
        settings: Dict[str, Any] = {
            "voltage_V": scu.get_voltage(channel),
            "current_compliance_A": scu.get_current_compliance(channel),
            "measured_current_A": scu.measure_current(channel),
        }
        self.snapshot.add(f"{label}[ch{channel}]", settings)
        return settings

    def snapshot_psu(self, psu: "ATE.PSU", channel: int, label: str = "PSU") -> Dict[str, Any]:
        """Read an HP6624A (PSU) channel's programmed voltage/current compliance,
        and measured (actual) output voltage/current."""
        settings: Dict[str, Any] = {
            "voltage_V": psu.get_programmed_voltage(channel),
            "current_compliance_A": psu.get_programmed_current(channel),
            "measured_voltage_V": psu.get_output_voltage(channel),
            "measured_current_A": psu.get_output_current(channel),
        }
        self.snapshot.add(f"{label}[ch{channel}]", settings)
        return settings

    def open_no_reset(self, device: D, retries: int = 3, retry_delay: float = 2.0) -> D:
        """Open a device's VISA resource without the context manager.

        ``ATEBase.__exit__`` issues ``*RST``; opening the resource manually and
        closing it later without a reset preserves the device's live
        configuration, which is required when snapshotting an already-configured
        instrument (e.g. an active PSU providing ESD protection).

        The VXI-11/TCPIP transport occasionally fails to connect transiently
        (e.g. ``VI_ERROR_RSRC_NFOUND``, RPC portmapper timeouts); retry a few
        times with a short delay before giving up.
        """
        last_exc = pyvisa.errors.VisaIOError(StatusCode.error_resource_not_found)
        for attempt in range(1, retries + 1):
            try:
                device.resource = self.rm.open_resource(device.address)  # type: ignore[assignment]
                device.resource.timeout = 5000
                return device
            except pyvisa.errors.VisaIOError as exc:
                last_exc = exc
                logger.warning(f"VISA open failed for {device.tag} at {device.address} "
                                f"(attempt {attempt}/{retries}): {exc}")
                if attempt < retries:
                    sleep(retry_delay)
        raise last_exc

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
