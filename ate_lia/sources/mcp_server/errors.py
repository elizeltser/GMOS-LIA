"""
Structured error types for the operating-point MCP session.

Every hardware-touching method in ``operating_point_session`` raises one of
these (or lets a ``pyvisa`` exception propagate) instead of logging and
swallowing failures. The MCP tool wrapper in ``server.py`` catches these at
the boundary and converts them into a structured ``{"ok": False, ...}``
response for the co-worker.
"""


class SessionError(Exception):
    """Base class for all errors raised by the operating-point session."""

    code: str = "session_error"


class OutOfRangeError(SessionError):
    """A setpoint (or a measured outcome tied to one) fell outside its
    hard-enforced safety range."""

    code = "out_of_range"

    def __init__(self, parameter: str, value: float, low: float, high: float):
        self.parameter = parameter
        self.value = value
        self.low = low
        self.high = high
        super().__init__(
            f"{parameter}={value:g} outside allowed range [{low:g}, {high:g}]"
        )


class DrainVoltageError(SessionError):
    """A drain-voltage setpoint left Vd at or below the minimum headroom."""

    code = "drain_voltage_violation"

    def __init__(self, channel: str, vd: float, minimum: float):
        self.channel = channel
        self.vd = vd
        self.minimum = minimum
        super().__init__(
            f"{channel}: Vd={vd:g}V <= minimum {minimum:g}V after settling"
        )


class PhaseZeroError(SessionError):
    """Auto-phase did not converge to a stable theta within the retry budget."""

    code = "phase_zero_failed"

    def __init__(self, iterations: int, last_sigma_deg: float):
        self.iterations = iterations
        self.last_sigma_deg = last_sigma_deg
        super().__init__(
            f"phase auto-zero did not converge after {iterations} iterations "
            f"(last sigma={last_sigma_deg:g} deg)"
        )


class InstrumentIOError(SessionError):
    """An instrument I/O call failed (VISA error, malformed response, etc.)."""

    code = "instrument_io_error"

    def __init__(self, device: str, operation: str, original: Exception):
        self.device = device
        self.operation = operation
        self.original = original
        super().__init__(f"{device}.{operation} failed: {original}")


class MonitorStateError(SessionError):
    """A monitor-control tool was called in an invalid state (e.g. starting
    an already-running monitor, or polling/stopping when none is running)."""

    code = "monitor_state_error"
