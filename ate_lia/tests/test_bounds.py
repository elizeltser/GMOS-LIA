"""
Tests for mcp_server.bounds's hard-enforced safety range checks.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'python', 'sources'))

from mcp_server import bounds
from mcp_server.errors import OutOfRangeError


def test_check_range_accepts_in_range_value():
    bounds.check_range("offset", 1.0, 0.9, 1.1)  # should not raise


@pytest.mark.parametrize("value", [0.5, 1.5])
def test_check_range_rejects_offset_out_of_range(value):
    with pytest.raises(OutOfRangeError) as exc_info:
        bounds.check_range("offset", value, bounds.OFFSET_MIN_V, bounds.OFFSET_MAX_V)
    assert exc_info.value.code == "out_of_range"
    assert exc_info.value.parameter == "offset"
    assert exc_info.value.value == value
    assert exc_info.value.low == bounds.OFFSET_MIN_V
    assert exc_info.value.high == bounds.OFFSET_MAX_V


@pytest.mark.parametrize("value", [1e-6, 20e-6])
def test_check_range_rejects_scu_current_out_of_range(value):
    with pytest.raises(OutOfRangeError):
        bounds.check_range(
            "scu_current", value, bounds.SCU_CURRENT_MIN_A, bounds.SCU_CURRENT_MAX_A
        )


@pytest.mark.parametrize("value", [2.0, 3.5])
def test_check_range_rejects_heater_voltage_out_of_range(value):
    with pytest.raises(OutOfRangeError):
        bounds.check_range(
            "heater_voltage", value, bounds.HEATER_MIN_V, bounds.HEATER_MAX_V
        )


def test_check_range_accepts_boundary_values():
    bounds.check_range(
        "offset", bounds.OFFSET_MIN_V, bounds.OFFSET_MIN_V, bounds.OFFSET_MAX_V
    )
    bounds.check_range(
        "offset", bounds.OFFSET_MAX_V, bounds.OFFSET_MIN_V, bounds.OFFSET_MAX_V
    )
