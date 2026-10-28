"""
Keysight DSO9104A Infiniium Oscilloscope wrapper.

Covers the subset of the Infiniium SCPI command set needed to configure a
channel, acquire a single time-domain record and read it back as calibrated
(time, volts) arrays. Not a full driver: triggering is limited to the
free-run ("auto sweep") mode used for noise/spectrum captures, where the
scope just digitizes continuously without waiting for an edge.
"""

import logging
from typing import Tuple

import numpy as np

from .ate_base import ATEBase

logger = logging.getLogger(__name__)


class DSO9104A(ATEBase):
    def __init__(self, tag: str = 'Scope', rm=None) -> None:  # type: ignore
        super().__init__(tag, rm)

    # ------------------------------------------------------------------
    # Channel configuration
    # ------------------------------------------------------------------

    def set_channel_display(self, channel: int, on: bool = True) -> None:
        self.write(f":CHANnel{channel}:DISPlay {1 if on else 0}")

    def set_channel_scale(self, channel: int, volts_per_div: float) -> None:
        """Vertical scale (V/div)."""
        self.write(f":CHANnel{channel}:SCALe {volts_per_div}")

    def set_channel_range(self, channel: int, volts_full_scale: float) -> None:
        """Full vertical range (V), i.e. 8x the V/div on this scope."""
        self.write(f":CHANnel{channel}:RANGe {volts_full_scale}")

    def set_channel_offset(self, channel: int, offset_v: float) -> None:
        self.write(f":CHANnel{channel}:OFFSet {offset_v}")

    def set_channel_coupling(self, channel: int, coupling: str = "DC") -> None:
        """``coupling``: ``"DC"`` or ``"AC"``."""
        coupling = coupling.upper()
        if coupling not in ("DC", "AC"):
            raise ValueError(f"coupling must be 'DC' or 'AC', got {coupling!r}")
        self.write(f":CHANnel{channel}:COUPling {coupling}")

    def set_channel_impedance(self, channel: int, impedance: str = "ONEMeg") -> None:
        """``impedance``: ``"ONEMeg"`` or ``"FIFTy"``."""
        self.write(f":CHANnel{channel}:IMPedance {impedance}")

    def get_channel_coupling(self, channel: int) -> str:
        return self.query(f":CHANnel{channel}:COUPling?").strip()

    def get_channel_scale(self, channel: int) -> float:
        return float(self.query(f":CHANnel{channel}:SCALe?"))

    def get_channel_offset(self, channel: int) -> float:
        return float(self.query(f":CHANnel{channel}:OFFSet?"))

    # ------------------------------------------------------------------
    # Timebase
    # ------------------------------------------------------------------

    def set_timebase_range(self, seconds: float) -> None:
        """Total displayed time span (s), i.e. 10x the time/div."""
        self.write(f":TIMebase:RANGe {seconds}")

    def set_timebase_position(self, seconds: float) -> None:
        self.write(f":TIMebase:POSition {seconds}")

    def get_timebase_range(self) -> float:
        return float(self.query(":TIMebase:RANGe?"))

    # ------------------------------------------------------------------
    # Acquisition
    # ------------------------------------------------------------------

    def set_acquisition_mode(self, mode: str = "HRESolution") -> None:
        """``mode``: e.g. ``"RTIMe"``, ``"HRESolution"``, ``"PDETect"``,
        ``"AVERage"``."""
        self.write(f":ACQuire:MODE {mode}")

    def set_acquisition_count(self, count: int) -> None:
        """Number of averages, used when acquisition mode is ``AVERage``."""
        self.write(f":ACQuire:COUNt {count}")

    def set_sample_rate(self, hz: float | None) -> None:
        """Analog sample rate (Hz). ``None`` lets the scope pick it (AUTO)."""
        if hz is None:
            self.write(":ACQuire:SRATe:ANALog AUTO")
        else:
            self.write(f":ACQuire:SRATe:ANALog {hz}")

    def set_acquisition_points(self, n: int) -> None:
        """Requested number of time-domain points for the next acquisition."""
        self.write(f":ACQuire:POINts:ANALog {n}")

    def get_sample_rate(self) -> float:
        return float(self.query(":ACQuire:SRATe:ANALog?"))

    # ------------------------------------------------------------------
    # Trigger (free-run / auto-sweep only — sufficient for a noise capture)
    # ------------------------------------------------------------------

    def set_trigger_auto_sweep(self) -> None:
        """Free-run: the scope acquires without waiting for a trigger event."""
        self.write(":TRIGger:SWEep AUTO")

    # ------------------------------------------------------------------
    # Acquisition control
    # ------------------------------------------------------------------

    def digitize(self, channel: int, timeout_ms: int | None = None) -> None:
        """Single-shot acquisition of ``channel``; blocks (via ``*OPC?``)
        until the acquisition completes."""
        if timeout_ms is not None:
            self.resource.timeout = timeout_ms
        self.write(f":DIGitize CHANnel{channel}")
        self.opc()

    def stop(self) -> None:
        self.write(":STOP")

    # ------------------------------------------------------------------
    # Waveform readback
    # ------------------------------------------------------------------

    def get_waveform(self, channel: int) -> Tuple[np.ndarray, np.ndarray]:
        """Read back the most recently digitized record on ``channel``.

        Returns ``(t, v)`` as numpy arrays in seconds / volts, computed from
        the scope's preamble (``:WAVeform:PREamble?``) so the result is
        correctly scaled regardless of the active vertical/horizontal
        settings.
        """
        self.write(f":WAVeform:SOURce CHANnel{channel}")
        self.write(":WAVeform:FORMat WORD")
        self.write(":WAVeform:BYTeorder LSBFirst")
        self.write(":WAVeform:POINts:MODE RAW")

        preamble = self.query(":WAVeform:PREamble?").strip().split(",")
        # Standard Keysight preamble layout:
        # format, type, points, count, xincrement, xorigin, xreference,
        # yincrement, yorigin, yreference
        x_increment = float(preamble[4])
        x_origin = float(preamble[5])
        x_reference = float(preamble[6])
        y_increment = float(preamble[7])
        y_origin = float(preamble[8])
        y_reference = float(preamble[9])

        raw = np.asarray(
            self.resource.query_binary_values(
                ":WAVeform:DATA?", datatype="h", is_big_endian=False
            ),
            dtype=np.float64,
        )
        voltage = (raw - y_reference) * y_increment + y_origin
        index = np.arange(raw.size, dtype=np.float64)
        time = (index - x_reference) * x_increment + x_origin
        logger.debug(
            f"[{self.tag}] read {raw.size} points from CH{channel}, "
            f"dt={x_increment:.3e}s"
        )
        return time, voltage

    def autoscale(self) -> None:
        self.write(":AUToscale")
