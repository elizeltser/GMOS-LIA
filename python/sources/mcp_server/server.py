"""
MCP tool server wrapping ``OperatingPointSession`` for a Claude Code co-worker
searching for the GMOS transistors' optimal operating point.

Launched by ``.mcp.json`` at the repo root; opening a Claude Code session in
this repo auto-connects to it over stdio. Instruments are opened lazily on
the first hardware-touching tool call, not at process startup, so simply
having the server running does not touch the GPIB bus.
"""

import atexit
import logging
import os
import signal
import sys
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp.server.fastmcp import FastMCP

from config import LIAInstrumentConfig
from mcp_server.errors import SessionError
from mcp_server.operating_point_session import OperatingPointSession

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

mcp = FastMCP("gmos-operating-point")
_session: OperatingPointSession | None = None


def _get_session() -> OperatingPointSession:
    global _session
    if _session is None:
        _session = OperatingPointSession()
    return _session


def _tool_result(fn):
    """Call ``fn`` and convert any ``SessionError``/instrument exception into
    a structured ``{"ok": False, ...}`` dict instead of raising into the MCP
    transport or silently logging it away."""
    try:
        result = fn()
    except SessionError as exc:
        return {"ok": False, "error_code": exc.code, "error": str(exc)}
    except Exception as exc:  # pyvisa errors, programming bugs, etc.
        logger.exception("unexpected error in tool call")
        return {"ok": False, "error_code": "internal_error", "error": str(exc)}
    return {"ok": True, **result}


@mcp.tool()
def open_session() -> dict:
    """Open LIA/SCU1/SCU2/PSU and ensure ESD/fan protection is on."""
    return _tool_result(lambda: _get_session().open_instruments())


@mcp.tool()
def configure_signal(
    amplitude_v: float = 5e-3,
    frequency_hz: float = 518.0,
    sensitivity: str | None = None,
    filter_slope: str | None = None,
    time_constant: str | None = None,
) -> dict:
    """Apply LIA excitation/filter settings (amplitude (default 5 mV, hard
    limit 7 mV), frequency (default 518 Hz, read back and returned),
    sensitivity, filter slope, time constant); sensitivity, filter slope and
    time constant left as None keep the codebase default from
    LIAInstrumentConfig. Call once at the start of a session, before
    reading R."""

    def _do():
        import dataclasses

        cfg = LIAInstrumentConfig()
        overrides: dict[str, Any] = {"amplitude": amplitude_v}
        if sensitivity is not None:
            import ATE

            overrides["sensitivity"] = ATE.Sensitivity[sensitivity]
        if filter_slope is not None:
            import ATE

            overrides["filter_slope"] = ATE.FilterSlope[filter_slope]
        if time_constant is not None:
            import ATE

            overrides["time_constant"] = ATE.TimeConstant[time_constant]
        cfg = dataclasses.replace(cfg, **overrides)
        return _get_session().configure_signal(cfg, frequency_hz)

    return _tool_result(_do)


@mcp.tool()
def set_offset(offset_v: float) -> dict:
    """Set the LIA DC reference offset (shared Vgs of both transistors).
    Hard-rejected outside 0.87-1.1V (bounds.py)."""
    return _tool_result(lambda: _get_session().set_offset(offset_v))


@mcp.tool()
def set_drain_voltage(channel: str, voltage_v: float) -> dict:
    """Set SCU1 or SCU2's voltage-source level (drives the transistor drain
    through a 330kOhm series resistor). The resulting measured drain current
    must land in 7-10uA and the derived drain voltage Vd must exceed 120mV;
    otherwise the voltage is rolled back and this call fails."""
    return _tool_result(
        lambda: _get_session().set_drain_voltage(channel, voltage_v)
    )


@mcp.tool()
def read_drain_state(channel: str) -> dict:
    """Read-only spot check of Vscu/Iscu/Vd for SCU1 or SCU2; never rejects."""
    return _tool_result(lambda: _get_session().read_drain_state(channel))


@mcp.tool()
def set_heater_voltage(channel: int, voltage_v: float) -> dict:
    """Set PSU heater voltage on channel 1 or 3. Hard-rejected outside
    2.85-3.1V (bounds.py). Channel 1 heats the SCU1 transistor, channel 3 the
    SCU2 one (config.HEATER_CHANNEL_FOR_SCU)."""
    return _tool_result(
        lambda: _get_session().set_heater_voltage(channel, voltage_v)
    )


@mcp.tool()
def zero_phase(
    n_samples: int = 30,
    sample_interval: float = 2.0,
    sigma_tolerance_deg: float = 0.2,
    max_iterations: int = 5,
) -> dict:
    """Auto-phase repeatedly until the standard deviation of theta across
    n_samples drops below sigma_tolerance_deg (default 0.2deg), up to
    max_iterations attempts."""
    return _tool_result(
        lambda: _get_session().zero_phase(
            n_samples, sample_interval, sigma_tolerance_deg, max_iterations
        )
    )


@mcp.tool()
def read_r(
    n_samples: int = 1,
    sample_interval: float = 0.5,
    force_fresh_snap: bool = False,
) -> dict:
    """On-demand LIA R/theta readout, averaged over n_samples. If a
    continuous monitor is running, served from its latest buffered sample
    unless force_fresh_snap is set."""
    return _tool_result(
        lambda: _get_session().read_r(n_samples, sample_interval, force_fresh_snap)
    )


@mcp.tool()
def start_monitoring(
    sample_interval: float = 1.0,
    drift_window_s: float = 60.0,
    label: str | None = None,
) -> dict:
    """Start continuous R/theta monitoring in a background thread, logging
    to CSV and tracking a live drift-slope fit."""
    return _tool_result(
        lambda: _get_session().start_monitoring(sample_interval, drift_window_s, label)
    )


@mcp.tool()
def monitor_status() -> dict:
    """Non-blocking poll of the running monitor: latest R/theta, elapsed
    time, sample count, and whole-run + windowed drift slopes."""
    return _tool_result(lambda: _get_session().monitor_status())


@mcp.tool()
def note_event(note: str) -> dict:
    """Attach a narrative note (e.g. "trying offset=0.97V") to the monitor's
    next sample row, so the resulting plot/CSV shows when it happened."""
    return _tool_result(lambda: _get_session().note_event(note))


@mcp.tool()
def stop_monitoring(plot: bool = True) -> dict:
    """Stop the running monitor, close its CSV, and optionally render an
    R/theta-vs-time plot with drift-fit overlays and event markers."""
    return _tool_result(lambda: _get_session().stop_monitoring(plot))


@mcp.tool()
def plot_monitor_session() -> dict:
    """Render a plot from the monitor's current buffer without stopping it."""
    return _tool_result(lambda: _get_session().plot_monitor_session())


@mcp.tool()
def snapshot_state() -> dict:
    """Full readback of every live setpoint: offset, both SCU drain
    states (Vscu/Iscu/Vd), and both heater voltages."""
    return _tool_result(lambda: _get_session().snapshot_state())


@mcp.tool()
def close_session() -> dict:
    """De-energize LIA/SCU1/SCU2/PSU and close all instrument handles."""
    return _tool_result(lambda: _get_session().close())


def _shutdown(*_args) -> None:
    if _session is not None:
        try:
            _session.close()
        except Exception:
            logger.exception("error during session shutdown")


atexit.register(_shutdown)
signal.signal(signal.SIGTERM, lambda *_a: (_shutdown(), sys.exit(0)))
signal.signal(signal.SIGINT, lambda *_a: (_shutdown(), sys.exit(0)))


if __name__ == "__main__":
    mcp.run(transport="stdio")
