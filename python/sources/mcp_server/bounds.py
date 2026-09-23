"""
Hard-enforced safety bounds for the operating-point MCP session.

These are physical safety limits on the GMOS transistors under test, not
tunable experiment parameters — they are deliberately plain constants rather
than TOML-configurable fields, so a setpoint outside them is always rejected
rather than silently adjustable by an operator's config file. Non-safety
knobs (sample intervals, sigma tolerance, drift window, settle time) are
exposed as tool parameters instead, with sane defaults.
"""

from .errors import OutOfRangeError

# LIA reference DC offset == shared Vgs of both transistors.
OFFSET_MIN_V = 0.6
OFFSET_MAX_V = 1.1

# LIA excitation amplitude limit (device safety / linear-ish regime).
AMPLITUDE_MAX_V = 0.007

# Target drain current range (measured via SCU, voltage-source mode).
SCU_CURRENT_MIN_A = 7e-6
SCU_CURRENT_MAX_A = 10e-6

# Heater voltage range (PSU ch1 / ch3).
HEATER_MIN_V = 2.8
HEATER_MAX_V = 3.1

# Minimum acceptable drain voltage: Vd = Vscu - SERIES_RESISTANCE_OHM * Iscu.
VD_MIN_V = 0.120
SERIES_RESISTANCE_OHM = 330e3

# How long to wait after a drain-voltage setpoint before measuring Iscu/Vd.
SETTLE_AFTER_SETPOINT_S = 2.0

# Current compliance applied when SCU1/SCU2 are in voltage-source mode; well
# above the 7-10uA target range so it never clips a valid operating point.
SCU_CURRENT_COMPLIANCE_A = 1e-3


def check_range(name: str, value: float, low: float, high: float) -> None:
    """Raise ``OutOfRangeError`` if ``value`` is outside ``[low, high]``."""
    if not (low <= value <= high):
        raise OutOfRangeError(name, value, low, high)
